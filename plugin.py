import os
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


class Plugin:
    name = "FFmpeg Smart Profiles"
    version = "0.1.0-dev.3"
    description = (
        "Installs FFmpeg Smart stream/output profiles and manages hardware "
        "capacity cache rebuilds."
    )
    author = "matrix2669"
    help_url = "https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin"

    fields = [
        {"id": "stream_profile_name", "label": "Stream profile name", "type": "string", "default": "FFmpeg Smart"},
        {"id": "install_passthrough_output", "label": "Install passthrough output profile", "type": "boolean", "default": True},
        {"id": "install_720p_output", "label": "Install 720p output profile", "type": "boolean", "default": True},
        {"id": "install_1080p_output", "label": "Install 1080p output profile", "type": "boolean", "default": True},
        {"id": "update_existing", "label": "Update existing managed profiles", "type": "boolean", "default": True},
    ]

    actions = [
        {"id": "install_profiles", "label": "Install or Update Profiles", "button_label": "Install / Update", "button_color": "blue"},
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
                "message": "Channels using these profiles may need to be reassigned first.",
            },
        },
    ]

    def run(self, action: str, params: dict, context: dict):
        settings = context.get("settings") or {}
        logger = context.get("logger")
        if action == "install_profiles":
            return self._install_profiles(settings, logger)
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

    @staticmethod
    def _output_definitions():
        common = (
            "-nostdin -hide_banner -loglevel warning -i pipe:0 "
            "-map 0:v:0 -map 0:a:0? "
        )
        trailer = (
            "-avoid_negative_ts make_zero -start_at_zero -mpegts_copyts 0 "
            "-mpegts_flags +pat_pmt_at_frames+resend_headers -flush_packets 1 "
            "-f mpegts pipe:1"
        )
        return {
            "passthrough": {
                "name": "FFmpeg Smart - Passthrough",
                "command": "ffmpeg",
                "parameters": common + "-c copy " + trailer,
            },
            "720p": {
                "name": "FFmpeg Smart - 720p 2M Stereo",
                "command": "ffmpeg",
                "parameters": (
                    common
                    + "-c:v libx264 -preset faster -b:v 1700k -maxrate 2000k "
                    "-bufsize 4000k -vf \"scale=w=-2:h=min(720\\,ih)\" "
                    "-c:a aac -b:a 192k -ac 2 "
                    + trailer
                ),
            },
            "1080p": {
                "name": "FFmpeg Smart - 1080p 8M Stereo",
                "command": "ffmpeg",
                "parameters": (
                    common
                    + "-c:v libx264 -preset faster -b:v 6800k -maxrate 8000k "
                    "-bufsize 16000k -vf \"scale=w=-2:h=min(1080\\,ih)\" "
                    "-c:a aac -b:a 192k -ac 2 "
                    + trailer
                ),
            },
        }

    def _stream_definition(self, settings):
        name = str(settings.get("stream_profile_name") or "FFmpeg Smart").strip()
        if not name:
            raise ValueError("Stream profile name cannot be empty")
        return {
            "name": name,
            "command": str(SCRIPT_PATH),
            "parameters": '-i "{streamUrl}" -user_agent "{userAgent}"',
            "is_active": True,
        }

    def _selected_output_definitions(self, settings):
        definitions = self._output_definitions()
        selected = []
        if settings.get("install_passthrough_output", True):
            selected.append(definitions["passthrough"])
        if settings.get("install_720p_output", True):
            selected.append(definitions["720p"])
        if settings.get("install_1080p_output", True):
            selected.append(definitions["1080p"])
        return selected

    def _install_profiles(self, settings, logger):
        from django.db import transaction
        from core.models import OutputProfile, StreamProfile

        self._ensure_script()
        update_existing = bool(settings.get("update_existing", True))
        result = {"created": [], "updated": [], "unchanged": [], "conflicts": []}

        with transaction.atomic():
            self._upsert_profile(
                StreamProfile,
                self._stream_definition(settings),
                update_existing,
                result,
                managed_command=lambda command: Path(command).name == SCRIPT_PATH.name,
            )
            for definition in self._selected_output_definitions(settings):
                self._upsert_profile(
                    OutputProfile,
                    {**definition, "is_active": True},
                    update_existing,
                    result,
                    managed_command=lambda command: command == "ffmpeg",
                )

        if logger:
            logger.info("FFmpeg Smart profile install result: %s", result)
        return {"status": "ok", "message": self._result_message(result), **result}

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
        stream = self._stream_definition(settings)
        outputs = list(self._output_definitions().values())
        with transaction.atomic():
            self._remove_matching(
                StreamProfile,
                stream,
                lambda command: Path(command).name == SCRIPT_PATH.name,
                removed,
                skipped,
            )
            for definition in outputs:
                self._remove_matching(
                    OutputProfile,
                    definition,
                    lambda command: command == "ffmpeg",
                    removed,
                    skipped,
                )
        if logger:
            logger.info("FFmpeg Smart profile removal: removed=%s skipped=%s", removed, skipped)
        return {
            "status": "ok",
            "message": f"Removed {len(removed)} profile(s); skipped {len(skipped)}.",
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
        elif lines and any("Cache rebuild complete" in line for line in lines):
            status = "complete"
            message = "Hardware cache rebuild completed successfully."
        elif lines:
            status = "error"
            message = "Hardware benchmark is not running and did not report successful completion."
        else:
            status = "idle"
            message = "No hardware benchmark has been started by this plugin."
        return {"status": status, "message": message, "pid": pid, "recent_log": lines}

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
            f"unchanged {len(result['unchanged'])}, conflicts {len(result['conflicts'])}."
        )
