import copy
import glob
import logging
import os
import re
import shlex
import signal
import subprocess
import threading
import time
from pathlib import Path


PLUGIN_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = PLUGIN_DIR / "ffmpeg-smart.sh"
LAUNCHER_PATH = PLUGIN_DIR / "ffmpeg-smart-plugin.sh"
STATE_DIR = Path(os.environ.get("FFMPEG_SMART_STATE_DIR", "/data/ffmpeg_smart_profiles"))
RUNTIME_DIR = STATE_DIR / "runtime"
PID_FILE = RUNTIME_DIR / "recache.pid"
LOG_FILE = RUNTIME_DIR / "recache.log"
BENCHMARK_LOCK_FILE = STATE_DIR / ".benchmark.lock"
CACHE_FILE = STATE_DIR / ".capabilities.cache"
CACHE_NOTIFICATION_KEY = "ffmpeg-smart-hardware-cache"
logger = logging.getLogger(__name__)


def _repair_script_permissions():
    for script in (SCRIPT_PATH, LAUNCHER_PATH):
        if not script.is_file():
            raise RuntimeError(f"Bundled script is missing: {script}")
        mode = script.stat().st_mode
        if mode & 0o111 != 0o111:
            script.chmod(mode | 0o111)


_repair_script_permissions()


LEGACY_OUTPUT_NAMES = {
    "FFmpeg Smart - Passthrough",
    "FFmpeg Smart - 720p 2M Stereo",
    "FFmpeg Smart - 1080p 8M Stereo",
}
POLICY_DEFAULTS = {
    "stream_1": {"10bit": True, "hdr": True, "sdr": False, "deint": False},
    "stream_2": {"10bit": False, "hdr": False, "sdr": False, "deint": False},
    "output_1": {"10bit": False, "hdr": False, "sdr": True, "deint": True},
    "output_2": {"10bit": False, "hdr": False, "sdr": False, "deint": False},
    "output_3": {"10bit": False, "hdr": False, "sdr": False, "deint": False},
}
ADVANCED_MODE_OPTIONS = [
    {"value": "inherit", "label": "Use FFmpeg Smart default"},
    {"value": "add", "label": "Add to default"},
    {"value": "replace", "label": "Replace default"},
]
MAPPING_MODE_OPTIONS = [
    {"value": "inherit", "label": "First video and optional first audio"},
    {"value": "all", "label": "Map all input streams"},
    {"value": "add", "label": "Add custom mappings to default"},
    {"value": "replace", "label": "Replace default mappings"},
]
ADVANCED_DEFAULT_HELP = {
    "input": "Inherit currently uses: -fflags +genpts+igndts+discardcorrupt -err_detect ignore_err. These run before -i. Replace removes only this managed group; URL, user-agent, reconnect, and hardware setup remain Smart-owned.",
    "mapping": "Inherit currently uses: -map 0:v:0 -map 0:a:0? (first video and optional first audio). Smart requires exactly one mapped video per job; Map all is valid only when the input contains one video.",
    "video": "Inherit is calculated only when video transcodes: -b:v <target> -maxrate <rate> -bufsize <buffer> -g <rounded source fps> -bf <0 or 2> <accelerator tuning> -fps_mode cfr -r <source fps> [-tag:v hvc1]. Target is 8 Mbps at 1080p scaled by output pixels with a 2 Mbps floor; without -maxbr, maxrate is 125% and buffer 200% of target. With -maxbr, target is capped at 85%, maxrate equals the limit, and buffer is 2x the limit. Replace keeps Smart's encoder, filters, color policy, and explicit -maxbr ceiling.",
    "audio": "Inherit is calculated per stream: no audio adds no options; compatible AAC uses -c:a copy; otherwise Smart uses -c:a aac -b:a <rate> -ac <channels> [-ch_layout ...] -af aresample=async=1. Rates are 96k mono, 192k stereo, 384k 5.1, 512k 7.1, or 64k/channel otherwise. An explicit -maxchan ceiling still follows Add or Replace.",
    "mux": "Inherit currently uses: -avoid_negative_ts make_zero -start_at_zero -mpegts_copyts 0 -mpegts_flags +pat_pmt_at_frames+resend_headers -flush_packets 1 -max_muxing_queue_size 4096. Smart always appends -f mpegts pipe:1 after this group.",
}


def policy_fields(
    prefix,
    label,
    *,
    ten_bit_default=False,
    hdr_default=False,
    sdr_default=False,
    deint_default=False,
):
    return [
        {
            "id": f"{prefix}_10bit",
            "label": f"{label}: allow 10-bit",
            "type": "boolean",
            "default": ten_bit_default,
            "help_text": "Unchecked leaves 10-bit on the wrapper's automatic hardware policy.",
        },
        {
            "id": f"{prefix}_hdr",
            "label": f"{label}: allow HDR",
            "type": "boolean",
            "default": hdr_default,
            "help_text": "Force SDR overrides this setting when both are checked.",
        },
        {
            "id": f"{prefix}_sdr",
            "label": f"{label}: force SDR",
            "type": "boolean",
            "default": sdr_default,
            "help_text": "Takes precedence over Allow HDR.",
        },
        {
            "id": f"{prefix}_deint",
            "label": f"{label}: force deinterlace",
            "type": "boolean",
            "default": deint_default,
        },
    ]


def advanced_ffmpeg_fields(prefix, label):
    return [
        {
            "id": f"{prefix}_ffmpeg_input_mode",
            "label": f"{label}: input defaults",
            "type": "select",
            "default": "inherit",
            "options": copy.deepcopy(ADVANCED_MODE_OPTIONS),
            "help_text": ADVANCED_DEFAULT_HELP["input"],
        },
        {
            "id": f"{prefix}_ffmpeg_input_options",
            "label": f"{label}: input options",
            "type": "string",
            "default": "",
            "help_text": "For example: -fflags +discardcorrupt+genpts+nobuffer. Text with Inherit selected is treated as Add.",
        },
        {
            "id": f"{prefix}_ffmpeg_mapping_mode",
            "label": f"{label}: stream mapping",
            "type": "select",
            "default": "inherit",
            "options": copy.deepcopy(MAPPING_MODE_OPTIONS),
            "help_text": ADVANCED_DEFAULT_HELP["mapping"],
        },
        {
            "id": f"{prefix}_ffmpeg_mapping",
            "label": f"{label}: custom stream mappings",
            "type": "string",
            "default": "",
            "help_text": "Use typed mappings such as -map 0:v:0 -map 0:a:0?. Replace must select exactly one video; Add already inherits its one video. Use Map all input streams instead of entering -map 0 here.",
        },
        {
            "id": f"{prefix}_ffmpeg_video_mode",
            "label": f"{label}: video tuning defaults",
            "type": "select",
            "default": "inherit",
            "options": copy.deepcopy(ADVANCED_MODE_OPTIONS),
            "help_text": ADVANCED_DEFAULT_HELP["video"],
        },
        {
            "id": f"{prefix}_ffmpeg_video_options",
            "label": f"{label}: video tuning options",
            "type": "string",
            "default": "",
            "help_text": "For example: -g 60 -keyint_min 60 -sc_threshold 0 -force_key_frames 'expr:gte(t,n_forced*2)'.",
        },
        {
            "id": f"{prefix}_ffmpeg_audio_mode",
            "label": f"{label}: audio defaults",
            "type": "select",
            "default": "inherit",
            "options": copy.deepcopy(ADVANCED_MODE_OPTIONS),
            "help_text": ADVANCED_DEFAULT_HELP["audio"],
        },
        {
            "id": f"{prefix}_ffmpeg_audio_options",
            "label": f"{label}: audio options",
            "type": "string",
            "default": "",
            "help_text": "For example: -c:a ac3 or -c:a aac -b:a 256k.",
        },
        {
            "id": f"{prefix}_ffmpeg_options_mode",
            "label": f"{label}: MPEG-TS/output defaults",
            "type": "select",
            "default": "inherit",
            "options": copy.deepcopy(ADVANCED_MODE_OPTIONS),
            "help_text": ADVANCED_DEFAULT_HELP["mux"],
        },
        {
            "id": f"{prefix}_ffmpeg_options",
            "label": f"{label}: MPEG-TS/output options",
            "type": "string",
            "default": "",
            "help_text": "For example: -mpegts_flags +pat_pmt_at_frames+resend_headers+initial_discontinuity -muxdelay 0. Existing beta.3 values continue here.",
        },
    ]


class Plugin:
    name = "FFmpeg Smart Profiles"
    version = "0.2.0-beta.6"
    description = (
        "Installs FFmpeg Smart stream/output profiles and manages hardware "
        "capacity cache rebuilds."
    )
    author = "matrix2669"
    help_url = "https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin"

    fields = [
        {"id": "stream_1_enabled", "label": "Enable Stream Profile 1", "type": "boolean", "default": True},
        {"id": "stream_1_name", "label": "Stream Profile 1 name", "type": "string", "default": "FFmpeg Smart"},
        *policy_fields(
            "stream_1",
            "Stream Profile 1",
            ten_bit_default=True,
            hdr_default=True,
        ),
        {
            "id": "stream_1_options",
            "label": "Stream Profile 1 options",
            "type": "string",
            "default": "",
            "help_text": "Optional ffmpeg-smart flags, for example: -vc h264 -maxres 1080 -maxbr 8M -maxchan 2",
        },
        *advanced_ffmpeg_fields("stream_1", "Stream Profile 1"),
        {"id": "stream_2_enabled", "label": "Enable Stream Profile 2", "type": "boolean", "default": False},
        {"id": "stream_2_name", "label": "Stream Profile 2 name", "type": "string", "default": ""},
        *policy_fields("stream_2", "Stream Profile 2"),
        {
            "id": "stream_2_options",
            "label": "Stream Profile 2 options",
            "type": "string",
            "default": "",
        },
        *advanced_ffmpeg_fields("stream_2", "Stream Profile 2"),
        {"id": "output_1_enabled", "label": "Enable Output Profile 1", "type": "boolean", "default": True},
        {"id": "output_1_name", "label": "Output Profile 1 name", "type": "string", "default": "FFMpeg Smart - 720p Mobile"},
        *policy_fields(
            "output_1",
            "Output Profile 1",
            sdr_default=True,
            deint_default=True,
        ),
        {"id": "output_1_options", "label": "Output Profile 1 options", "type": "string", "default": "-maxres 720 -maxbr 2M -maxchan 2"},
        *advanced_ffmpeg_fields("output_1", "Output Profile 1"),
        {"id": "output_2_enabled", "label": "Enable Output Profile 2", "type": "boolean", "default": False},
        {"id": "output_2_name", "label": "Output Profile 2 name", "type": "string", "default": ""},
        *policy_fields("output_2", "Output Profile 2"),
        {"id": "output_2_options", "label": "Output Profile 2 options", "type": "string", "default": ""},
        *advanced_ffmpeg_fields("output_2", "Output Profile 2"),
        {"id": "output_3_enabled", "label": "Enable Output Profile 3", "type": "boolean", "default": False},
        {"id": "output_3_name", "label": "Output Profile 3 name", "type": "string", "default": ""},
        *policy_fields("output_3", "Output Profile 3"),
        {"id": "output_3_options", "label": "Output Profile 3 options", "type": "string", "default": ""},
        *advanced_ffmpeg_fields("output_3", "Output Profile 3"),
        {
            "id": "remove_missing_profiles",
            "label": "Remove disabled or renamed managed profiles",
            "type": "boolean",
            "default": True,
        },
        {
            "id": "update_existing",
            "label": "Update existing managed profiles",
            "type": "boolean",
            "default": True,
            "help_text": "Only profiles already pointing to an FFmpeg Smart managed script or matching this plugin's native FFmpeg templates are updated.",
        },
        {
            "id": "flag_reference_video",
            "label": "Other flags: video and limits",
            "type": "info",
            "description": "-vc h264|hevc selects output codec; -maxres 720 limits vertical resolution; -maxbr 2M limits video bitrate; -maxchan 2 limits audio channels.",
        },
        {
            "id": "flag_reference_hardware",
            "label": "Other flags: hardware selection",
            "type": "info",
            "description": "-accel qsv|vaapi|software overrides acceleration; -device, -dri-device, -qsv-device, or -vaapi-device /dev/dri/renderD128 selects a specific device.",
        },
        {
            "id": "flag_reference_policy",
            "label": "Managed policy flags",
            "type": "info",
            "description": "The controls above generate -10bit, -hdr, -sdr, and -deint. Force SDR overrides Allow HDR. If a policy flag is entered in Additional options, Install / Update moves it to the matching checkbox and removes the duplicate.",
        },
        {
            "id": "flag_reference_managed",
            "label": "Input and maintenance flags",
            "type": "info",
            "description": "-i and -user_agent are added by the plugin. Use Rebuild Hardware Cache instead of putting --recache or --recache-only in a profile.",
        },
        {
            "id": "flag_reference_ffmpeg",
            "label": "Advanced FFmpeg Smart options",
            "type": "info",
            "description": "Each profile can inherit, add to, or replace scoped input, video-tuning, audio, and MPEG-TS defaults, plus select default, all-stream, or custom mapping. FFmpeg Smart keeps ownership of the hardware encoder, hardware filters, input, and final MPEG-TS pipe.",
        },
        {
            "id": "profile_note",
            "label": "Profile behavior",
            "type": "info",
            "description": "All managed profiles use the bundled FFmpeg Smart launcher and persistent state in /data/ffmpeg_smart_profiles. A missing or stale capability cache is reported as an ffmpeg-smart error until Rebuild Hardware Cache succeeds.",
        },
    ]

    actions = [
        {
            "id": "install_profiles",
            "label": "Install or Update Profiles",
            "button_label": "Install / Update",
            "button_color": "blue",
            "confirm": {
                "required": True,
                "title": "Install or update profiles?",
                "message": "Adding a new profile requires a full Dispatcharr restart before it can be used. Updates to existing profiles work without a restart. Continue?",
            },
        },
        {
            "id": "rebuild_cache",
            "label": "Rebuild Hardware Cache",
            "button_label": "Start Benchmark",
            "button_color": "orange",
            "confirm": {
                "required": True,
                "title": "Rebuild hardware cache?",
                "message": "This stops active FFmpeg Smart transcodes, blocks new ones until the benchmark finishes, and places a heavy concurrent load on every visible GPU. Proxy-only streams continue running.",
            },
        },
        {"id": "benchmark_status", "label": "Benchmark Status", "button_label": "Check Status"},
        {
            "id": "remove_profiles",
            "label": "Remove Managed Profiles",
            "button_label": "Remove Profiles",
            "button_color": "red",
            "confirm": {
                "required": True,
                "title": "Remove managed profiles?",
                "message": "Removing profiles requires a full Dispatcharr restart before the change fully takes effect. Channels using these profiles may need to be reassigned first. Continue?",
            },
        },
    ]

    def __init__(self):
        self.actions = copy.deepcopy(type(self).actions)
        gpu_count = len(glob.glob("/dev/dri/renderD*"))
        if gpu_count <= 0:
            estimate = "about 1–2 minutes (no DRM GPU detected)"
        elif gpu_count == 1:
            estimate = "about 1–2 minutes for 1 detected GPU"
        else:
            estimate = (
                f"about {gpu_count * 2}–{gpu_count * 4} minutes for "
                f"{gpu_count} detected GPUs"
            )
        for action in self.actions:
            if action.get("id") == "rebuild_cache":
                action["confirm"]["message"] += f" Estimated runtime: {estimate}."
        if os.environ.get("DJANGO_SETTINGS_MODULE"):
            self._sync_cache_notification()

    def run(self, action: str, params: dict, context: dict):
        settings = context.get("settings") or {}
        logger = context.get("logger")
        if action == "install_profiles":
            normalized_settings, normalized_flags = self._normalize_policy_settings(settings)
            result = self._install_profiles(normalized_settings, logger)
            if normalized_flags:
                self._save_normalized_settings(normalized_settings)
                result["normalized_policy_flags"] = normalized_flags
                result["message"] += (
                    " Policy flags were moved from Additional options to their "
                    "checkboxes; refresh the settings page to see the changes."
                )
            return result
        if action == "remove_profiles":
            return self._remove_profiles(settings, logger)
        if action == "rebuild_cache":
            return self._start_recache(logger)
        if action == "benchmark_status":
            return self._benchmark_status()
        return {"status": "error", "message": f"Unknown action: {action}"}

    def stop(self, context: dict):
        pid = self._read_pid()
        if pid and self._pid_is_running(pid):
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    def _stream_definitions(self, settings):
        defaults = {
            1: (True, "FFmpeg Smart", ""),
            2: (False, "", ""),
        }
        definitions = []
        for slot, (enabled, default_name, default_options) in defaults.items():
            if not settings.get(f"stream_{slot}_enabled", enabled):
                continue
            name = str(settings.get(f"stream_{slot}_name") or default_name).strip()
            if not name:
                raise ValueError(f"Stream Profile {slot} name cannot be empty")
            options = self._profile_options(
                settings,
                f"stream_{slot}",
                str(settings.get(f"stream_{slot}_options", default_options) or ""),
                f"Stream Profile {slot} options",
            )
            ffmpeg_options = self._advanced_ffmpeg_parameters(
                settings,
                f"stream_{slot}",
                f"Stream Profile {slot}",
            )
            definitions.append(
                {
                    "name": name,
                    "command": str(LAUNCHER_PATH),
                    "parameters": self._join_parameters(
                        '-i "{streamUrl}" -user_agent "{userAgent}"',
                        options,
                        ffmpeg_options,
                    ),
                    "is_active": True,
                }
            )
        self._validate_unique_names(definitions, "Stream Profile")
        return definitions

    def _output_definitions(self, settings):
        defaults = {
            1: (True, "FFMpeg Smart - 720p Mobile", "-maxres 720 -maxbr 2M -maxchan 2"),
            2: (False, "", ""),
            3: (False, "", ""),
        }
        definitions = []
        for slot, (enabled, default_name, default_options) in defaults.items():
            if not settings.get(f"output_{slot}_enabled", enabled):
                continue
            name = str(settings.get(f"output_{slot}_name") or default_name).strip()
            if not name:
                raise ValueError(f"Output Profile {slot} name cannot be empty")
            options = self._profile_options(
                settings,
                f"output_{slot}",
                str(settings.get(f"output_{slot}_options", default_options) or ""),
                f"Output Profile {slot} options",
            )
            ffmpeg_options = self._advanced_ffmpeg_parameters(
                settings,
                f"output_{slot}",
                f"Output Profile {slot}",
            )
            definitions.append(
                {
                    "name": name,
                    "command": str(LAUNCHER_PATH),
                    "parameters": self._join_parameters("-i pipe:0", options, ffmpeg_options),
                }
            )
        self._validate_unique_names(definitions, "Output Profile")
        return definitions

    @staticmethod
    def _validate_unique_names(definitions, label):
        names = [definition["name"] for definition in definitions]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f"Duplicate {label} name(s): {', '.join(duplicates)}")

    @staticmethod
    def _validate_options(options, label):
        try:
            tokens = shlex.split(options)
        except ValueError as exc:
            raise ValueError(f"{label} contains invalid quoting: {exc}") from exc
        forbidden = {"-i", "--cache-status", "--recache", "--recache-only"}
        invalid = next((token for token in tokens if token in forbidden), None)
        if invalid:
            raise ValueError(f"{label} cannot contain {invalid}")
        return options.strip()

    @staticmethod
    def _advanced_tokens(options, label):
        try:
            return shlex.split(options)
        except ValueError as exc:
            raise ValueError(f"{label} contains invalid quoting: {exc}") from exc

    @staticmethod
    def _advanced_mode(settings, key, label, *, mapping=False):
        mode = str(settings.get(key, "inherit") or "inherit")
        allowed = {"inherit", "add", "replace"}
        if mapping:
            allowed.add("all")
        if mode not in allowed:
            raise ValueError(
                f"{label} mode must be one of: {', '.join(sorted(allowed))}"
            )
        return mode

    @staticmethod
    def _validate_advanced_tokens(scope, tokens, label):
        for token in tokens:
            option = token.split("=", 1)[0]
            audio_codec = (
                option in {"-acodec", "-c:a", "-codec:a"}
                or option.startswith("-c:a:")
                or option.startswith("-codec:a:")
            )
            if audio_codec:
                if scope == "audio":
                    continue
                raise ValueError(f"{label} cannot contain audio option {option}")

            wrapper_owned = (
                option
                in {
                    "-i",
                    "-f",
                    "-map",
                    "-user_agent",
                    "-c",
                    "-codec",
                    "-vcodec",
                    "-device",
                    "-dri-device",
                    "-dri_device",
                    "-qsv-device",
                    "-qsv_device",
                    "-vaapi-device",
                    "-vaapi_device",
                    "-init_hw_device",
                    "-filter_hw_device",
                    "-vf",
                    "-filter",
                    "-filter_complex",
                }
                or option.startswith("-hwaccel")
                or option.startswith("-c:")
                or option.startswith("-codec:")
                or option.startswith("-filter:")
                or option.startswith("-filter_complex")
            )
            if wrapper_owned or token == "pipe:1":
                raise ValueError(
                    f"{label} cannot contain FFmpeg Smart-owned option {option}"
                )

    @classmethod
    def _mapping_specs(cls, options, label):
        tokens = cls._advanced_tokens(options, label)
        if not tokens:
            return []
        if "-map" not in tokens:
            if any(token.startswith("-map") for token in tokens):
                raise ValueError(f"{label} supports only -map <specifier> pairs")
            return tokens

        specs = []
        index = 0
        while index < len(tokens):
            if tokens[index] != "-map" or index + 1 >= len(tokens):
                raise ValueError(f"{label} must contain complete -map <specifier> pairs")
            specs.append(tokens[index + 1])
            index += 2
        return specs

    @staticmethod
    def _validate_mapping_specs(mode, specs, label):
        video_selectors = 0
        for specifier in specs:
            if not specifier:
                raise ValueError(f"{label} cannot contain an empty stream specifier")
            negative = specifier.startswith("-")
            base = specifier[1:] if negative else specifier
            video_selector = (
                base in {"0", "0:v", "0:V", "0:v?", "0:V?"}
                or base.startswith(("0:v:", "0:V:"))
            )
            non_video_selector = bool(
                re.fullmatch(r"0:[asdt](?::.*|\?)?", base)
            )
            if negative and video_selector:
                raise ValueError(
                    f"{label} cannot remove video; FFmpeg Smart requires exactly one mapped video"
                )
            if negative:
                if not non_video_selector:
                    raise ValueError(
                        f"{label} negative mappings must name an audio, subtitle, data, or attachment stream"
                    )
                continue
            if video_selector:
                video_selectors += 1
            elif not non_video_selector:
                raise ValueError(
                    f"{label} positive mappings must use input 0 and an explicit stream type"
                )

        if mode == "add" and video_selectors:
            raise ValueError(
                f"{label} Add already inherits one video and cannot add another video mapping"
            )
        if mode == "replace" and video_selectors != 1:
            raise ValueError(
                f"{label} Replace must contain exactly one positive video mapping"
            )

    @classmethod
    def _advanced_ffmpeg_parameters(cls, settings, prefix, label):
        parameters = []
        groups = (
            ("input", "ffmpeg_input_mode", "ffmpeg_input_options", "-ffmpeg-input"),
            ("video", "ffmpeg_video_mode", "ffmpeg_video_options", "-ffmpeg-video"),
            ("audio", "ffmpeg_audio_mode", "ffmpeg_audio_options", "-ffmpeg-audio"),
            ("mux", "ffmpeg_options_mode", "ffmpeg_options", "-ffmpeg-mux"),
        )

        group_parts = {}
        for scope, mode_suffix, options_suffix, wrapper_prefix in groups:
            scoped_parts = []
            mode = cls._advanced_mode(
                settings,
                f"{prefix}_{mode_suffix}",
                f"{label} {scope}",
            )
            tokens = cls._advanced_tokens(
                str(settings.get(f"{prefix}_{options_suffix}", "") or ""),
                f"{label} {scope} options",
            )
            cls._validate_advanced_tokens(scope, tokens, f"{label} {scope} options")
            if tokens and mode == "inherit":
                mode = "add"
            if mode != "inherit":
                scoped_parts.append(f"{wrapper_prefix}-mode {mode}")
            scoped_parts.extend(
                f"{wrapper_prefix}-option {shlex.quote(token)}" for token in tokens
            )
            group_parts[scope] = scoped_parts

        mapping_mode = cls._advanced_mode(
            settings,
            f"{prefix}_ffmpeg_mapping_mode",
            f"{label} mapping",
            mapping=True,
        )
        mapping_specs = cls._mapping_specs(
            str(settings.get(f"{prefix}_ffmpeg_mapping", "") or ""),
            f"{label} custom mapping",
        )
        if mapping_specs and mapping_mode == "inherit":
            mapping_mode = "add"
        if mapping_mode == "all" and mapping_specs:
            raise ValueError(f"{label} all-stream mapping cannot include custom mappings")
        if mapping_mode == "replace" and not mapping_specs:
            raise ValueError(f"{label} replacement mapping requires at least one -map value")
        cls._validate_mapping_specs(mapping_mode, mapping_specs, f"{label} custom mapping")
        if mapping_mode != "inherit":
            parameters.append(f"-ffmpeg-map-mode {mapping_mode}")
        parameters.extend(
            f"-ffmpeg-map {shlex.quote(specifier)}" for specifier in mapping_specs
        )

        return " ".join(
            (
                *group_parts["input"],
                *parameters,
                *group_parts["video"],
                *group_parts["audio"],
                *group_parts["mux"],
            )
        )

    @staticmethod
    def _normalize_policy_settings(settings):
        normalized = dict(settings or {})
        flag_fields = {
            "-10bit": "10bit",
            "-hdr": "hdr",
            "-sdr": "sdr",
            "-deint": "deint",
            "-deinterlace": "deint",
        }
        moved = []
        for prefix in POLICY_DEFAULTS:
            options_key = f"{prefix}_options"
            options = str(normalized.get(options_key, "") or "")
            try:
                tokens = shlex.split(options)
            except ValueError:
                # The enabled profile's normal validation will report invalid
                # quoting; disabled draft profiles should not block installs.
                continue
            remaining = []
            for token in tokens:
                field_suffix = flag_fields.get(token)
                if field_suffix is None:
                    remaining.append(token)
                    continue
                normalized[f"{prefix}_{field_suffix}"] = True
                moved.append(f"{prefix}:{token}")
            if len(remaining) != len(tokens):
                normalized[options_key] = " ".join(shlex.quote(token) for token in remaining)
        return normalized, moved

    @staticmethod
    def _save_normalized_settings(settings):
        from apps.plugins.models import PluginConfig

        config = PluginConfig.objects.get(key="ffmpeg_smart_profiles")
        config.settings = settings
        config.save(update_fields=["settings", "updated_at"])

    @classmethod
    def _profile_options(cls, settings, prefix, additional_options, label):
        settings, _ = cls._normalize_policy_settings(settings)
        options = cls._validate_options(settings.get(f"{prefix}_options", additional_options), label)
        generated = []
        defaults = POLICY_DEFAULTS[prefix]

        if settings.get(f"{prefix}_10bit", defaults["10bit"]):
            generated.append("-10bit")

        allow_hdr = bool(settings.get(f"{prefix}_hdr", defaults["hdr"]))
        force_sdr = bool(settings.get(f"{prefix}_sdr", defaults["sdr"]))
        if force_sdr:
            generated.append("-sdr")
        elif allow_hdr:
            generated.append("-hdr")

        if settings.get(f"{prefix}_deint", defaults["deint"]):
            generated.append("-deint")

        return " ".join(part for part in (options, *generated) if part)

    @staticmethod
    def _join_parameters(*parts):
        return " ".join(part for part in parts if part).strip()

    @staticmethod
    def _is_managed_script(command):
        return Path(command).name in {SCRIPT_PATH.name, LAUNCHER_PATH.name}

    def _install_profiles(self, settings, logger):
        from django.db import transaction
        from core.models import OutputProfile, StreamProfile

        self._ensure_script()
        update_existing = bool(settings.get("update_existing", True))
        result = {"created": [], "updated": [], "unchanged": [], "removed": [], "conflicts": []}
        stream_definitions = self._stream_definitions(settings)
        output_definitions = self._output_definitions(settings)

        with transaction.atomic():
            for definition in stream_definitions:
                self._upsert_profile(
                    StreamProfile,
                    definition,
                    update_existing,
                    result,
                    managed_command=self._is_managed_script,
                )
            for definition in output_definitions:
                self._upsert_profile(
                    OutputProfile,
                    {**definition, "is_active": True},
                    update_existing,
                    result,
                    managed_command=lambda command, name=definition["name"]: (
                        self._is_managed_script(command)
                        or (name in LEGACY_OUTPUT_NAMES and command == "ffmpeg")
                    ),
                )
            if settings.get("remove_missing_profiles", True):
                desired_stream_names = {definition["name"] for definition in stream_definitions}
                desired_names = {definition["name"] for definition in output_definitions}
                for profile in StreamProfile.objects.all():
                    if not self._is_managed_script(profile.command) or profile.name in desired_stream_names:
                        continue
                    if profile.locked:
                        result["conflicts"].append(f"{profile.name} (locked, disabled or renamed)")
                    else:
                        result["removed"].append(profile.name)
                        profile.delete()
                for profile in OutputProfile.objects.all():
                    legacy = profile.name in LEGACY_OUTPUT_NAMES and profile.command == "ffmpeg"
                    if (not self._is_managed_script(profile.command) and not legacy) or profile.name in desired_names:
                        continue
                    if profile.locked:
                        result["conflicts"].append(f"{profile.name} (locked, disabled or renamed)")
                    else:
                        result["removed"].append(profile.name)
                        profile.delete()

        if logger:
            logger.info("FFmpeg Smart profile install result: %s", result)
        return self._install_result(result)

    @classmethod
    def _install_result(cls, result):
        restart_required = bool(result["created"] or result["removed"])
        message = cls._result_message(result)
        if result["created"]:
            message += " Restart Dispatcharr before using newly added profiles."
        elif result["removed"]:
            message += " Restart Dispatcharr for removed profiles to fully take effect."
        elif result["updated"]:
            message += " Updated profiles are available without restarting Dispatcharr."
        return {
            "status": "ok",
            "message": message,
            "restart_required": restart_required,
            **result,
        }

    @staticmethod
    def _upsert_profile(model, desired, update_existing, result, managed_command):
        matches = list(model.objects.filter(name=desired["name"]).order_by("pk")[:2])
        if len(matches) > 1:
            result["conflicts"].append(f'{desired["name"]} (duplicate names)')
            return
        if not matches:
            model.objects.create(**desired)
            result["created"].append(desired["name"])
            return

        profile = matches[0]
        if profile.locked:
            result["conflicts"].append(f'{desired["name"]} (locked)')
            return
        if not managed_command(profile.command):
            result["conflicts"].append(f'{desired["name"]} (different command)')
            return

        changed = any(getattr(profile, key) != value for key, value in desired.items())
        if not changed:
            result["unchanged"].append(desired["name"])
            return
        if not update_existing:
            result["conflicts"].append(f'{desired["name"]} (updates disabled)')
            return
        for key, value in desired.items():
            setattr(profile, key, value)
        profile.save(update_fields=list(desired))
        result["updated"].append(desired["name"])

    def _remove_profiles(self, settings, logger):
        from django.db import transaction
        from core.models import OutputProfile, StreamProfile

        removed = []
        skipped = []
        with transaction.atomic():
            for profile in StreamProfile.objects.all():
                if not self._is_managed_script(profile.command):
                    continue
                if profile.locked:
                    skipped.append(profile.name)
                else:
                    removed.append(profile.name)
                    profile.delete()
            for profile in OutputProfile.objects.all():
                legacy = profile.name in LEGACY_OUTPUT_NAMES and profile.command == "ffmpeg"
                if not self._is_managed_script(profile.command) and not legacy:
                    continue
                if profile.locked:
                    skipped.append(profile.name)
                else:
                    removed.append(profile.name)
                    profile.delete()
        if logger:
            logger.info("FFmpeg Smart profile removal: removed=%s skipped=%s", removed, skipped)
        return {
            "status": "ok",
            "message": (
                f"Removed {len(removed)} profile(s); skipped {len(skipped)}. "
                "Restart Dispatcharr for the removal to fully take effect."
            ),
            "restart_required": True,
            "removed": removed,
            "skipped": skipped,
        }

    @staticmethod
    def _remove_matching(model, definition, managed_command, removed, skipped):
        for profile in model.objects.filter(name=definition["name"]):
            if profile.locked or not managed_command(profile.command):
                skipped.append(profile.name)
                continue
            profile.delete()
            removed.append(profile.name)

    def _start_recache(self, logger):
        self._ensure_script()
        pid = self._read_pid()
        if pid and self._pid_is_running(pid):
            return {"status": "running", "message": f"Benchmark is already running (PID {pid})."}

        try:
            BENCHMARK_LOCK_FILE.write_text("starting\n", encoding="utf-8")
            stopped = self._stop_active_streams(logger)
            log_handle = LOG_FILE.open("w", encoding="utf-8")
            try:
                process = subprocess.Popen(
                    [str(LAUNCHER_PATH), "--recache-only"],
                    stdin=subprocess.DEVNULL,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    close_fds=True,
                )
            finally:
                log_handle.close()
        except Exception:
            BENCHMARK_LOCK_FILE.unlink(missing_ok=True)
            raise
        PID_FILE.write_text(str(process.pid), encoding="utf-8")
        self._sync_cache_notification()
        threading.Thread(
            target=self._monitor_recache_completion,
            args=(process,),
            name="ffmpeg-smart-cache-notification",
            daemon=True,
        ).start()
        if logger:
            logger.info("Started FFmpeg Smart cache rebuild PID %s", process.pid)
        return {
            "status": "queued",
            "message": (
                f"Stopped {stopped} active transcode stream(s), blocked new FFmpeg "
                f"Smart transcodes, and started the hardware benchmark (PID {process.pid})."
            ),
            "stopped_streams": stopped,
        }

    @classmethod
    def _monitor_recache_completion(cls, process):
        try:
            process.wait()
        finally:
            try:
                from django.db import close_old_connections

                close_old_connections()
                cls._sync_cache_notification()
                close_old_connections()
            except Exception:
                logger.debug(
                    "Could not synchronize FFmpeg Smart cache notification after rebuild",
                    exc_info=True,
                )

    @staticmethod
    def _stop_active_streams(logger):
        from apps.proxy.live_proxy.server import ProxyServer
        from apps.proxy.live_proxy.services.channel_service import ChannelService

        proxy_server = ProxyServer.get_instance()
        redis_client = proxy_server.redis_client
        if not redis_client:
            raise RuntimeError("Redis is unavailable; active streams cannot be stopped safely")

        channel_ids = Plugin._active_transcode_channel_ids(redis_client)
        if not channel_ids:
            return 0

        if logger:
            logger.warning(
                "Stopping %s active Dispatcharr stream(s) before hardware benchmark",
                len(channel_ids),
            )
        ChannelService.stop_channels(channel_ids)

        deadline = time.monotonic() + 15
        remaining = channel_ids
        while remaining and time.monotonic() < deadline:
            active = set(Plugin._active_transcode_channel_ids(redis_client))
            remaining = [channel_id for channel_id in remaining if channel_id in active]
            if remaining:
                time.sleep(0.25)

        if remaining:
            raise RuntimeError(
                "Could not stop all active streams before benchmarking: "
                + ", ".join(remaining)
            )
        return len(channel_ids)

    @staticmethod
    def _active_transcode_channel_ids(redis_client):
        prefix = "live:channel:"
        input_suffix = ":transcode_active"
        output_marker = ":output:mpegts:p"
        output_suffix = ":state"
        channel_ids = set()

        for raw_key in redis_client.scan_iter(match=f"{prefix}*{input_suffix}"):
            key = raw_key.decode() if isinstance(raw_key, bytes) else str(raw_key)
            if key.startswith(prefix) and key.endswith(input_suffix):
                channel_ids.add(key[len(prefix):-len(input_suffix)])

        for raw_key in redis_client.scan_iter(
            match=f"{prefix}*{output_marker}*{output_suffix}"
        ):
            key = raw_key.decode() if isinstance(raw_key, bytes) else str(raw_key)
            if key.startswith(prefix) and output_marker in key and key.endswith(output_suffix):
                channel_ids.add(key[len(prefix):].split(output_marker, 1)[0])

        return sorted(filter(None, channel_ids))

    def _benchmark_status(self):
        pid = self._read_pid()
        running = bool(pid and self._pid_is_running(pid))
        lines = []
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]
        cache_status, cache_detail = self._cache_status()
        capabilities = self._capability_summary()
        if running:
            status = "running"
            message = f"Hardware benchmark is running (PID {pid})."
            if lines:
                message += f" Latest progress: {lines[-1]}"
            if cache_status == "valid" and capabilities:
                message += " Current capabilities while rebuild is active: " + capabilities["summary"]
            elif capabilities:
                message += (
                    f" Previous cached capabilities are not currently usable ({cache_status}): "
                    + capabilities["summary"]
                )
            else:
                message += f" Current cache status: {cache_status}."
        elif cache_status == "valid":
            status = "complete"
            message = "Hardware capability cache is valid for the current FFmpeg Smart version and hardware."
            if capabilities:
                message += " " + capabilities["summary"]
        else:
            status = "error"
            message = cache_detail + " Run Rebuild Hardware Cache before using FFmpeg Smart profiles."
            if capabilities:
                message += " Previous cached capabilities (not usable): " + capabilities["summary"]
        self._sync_cache_notification()
        return {
            "status": status,
            "message": message,
            "pid": pid,
            "cache_status": cache_status,
            "capabilities": capabilities,
            "recent_log": lines,
        }

    @classmethod
    def _cache_notification_state(cls):
        pid = cls._read_pid()
        if pid and cls._pid_is_running(pid):
            return {
                "state": "running",
                "notification_type": "info",
                "priority": "high",
                "title": "FFmpeg Smart hardware scan in progress",
                "message": (
                    "FFmpeg Smart managed streams are temporarily unavailable while "
                    "the hardware cache is rebuilt. New starts may be rejected until "
                    "the scan completes."
                ),
            }

        cache_status, cache_detail = cls._cache_status()
        if cache_status == "valid":
            return None
        return {
            "state": cache_status,
            "notification_type": "warning",
            "priority": "high",
            "title": "FFmpeg Smart hardware scan required",
            "message": (
                f"{cache_detail} Open FFmpeg Smart Profiles in Plugins and run "
                "Rebuild Hardware Cache before using managed profiles."
            ),
        }

    @classmethod
    def _sync_cache_notification(cls):
        try:
            from core.models import SystemNotification
            from core.utils import send_notification_dismissed, send_websocket_notification

            state = cls._cache_notification_state()
            existing = SystemNotification.objects.filter(
                notification_key=CACHE_NOTIFICATION_KEY
            ).first()
            if state is None:
                if existing:
                    existing.delete()
                    send_notification_dismissed(CACHE_NOTIFICATION_KEY)
                return

            previous_state = (existing.action_data or {}).get("cache_status") if existing else None
            notification, created = SystemNotification.objects.update_or_create(
                notification_key=CACHE_NOTIFICATION_KEY,
                defaults={
                    "notification_type": state["notification_type"],
                    "priority": state["priority"],
                    "source": SystemNotification.Source.SYSTEM,
                    "title": state["title"],
                    "message": state["message"],
                    "action_data": {
                        "plugin_key": "ffmpeg_smart_profiles",
                        "plugin_action": "rebuild_cache",
                        "cache_status": state["state"],
                    },
                    "is_active": True,
                    "admin_only": True,
                    "expires_at": None,
                },
            )
            if created or previous_state != state["state"]:
                if not created:
                    notification.dismissals.all().delete()
                send_websocket_notification(notification)
        except Exception:
            logger.debug(
                "Could not synchronize FFmpeg Smart cache notification",
                exc_info=True,
            )

    @staticmethod
    def _cache_status():
        details = {
            "missing": "Hardware capability cache is missing.",
            "invalid": "Hardware capability cache is invalid or unreadable.",
            "stale": "Hardware capability cache does not match the current FFmpeg Smart version or hardware.",
            "unavailable": "Hardware capability cache could not be validated.",
        }
        try:
            result = subprocess.run(
                [str(LAUNCHER_PATH), "--cache-status"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return "unavailable", f"Hardware capability cache could not be validated: {exc}."

        match = re.search(
            r"^FFMPEG_SMART_CACHE_STATUS=(valid|missing|invalid|stale|unavailable)$",
            result.stdout,
            re.MULTILINE,
        )
        if not match:
            detail = (result.stderr or result.stdout).strip().splitlines()
            suffix = f" Wrapper response: {detail[-1]}" if detail else ""
            return "unavailable", details["unavailable"] + suffix
        status = match.group(1)
        if status == "valid" and result.returncode == 0:
            return status, "Hardware capability cache is valid."
        if (status == "valid") != (result.returncode == 0):
            return (
                "unavailable",
                "Hardware capability cache returned an inconsistent validation result.",
            )
        return status, details.get(status, details["unavailable"])

    @staticmethod
    def _capability_summary():
        try:
            values = {}
            for line in CACHE_FILE.read_text(encoding="utf-8").splitlines():
                match = re.fullmatch(r"([A-Z0-9_]+)='(.*)'", line.strip())
                if match:
                    values[match.group(1)] = match.group(2)
        except OSError:
            return None

        accel = values.get("BEST_ACCEL", "unknown")
        codec = values.get("BEST_CODEC", "unknown")
        primary = Plugin._device_capability(values, "PRIMARY")
        secondary = Plugin._device_capability(values, "SECONDARY")
        if not primary and accel == "unknown" and codec == "unknown":
            return None

        decode_10bit = values.get("SUPPORTS_10BIT_DECODE", "false") == "true"
        encode_10bit = values.get("SUPPORTS_10BIT_ENCODE", "false") == "true"
        parts = [
            f"Capabilities: {accel.upper()}/{codec.upper()}",
            f"10-bit decode={'yes' if decode_10bit else 'no'}",
            f"encode={'yes' if encode_10bit else 'no'}",
        ]
        if primary:
            parts.append(
                f"primary {primary['device']} capacity={primary['capacity']} speed={primary['speed']}x"
            )
        if secondary:
            parts.append(
                f"secondary {secondary['device']} capacity={secondary['capacity']} speed={secondary['speed']}x"
            )
        return {
            "acceleration": accel,
            "codec": codec,
            "supports_10bit_decode": decode_10bit,
            "supports_10bit_encode": encode_10bit,
            "primary": primary,
            "secondary": secondary,
            "summary": "; ".join(parts) + ".",
        }

    @staticmethod
    def _device_capability(values, prefix):
        device = values.get(f"{prefix}_DEVICE", "")
        capacity = values.get(f"{prefix}_CAPACITY", "0")
        speed = values.get(f"{prefix}_SPEED", "0")
        if not device or capacity in ("", "0"):
            return None
        return {"device": device, "capacity": int(capacity), "speed": speed}

    @staticmethod
    def _read_pid():
        try:
            value = PID_FILE.read_text(encoding="utf-8").strip()
            return int(value) if value else None
        except (FileNotFoundError, ValueError, OSError):
            return None

    @staticmethod
    def _pid_is_running(pid):
        try:
            stat_fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
            if len(stat_fields) > 2 and stat_fields[2] == "Z":
                return False
            cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ")
            commands = (str(SCRIPT_PATH).encode(), str(LAUNCHER_PATH).encode())
            if not any(command in cmdline for command in commands) or b"--recache-only" not in cmdline:
                return False
            os.kill(pid, 0)
            return True
        except (FileNotFoundError, ProcessLookupError, PermissionError, OSError):
            return False

    @staticmethod
    def _ensure_script():
        _repair_script_permissions()
        try:
            RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
            probe = RUNTIME_DIR / f".write-test-{os.getpid()}-{time.monotonic_ns()}"
            probe.write_text("ok\n", encoding="utf-8")
            probe.unlink()
        except OSError as exc:
            raise RuntimeError(
                f"FFmpeg Smart state directory is not writable: {STATE_DIR}: {exc}"
            ) from exc

    @staticmethod
    def _result_message(result):
        return (
            f"Created {len(result['created'])}, updated {len(result['updated'])}, "
            f"unchanged {len(result['unchanged'])}, removed {len(result['removed'])}, "
            f"conflicts {len(result['conflicts'])}."
        )
