import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
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
        self.assertEqual(tokens[tokens.index('--plugin-shared-input-mode') + 1], 'auto')
        self.assertEqual(tokens[tokens.index('--plugin-shared-input-bytes') + 1], '16777216')
        self.assertEqual(tokens[tokens.index('--plugin-shared-input-deadline') + 1], '20')
        self.assertEqual(tokens[tokens.index('--plugin-shared-input-idle') + 1], '30')
        self.assertEqual(instance._output_definitions({})[0]['parameters'], '-i pipe:0 -maxres 720 -maxbr 2M -maxchan 2 -sdr -deint')
        fields = {f['id']: f for f in instance.fields}
        for slot in (1, 2):
            field = fields[f'stream_{slot}_shared_input_mode']
            self.assertEqual(field['default'], 'auto')
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
                with self.assertRaises(ValueError): instance._stream_definitions({f'stream_1_shared_input_{suffix}': value})
        for option in ('--shared-input', '--shared-input-auto', '--plugin-shared-input-mode'):
            with self.assertRaises(ValueError): instance._stream_definitions({'stream_1_options': option})

    def test_install_persists_defaults_once_without_overwriting_existing_settings(self):
        instance = plugin.Plugin()
        settings = {'stream_1_shared_input_mode': 'off', 'stream_1_options': '-vc h264', 'unrelated': {'keep': True}}
        result = {'message': 'Unchanged'}
        with patch.object(instance, '_install_profiles', return_value=result), patch.object(instance, '_save_normalized_settings') as save:
            instance.run('install_profiles', {}, {'settings': settings})
            saved = save.call_args.args[0]
            self.assertEqual(saved['stream_1_shared_input_mode'], 'off')
            self.assertEqual(saved['stream_1_options'], '-vc h264')
            self.assertEqual(saved['unrelated'], {'keep': True})
            self.assertEqual(saved['stream_2_shared_input_mode'], 'auto')
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
