import unittest

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


if __name__ == "__main__":
    unittest.main()
