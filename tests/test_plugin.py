import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import threading
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ffmpeg-smart-profiles"))

import plugin
from plugin import ADVANCED_DEFAULT_HELP, Plugin


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
    def test_advanced_mode_fields_show_the_inherited_defaults(self):
        suffixes = {
            "ffmpeg_input_mode": "input",
            "ffmpeg_mapping_mode": "mapping",
            "ffmpeg_video_mode": "video",
            "ffmpeg_audio_mode": "audio",
            "ffmpeg_options_mode": "mux",
        }
        fields = {field["id"]: field for field in Plugin.fields}
        for prefix in ("stream_1", "stream_2", "output_1", "output_2", "output_3"):
            for suffix, scope in suffixes.items():
                with self.subTest(prefix=prefix, scope=scope):
                    self.assertEqual(
                        fields[f"{prefix}_{suffix}"]["help_text"],
                        ADVANCED_DEFAULT_HELP[scope],
                    )

    def test_profile_actions_distinguish_creation_updates_and_removal_restarts(self):
        plugin = Plugin()
        actions = {action["id"]: action for action in plugin.actions}

        self.assertTrue(actions["install_profiles"]["confirm"]["required"])
        self.assertIn(
            "Adding a new profile requires a full Dispatcharr restart",
            actions["install_profiles"]["confirm"]["message"],
        )
        self.assertIn(
            "Updates to existing profiles work without a restart",
            actions["install_profiles"]["confirm"]["message"],
        )
        self.assertIn(
            "browser refresh may be needed",
            actions["install_profiles"]["confirm"]["message"],
        )
        self.assertTrue(actions["remove_profiles"]["confirm"]["required"])
        self.assertIn(
            "full Dispatcharr restart",
            actions["remove_profiles"]["confirm"]["message"],
        )

    def test_install_result_requires_restart_only_for_creation_or_removal(self):
        base = {"created": [], "updated": [], "unchanged": [], "removed": [], "conflicts": []}

        created = Plugin._install_result({**base, "created": ["New profile"]})
        updated = Plugin._install_result({**base, "updated": ["Existing profile"]})
        removed = Plugin._install_result({**base, "removed": ["Old profile"]})

        self.assertTrue(created["restart_required"])
        self.assertIn("newly added profiles", created["message"])
        self.assertFalse(updated["restart_required"])
        self.assertIn("without restarting Dispatcharr", updated["message"])
        self.assertTrue(removed["restart_required"])
        self.assertIn("removed profiles", removed["message"])

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
        self.assertTrue(
            all(profile["command"].endswith("ffmpeg-smart-plugin.sh") for profile in streams + outputs)
        )
        self.assertTrue(all(profile["parameters"].startswith("-i") for profile in streams + outputs))
        self.assertEqual(shlex.split(outputs[0]["parameters"])[:2], ["-i", "pipe:0"])
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

    def test_existing_ffmpeg_options_become_mux_additions_and_preserve_boundaries(self):
        plugin = Plugin()
        outputs = plugin._output_definitions(
            {
                "output_1_ffmpeg_options": (
                    "-metadata 'service_name=Mobile feed' -muxdelay 0 "
                    "'; touch /tmp/ffmpeg-smart-must-not-run'"
                ),
                "output_2_enabled": False,
                "output_3_enabled": False,
            }
        )

        tokens = shlex.split(outputs[0]["parameters"])
        passthrough = [
            tokens[index + 1]
            for index, token in enumerate(tokens)
            if token == "-ffmpeg-mux-option"
        ]
        self.assertIn("-ffmpeg-mux-mode", tokens)
        self.assertEqual(tokens[tokens.index("-ffmpeg-mux-mode") + 1], "add")
        self.assertEqual(
            passthrough,
            [
                "-metadata",
                "service_name=Mobile feed",
                "-muxdelay",
                "0",
                "; touch /tmp/ffmpeg-smart-must-not-run",
            ],
        )

    def test_scoped_ffmpeg_options_reject_invalid_quoting(self):
        plugin = Plugin()
        with self.assertRaisesRegex(ValueError, "mux options contains invalid quoting"):
            plugin._stream_definitions({"stream_1_ffmpeg_options": "'unterminated"})

    def test_profile_options_cannot_invoke_cache_maintenance_modes(self):
        plugin = Plugin()
        for option in ("--cache-status", "--recache", "--recache-only"):
            with self.subTest(option=option):
                with self.assertRaisesRegex(ValueError, f"cannot contain {option}"):
                    plugin._stream_definitions({"stream_1_options": option})

    def test_scoped_ffmpeg_options_route_the_advanced_example(self):
        plugin = Plugin()
        stream = plugin._stream_definitions(
            {
                "stream_1_ffmpeg_input_mode": "replace",
                "stream_1_ffmpeg_input_options": "-fflags +discardcorrupt+genpts+nobuffer",
                "stream_1_ffmpeg_mapping_mode": "all",
                "stream_1_ffmpeg_video_mode": "add",
                "stream_1_ffmpeg_video_options": (
                    "-g 60 -keyint_min 60 -sc_threshold 0 "
                    "-force_key_frames 'expr:gte(t,n_forced*2)'"
                ),
                "stream_1_ffmpeg_audio_mode": "replace",
                "stream_1_ffmpeg_audio_options": "-c:a ac3",
                "stream_1_ffmpeg_options_mode": "replace",
                "stream_1_ffmpeg_options": (
                    "-mpegts_flags "
                    "+pat_pmt_at_frames+resend_headers+initial_discontinuity"
                ),
            }
        )[0]

        tokens = shlex.split(stream["parameters"])
        self.assertLess(tokens.index("-ffmpeg-input-mode"), tokens.index("-ffmpeg-map-mode"))
        self.assertLess(tokens.index("-ffmpeg-map-mode"), tokens.index("-ffmpeg-video-mode"))
        self.assertLess(tokens.index("-ffmpeg-video-mode"), tokens.index("-ffmpeg-audio-mode"))
        self.assertLess(tokens.index("-ffmpeg-audio-mode"), tokens.index("-ffmpeg-mux-mode"))
        self.assertIn("expr:gte(t,n_forced*2)", tokens)
        self.assertIn("+pat_pmt_at_frames+resend_headers+initial_discontinuity", tokens)

    def test_custom_mapping_accepts_ffmpeg_map_pairs(self):
        plugin = Plugin()
        output = plugin._output_definitions(
            {
                "output_1_ffmpeg_mapping_mode": "replace",
                "output_1_ffmpeg_mapping": "-map 0:v:0 -map 0:a:0?",
            }
        )[0]

        tokens = shlex.split(output["parameters"])
        self.assertEqual(
            [tokens[index + 1] for index, token in enumerate(tokens) if token == "-ffmpeg-map"],
            ["0:v:0", "0:a:0?"],
        )

    def test_replace_modes_can_intentionally_remove_non_mapping_defaults(self):
        plugin = Plugin()
        stream = plugin._stream_definitions(
            {
                "stream_1_ffmpeg_input_mode": "replace",
                "stream_1_ffmpeg_video_mode": "replace",
                "stream_1_ffmpeg_audio_mode": "replace",
                "stream_1_ffmpeg_options_mode": "replace",
            }
        )[0]

        tokens = shlex.split(stream["parameters"])
        self.assertEqual(tokens.count("replace"), 4)

    def test_scoped_options_reject_smart_owned_structure(self):
        plugin = Plugin()
        cases = (
            {"stream_1_ffmpeg_input_options": "-i other.ts"},
            {"stream_1_ffmpeg_input_options": "-analyzeduration 1000000"},
            {"stream_1_ffmpeg_input_options": "-probesize 1000000"},
            {"stream_1_ffmpeg_video_options": "-c:v copy"},
            {"stream_1_ffmpeg_video_options": "-vf scale=1280:720"},
            {"stream_1_ffmpeg_options": "-f matroska"},
            {"stream_1_ffmpeg_options": "pipe:1"},
        )
        for settings in cases:
            with self.subTest(settings=settings):
                with self.assertRaisesRegex(ValueError, "FFmpeg Smart-owned"):
                    plugin._stream_definitions(settings)

    def test_mapping_modes_reject_incomplete_or_conflicting_values(self):
        plugin = Plugin()
        with self.assertRaisesRegex(ValueError, "complete -map"):
            plugin._stream_definitions(
                {
                    "stream_1_ffmpeg_mapping_mode": "replace",
                    "stream_1_ffmpeg_mapping": "-map",
                }
            )
        with self.assertRaisesRegex(ValueError, "all-stream mapping"):
            plugin._stream_definitions(
                {
                    "stream_1_ffmpeg_mapping_mode": "all",
                    "stream_1_ffmpeg_mapping": "-map 0:v:0",
                }
            )
        with self.assertRaisesRegex(ValueError, "exactly one positive video"):
            plugin._stream_definitions(
                {
                    "stream_1_ffmpeg_mapping_mode": "replace",
                    "stream_1_ffmpeg_mapping": "-map 0:a:0?",
                }
            )
        with self.assertRaisesRegex(ValueError, "already inherits one video"):
            plugin._stream_definitions(
                {
                    "stream_1_ffmpeg_mapping_mode": "add",
                    "stream_1_ffmpeg_mapping": "-map 0:v:1",
                }
            )
        with self.assertRaisesRegex(ValueError, "explicit stream type"):
            plugin._stream_definitions(
                {
                    "stream_1_ffmpeg_mapping_mode": "replace",
                    "stream_1_ffmpeg_mapping": "-map 0:0",
                }
            )

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

    def test_manual_probe_limits_are_removed_from_saved_input_options(self):
        plugin = Plugin()
        normalized, removed = plugin._normalize_adaptive_probe_settings(
            {
                "stream_1_ffmpeg_input_mode": "add",
                "stream_1_ffmpeg_input_options": (
                    "-fflags +discardcorrupt -analyzeduration 1000000 "
                    "-probesize=1000000"
                ),
            }
        )

        self.assertEqual(
            normalized["stream_1_ffmpeg_input_options"],
            "-fflags +discardcorrupt",
        )
        self.assertEqual(
            removed,
            ["stream_1:-analyzeduration", "stream_1:-probesize"],
        )

        malformed, _ = plugin._normalize_adaptive_probe_settings(
            {"stream_1_ffmpeg_input_options": "-analyzeduration -fflags +genpts"}
        )
        self.assertEqual(
            malformed["stream_1_ffmpeg_input_options"],
            "-fflags +genpts",
        )

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
                        "output_2_options": "-maxres 1080 -10bit -hdr -sdr -deinterlace",
                        "output_2_ffmpeg_input_options": (
                            "-analyzeduration 1000000 -probesize 1000000"
                        ),
                    }
                },
            )

        saved = save_settings.call_args.args[0]
        self.assertEqual(saved["output_2_options"], "-maxres 1080")
        self.assertTrue(saved["output_2_10bit"])
        self.assertTrue(saved["output_2_hdr"])
        self.assertTrue(saved["output_2_sdr"])
        self.assertTrue(saved["output_2_deint"])
        self.assertEqual(saved["output_2_ffmpeg_input_options"], "")
        self.assertEqual(
            result["normalized_probe_options"],
            ["output_2:-analyzeduration", "output_2:-probesize"],
        )
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
                patch.object(
                    Plugin,
                    "_cache_status",
                    return_value=(
                        "stale",
                        "Hardware capability cache does not match current hardware.",
                    ),
                ),
            ):
                result = Plugin()._benchmark_status()

        self.assertEqual(result["status"], "running")
        self.assertIn("Latest progress: Testing 18 concurrent streams", result["message"])
        self.assertIn("Previous cached capabilities are not currently usable (stale)", result["message"])

    def test_stale_cache_is_error_even_when_previous_log_completed(self):
        capabilities = {"summary": "Capabilities: VAAPI/HEVC."}
        with TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "recache.log"
            log_file.write_text("[ffmpeg-smart] Cache rebuild complete\n", encoding="utf-8")
            with (
                patch.object(Plugin, "_read_pid", return_value=None),
                patch.object(
                    Plugin,
                    "_cache_status",
                    return_value=(
                        "stale",
                        "Hardware capability cache does not match the current FFmpeg Smart version or hardware.",
                    ),
                ),
                patch.object(Plugin, "_capability_summary", return_value=capabilities),
                patch("plugin.LOG_FILE", log_file),
            ):
                result = Plugin()._benchmark_status()

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["cache_status"], "stale")
        self.assertIn("Status check completed. Hardware recheck required", result["message"])
        self.assertIn("does not match", result["message"])
        self.assertIn("Run Rebuild Hardware Cache", result["message"])
        self.assertIn("Previous cached capabilities (not usable)", result["message"])

    def test_valid_cache_is_complete_without_a_plugin_rebuild_log(self):
        with TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "missing-recache.log"
            with (
                patch.object(Plugin, "_read_pid", return_value=None),
                patch.object(
                    Plugin,
                    "_cache_status",
                    return_value=("valid", "Hardware capability cache is valid."),
                ),
                patch.object(Plugin, "_capability_summary", return_value=None),
                patch("plugin.LOG_FILE", log_file),
            ):
                result = Plugin()._benchmark_status()

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["cache_status"], "valid")
        self.assertIn("valid for the current", result["message"])

    def test_cache_status_uses_wrapper_machine_status(self):
        cases = (
            (0, "valid", "valid"),
            (78, "missing", "missing"),
            (78, "invalid", "invalid"),
            (78, "stale", "stale"),
        )
        for returncode, marker, expected in cases:
            with self.subTest(marker=marker):
                completed = subprocess.CompletedProcess(
                    args=[],
                    returncode=returncode,
                    stdout=f"FFMPEG_SMART_CACHE_STATUS={marker}\n",
                    stderr="",
                )
                with patch("plugin.subprocess.run", return_value=completed) as run:
                    status, _ = Plugin._cache_status()

                self.assertEqual(status, expected)
                self.assertEqual(
                    run.call_args.args[0],
                    [str(plugin.LAUNCHER_PATH), "--cache-status"],
                )

    def test_cache_status_rejects_inconsistent_wrapper_result(self):
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=78,
            stdout="FFMPEG_SMART_CACHE_STATUS=valid\n",
            stderr="",
        )
        with patch("plugin.subprocess.run", return_value=completed):
            status, detail = Plugin._cache_status()

        self.assertEqual(status, "unavailable")
        self.assertIn("inconsistent", detail)


class CacheNotificationTests(unittest.TestCase):
    def test_notification_state_distinguishes_required_running_and_valid(self):
        with (
            patch.object(Plugin, "_read_pid", return_value=1234),
            patch.object(Plugin, "_pid_is_running", return_value=True),
        ):
            running = Plugin._cache_notification_state()
        self.assertEqual(running["state"], "running")
        self.assertIn("acceleration bypassed", running["title"])
        self.assertIn("scan is in progress", running["message"])

        with (
            patch.object(Plugin, "_read_pid", return_value=None),
            patch.object(
                Plugin,
                "_cache_status",
                return_value=("stale", "Hardware capability cache is stale."),
            ),
        ):
            stale = Plugin._cache_notification_state()
        self.assertEqual(stale["state"], "stale")
        self.assertIn("acceleration bypassed", stale["title"])
        self.assertIn("basic FFmpeg stream copy", stale["message"])

        with (
            patch.object(Plugin, "_read_pid", return_value=None),
            patch.object(
                Plugin,
                "_cache_status",
                return_value=("valid", "Hardware capability cache is valid."),
            ),
        ):
            self.assertIsNone(Plugin._cache_notification_state())

    def test_persistent_notification_is_created_and_cleared(self):
        class FakeDismissals:
            def __init__(self):
                self.delete_count = 0

            def all(self):
                return self

            def delete(self):
                self.delete_count += 1

        class FakeNotification:
            def __init__(self, manager, notification_key, defaults):
                self.manager = manager
                self.id = 1
                self.notification_key = notification_key
                self.created_at = None
                self.dismissals = FakeDismissals()
                self.apply(defaults)

            def apply(self, defaults):
                for key, value in defaults.items():
                    setattr(self, key, value)

            def delete(self):
                self.manager.current = None

        class FakeManager:
            def __init__(self):
                self.current = None

            def filter(self, **kwargs):
                self.key = kwargs["notification_key"]
                return self

            def first(self):
                return self.current

            def update_or_create(self, notification_key, defaults):
                created = self.current is None
                if created:
                    self.current = FakeNotification(self, notification_key, defaults)
                else:
                    self.current.apply(defaults)
                self.defaults = defaults
                self.key = notification_key
                return self.current, created

        manager = FakeManager()
        models_module = types.ModuleType("core.models")
        notification_class = type(
            "SystemNotification",
            (),
            {"objects": manager, "Source": type("Source", (), {"SYSTEM": "system"})},
        )
        models_module.SystemNotification = notification_class
        refreshes = []
        cleared = []
        utils_module = types.ModuleType("core.utils")
        utils_module.send_websocket_update = lambda *args: refreshes.append(args)
        utils_module.send_notification_dismissed = cleared.append
        core_module = types.ModuleType("core")

        with patch.dict(
            sys.modules,
            {"core": core_module, "core.models": models_module, "core.utils": utils_module},
        ):
            with patch.object(
                Plugin,
                "_cache_notification_state",
                return_value={
                    "state": "stale",
                    "notification_type": "warning",
                    "priority": "high",
                    "title": "FFmpeg Smart hardware scan required",
                    "message": "Run the hardware scan.",
                },
            ):
                Plugin._sync_cache_notification()

            self.assertEqual(manager.key, plugin.CACHE_NOTIFICATION_KEY)
            self.assertEqual(manager.defaults["action_data"]["cache_status"], "stale")
            self.assertTrue(manager.defaults["admin_only"])
            self.assertEqual(manager.current.dismissals.delete_count, 1)
            self.assertEqual(
                refreshes[-1],
                ("updates", "update", {"type": "notifications_cleared"}),
            )

            Plugin._sync_cache_notification()
            self.assertEqual(manager.current.dismissals.delete_count, 2)
            self.assertEqual(len(refreshes), 2)

            with patch.object(
                Plugin,
                "_cache_notification_state",
                return_value={
                    "state": "stale",
                    "notification_type": "warning",
                    "priority": "high",
                    "title": "FFmpeg Smart hardware acceleration bypassed",
                    "message": "Run the hardware scan.",
                },
            ):
                Plugin._sync_cache_notification(fallback_token="fallback-1")
                self.assertEqual(manager.current.dismissals.delete_count, 3)
                self.assertEqual(len(refreshes), 3)

                Plugin._sync_cache_notification(fallback_token="fallback-1")
                self.assertEqual(manager.current.dismissals.delete_count, 3)
                self.assertEqual(len(refreshes), 3)

                Plugin._sync_cache_notification(fallback_token="fallback-2")
                self.assertEqual(manager.current.dismissals.delete_count, 4)
                self.assertEqual(len(refreshes), 4)
                self.assertEqual(
                    manager.defaults["action_data"]["fallback_token"],
                    "fallback-2",
                )

            with patch.object(Plugin, "_cache_notification_state", return_value=None):
                Plugin._sync_cache_notification()

        self.assertIsNone(manager.current)
        self.assertEqual(cleared, [plugin.CACHE_NOTIFICATION_KEY])
        self.assertEqual(len(refreshes), 5)

    def test_fallback_marker_syncs_only_new_invocation_tokens(self):
        with (
            patch.object(
                Plugin,
                "_read_fallback_marker",
                side_effect=["fallback-1", "fallback-1", "fallback-2"],
            ),
            patch.object(Plugin, "_sync_cache_notification") as sync,
        ):
            token = Plugin._sync_fallback_marker(None)
            token = Plugin._sync_fallback_marker(token)
            token = Plugin._sync_fallback_marker(token)

        self.assertEqual(token, "fallback-2")
        self.assertEqual(
            [call.kwargs for call in sync.call_args_list],
            [
                {"fallback_token": "fallback-1"},
                {"fallback_token": "fallback-2"},
            ],
        )

    def test_notification_watcher_is_singleton_and_stops_cleanly(self):
        entered = threading.Event()

        def wait_for_stop(stop_event):
            entered.set()
            stop_event.wait(5)

        with patch.object(Plugin, "_watch_fallback_invocations", side_effect=wait_for_stop):
            Plugin._start_notification_watcher()
            self.assertTrue(entered.wait(1))
            first_thread = Plugin._notification_watcher_thread
            Plugin._start_notification_watcher()
            self.assertIs(Plugin._notification_watcher_thread, first_thread)
            Plugin._stop_notification_watcher()

        self.assertFalse(first_thread.is_alive())
        self.assertIsNone(Plugin._notification_watcher_thread)


class PersistentStateTests(unittest.TestCase):
    def test_default_state_is_outside_replaceable_plugin_directory(self):
        import plugin

        self.assertEqual(plugin.STATE_DIR, Path("/data/ffmpeg_smart_profiles"))
        self.assertEqual(plugin.CACHE_FILE, plugin.STATE_DIR / ".capabilities.cache")
        self.assertEqual(plugin.BENCHMARK_LOCK_FILE, plugin.STATE_DIR / ".benchmark.lock")
        self.assertEqual(plugin.RUNTIME_DIR, plugin.STATE_DIR / "runtime")

    def test_legacy_and_launcher_commands_are_managed(self):
        self.assertTrue(Plugin._is_managed_script("/old/plugin/ffmpeg-smart.sh"))
        self.assertTrue(Plugin._is_managed_script("/new/plugin/ffmpeg-smart-plugin.sh"))
        self.assertFalse(Plugin._is_managed_script("/bin/bash"))
        self.assertFalse(Plugin._is_managed_script("ffmpeg"))

    def test_plugin_load_repairs_install_modes_before_direct_launcher_use(self):
        source_dir = REPO_ROOT / "ffmpeg-smart-profiles"
        with TemporaryDirectory() as temp_dir:
            plugin_dir = Path(temp_dir) / "plugin"
            state_dir = Path(temp_dir) / "state"
            plugin_dir.mkdir()
            plugin_path = plugin_dir / "plugin.py"
            launcher = plugin_dir / "ffmpeg-smart-plugin.sh"
            wrapper = plugin_dir / "ffmpeg-smart.sh"
            shutil.copyfile(source_dir / plugin_path.name, plugin_path)
            shutil.copyfile(source_dir / launcher.name, launcher)
            shutil.copyfile(source_dir / wrapper.name, wrapper)
            launcher.chmod(0o644)
            wrapper.chmod(0o644)

            fake_bin = Path(temp_dir) / "bin"
            fake_bin.mkdir()
            fake_ffmpeg = fake_bin / "ffmpeg"
            fake_ffmpeg.write_text("#!/bin/bash\nprintf 'proxy output\\n'\n", encoding="utf-8")
            fake_ffmpeg.chmod(0o755)

            spec = importlib.util.spec_from_file_location("installed_mode_repair_test", plugin_path)
            installed_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(installed_module)

            self.assertEqual(wrapper.stat().st_mode & 0o777, 0o755)
            self.assertEqual(launcher.stat().st_mode & 0o777, 0o755)
            environment = os.environ.copy()
            environment["FFMPEG_SMART_STATE_DIR"] = str(state_dir)
            environment["PATH"] = f"{fake_bin}{os.pathsep}{environment['PATH']}"
            result = subprocess.run(
                [str(launcher), "-i", "/unavailable/input.ts"],
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            marker_exists = (state_dir / "runtime" / "fallback-invocation").is_file()

        self.assertEqual(result.returncode, 0)
        self.assertIn("[ffmpeg-smart] WARNING [degraded-proxy]", result.stderr)
        self.assertIn("proxy output", result.stdout)
        self.assertTrue(marker_exists)

    def test_launcher_enables_degraded_proxy_and_invocation_marker(self):
        launcher = (REPO_ROOT / "ffmpeg-smart-profiles" / "ffmpeg-smart-plugin.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("FFMPEG_SMART_CACHE_FALLBACK", launcher)
        self.assertIn("FFMPEG_SMART_FALLBACK_MARKER", launcher)
        self.assertIn("runtime/fallback-invocation", launcher)

    def test_script_check_repairs_execute_bits(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            wrapper = temp_path / "ffmpeg-smart.sh"
            launcher = temp_path / "ffmpeg-smart-plugin.sh"
            runtime = temp_path / "state" / "runtime"
            wrapper.write_text("#!/bin/bash\n", encoding="utf-8")
            launcher.write_text("#!/bin/bash\n", encoding="utf-8")
            wrapper.chmod(0o644)
            launcher.chmod(0o644)
            with (
                patch("plugin.SCRIPT_PATH", wrapper),
                patch("plugin.LAUNCHER_PATH", launcher),
                patch("plugin.STATE_DIR", runtime.parent),
                patch("plugin.RUNTIME_DIR", runtime),
            ):
                Plugin._ensure_script()

            self.assertEqual(wrapper.stat().st_mode & 0o777, 0o755)
            self.assertEqual(launcher.stat().st_mode & 0o777, 0o755)


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
        self.assertEqual(
            [field["id"] for field in Plugin.fields],
            [field["id"] for field in manifest["fields"]],
        )
        self.assertEqual(Plugin.fields, manifest["fields"])
        self.assertEqual(
            [action["id"] for action in Plugin.actions],
            [action["id"] for action in manifest["actions"]],
        )
        install_action = next(
            action for action in manifest["actions"] if action["id"] == "install_profiles"
        )
        self.assertEqual(
            next(action for action in Plugin.actions if action["id"] == "install_profiles")[
                "confirm"
            ]["message"],
            install_action["confirm"]["message"],
        )

    def test_runtime_files_use_stable_plugin_directory(self):
        runtime_dir = REPO_ROOT / "ffmpeg-smart-profiles"

        for filename in (
            "FFMPEG_SMART_SOURCE.json",
            "ffmpeg-smart-plugin.sh",
            "ffmpeg-smart.sh",
            "plugin.json",
            "plugin.py",
        ):
            self.assertTrue((runtime_dir / filename).is_file(), filename)

    def test_bundled_wrapper_copies_mapped_auxiliary_streams(self):
        wrapper = (
            REPO_ROOT / "ffmpeg-smart-profiles" / "ffmpeg-smart.sh"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "MAPPED_AUXILIARY_CODEC_ARGS=(-c:s copy -c:d copy -c:t copy)",
            wrapper,
        )
        self.assertEqual(
            wrapper.count('"${MAPPED_AUXILIARY_CODEC_ARGS[@]}"'),
            2,
        )

    def test_bundled_wrapper_keeps_benchmark_lock_owner_scoped(self):
        wrapper = (
            REPO_ROOT / "ffmpeg-smart-profiles" / "ffmpeg-smart.sh"
        ).read_text(encoding="utf-8")

        self.assertIn('[[ "${BASH_SUBSHELL:-0}" -eq 0 ]] || return 0', wrapper)
        self.assertIn('BENCHMARK_LOCK_OWNER_PID="$$"', wrapper)
        self.assertIn("trap cleanup_benchmark_lock EXIT", wrapper)


if __name__ == "__main__":
    unittest.main()
