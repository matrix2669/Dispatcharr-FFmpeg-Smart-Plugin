#!/usr/bin/env bash

set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export FFMPEG_SMART_STATE_DIR="${FFMPEG_SMART_STATE_DIR:-/data/ffmpeg_smart_profiles}"
export FFMPEG_SMART_REQUIRE_CACHE="${FFMPEG_SMART_REQUIRE_CACHE:-true}"

exec "$SCRIPT_DIR/ffmpeg-smart.sh" "$@"
