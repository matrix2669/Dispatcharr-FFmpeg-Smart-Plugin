import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'ffmpeg-smart-profiles'))
import plugin


class SharedInputSettingsTests(unittest.TestCase):
    def test_stream_defaults_and_output_pipe_are_independent(self):
        instance = plugin.Plugin()
        tokens = shlex.split(instance._stream_definitions({})[0]['parameters'])
        self.assertEqual(tokens[tokens.index('--plugin-shared-input-mode') + 1], 'off')
        self.assertNotIn('--plugin-shared-input-bytes', tokens)
        self.assertNotIn('--plugin-shared-input-deadline', tokens)
        self.assertNotIn('--plugin-shared-input-idle', tokens)
        auto_tokens = shlex.split(instance._stream_definitions({'stream_1_shared_input_mode': 'auto'})[0]['parameters'])
        self.assertEqual(auto_tokens[auto_tokens.index('--plugin-shared-input-bytes') + 1], '16777216')
        self.assertEqual(auto_tokens[auto_tokens.index('--plugin-shared-input-deadline') + 1], '20')
        self.assertEqual(auto_tokens[auto_tokens.index('--plugin-shared-input-idle') + 1], '30')
        self.assertEqual(instance._output_definitions({})[0]['parameters'], '-i pipe:0 -maxres 720 -maxbr 2M -maxchan 2 -sdr -deint')
        fields = {f['id']: f for f in instance.fields}
        for slot in (1, 2):
            field = fields[f'stream_{slot}_shared_input_mode']
            self.assertEqual(field['default'], 'off')
            self.assertEqual([o['value'] for o in field['options']], ['off', 'auto', 'strict'])
            self.assertIn('does not detect the body format', field['help_text'])
        self.assertFalse(any(key.startswith('output_') and 'shared_input' in key for key in fields))

    def test_modes_limits_and_custom_options_preserve_policy(self):
        instance = plugin.Plugin()
        settings = {'stream_1_shared_input_mode': 'strict', 'stream_1_shared_input_mib': '8', 'stream_1_shared_input_deadline': '12', 'stream_1_shared_input_idle': '15', 'stream_1_options': '-vc h264', 'stream_1_ffmpeg_options': '-metadata service_name=Example'}
        tokens = shlex.split(instance._stream_definitions(settings)[0]['parameters'])
        self.assertEqual(tokens[tokens.index('-vc') + 1], 'h264')
        self.assertEqual(tokens[tokens.index('--plugin-shared-input-mode') + 1], 'strict')
        self.assertEqual(tokens[tokens.index('--plugin-shared-input-bytes') + 1], '8388608')
        self.assertIn('service_name=Example', tokens)
        settings.update(stream_1_shared_input_mode='off', stream_1_shared_input_mib='draft')
        tokens = shlex.split(instance._stream_definitions(settings)[0]['parameters'])
        self.assertIn('off', tokens)
        self.assertNotIn('--plugin-shared-input-bytes', tokens)
        settings.update(stream_1_shared_input_mode='auto', stream_1_shared_input_mib='16', stream_1_ffmpeg_input_options='-headers "Authorization: private"')
        parameters = instance._stream_definitions(settings)[0]['parameters']
        self.assertIn('Authorization: private', parameters)
        settings['stream_1_shared_input_mode'] = 'strict'
        with self.assertRaisesRegex(ValueError, 'does not support custom input options'):
            instance._stream_definitions(settings)

    def test_invalid_modes_and_bounds_fail_before_reconciliation(self):
        instance = plugin.Plugin()
        for suffix, value in (('mode', 'unknown'), ('mib', '0'), ('mib', '1025'), ('mib', '2; touch bad'), ('deadline', '301'), ('idle', '-1')):
            with self.subTest(suffix=suffix, value=value):
                with self.assertRaises(ValueError): instance._stream_definitions({'stream_1_shared_input_mode': 'auto', f'stream_1_shared_input_{suffix}': value})
        for option in ('--shared-input', '--shared-input-auto', '--plugin-shared-input-mode'):
            with self.assertRaises(ValueError): instance._stream_definitions({'stream_1_options': option})

    def test_install_persists_defaults_once_without_overwriting_existing_settings(self):
        instance = plugin.Plugin()
        for mode in ('off', 'auto', 'strict'):
            settings = {'stream_1_shared_input_mode': mode, 'stream_1_options': '-vc h264', 'unrelated': {'keep': True}}
            result = {'message': 'Unchanged'}
            with patch.object(instance, '_install_profiles', return_value=result), patch.object(instance, '_save_normalized_settings') as save:
                instance.run('install_profiles', {}, {'settings': settings})
                saved = save.call_args.args[0]
                self.assertEqual(saved['stream_1_shared_input_mode'], mode)
                self.assertEqual(saved['stream_1_options'], '-vc h264')
                self.assertEqual(saved['unrelated'], {'keep': True})
                self.assertEqual(saved['stream_2_shared_input_mode'], 'off')
                save.reset_mock()
                instance.run('install_profiles', {}, {'settings': saved})
                save.assert_not_called()


class SharedInputLauncherTests(unittest.TestCase):
    def run_launcher(self, args, **environment):
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            shutil.copy2(ROOT / 'ffmpeg-smart-profiles/ffmpeg-smart-plugin.sh', folder / 'ffmpeg-smart-plugin.sh')
            wrapper = folder / 'ffmpeg-smart.sh'
            wrapper.write_text('''#!/usr/bin/env python3
import json, os, sys
print(json.dumps({'args': sys.argv[1:], 'settings': {k: v for k, v in os.environ.items() if k.startswith('FFMPEG_SMART_SHARED_INPUT')}}))
''')
            wrapper.chmod(0o755)
            return subprocess.run([str(folder / 'ffmpeg-smart-plugin.sh'), *args], env=dict(os.environ, **environment), capture_output=True, text=True)

    def test_launcher_maps_mode_and_limits_without_shell_evaluation(self):
        args = ['-i', 'http://user:private@example.invalid/live.ts', '--plugin-shared-input-mode', 'strict', '--plugin-shared-input-bytes', '8388608', '--plugin-shared-input-deadline', '12', '--plugin-shared-input-idle', '15', '-vc', 'h264', '-ffmpeg-mux-option', 'service_name=$(printf injected)']
        result = self.run_launcher(args)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['settings']['FFMPEG_SMART_SHARED_INPUT'], 'true')
        self.assertEqual(payload['settings']['FFMPEG_SMART_SHARED_INPUT_BYTES'], '8388608')
        self.assertEqual(payload['settings']['FFMPEG_SMART_SHARED_INPUT_DEADLINE'], '12')
        self.assertEqual(payload['settings']['FFMPEG_SMART_SHARED_INPUT_IDLE'], '15')
        self.assertEqual(payload['args'], args[:2] + args[10:])
        self.assertEqual(result.stderr, '')
        for mode, expected in (('off', 'false'), ('auto', 'auto')):
            result = self.run_launcher(['-i', 'INPUT', '--plugin-shared-input-mode', mode])
            self.assertEqual(json.loads(result.stdout)['settings']['FFMPEG_SMART_SHARED_INPUT'], expected)

    def test_output_and_maintenance_do_not_inherit_shared_input(self):
        for args in (['-i', 'pipe:0'], ['--recache-only'], ['--cache-status']):
            result = self.run_launcher(args, FFMPEG_SMART_SHARED_INPUT='true')
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload['args'], args)
            self.assertEqual(payload['settings']['FFMPEG_SMART_SHARED_INPUT'], 'false')

    def test_advanced_values_resembling_launcher_flags_remain_values(self):
        args = ['-i', 'INPUT', '-ffmpeg-mux-option', '--plugin-shared-input-mode', '-ffmpeg-mux-option', 'strict']
        result = self.run_launcher(args)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['args'], args)
        self.assertEqual(payload['settings']['FFMPEG_SMART_SHARED_INPUT'], 'false')

    def test_launcher_rejects_missing_invalid_and_out_of_range_values(self):
        for args in (['--plugin-shared-input-mode'], ['--plugin-shared-input-mode', 'private-value'], ['--plugin-shared-input-bytes', '1'], ['--plugin-shared-input-deadline', '301'], ['--plugin-shared-input-idle', '$(touch bad)']):
            result = self.run_launcher(args)
            self.assertEqual(result.returncode, 64)
            self.assertEqual(result.stdout, '')
            self.assertNotIn('private-value', result.stderr)
            self.assertNotIn('$(touch bad)', result.stderr)

    def test_unspecified_settings_preserve_proxy_only_legacy_input(self):
        body = (b'\x47' + bytes(range(187))) * 600
        requests = []
        class RecordingProxy(BaseHTTPRequestHandler):
            def log_message(self, *_args): pass
            def do_GET(self):
                requests.append(self.path)
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        proxy = ThreadingHTTPServer(('127.0.0.1', 0), RecordingProxy)
        threading.Thread(target=proxy.serve_forever, daemon=True).start()
        try:
            with socket.socket() as unused_origin:
                unused_origin.bind(('127.0.0.1', 0))
                source = 'http://127.0.0.1:%d/live.ts' % unused_origin.getsockname()[1]
                # Keep the origin bound but not listening: only the proxy can
                # serve this TS source, so default Auto would break acquisition.
                with TemporaryDirectory() as temp:
                    folder = Path(temp)
                    fake_bin = folder / 'bin'
                    fake_bin.mkdir()
                    ffmpeg = fake_bin / 'ffmpeg'
                    ffmpeg.write_text('''#!/usr/bin/env python3
import sys, urllib.request
if sys.argv[1:] == ['-version']:
    print('ffmpeg version legacy-proxy-fixture'); sys.exit()
with urllib.request.urlopen(sys.argv[sys.argv.index('-i') + 1], timeout=5) as response:
    sys.stdout.buffer.write(response.read())
''')
                    ffmpeg.chmod(0o755)
                    definition = plugin.Plugin()._stream_definitions({})[0]
                    parameters = definition['parameters'].replace('{streamUrl}', source).replace('{userAgent}', 'local-fixture')
                    env = dict(os.environ, PATH=str(fake_bin) + os.pathsep + os.environ['PATH'], FFMPEG_SMART_STATE_DIR=str(folder / 'state'), FFMPEG_SMART_REQUIRE_CACHE='true', FFMPEG_SMART_CACHE_FALLBACK='proxy')
                    for key in list(env):
                        if key.lower() == 'no_proxy': del env[key]
                    address = 'http://127.0.0.1:%d' % proxy.server_port
                    for key in ('http_proxy', 'HTTP_PROXY', 'https_proxy', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY'):
                        env[key] = address
                    result = subprocess.run([definition['command'], *shlex.split(parameters)], env=env, capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, body)
                    self.assertEqual(requests, [source])
                    self.assertNotIn(b'upstream_opens=', result.stderr)
        finally:
            proxy.shutdown()
            proxy.server_close()


class SharedHelperPackagingTests(unittest.TestCase):
    def test_runtime_presence_and_metadata_omission_checks_include_python_helper(self):
        helper = ROOT / 'ffmpeg-smart-profiles/lib/ffsmart-shared-input.py'
        self.assertIn(helper, plugin.RUNTIME_MODULE_PATHS)
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            shutil.copytree(ROOT / 'ffmpeg-smart-profiles', folder / 'ffmpeg-smart-profiles', ignore=shutil.ignore_patterns('__pycache__'))
            (folder / 'scripts').mkdir()
            shutil.copy2(ROOT / 'scripts/check-ffmpeg-smart-source.sh', folder / 'scripts/check-ffmpeg-smart-source.sh')
            metadata_path = folder / 'ffmpeg-smart-profiles/FFMPEG_SMART_SOURCE.json'
            metadata = json.loads(metadata_path.read_text())
            metadata['files'] = [entry for entry in metadata['files'] if entry['path'] != 'lib/ffsmart-shared-input.py']
            metadata_path.write_text(json.dumps(metadata))
            result = subprocess.run([str(folder / 'scripts/check-ffmpeg-smart-source.sh'), '--offline'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('ffsmart-shared-input.py', result.stderr)


class GenericCodecPolicySettingsTests(unittest.TestCase):
    def test_defaults_remain_universal_and_output_has_no_new_controls(self):
        instance = plugin.Plugin()
        tokens = shlex.split(instance._stream_definitions({})[0]['parameters'])
        self.assertEqual(tokens[tokens.index('--copy-codecs') + 1], 'h264,hevc')
        self.assertNotIn('--fallback-codec', tokens)
        fields = {field['id']: field for field in instance.fields}
        for slot in (1, 2):
            self.assertEqual(fields[f'stream_{slot}_copy_codecs']['default'], 'h264,hevc')
            self.assertEqual(fields[f'stream_{slot}_fallback_codec']['default'], 'auto')
        self.assertFalse(any(key.startswith('output_') and ('copy_codecs' in key or 'fallback_codec' in key) for key in fields))
        self.assertNotIn('--copy-codecs', instance._output_definitions({})[0]['parameters'])

    def test_custom_copy_set_fallback_and_explicit_codec_have_independent_tokens(self):
        settings = {'stream_1_copy_codecs': 'h264,mpeg2video', 'stream_1_fallback_codec': 'h264', 'stream_1_options': '-vc hevc -deint'}
        tokens = shlex.split(plugin.Plugin()._stream_definitions(settings)[0]['parameters'])
        self.assertEqual(tokens[tokens.index('--copy-codecs') + 1], 'h264,mpeg2video')
        self.assertEqual(tokens[tokens.index('--fallback-codec') + 1], 'h264')
        self.assertEqual(tokens[tokens.index('-vc') + 1], 'hevc')
        self.assertEqual(tokens.count('-vc'), 1)
        self.assertIn('-deint', tokens)
        outputs = plugin.Plugin()._output_definitions({'output_1_options': '--copy-codecs h264,mpeg2video --fallback-codec h264'})
        self.assertIn('--copy-codecs h264,mpeg2video --fallback-codec h264', outputs[0]['parameters'])

    def test_invalid_lists_and_targets_are_rejected_before_profile_mutation(self):
        instance = plugin.Plugin()
        for value in ('', 'h264,', 'h264,,hevc', 'h264, mpeg2video', 'h264;touch_bad'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                instance._stream_definitions({'stream_1_copy_codecs': value})
        with self.assertRaises(ValueError): instance._stream_definitions({'stream_1_fallback_codec': 'mpeg2video'})
        for option in ('--copy-codecs h264', '--fallback-codec h264'):
            with self.assertRaisesRegex(ValueError, 'codec policy belongs'):
                instance._stream_definitions({'stream_1_options': option})

    def test_persistence_preserves_explicit_values_and_is_idempotent(self):
        instance = plugin.Plugin()
        settings = {'stream_1_copy_codecs': 'h264,mpeg2video', 'stream_1_fallback_codec': 'h264', 'stream_1_options': '-vc hevc', 'unrelated': True}
        with patch.object(instance, '_install_profiles', return_value={'message': 'Unchanged'}), patch.object(instance, '_save_normalized_settings') as save:
            instance.run('install_profiles', {}, {'settings': settings})
            saved = save.call_args.args[0]
            self.assertEqual(saved['stream_1_copy_codecs'], 'h264,mpeg2video')
            self.assertEqual(saved['stream_1_fallback_codec'], 'h264')
            self.assertEqual(saved['stream_1_options'], '-vc hevc')
            self.assertEqual(saved['stream_2_copy_codecs'], 'h264,hevc')
            self.assertEqual(saved['stream_2_fallback_codec'], 'auto')
            save.reset_mock()
            instance.run('install_profiles', {}, {'settings': saved})
            save.assert_not_called()
