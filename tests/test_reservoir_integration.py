"""Local end-to-end settings/launcher fixture; no external streams or services."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'ffmpeg-smart-profiles'))
import plugin


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class ReservoirIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory()
        cls.path = Path(cls.temp.name)
        fixture = cls.path / 'source.ts'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
                        'testsrc2=size=160x90:rate=25', '-f', 'lavfi', '-i',
                        'sine=frequency=1000:sample_rate=48000', '-t', '4',
                        '-c:v', 'mpeg2video', '-c:a', 'aac', '-f', 'mpegts', str(fixture)],
                       check=True, timeout=15)
        cls.body = fixture.read_bytes()
        cls.requests = []
        class Source(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_GET(self):
                cls.requests.append(self.path)
                self.send_response(200)
                self.send_header('Content-Type', 'video/mp2t')
                self.send_header('Content-Length', str(len(cls.body)))
                self.end_headers()
                try: self.wfile.write(cls.body)
                except (BrokenPipeError, ConnectionResetError): pass
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Source)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.temp.cleanup()

    def test_generated_http_stream_settings_launch(self):
        instance = plugin.Plugin()
        for rate in ('off', '1.05', '1.10'):
            with self.subTest(rate=rate):
                definition = instance._stream_definitions({'stream_1_reservoir_rate': rate})[0]
                params = definition['parameters'].replace('{streamUrl}',
                    f'http://127.0.0.1:{self.server.server_port}/source.ts').replace('{userAgent}', 'local-test')
                args = shlex.split(params)
                if rate == 'off': self.assertNotIn('--plugin-stream-reservoir-rate', args)
                else: self.assertEqual(args[args.index('--plugin-stream-reservoir-rate') + 1], rate)
                env = dict(os.environ, FFMPEG_SMART_STATE_DIR=str(self.path / ('state-' + rate)),
                           FFMPEG_SMART_REQUIRE_CACHE='true', FFMPEG_SMART_CACHE_FALLBACK='proxy',
                           NO_PROXY='127.0.0.1,localhost', no_proxy='127.0.0.1,localhost')
                before = len(self.requests)
                result = subprocess.run([definition['command'], *args], env=env,
                                        capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
                self.assertGreater(len(self.requests), before)
                self.assertGreater(len(result.stdout), 188)
                self.assertEqual(result.stdout[0], 0x47)
                marker = b'stream-reservoir rate='
                if rate == 'off': self.assertNotIn(marker, result.stderr)
                else: self.assertIn(marker + rate.encode(), result.stderr)

    def test_output_and_invalid_settings(self):
        instance = plugin.Plugin()
        self.assertNotIn('reservoir', instance._output_definitions({})[0]['parameters'])
        for bad in ('1', '1.2', 'true', ''):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                instance._stream_definitions({'stream_1_reservoir_rate': bad})
        with self.assertRaises(ValueError):
            instance._output_definitions({'output_1_reservoir_rate': '1.05'})


if __name__ == '__main__':
    unittest.main()
