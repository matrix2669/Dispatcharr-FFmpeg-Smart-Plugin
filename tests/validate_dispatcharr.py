"""Validate the plugin files installed in a Dispatcharr container."""

import importlib.util
import json
from pathlib import Path


PLUGIN_DIR = Path("/data/plugins/ffmpeg_smart_profiles")
PLUGIN_PATH = PLUGIN_DIR / "plugin.py"
MANIFEST_PATH = PLUGIN_DIR / "plugin.json"


spec = importlib.util.spec_from_file_location("installed_ffmpeg_smart", PLUGIN_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
plugin = module.Plugin()

assert plugin.version == "0.1.0-dev.7"
assert manifest["version"] == plugin.version
assert (PLUGIN_DIR / "ffmpeg-smart.sh").is_file()

streams = plugin._stream_definitions({})
outputs = plugin._output_definitions({})

assert len(streams) == 1
assert streams[0]["name"] == "FFmpeg Smart"
assert streams[0]["parameters"].endswith("-10bit -hdr")

assert len(outputs) == 1
assert outputs[0]["name"] == "FFMpeg Smart - 720p Mobile"
assert outputs[0]["parameters"] == (
    "-i pipe:0 -maxres 720 -maxbr 2M -maxchan 2 -sdr -deint"
)

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
