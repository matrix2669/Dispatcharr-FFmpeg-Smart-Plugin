import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ffmpeg-smart-profiles"))

from plugin import Plugin


REPO_ROOT = Path(__file__).resolve().parents[1]


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
    def test_profile_actions_warn_that_dispatcharr_restart_is_required(self):
        plugin = Plugin()
        actions = {action["id"]: action for action in plugin.actions}

        self.assertTrue(actions["install_profiles"]["confirm"]["required"])
        self.assertIn(
            "full Dispatcharr restart",
            actions["install_profiles"]["confirm"]["message"],
        )
        self.assertTrue(actions["remove_profiles"]["confirm"]["required"])
        self.assertIn(
            "full Dispatcharr restart",
            actions["remove_profiles"]["confirm"]["message"],
        )

    def test_benchmark_confirmation_estimates_from_detected_gpu_count(self):
        with patch("plugin.glob.glob", return_value=["renderD128", "renderD129"]):
            plugin = Plugin()

        rebuild = next(action for action in plugin.actions if action["id"] == "rebuild_cache")
        self.assertIn("4–8 minutes for 2 detected GPUs", rebuild["confirm"]["message"])

    def test_defaults_create_mobile_stream_and_output_profiles(self):
        plugin = Plugin()

        streams = plugin._stream_definitions({})
        outputs = plugin._output_definitions({})

        self.assertEqual([profile["name"] for profile in streams], ["FFmpeg Smart"])
        self.assertIn("-10bit", streams[0]["parameters"])
        self.assertIn("-hdr", streams[0]["parameters"])
        self.assertEqual([profile["name"] for profile in outputs], ["FFMpeg Smart - 720p Mobile"])
        self.assertTrue(all(profile["command"].endswith("ffmpeg-smart.sh") for profile in outputs))
        self.assertTrue(all(profile["parameters"].startswith("-i pipe:0") for profile in outputs))
        self.assertIn("-maxres 720 -maxbr 2M -maxchan 2", outputs[0]["parameters"])
        self.assertIn("-sdr", outputs[0]["parameters"])
        self.assertIn("-deint", outputs[0]["parameters"])

    def test_slots_can_be_disabled_renamed_and_reconfigured(self):
        plugin = Plugin()
        settings = {
            "stream_1_enabled": False,
            "stream_2_enabled": True,
            "stream_2_name": "Mobile Stream",
            "stream_2_options": "-vc h264 -maxres 720",
            "output_1_enabled": False,
            "output_2_enabled": True,
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

    def test_policy_checkboxes_generate_flags_and_sdr_overrides_hdr(self):
        plugin = Plugin()
        outputs = plugin._output_definitions(
            {
                "output_1_10bit": True,
                "output_1_hdr": True,
                "output_1_sdr": True,
                "output_1_deint": True,
                "output_2_enabled": False,
                "output_3_enabled": False,
            }
        )

        parameters = outputs[0]["parameters"]
        self.assertIn("-10bit", parameters)
        self.assertIn("-sdr", parameters)
        self.assertNotIn("-hdr", parameters)
        self.assertIn("-deint", parameters)

    def test_legacy_policy_flags_are_absorbed_by_checkbox_defaults(self):
        plugin = Plugin()
        normalized, moved = plugin._normalize_policy_settings(
            {"stream_1_options": "-10bit -hdr -maxres 1080"}
        )
        streams = plugin._stream_definitions(
            {"stream_1_options": "-10bit -hdr -maxres 1080"}
        )
        outputs = plugin._output_definitions(
            {"output_1_options": "-maxres 720 -sdr -deint"}
        )

        self.assertEqual(streams[0]["parameters"].count("-10bit"), 1)
        self.assertEqual(streams[0]["parameters"].count("-hdr"), 1)
        self.assertEqual(outputs[0]["parameters"].count("-sdr"), 1)
        self.assertEqual(outputs[0]["parameters"].count("-deint"), 1)
        self.assertEqual(normalized["stream_1_options"], "-maxres 1080")
        self.assertTrue(normalized["stream_1_10bit"])
        self.assertTrue(normalized["stream_1_hdr"])
        self.assertEqual(moved, ["stream_1:-10bit", "stream_1:-hdr"])

    def test_install_persists_normalized_policy_controls(self):
        plugin = Plugin()
        install_result = {
            "status": "ok",
            "message": "Installed profiles. Restart Dispatcharr.",
        }
        with (
            patch.object(plugin, "_install_profiles", return_value=install_result),
            patch.object(plugin, "_save_normalized_settings") as save_settings,
        ):
            result = plugin.run(
                "install_profiles",
                {},
                {
                    "settings": {
                        "output_2_options": "-maxres 1080 -10bit -hdr -sdr -deinterlace"
                    }
                },
            )

        saved = save_settings.call_args.args[0]
        self.assertEqual(saved["output_2_options"], "-maxres 1080")
        self.assertTrue(saved["output_2_10bit"])
        self.assertTrue(saved["output_2_hdr"])
        self.assertTrue(saved["output_2_sdr"])
        self.assertTrue(saved["output_2_deint"])
        self.assertIn("refresh the settings page", result["message"])


class CapabilityStatusTests(unittest.TestCase):
    def test_summarizes_cached_primary_and_secondary_capabilities(self):
        cache = "\n".join(
            [
                "BEST_ACCEL='vaapi'",
                "BEST_CODEC='hevc'",
                "SUPPORTS_10BIT_DECODE='true'",
                "SUPPORTS_10BIT_ENCODE='true'",
                "PRIMARY_DEVICE='/dev/dri/renderD129'",
                "PRIMARY_SPEED='14'",
                "PRIMARY_CAPACITY='18'",
                "SECONDARY_DEVICE='/dev/dri/renderD128'",
                "SECONDARY_SPEED='9.62'",
                "SECONDARY_CAPACITY='15'",
            ]
        )
        with TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / ".capabilities.cache"
            cache_path.write_text(cache, encoding="utf-8")
            with patch("plugin.CACHE_FILE", cache_path):
                summary = Plugin._capability_summary()

        self.assertEqual(summary["acceleration"], "vaapi")
        self.assertEqual(summary["primary"]["capacity"], 18)
        self.assertEqual(summary["secondary"]["capacity"], 15)
        self.assertIn("VAAPI/HEVC", summary["summary"])

    def test_missing_cache_returns_none(self):
        with patch("plugin.CACHE_FILE", Path("/definitely/missing/cache")):
            self.assertIsNone(Plugin._capability_summary())

    def test_running_status_includes_progress_and_cached_capabilities(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pid_file = temp_path / "recache.pid"
            log_file = temp_path / "recache.log"
            cache_file = temp_path / ".capabilities.cache"
            pid_file.write_text("1234", encoding="utf-8")
            log_file.write_text("Testing 18 concurrent streams for 10s...\n", encoding="utf-8")
            cache_file.write_text(
                "BEST_ACCEL='vaapi'\nBEST_CODEC='hevc'\n",
                encoding="utf-8",
            )
            with (
                patch("plugin.PID_FILE", pid_file),
                patch("plugin.LOG_FILE", log_file),
                patch("plugin.CACHE_FILE", cache_file),
                patch.object(Plugin, "_pid_is_running", return_value=True),
            ):
                result = Plugin()._benchmark_status()

        self.assertEqual(result["status"], "running")
        self.assertIn("Latest progress: Testing 18 concurrent streams", result["message"])
        self.assertIn("Cached capabilities while rebuild is active", result["message"])


class ReleaseMetadataTests(unittest.TestCase):
    def test_all_version_sources_agree(self):
        version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        manifest = json.loads(
            (REPO_ROOT / "ffmpeg-smart-profiles" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(version, Plugin.version)
        self.assertEqual(version, manifest["version"])

    def test_runtime_files_use_stable_plugin_directory(self):
        runtime_dir = REPO_ROOT / "ffmpeg-smart-profiles"

        for filename in (
            "FFMPEG_SMART_SOURCE.json",
            "ffmpeg-smart.sh",
            "plugin.json",
            "plugin.py",
        ):
            self.assertTrue((runtime_dir / filename).is_file(), filename)


if __name__ == "__main__":
    unittest.main()
