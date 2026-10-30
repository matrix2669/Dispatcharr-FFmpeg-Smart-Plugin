import json
import os
from pathlib import Path
import shlex
import shutil
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'ffmpeg-smart-profiles'))
import plugin


class SimplifiedProfileSettingsTests(unittest.TestCase):
    def test_blank_copy_default_and_removed_ui_have_no_generated_tuning(self):
        instance = plugin.Plugin()
        fields = {f['id']: f for f in instance.fields}
        for slot in (1, 2):
            self.assertEqual(fields[f'stream_{slot}_copy_codecs']['default'], '')
            self.assertIn('preferred codec', fields[f'stream_{slot}_copy_codecs']['help_text'])
        self.assertFalse(any('shared_input' in key or key.endswith('_fallback_codec') for key in fields))
        tokens = shlex.split(instance._stream_definitions({})[0]['parameters'])
        self.assertEqual(tokens[tokens.index('--copy-codecs') + 1], 'preferred')
        self.assertFalse(any(token.startswith('--plugin-shared-input') for token in tokens))
        self.assertNotIn('--fallback-codec', tokens)
        self.assertEqual(instance._output_definitions({})[0]['parameters'], '-i pipe:0 -maxres 720 -maxbr 2M -maxchan 2 -sdr -deint')

    def test_whitespace_case_and_mpeg2_alias_preserve_explicit_codec(self):
        instance = plugin.Plugin()
        settings = {'stream_1_copy_codecs': ' H264, MPEG2VIDEO ', 'stream_1_options': '-vc hevc -deint'}
        tokens = shlex.split(instance._stream_definitions(settings)[0]['parameters'])
        self.assertEqual(tokens[tokens.index('--copy-codecs') + 1], 'h264,mpeg2')
        self.assertEqual(tokens[tokens.index('-vc') + 1], 'hevc')
        self.assertEqual(tokens.count('-vc'), 1)
        self.assertNotIn('--fallback-codec', tokens)
        tokens = shlex.split(instance._stream_definitions({'stream_1_copy_codecs': '   '})[0]['parameters'])
        self.assertEqual(tokens[tokens.index('--copy-codecs') + 1], 'preferred')

    def test_malformed_lists_are_rejected_before_profile_reconciliation(self):
        instance = plugin.Plugin()
        for value in ('h264,', ',h264', 'h264,,mpeg2', 'h2 64', 'h264;touch_bad', 'preferred', 'preferred,h264'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                instance._stream_definitions({'stream_1_copy_codecs': value})
        for options in ('--copy-codecs h264', '--fallback-codec h264'):
            with self.assertRaises(ValueError): instance._stream_definitions({'stream_1_options': options})

    def test_retired_settings_and_old_csv_migrate_once_with_visible_report(self):
        instance = plugin.Plugin()
        settings = {'stream_1_copy_codecs': ' H264, MPEG2VIDEO ', 'stream_1_fallback_codec': 'h264', 'stream_1_shared_input_mode': 'strict', 'stream_1_shared_input_mib': '8', 'stream_1_shared_input_deadline': '12', 'stream_1_shared_input_idle': '15', 'stream_1_options': '-vc hevc', 'unrelated': {'keep': True}}
        with patch.object(instance, '_install_profiles', side_effect=lambda *_: {'message': 'Unchanged'}), patch.object(instance, '_save_normalized_settings') as save:
            result = instance.run('install_profiles', {}, {'settings': settings})
            saved = save.call_args.args[0]
            self.assertEqual(saved['stream_1_copy_codecs'], 'h264,mpeg2')
            self.assertEqual(saved['stream_2_copy_codecs'], '')
            self.assertEqual(saved['stream_1_options'], '-vc hevc')
            self.assertEqual(saved['unrelated'], {'keep': True})
            self.assertFalse(any('shared_input' in key or key.endswith('_fallback_codec') for key in saved))
            self.assertIn('stream_1_fallback_codec', result['retired_profile_settings'])
            self.assertIn('stream_1_shared_input_mode', result['retired_profile_settings'])
            self.assertIn('conversion overrides were removed', result['message'])
            save.reset_mock()
            result = instance.run('install_profiles', {}, {'settings': saved})
            save.assert_not_called()
            self.assertNotIn('retired_profile_settings', result)

    def test_old_explicit_lists_and_output_expert_arguments_remain_supported(self):
        instance = plugin.Plugin()
        normalized, changed, retired = instance._normalize_simplified_settings({'stream_1_copy_codecs': 'h264,hevc', 'stream_2_copy_codecs': ''})
        self.assertEqual(normalized['stream_1_copy_codecs'], 'h264,hevc')
        self.assertEqual(changed, [])
        self.assertEqual(retired, [])
        options = '--copy-codecs h264,mpeg2video --fallback-codec h264'
        self.assertIn(options, instance._output_definitions({'output_1_options': options})[0]['parameters'])


class AutomaticInputLauncherTests(unittest.TestCase):
    def run_launcher(self, args, **environment):
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            shutil.copy2(ROOT / 'ffmpeg-smart-profiles/ffmpeg-smart-plugin.sh', folder / 'ffmpeg-smart-plugin.sh')
            wrapper = folder / 'ffmpeg-smart.sh'
            wrapper.write_text("""#!/usr/bin/env python3
import json, os, sys
print(json.dumps({'args': sys.argv[1:], 'settings': {k: v for k, v in os.environ.items() if k.startswith('FFMPEG_SMART_SHARED_INPUT')}}))
""")
            wrapper.chmod(0o755)
            return subprocess.run([str(folder / 'ffmpeg-smart-plugin.sh'), *args], env=dict(os.environ, **environment), capture_output=True, text=True)

    def test_http_is_automatic_with_fixed_bounds_and_literal_argument_boundaries(self):
        args = ['-i', 'https://source.invalid/live.ts', '-vc', 'h264', '-ffmpeg-mux-option', 'service_name=$(printf injected)']
        result = self.run_launcher(args, FFMPEG_SMART_SHARED_INPUT_BYTES='1', FFMPEG_SMART_SHARED_INPUT_DEADLINE='999', FFMPEG_SMART_SHARED_INPUT_IDLE='999')
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['args'], args)
        self.assertEqual(payload['settings'], {'FFMPEG_SMART_SHARED_INPUT': 'auto', 'FFMPEG_SMART_SHARED_INPUT_BYTES': '67108864', 'FFMPEG_SMART_SHARED_INPUT_DEADLINE': '10', 'FFMPEG_SMART_SHARED_INPUT_IDLE': '30'})
        self.assertEqual(result.stderr, '')

    def test_pipe_non_http_and_maintenance_keep_existing_input(self):
        for args in (['-i', 'pipe:0'], ['-i', 'rtsp://source.invalid/live'], ['--recache-only'], ['--cache-status']):
            result = self.run_launcher(args, FFMPEG_SMART_SHARED_INPUT='true')
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload['args'], args)
            self.assertEqual(payload['settings']['FFMPEG_SMART_SHARED_INPUT'], 'false')

    def test_old_profile_selector_arguments_are_consumed_but_fixed_policy_applies(self):
        args = ['-i', 'https://source.invalid/live.ts', '--plugin-shared-input-mode', 'off', '--plugin-shared-input-bytes', '8388608', '--plugin-shared-input-deadline', '12', '--plugin-shared-input-idle', '15']
        result = self.run_launcher(args)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['args'], args[:2])
        self.assertEqual(payload['settings']['FFMPEG_SMART_SHARED_INPUT'], 'auto')
        self.assertEqual(payload['settings']['FFMPEG_SMART_SHARED_INPUT_BYTES'], '67108864')
        self.assertEqual(payload['settings']['FFMPEG_SMART_SHARED_INPUT_DEADLINE'], '10')
        self.assertEqual(payload['settings']['FFMPEG_SMART_SHARED_INPUT_IDLE'], '30')

    def test_advanced_values_resembling_old_launcher_selectors_remain_values(self):
        args = ['-i', 'INPUT', '-ffmpeg-mux-option', '--plugin-shared-input-mode', '-ffmpeg-mux-option', 'strict']
        result = self.run_launcher(args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['args'], args)

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
