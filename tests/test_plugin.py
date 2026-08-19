import unittest
from unittest.mock import patch

from plugin import Plugin


class FakeRedis:
    def __init__(self, keys):
        self.keys = keys

    def scan_iter(self, match):
        if match.endswith(":transcode_active"):
            suffix = ":transcode_active"
            return iter(key for key in self.keys if key.decode().endswith(suffix))
        marker = ":output:mpegts:p"
        suffix = ":state"
        return iter(
            key
            for key in self.keys
            if marker in key.decode() and key.decode().endswith(suffix)
        )


class ActiveTranscodeSelectionTests(unittest.TestCase):
    def test_selects_input_and_output_transcodes_but_not_proxy_only_streams(self):
        redis_client = FakeRedis(
            [
                b"live:channel:input-transcode:transcode_active",
                b"live:channel:output-transcode:output:mpegts:p4:state",
                b"live:channel:proxy-only:metadata",
            ]
        )

        self.assertEqual(
            Plugin._active_transcode_channel_ids(redis_client),
            ["input-transcode", "output-transcode"],
        )

    def test_deduplicates_channels_with_input_and_output_transcodes(self):
        redis_client = FakeRedis(
            [
                b"live:channel:both:transcode_active",
                b"live:channel:both:output:mpegts:p2:state",
            ]
        )

        self.assertEqual(Plugin._active_transcode_channel_ids(redis_client), ["both"])


class ProfileDefinitionTests(unittest.TestCase):
    def test_benchmark_confirmation_estimates_from_detected_gpu_count(self):
        with patch("plugin.glob.glob", return_value=["renderD128", "renderD129"]):
            plugin = Plugin()

        rebuild = next(action for action in plugin.actions if action["id"] == "rebuild_cache")
        self.assertIn("4–8 minutes for 2 detected GPUs", rebuild["confirm"]["message"])

    def test_defaults_create_one_stream_and_three_script_output_profiles(self):
        plugin = Plugin()

        streams = plugin._stream_definitions({})
        outputs = plugin._output_definitions({})

        self.assertEqual([profile["name"] for profile in streams], ["FFmpeg Smart"])
        self.assertEqual(len(outputs), 3)
        self.assertTrue(all(profile["command"].endswith("ffmpeg-smart.sh") for profile in outputs))
        self.assertTrue(all(profile["parameters"].startswith("-i pipe:0") for profile in outputs))

    def test_slots_can_be_disabled_renamed_and_reconfigured(self):
        plugin = Plugin()
        settings = {
            "stream_1_enabled": False,
            "stream_2_enabled": True,
            "stream_2_name": "Mobile Stream",
            "stream_2_options": "-vc h264 -maxres 720",
            "output_1_enabled": False,
            "output_2_name": "Mobile Output",
            "output_2_options": "-vc h264 -maxres 480 -maxbr 1M",
            "output_3_enabled": False,
        }

        streams = plugin._stream_definitions(settings)
        outputs = plugin._output_definitions(settings)

        self.assertEqual(streams[0]["name"], "Mobile Stream")
        self.assertIn("-maxres 720", streams[0]["parameters"])
        self.assertEqual(outputs[0]["name"], "Mobile Output")
        self.assertIn("-maxbr 1M", outputs[0]["parameters"])


if __name__ == "__main__":
    unittest.main()
