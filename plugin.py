import copy
import glob
import os
import re
import shlex
import signal
import subprocess
import time
from pathlib import Path


PLUGIN_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = PLUGIN_DIR / "ffmpeg-smart.sh"
RUNTIME_DIR = PLUGIN_DIR / "runtime"
PID_FILE = RUNTIME_DIR / "recache.pid"
LOG_FILE = RUNTIME_DIR / "recache.log"
BENCHMARK_LOCK_FILE = PLUGIN_DIR / ".benchmark.lock"
CACHE_FILE = PLUGIN_DIR / ".capabilities.cache"
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


class Plugin:
    name = "FFmpeg Smart Profiles"
    version = "0.1.0-dev.7"
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
            "help_text": "Additional flags, for example: -vc h264 -maxres 1080 -maxbr 8M -maxchan 2",
        },
        {"id": "stream_2_enabled", "label": "Enable Stream Profile 2", "type": "boolean", "default": False},
        {"id": "stream_2_name", "label": "Stream Profile 2 name", "type": "string", "default": ""},
        *policy_fields("stream_2", "Stream Profile 2"),
        {
            "id": "stream_2_options",
            "label": "Stream Profile 2 options",
            "type": "string",
            "default": "",
        },
        {"id": "output_1_enabled", "label": "Enable Output Profile 1", "type": "boolean", "default": True},
        {"id": "output_1_name", "label": "Output Profile 1 name", "type": "string", "default": "FFMpeg Smart - 720p Mobile"},
        *policy_fields(
            "output_1",
            "Output Profile 1",
            sdr_default=True,
            deint_default=True,
        ),
        {"id": "output_1_options", "label": "Output Profile 1 options", "type": "string", "default": "-maxres 720 -maxbr 2M -maxchan 2"},
        {"id": "output_2_enabled", "label": "Enable Output Profile 2", "type": "boolean", "default": False},
        {"id": "output_2_name", "label": "Output Profile 2 name", "type": "string", "default": ""},
        *policy_fields("output_2", "Output Profile 2"),
        {"id": "output_2_options", "label": "Output Profile 2 options", "type": "string", "default": ""},
        {"id": "output_3_enabled", "label": "Enable Output Profile 3", "type": "boolean", "default": False},
        {"id": "output_3_name", "label": "Output Profile 3 name", "type": "string", "default": ""},
        *policy_fields("output_3", "Output Profile 3"),
        {"id": "output_3_options", "label": "Output Profile 3 options", "type": "string", "default": ""},
        {
            "id": "remove_missing_profiles",
            "label": "Remove disabled or renamed managed profiles",
            "type": "boolean",
            "default": True,
        },
        {"id": "update_existing", "label": "Update existing managed profiles", "type": "boolean", "default": True},
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
            "id": "profile_note",
            "label": "Profile behavior",
            "type": "info",
            "description": "All managed Stream and Output Profiles use the bundled ffmpeg-smart.sh. Output Profiles use its pipe-safe input mode.",
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
                "message": "Installing or updating profiles requires a full Dispatcharr restart before the profiles can be used. Continue?",
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
            definitions.append(
                {
                    "name": name,
                    "command": str(SCRIPT_PATH),
                    "parameters": self._join_parameters(
                        '-i "{streamUrl}" -user_agent "{userAgent}"', options
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
            definitions.append(
                {
                    "name": name,
                    "command": str(SCRIPT_PATH),
                    "parameters": self._join_parameters("-i pipe:0", options),
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
        forbidden = {"-i", "--recache", "--recache-only"}
        invalid = next((token for token in tokens if token in forbidden), None)
        if invalid:
            raise ValueError(f"{label} cannot contain {invalid}")
        return options.strip()

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
    def _join_parameters(base, options):
        return f"{base} {options}".strip()

    @staticmethod
    def _is_managed_script(command):
        return Path(command).name == SCRIPT_PATH.name

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
        return {
            "status": "ok",
            "message": self._result_message(result) + " Restart Dispatcharr before using these profiles.",
            "restart_required": True,
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
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        pid = self._read_pid()
        if pid and self._pid_is_running(pid):
            return {"status": "running", "message": f"Benchmark is already running (PID {pid})."}

        try:
            BENCHMARK_LOCK_FILE.write_text("starting\n", encoding="utf-8")
            stopped = self._stop_active_streams(logger)
            log_handle = LOG_FILE.open("w", encoding="utf-8")
            try:
                process = subprocess.Popen(
                    [str(SCRIPT_PATH), "--recache-only"],
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
        if running:
            status = "running"
            message = f"Hardware benchmark is running (PID {pid})."
            if lines:
                message += f" Latest progress: {lines[-1]}"
        elif lines and any("Cache rebuild complete" in line for line in lines):
            status = "complete"
            message = "Hardware cache rebuild completed successfully."
        elif lines:
            status = "error"
            message = "Hardware benchmark is not running and did not report successful completion."
        else:
            status = "idle"
            message = "No hardware benchmark has been started by this plugin."
        capabilities = self._capability_summary()
        if capabilities:
            label = "Cached capabilities while rebuild is active: " if running else ""
            message += " " + label + capabilities["summary"]
        elif not running:
            message += " No valid hardware capability cache is available."
        return {
            "status": status,
            "message": message,
            "pid": pid,
            "capabilities": capabilities,
            "recent_log": lines,
        }

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
            if str(SCRIPT_PATH).encode() not in cmdline or b"--recache-only" not in cmdline:
                return False
            os.kill(pid, 0)
            return True
        except (FileNotFoundError, ProcessLookupError, PermissionError, OSError):
            return False

    @staticmethod
    def _ensure_script():
        if not SCRIPT_PATH.is_file():
            raise RuntimeError(f"Bundled script is missing: {SCRIPT_PATH}")
        SCRIPT_PATH.chmod(SCRIPT_PATH.stat().st_mode | 0o111)

    @staticmethod
    def _result_message(result):
        return (
            f"Created {len(result['created'])}, updated {len(result['updated'])}, "
            f"unchanged {len(result['unchanged'])}, removed {len(result['removed'])}, "
            f"conflicts {len(result['conflicts'])}."
        )
