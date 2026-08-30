"""Validate the plugin files installed in a Dispatcharr container."""

import importlib.util
import json
import os
import shlex
from pathlib import Path


PLUGIN_DIR = Path("/data/plugins/ffmpeg_smart_profiles")
PLUGIN_PATH = PLUGIN_DIR / "plugin.py"
MANIFEST_PATH = PLUGIN_DIR / "plugin.json"


spec = importlib.util.spec_from_file_location("installed_ffmpeg_smart", PLUGIN_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
plugin = module.Plugin()

assert plugin.version == "0.2.1-beta.1"
assert manifest["version"] == plugin.version
assert (PLUGIN_DIR / "ffmpeg-smart.sh").is_file()
assert (PLUGIN_DIR / "ffmpeg-smart-plugin.sh").is_file()
assert os.access(PLUGIN_DIR / "ffmpeg-smart.sh", os.X_OK)
assert os.access(PLUGIN_DIR / "ffmpeg-smart-plugin.sh", os.X_OK)
assert module.STATE_DIR == Path("/data/ffmpeg_smart_profiles")
assert module.CACHE_FILE == module.STATE_DIR / ".capabilities.cache"

streams = plugin._stream_definitions({})
outputs = plugin._output_definitions({})

assert len(streams) == 1
assert streams[0]["name"] == "FFmpeg Smart"
assert streams[0]["command"] == str(PLUGIN_DIR / "ffmpeg-smart-plugin.sh")
assert streams[0]["parameters"].endswith("-10bit -hdr")

assert len(outputs) == 1
assert outputs[0]["name"] == "FFMpeg Smart - 720p Mobile"
assert outputs[0]["command"] == str(PLUGIN_DIR / "ffmpeg-smart-plugin.sh")
assert outputs[0]["parameters"] == (
    "-i pipe:0 -maxres 720 -maxbr 2M -maxchan 2 -sdr -deint"
)

with_ffmpeg_options = plugin._output_definitions(
    {
        "output_1_ffmpeg_options": "-metadata 'service_name=Mobile feed' -muxdelay 0",
        "output_2_enabled": False,
        "output_3_enabled": False,
    }
)[0]["parameters"]
assert "-ffmpeg-mux-mode add" in with_ffmpeg_options
assert "-ffmpeg-mux-option -metadata" in with_ffmpeg_options
assert "-ffmpeg-mux-option 'service_name=Mobile feed'" in with_ffmpeg_options
assert "-ffmpeg-mux-option -muxdelay -ffmpeg-mux-option 0" in with_ffmpeg_options

advanced = plugin._stream_definitions(
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
            "-mpegts_flags +pat_pmt_at_frames+resend_headers+initial_discontinuity"
        ),
    }
)[0]["parameters"]
advanced_tokens = shlex.split(advanced)
assert advanced_tokens.index("-ffmpeg-input-mode") < advanced_tokens.index("-ffmpeg-map-mode")
assert advanced_tokens.index("-ffmpeg-map-mode") < advanced_tokens.index("-ffmpeg-video-mode")
assert advanced_tokens.index("-ffmpeg-video-mode") < advanced_tokens.index("-ffmpeg-audio-mode")
assert advanced_tokens.index("-ffmpeg-audio-mode") < advanced_tokens.index("-ffmpeg-mux-mode")
assert "expr:gte(t,n_forced*2)" in advanced_tokens

# Force SDR must win without raising an error when both controls are enabled.
override = plugin._stream_definitions(
    {"stream_1_hdr": True, "stream_1_sdr": True}
)[0]["parameters"]
assert "-sdr" in override
assert "-hdr" not in override

legacy_stream = plugin._stream_definitions(
    {"stream_1_options": "-10bit -hdr"}
)[0]["parameters"]
legacy_output = plugin._output_definitions(
    {"output_1_options": "-maxres 720 -maxbr 2M -maxchan 2 -sdr -deint"}
)[0]["parameters"]
assert legacy_stream.count("-10bit") == 1
assert legacy_stream.count("-hdr") == 1
assert legacy_output.count("-sdr") == 1
assert legacy_output.count("-deint") == 1

normalized, moved = plugin._normalize_policy_settings(
    {"output_2_options": "-maxres 1080 -10bit -hdr -sdr -deinterlace"}
)
assert normalized["output_2_options"] == "-maxres 1080"
assert normalized["output_2_10bit"] is True
assert normalized["output_2_hdr"] is True
assert normalized["output_2_sdr"] is True
assert normalized["output_2_deint"] is True
assert len(moved) == 4

print("Installed Dispatcharr plugin defaults and generated profiles passed")
