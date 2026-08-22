#!/bin/bash
if [ -z "$BASH_VERSION" ]; then exec bash "$0" "$@"; fi
set -euo pipefail

LOG_PREFIX="[ffmpeg-smart]"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="1.1.0-beta.1"
CAPACITY_BENCHMARK_VERSION="concurrency-1.2-v1"
STATE_DIR="${FFMPEG_SMART_STATE_DIR:-$SCRIPT_DIR}"
REQUIRE_CACHE_VALUE="${FFMPEG_SMART_REQUIRE_CACHE:-false}"
case "$REQUIRE_CACHE_VALUE" in
    true|TRUE|True|1|yes|YES|Yes) REQUIRE_CACHE=true ;;
    false|FALSE|False|0|no|NO|No|'') REQUIRE_CACHE=false ;;
    *)
        echo "$LOG_PREFIX ERROR [configuration]: FFMPEG_SMART_REQUIRE_CACHE must be true or false" >&2
        exit 64
        ;;
esac
if ! mkdir -p -- "$STATE_DIR" 2>/dev/null; then
    echo "$LOG_PREFIX ERROR [state-directory]: Cannot create persistent state directory: $STATE_DIR" >&2
    exit 73
fi
STATE_DIR="$(cd "$STATE_DIR" && pwd)"
if [[ ! -w "$STATE_DIR" ]]; then
    echo "$LOG_PREFIX ERROR [state-directory]: Persistent state directory is not writable: $STATE_DIR" >&2
    exit 73
fi
CACHE_FILE="$STATE_DIR/.capabilities.cache"
PROBE_SAMPLE="$STATE_DIR/probe-sample.mkv"
BENCHMARK_LOCK_FILE="$STATE_DIR/.benchmark.lock"
PROBE_SAMPLE_URL="https://repo.jellyfin.org/archive/jellyfish/media/jellyfish-3-mbps-hd-hevc-10bit.mkv"

DRI_DEVICE="${DRI_DEVICE:-}"
VAAPI_DEVICE="${VAAPI_DEVICE:-}"
QSV_DEVICE="${QSV_DEVICE:-}"
DRI_DEVICE_WAS_SET=false
VAAPI_DEVICE_WAS_SET=false
QSV_DEVICE_WAS_SET=false
[[ -n "$DRI_DEVICE" ]] && DRI_DEVICE_WAS_SET=true
[[ -n "$VAAPI_DEVICE" ]] && VAAPI_DEVICE_WAS_SET=true
[[ -n "$QSV_DEVICE" ]] && QSV_DEVICE_WAS_SET=true

# Device overrides must be known before hardware fingerprinting and cache load.
CLI_ARGS=("$@")
for ((CLI_INDEX = 0; CLI_INDEX < ${#CLI_ARGS[@]}; CLI_INDEX++)); do
    case "${CLI_ARGS[$CLI_INDEX]}" in
        -device|-dri-device)
            (( CLI_INDEX + 1 < ${#CLI_ARGS[@]} )) || { echo "$LOG_PREFIX ERROR: ${CLI_ARGS[$CLI_INDEX]} requires a device path" >&2; exit 1; }
            CLI_INDEX=$((CLI_INDEX + 1))
            DRI_DEVICE="${CLI_ARGS[$CLI_INDEX]}"
            VAAPI_DEVICE="$DRI_DEVICE"
            QSV_DEVICE="$DRI_DEVICE"
            DRI_DEVICE_WAS_SET=true
            VAAPI_DEVICE_WAS_SET=true
            QSV_DEVICE_WAS_SET=true
            ;;
        -vaapi-device)
            (( CLI_INDEX + 1 < ${#CLI_ARGS[@]} )) || { echo "$LOG_PREFIX ERROR: -vaapi-device requires a device path" >&2; exit 1; }
            CLI_INDEX=$((CLI_INDEX + 1))
            VAAPI_DEVICE="${CLI_ARGS[$CLI_INDEX]}"
            VAAPI_DEVICE_WAS_SET=true
            ;;
        -qsv-device)
            (( CLI_INDEX + 1 < ${#CLI_ARGS[@]} )) || { echo "$LOG_PREFIX ERROR: -qsv-device requires a device path" >&2; exit 1; }
            CLI_INDEX=$((CLI_INDEX + 1))
            QSV_DEVICE="${CLI_ARGS[$CLI_INDEX]}"
            QSV_DEVICE_WAS_SET=true
            ;;
    esac
done

get_dri_vendor() {
    local dev="$1"
    local node="${dev##*/}"
    local vendor_file="/sys/class/drm/$node/device/vendor"
    [[ -r "$vendor_file" ]] || return 1
    cat "$vendor_file" 2>/dev/null
}

get_dri_hardware_key() {
    local dev="$1" node="${dev##*/}"
    local vendor device revision subsystem_vendor subsystem_device
    vendor="$(cat "/sys/class/drm/$node/device/vendor" 2>/dev/null || true)"
    device="$(cat "/sys/class/drm/$node/device/device" 2>/dev/null || true)"
    revision="$(cat "/sys/class/drm/$node/device/revision" 2>/dev/null || true)"
    subsystem_vendor="$(cat "/sys/class/drm/$node/device/subsystem_vendor" 2>/dev/null || true)"
    subsystem_device="$(cat "/sys/class/drm/$node/device/subsystem_device" 2>/dev/null || true)"
    echo "${vendor:-unknown}:${device:-unknown}:${revision:-unknown}:${subsystem_vendor:-unknown}:${subsystem_device:-unknown}"
}

auto_select_dri_device() {
    local dev vendor
    local fallback=""
    for dev in /dev/dri/renderD*; do
        [[ -e "$dev" ]] || continue
        [[ -z "$fallback" ]] && fallback="$dev"
        vendor="$(get_dri_vendor "$dev" || true)"
        case "$vendor" in
            0x8086|0x1002)
                echo "$dev"
                return 0
                ;;
        esac
    done
    if [[ -n "$fallback" ]]; then
        echo "$fallback"
        return 0
    fi
    return 1
}

get_ffmpeg_job_load_milli() {
    local proc="$1"
    local env_line key value
    local input_width="" input_height="" output_width="" output_height="" fps=""
    local fps_num fps_den input_pixels output_pixels max_pixels load

    [[ -r "$proc/environ" ]] || { echo 1000; return; }
    while IFS= read -r env_line; do
        key="${env_line%%=*}"
        value="${env_line#*=}"
        case "$key" in
            FFMPEG_SMART_INPUT_WIDTH) input_width="$value" ;;
            FFMPEG_SMART_INPUT_HEIGHT) input_height="$value" ;;
            FFMPEG_SMART_OUTPUT_WIDTH) output_width="$value" ;;
            FFMPEG_SMART_OUTPUT_HEIGHT) output_height="$value" ;;
            FFMPEG_SMART_FPS_FRAC) fps="$value" ;;
        esac
    done < <(tr '\0' '\n' < "$proc/environ" 2>/dev/null || true)

    if [[ ! "$input_width" =~ ^[1-9][0-9]*$ || ! "$input_height" =~ ^[1-9][0-9]*$ ||
          ! "$output_width" =~ ^[1-9][0-9]*$ || ! "$output_height" =~ ^[1-9][0-9]*$ ||
          ! "$fps" =~ ^([1-9][0-9]*)/([1-9][0-9]*)$ ]]; then
        echo 1000
        return
    fi
    fps_num="${BASH_REMATCH[1]}"
    fps_den="${BASH_REMATCH[2]}"
    input_pixels=$((input_width * input_height * fps_num))
    output_pixels=$((output_width * output_height * fps_num))
    max_pixels="$input_pixels"
    (( output_pixels > max_pixels )) && max_pixels="$output_pixels"
    load=$((max_pixels * 1000 / (1920 * 1080 * 30 * fps_den)))
    (( load > 0 )) || load=1
    echo "$load"
}

get_ffmpeg_load_milli_on_device() {
    local device="$1"
    local proc comm fd target total=0
    for proc in /proc/[0-9]*; do
        [[ -r "$proc/comm" ]] || continue
        read -r comm < "$proc/comm" || continue
        [[ "$comm" == "ffmpeg" ]] || continue
        for fd in "$proc"/fd/*; do
            [[ -e "$fd" ]] || continue
            target="$(readlink "$fd" 2>/dev/null || true)"
            if [[ "$target" == "$device" || "$target" == "$device (deleted)" ]]; then
                total=$((total + $(get_ffmpeg_job_load_milli "$proc")))
                break
            fi
        done
    done
    echo "$total"
}

select_least_loaded_dri_device() {
    local primary="${PRIMARY_DEVICE:-}"
    local secondary="${SECONDARY_DEVICE:-}"
    local primary_capacity secondary_capacity
    local primary_load secondary_load selected

    primary_capacity=$(( ${PRIMARY_CAPACITY:-0} * 1000 ))
    secondary_capacity=$(( ${SECONDARY_CAPACITY:-0} * 1000 ))

    [[ -n "$primary" && -e "$primary" && "$primary_capacity" =~ ^[1-9][0-9]*$ ]] || return 1
    if [[ -z "$secondary" || ! -e "$secondary" || ! "$secondary_capacity" =~ ^[1-9][0-9]*$ ]]; then
        echo "$primary"
        return 0
    fi

    primary_load="$(get_ffmpeg_load_milli_on_device "$primary")"
    secondary_load="$(get_ffmpeg_load_milli_on_device "$secondary")"
    selected="$primary"
    # Compare the fractions without floating point. A tie deliberately favors primary.
    if (( secondary_load * primary_capacity < primary_load * secondary_capacity )); then
        selected="$secondary"
    fi
    echo "$LOG_PREFIX GPU load (1080p30 milli-units): primary=$primary_load/$primary_capacity secondary=$secondary_load/$secondary_capacity selected=$selected" >&2
    echo "$selected"
}

if [[ "$(uname -s)" == "Linux" ]]; then
    if [[ -z "$DRI_DEVICE" ]]; then
        DRI_DEVICE="$(auto_select_dri_device || true)"
    fi
    [[ -z "$VAAPI_DEVICE" ]] && VAAPI_DEVICE="$DRI_DEVICE"
    [[ -z "$QSV_DEVICE" ]] && QSV_DEVICE="$DRI_DEVICE"
fi

get_hw_fingerprint() {
    local fp="script=$VERSION;"
    local dev node hardware_key
    for dev in /dev/dri/renderD*; do
        [[ -e "$dev" ]] || continue
        node="${dev##*/}"
        hardware_key="$(get_dri_hardware_key "$dev")"
        fp+="dri:${node}:${hardware_key};"
    done
    if [[ "$(uname -s)" == "Linux" ]]; then
        fp+="selected:dri=${DRI_DEVICE:-none},vaapi=${VAAPI_DEVICE:-none},qsv=${QSV_DEVICE:-none};"
    fi
    [[ -e /dev/nvidia0 ]] && fp+="nvidia:$(nvidia-smi --query-gpu=gpu_name --format=csv,noheader 2>/dev/null | head -1 | tr ' ' '_');"
    [[ "$(uname -s)" == "Darwin" ]] && fp+="darwin:$(system_profiler SPDisplaysDataType 2>/dev/null | grep 'Chip' | head -1 | tr ' ' '_');"
    echo "$fp"
}

ensure_probe_sample() {
    [[ -f "$PROBE_SAMPLE" ]] && return 0
    echo "$LOG_PREFIX Downloading probe sample (~4MB)..." >&2
    curl -fsSL -o "$PROBE_SAMPLE" "$PROBE_SAMPLE_URL" 2>/dev/null || {
        echo "$LOG_PREFIX WARNING: Failed to download probe sample, using synthetic test" >&2
        return 1
    }
}

parse_bench_speed() {
    local output="$1"
    grep -oP 'speed=\s*\K[0-9.]+(?=x)' <<<"$output" | tail -1 || true
}

log_bench_failure() {
    local label="$1"
    local output="$2"
    echo "$LOG_PREFIX WARNING: $label benchmark produced no speed result" >&2
    tail -n 8 <<<"$output" | sed "s/^/$LOG_PREFIX   /" >&2
}

bench_encoder() {
    local encoder="$1"
    local sample_duration="${2:-5}"
    local synthetic_duration="${3:-2}"
    local pix_fmt="nv12"
    local size="1920x1080"
    local bench_timeout=$((sample_duration + 15))
    local output speed
    local lp_speed=""
    local use_sample="false"
    [[ -f "$PROBE_SAMPLE" ]] && use_sample="true"
    local prod_opts="-b:v 8M -maxrate 10M -bufsize 16M -g 30 -bf 2"
    local lp_prod_opts="-b:v 8M -maxrate 10M -bufsize 16M -g 30 -bf 0 -look_ahead 0"

    case "$encoder" in
        *_qsv)
            [[ -n "$QSV_DEVICE" && -e "$QSV_DEVICE" ]] || { echo "0:"; return; }
            if [[ "$use_sample" == "true" ]]; then
                output=$(timeout "${bench_timeout}s" ffmpeg -nostdin -hide_banner -benchmark \
                    -init_hw_device "qsv=qsv:hw,child_device=$QSV_DEVICE" \
                    -filter_hw_device qsv \
                    -hwaccel qsv -hwaccel_device qsv -hwaccel_output_format qsv \
                    -stream_loop -1 -i "$PROBE_SAMPLE" -t "$sample_duration" \
                    -vf "scale_qsv=format=$pix_fmt" -an \
                    -c:v "$encoder" -preset faster $prod_opts -f null - 2>&1 || true)
            else
                output=$(timeout "${bench_timeout}s" ffmpeg -nostdin -hide_banner -benchmark \
                    -init_hw_device "qsv=qsv:hw,child_device=$QSV_DEVICE" \
                    -filter_hw_device qsv \
                    -f lavfi -i "testsrc2=size=$size:rate=30" -t "$synthetic_duration" \
                    -vf "format=$pix_fmt,hwupload=extra_hw_frames=16" \
                    -c:v "$encoder" -preset faster $prod_opts -f null - 2>&1 || true)
            fi
            speed=$(parse_bench_speed "$output")
            [[ -n "$speed" ]] || log_bench_failure "$encoder" "$output"
            if [[ "$use_sample" == "true" ]]; then
                output=$(timeout "${bench_timeout}s" ffmpeg -nostdin -hide_banner -benchmark \
                    -init_hw_device "qsv=qsv:hw,child_device=$QSV_DEVICE" \
                    -filter_hw_device qsv \
                    -hwaccel qsv -hwaccel_device qsv -hwaccel_output_format qsv \
                    -stream_loop -1 -i "$PROBE_SAMPLE" -t "$sample_duration" \
                    -vf "scale_qsv=format=$pix_fmt" -an \
                    -c:v "$encoder" -low_power true $lp_prod_opts -f null - 2>&1 || true)
            else
                output=$(timeout "${bench_timeout}s" ffmpeg -nostdin -hide_banner -benchmark \
                    -init_hw_device "qsv=qsv:hw,child_device=$QSV_DEVICE" \
                    -filter_hw_device qsv \
                    -f lavfi -i "testsrc2=size=$size:rate=30" -t "$synthetic_duration" \
                    -vf "format=$pix_fmt,hwupload=extra_hw_frames=16" \
                    -c:v "$encoder" -low_power true $lp_prod_opts -f null - 2>&1 || true)
            fi
            lp_speed=$(parse_bench_speed "$output")
            ;;
        *_vaapi)
            [[ -n "$VAAPI_DEVICE" && -e "$VAAPI_DEVICE" ]] || { echo "0:"; return; }
            if [[ "$use_sample" == "true" ]]; then
                output=$(timeout "${bench_timeout}s" ffmpeg -nostdin -hide_banner -benchmark \
                    -hwaccel vaapi -hwaccel_output_format vaapi -vaapi_device "$VAAPI_DEVICE" \
                    -stream_loop -1 -i "$PROBE_SAMPLE" -t "$sample_duration" \
                    -vf "scale_vaapi=format=$pix_fmt" -an \
                    -c:v "$encoder" -rc_mode VBR $prod_opts -f null - 2>&1 || true)
            else
                output=$(timeout "${bench_timeout}s" ffmpeg -nostdin -hide_banner -benchmark \
                    -vaapi_device "$VAAPI_DEVICE" \
                    -f lavfi -i "testsrc2=size=$size:rate=30" -t "$synthetic_duration" \
                    -vf "format=$pix_fmt,hwupload,scale_vaapi=format=$pix_fmt" \
                    -c:v "$encoder" -rc_mode VBR $prod_opts -f null - 2>&1 || true)
            fi
            speed=$(parse_bench_speed "$output")
            [[ -n "$speed" ]] || log_bench_failure "$encoder" "$output"
            if [[ "$use_sample" == "true" ]]; then
                output=$(timeout "${bench_timeout}s" ffmpeg -nostdin -hide_banner -benchmark \
                    -hwaccel vaapi -hwaccel_output_format vaapi -vaapi_device "$VAAPI_DEVICE" \
                    -stream_loop -1 -i "$PROBE_SAMPLE" -t "$sample_duration" \
                    -vf "scale_vaapi=format=$pix_fmt" -an \
                    -c:v "$encoder" -rc_mode VBR -low_power 1 $lp_prod_opts -f null - 2>&1 || true)
            else
                output=$(timeout "${bench_timeout}s" ffmpeg -nostdin -hide_banner -benchmark \
                    -vaapi_device "$VAAPI_DEVICE" \
                    -f lavfi -i "testsrc2=size=$size:rate=30" -t "$synthetic_duration" \
                    -vf "format=$pix_fmt,hwupload,scale_vaapi=format=$pix_fmt" \
                    -c:v "$encoder" -rc_mode VBR -low_power 1 $lp_prod_opts -f null - 2>&1 || true)
            fi
            lp_speed=$(parse_bench_speed "$output")
            ;;
        *_nvenc)
            output=$(timeout 15s ffmpeg -nostdin -hide_banner -benchmark \
                -init_hw_device cuda=cuda -filter_hw_device cuda \
                -f lavfi -i "testsrc2=size=$size:rate=30" -t "$synthetic_duration" \
                -vf "format=$pix_fmt,hwupload_cuda" \
                -c:v "$encoder" -f null - 2>&1 || true)
            speed=$(parse_bench_speed "$output")
            [[ -n "$speed" ]] || log_bench_failure "$encoder" "$output"
            ;;
        *_videotoolbox)
            output=$(timeout 15s ffmpeg -nostdin -hide_banner -benchmark \
                -f lavfi -i "testsrc2=size=$size:rate=30" -t "$synthetic_duration" \
                -c:v "$encoder" -f null - 2>&1 || true)
            speed=$(parse_bench_speed "$output")
            [[ -n "$speed" ]] || log_bench_failure "$encoder" "$output"
            ;;
        *_v4l2m2m)
            output=$(timeout 15s ffmpeg -nostdin -hide_banner -benchmark \
                -f lavfi -i "testsrc2=size=$size:rate=30" -t "$synthetic_duration" \
                -c:v "$encoder" -f null - 2>&1 || true)
            speed=$(parse_bench_speed "$output")
            [[ -n "$speed" ]] || log_bench_failure "$encoder" "$output"
            ;;
        *)
            if [[ "$use_sample" == "true" ]]; then
                output=$(timeout 15s ffmpeg -nostdin -hide_banner -benchmark \
                    -i "$PROBE_SAMPLE" -t "$sample_duration" \
                    -vf "format=yuv420p" -an \
                    -c:v "$encoder" -preset faster $prod_opts -f null - 2>&1 || true)
            else
                output=$(timeout 15s ffmpeg -nostdin -hide_banner -benchmark \
                    -f lavfi -i "testsrc2=size=$size:rate=30" -t "$synthetic_duration" \
                    -c:v "$encoder" -preset faster $prod_opts -f null - 2>&1 || true)
            fi
            speed=$(parse_bench_speed "$output")
            [[ -n "$speed" ]] || log_bench_failure "$encoder" "$output"
            ;;
    esac
    echo "${speed:-0}:${lp_speed}"
}

test_encoder() {
    local encoder="$1"
    local test_10bit="${2:-false}"
    local pix_fmt="nv12"
    [[ "$test_10bit" == "true" ]] && pix_fmt="p010le"
    local size="256x256"
    case "$encoder" in
        *_qsv)
            [[ -n "$QSV_DEVICE" && -e "$QSV_DEVICE" ]] || return 1
            if [[ "$test_10bit" == "true" && -f "$PROBE_SAMPLE" ]]; then
                timeout 10s ffmpeg -nostdin -hide_banner -v error \
                    -init_hw_device "qsv=qsv:hw,child_device=$QSV_DEVICE" \
                    -filter_hw_device qsv \
                    -hwaccel qsv -hwaccel_device qsv -hwaccel_output_format qsv \
                    -i "$PROBE_SAMPLE" -t 0.5 \
                    -vf "scale_qsv=format=p010le" \
                    -c:v "$encoder" -profile:v main10 -f null - 2>/dev/null
            else
                local qsv_profile=()
                [[ "$test_10bit" == "true" ]] && qsv_profile=(-profile:v main10)
                timeout 10s ffmpeg -nostdin -hide_banner -v error \
                    -init_hw_device "qsv=qsv:hw,child_device=$QSV_DEVICE" \
                    -filter_hw_device qsv \
                    -f lavfi -i "color=black:size=$size:rate=30,format=$pix_fmt" \
                    -t 0.2 \
                    -vf "hwupload=extra_hw_frames=16" \
                    -c:v "$encoder" "${qsv_profile[@]}" -f null - 2>/dev/null
            fi
            ;;
        *_vaapi)
            [[ -n "$VAAPI_DEVICE" && -e "$VAAPI_DEVICE" ]] || return 1
            if [[ "$test_10bit" == "true" && -f "$PROBE_SAMPLE" ]]; then
                timeout 10s ffmpeg -nostdin -hide_banner -v error \
                    -hwaccel vaapi -hwaccel_output_format vaapi -vaapi_device "$VAAPI_DEVICE" \
                    -i "$PROBE_SAMPLE" -t 0.5 \
                    -vf "scale_vaapi=format=p010le" \
                    -c:v "$encoder" -f null - 2>/dev/null
            else
                timeout 10s ffmpeg -nostdin -hide_banner -v error \
                    -vaapi_device "$VAAPI_DEVICE" \
                    -f lavfi -i "color=black:size=$size:rate=30,format=$pix_fmt" \
                    -t 0.2 \
                    -vf "hwupload,scale_vaapi=format=$pix_fmt" \
                    -c:v "$encoder" -f null - 2>/dev/null
            fi
            ;;
        *_nvenc)
            timeout 10s ffmpeg -nostdin -hide_banner -v error \
                -init_hw_device cuda=cuda -filter_hw_device cuda \
                -f lavfi -i "color=black:size=$size:rate=30,format=$pix_fmt,hwupload_cuda" \
                -t 0.2 -c:v "$encoder" -f null - 2>/dev/null
            ;;
        *_videotoolbox|*_v4l2m2m)
            timeout 10s ffmpeg -nostdin -hide_banner -v error \
                -f lavfi -i "color=black:size=$size:rate=30,format=$pix_fmt" \
                -t 0.2 -c:v "$encoder" -f null - 2>/dev/null
            ;;
        *)
            timeout 10s ffmpeg -nostdin -hide_banner -v error \
                -f lavfi -i "color=black:size=$size:rate=30" \
                -t 0.2 -c:v "$encoder" -f null - 2>/dev/null
            ;;
    esac
}

test_10bit_decode() {
    local accel="$1"
    local hwaccel_args=()
    [[ ! -f "$PROBE_SAMPLE" ]] && return 1
    case "$accel" in
        qsv)
            [[ -n "$QSV_DEVICE" && -e "$QSV_DEVICE" ]] || return 1
            hwaccel_args=(
                -init_hw_device "qsv=qsv:hw,child_device=$QSV_DEVICE"
                -filter_hw_device qsv
                -hwaccel qsv
                -hwaccel_device qsv
                -hwaccel_output_format qsv
            )
            ;;
        vaapi)
            [[ -n "$VAAPI_DEVICE" && -e "$VAAPI_DEVICE" ]] || return 1
            hwaccel_args=(-hwaccel vaapi -hwaccel_output_format vaapi -vaapi_device "$VAAPI_DEVICE")
            ;;
        nvenc) hwaccel_args=(-hwaccel cuda -hwaccel_output_format cuda) ;;
        videotoolbox) hwaccel_args=(-hwaccel videotoolbox) ;;
        *) return 1 ;;
    esac
    timeout 5s ffmpeg -nostdin -hide_banner -v error \
        "${hwaccel_args[@]}" -i "$PROBE_SAMPLE" -t 0.2 \
        -f null - 2>/dev/null
}

run_concurrency_level() {
    local accel="$1" encoder="$2" device="$3" use_low_power="$4"
    local streams="$5" duration="$6"
    local min_speed="${CONCURRENCY_MIN_SPEED:-1.2}"
    local work_dir i pid wait_status status=0 speed observed_min=""
    local -a pids=()
    local -a cmd=()

    [[ "$min_speed" =~ ^[0-9]+([.][0-9]+)?$ ]] || { echo "$LOG_PREFIX ERROR: Invalid CONCURRENCY_MIN_SPEED: $min_speed" >&2; return 1; }
    work_dir="$(mktemp -d "${TMPDIR:-/tmp}/ffmpeg-smart-concurrency.XXXXXX")"
    for ((i = 1; i <= streams; i++)); do
        case "$accel" in
            qsv)
                cmd=(ffmpeg -nostdin -hide_banner -v error -nostats
                    -init_hw_device "qsv=qsv:hw,child_device=$device" -filter_hw_device qsv
                    -hwaccel qsv -hwaccel_device qsv -hwaccel_output_format qsv
                    -stream_loop -1 -i "$PROBE_SAMPLE"
                    -vf scale_qsv=format=nv12 -an -c:v "$encoder")
                if [[ "$use_low_power" == "1" ]]; then
                    cmd+=(-low_power true -look_ahead 0 -bf 0)
                else
                    cmd+=(-preset faster -bf 2)
                fi
                ;;
            vaapi)
                cmd=(ffmpeg -nostdin -hide_banner -v error -nostats
                    -hwaccel vaapi -hwaccel_output_format vaapi -vaapi_device "$device"
                    -stream_loop -1 -i "$PROBE_SAMPLE"
                    -vf scale_vaapi=format=nv12 -an -c:v "$encoder" -rc_mode VBR)
                if [[ "$use_low_power" == "1" ]]; then cmd+=(-low_power 1 -bf 0); else cmd+=(-bf 2); fi
                ;;
            *) rm -rf "$work_dir"; return 1 ;;
        esac
        cmd+=(-b:v 8M -maxrate 10M -bufsize 16M -g 30
            -progress "$work_dir/progress.$i" -f null -)
        timeout "${duration}s" "${cmd[@]}" > /dev/null 2>"$work_dir/error.$i" &
        pids+=("$!")
    done

    for pid in "${pids[@]}"; do
        if wait "$pid"; then wait_status=0; else wait_status=$?; fi
        # timeout(1) ending the intentionally unbounded worker is expected.
        [[ "$wait_status" == "124" || "$wait_status" == "143" ]] || status=1
    done
    for ((i = 1; i <= streams; i++)); do
        speed="$(sed -n 's/^speed=\([0-9.]*\)x$/\1/p' "$work_dir/progress.$i" 2>/dev/null | tail -1)"
        if [[ ! "$speed" =~ ^[0-9]+([.][0-9]+)?$ ]] || ! awk "BEGIN {exit !($speed >= $min_speed)}"; then
            status=1
            echo "$LOG_PREFIX   stream $i unstable speed=${speed:-missing}x" >&2
        elif [[ -z "$observed_min" ]] || awk "BEGIN {exit !($speed < $observed_min)}"; then
            observed_min="$speed"
        fi
    done
    if [[ "$status" == "0" ]]; then
        echo "$LOG_PREFIX   $streams streams stable minimum=${observed_min}x required=${min_speed}x" >&2
    fi
    rm -rf "$work_dir"
    return "$status"
}

find_concurrent_capacity() {
    local accel="$1" encoder="$2" device="$3" use_low_power="$4" estimate="$5"
    local short_duration="${CONCURRENCY_SHORT_DURATION:-10}"
    local confirm_duration="${CONCURRENCY_CONFIRM_DURATION:-30}"
    local max_streams="${CONCURRENCY_MAX_STREAMS:-64}"
    local low=0 high=0 test_level step candidate value

    for value in "$short_duration" "$confirm_duration" "$max_streams"; do
        [[ "$value" =~ ^[1-9][0-9]*$ ]] || { echo "$LOG_PREFIX ERROR: Invalid concurrency benchmark setting: $value" >&2; return 1; }
    done
    [[ "$estimate" =~ ^[1-9][0-9]*$ ]] || estimate=1
    (( estimate > max_streams )) && estimate="$max_streams"
    echo "$LOG_PREFIX Concurrent search on $device: estimate=$estimate short=${short_duration}s confirm=${confirm_duration}s" >&2

    if run_concurrency_level "$accel" "$encoder" "$device" "$use_low_power" "$estimate" "$short_duration"; then
        low="$estimate"
        step=$((estimate / 4)); (( step > 0 )) || step=1
        while (( low < max_streams )); do
            test_level=$((low + step)); (( test_level > max_streams )) && test_level="$max_streams"
            echo "$LOG_PREFIX Testing $test_level concurrent streams for ${short_duration}s..." >&2
            if run_concurrency_level "$accel" "$encoder" "$device" "$use_low_power" "$test_level" "$short_duration"; then
                low="$test_level"
                (( low == max_streams )) && break
            else
                high="$test_level"
                break
            fi
        done
    else
        high="$estimate"
    fi

    while (( high > 0 && high - low > 1 )); do
        test_level=$(((low + high) / 2))
        echo "$LOG_PREFIX Testing $test_level concurrent streams for ${short_duration}s..." >&2
        if run_concurrency_level "$accel" "$encoder" "$device" "$use_low_power" "$test_level" "$short_duration"; then low="$test_level"; else high="$test_level"; fi
    done

    candidate="$low"
    while (( candidate > 0 )); do
        echo "$LOG_PREFIX Confirming $candidate concurrent streams for ${confirm_duration}s..." >&2
        if run_concurrency_level "$accel" "$encoder" "$device" "$use_low_power" "$candidate" "$confirm_duration"; then break; fi
        candidate=$((candidate - 1))
    done
    if (( candidate < max_streams )); then
        test_level=$((candidate + 1))
        echo "$LOG_PREFIX Checking instability at $test_level streams for ${confirm_duration}s..." >&2
        while run_concurrency_level "$accel" "$encoder" "$device" "$use_low_power" "$test_level" "$confirm_duration"; do
            candidate="$test_level"
            (( candidate >= max_streams )) && break
            test_level=$((candidate + 1))
            echo "$LOG_PREFIX Checking $test_level streams for ${confirm_duration}s..." >&2
        done
    fi
    echo "$candidate"
}

lookup_cached_device_benchmark() {
    local hardware_key="$1" accel="$2" codec="$3" use_low_power="$4"
    local entry cached_key cached_accel cached_codec cached_lp cached_speed cached_capacity
    local -a entries=()
    [[ "${CACHED_CAPACITY_BENCHMARK_VERSION:-}" == "$CAPACITY_BENCHMARK_VERSION" ]] || return 1
    IFS=';' read -ra entries <<< "${CACHED_DEVICE_BENCHMARKS:-}"
    for entry in "${entries[@]}"; do
        [[ -n "$entry" ]] || continue
        IFS='|' read -r cached_key cached_accel cached_codec cached_lp cached_speed cached_capacity <<< "$entry"
        if [[ "$cached_key" == "$hardware_key" && "$cached_accel" == "$accel" &&
              "$cached_codec" == "$codec" && "$cached_lp" == "$use_low_power" &&
              "$cached_speed" =~ ^[0-9]+([.][0-9]+)?$ && "$cached_capacity" =~ ^[1-9][0-9]*$ ]]; then
            echo "$cached_speed:$cached_capacity"
            return 0
        fi
    done
    return 1
}

benchmark_dri_capacities() {
    local accel="$1"
    local codec="$2"
    local use_low_power="${3:-0}"
    local original_qsv="$QSV_DEVICE"
    local original_vaapi="$VAAPI_DEVICE"
    local encoder="${codec}_${accel}"
    local dev vendor hardware_key cached result speed lp_speed fastest capacity estimate
    local device_benchmarks=""
    local primary="" secondary="" primary_capacity=0 secondary_capacity=0
    local primary_speed=0 secondary_speed=0
    local -a compatible_devices=()

    case "$accel" in
        qsv|vaapi) ;;
        *)
            echo "PRIMARY_DEVICE=''"
            echo "PRIMARY_SPEED='0'"
            echo "PRIMARY_CAPACITY='0'"
            echo "SECONDARY_DEVICE=''"
            echo "SECONDARY_SPEED='0'"
            echo "SECONDARY_CAPACITY='0'"
            echo "DEVICE_BENCHMARKS=''"
            return
            ;;
    esac

    for dev in /dev/dri/renderD*; do
        [[ -e "$dev" ]] || continue
        vendor="$(get_dri_vendor "$dev" || true)"
        if [[ "$accel" == "qsv" && "$vendor" != "0x8086" ]]; then continue; fi
        if [[ "$accel" == "vaapi" && "$vendor" != "0x8086" && "$vendor" != "0x1002" ]]; then continue; fi
        compatible_devices+=("$dev")
    done

    for dev in "${compatible_devices[@]}"; do
        [[ "$accel" == "qsv" ]] && QSV_DEVICE="$dev" || VAAPI_DEVICE="$dev"
        hardware_key="$(get_dri_hardware_key "$dev")"
        cached="$(lookup_cached_device_benchmark "$hardware_key" "$accel" "$codec" "$use_low_power" || true)"
        if [[ -n "$cached" ]]; then
            fastest="${cached%%:*}"
            capacity="${cached##*:}"
            echo "$LOG_PREFIX Reusing verified capacity for $dev ($hardware_key): speed=${fastest}x capacity=$capacity" >&2
        else
            echo "$LOG_PREFIX Measuring single-stream $encoder speed on $dev..." >&2
            result="$(bench_encoder "$encoder")"
            speed="${result%%:*}"
            lp_speed="${result##*:}"
            if [[ "$use_low_power" == "1" ]]; then fastest="${lp_speed:-0}"; else fastest="${speed:-0}"; fi
            [[ "$fastest" =~ ^[0-9]+([.][0-9]+)?$ ]] || fastest=0
            estimate="$(awk "BEGIN {print int($fastest)}")"
            (( estimate > 0 )) || estimate=1
            if (( ${#compatible_devices[@]} > 1 )); then
                capacity="$(find_concurrent_capacity "$accel" "$encoder" "$dev" "$use_low_power" "$estimate")"
            else
                capacity="$estimate"
            fi
        fi
        [[ "$capacity" =~ ^[0-9]+$ ]] || capacity=0
        echo "$LOG_PREFIX   $dev speed=${fastest}x verified_capacity=$capacity" >&2
        (( capacity > 0 )) || continue
        device_benchmarks+="${hardware_key}|${accel}|${codec}|${use_low_power}|${fastest}|${capacity};"

        if (( capacity > primary_capacity )) || { (( capacity == primary_capacity )) && awk "BEGIN {exit !($fastest > $primary_speed)}"; }; then
            secondary="$primary"
            secondary_capacity="$primary_capacity"
            secondary_speed="$primary_speed"
            primary="$dev"
            primary_capacity="$capacity"
            primary_speed="$fastest"
        elif (( capacity > secondary_capacity )) || { (( capacity == secondary_capacity )) && awk "BEGIN {exit !($fastest > $secondary_speed)}"; }; then
            secondary="$dev"
            secondary_capacity="$capacity"
            secondary_speed="$fastest"
        fi
    done
    QSV_DEVICE="$original_qsv"
    VAAPI_DEVICE="$original_vaapi"

    echo "PRIMARY_DEVICE='$primary'"
    echo "PRIMARY_SPEED='$primary_speed'"
    echo "PRIMARY_CAPACITY='$primary_capacity'"
    echo "SECONDARY_DEVICE='$secondary'"
    echo "SECONDARY_SPEED='$secondary_speed'"
    echo "SECONDARY_CAPACITY='$secondary_capacity'"
    echo "DEVICE_BENCHMARKS='$device_benchmarks'"
}

probe_capabilities() {
    local results=""
    local encoders_list
    encoders_list=$(ffmpeg -hide_banner -encoders 2>/dev/null || true)
    ensure_probe_sample || true
    if [[ -f "$PROBE_SAMPLE" ]]; then
        echo "$LOG_PREFIX Benchmark source: $(basename "$PROBE_SAMPLE") (real decode/transcode)" >&2
    else
        echo "$LOG_PREFIX Benchmark source: synthetic lavfi fallback" >&2
    fi
    local accels_to_test=()
    local can_decode_10bit=""
    local can_encode_10bit=""
    local vendor=""
    if [[ "$(uname -s)" == "Darwin" ]]; then
        accels_to_test+=("videotoolbox")
    else
        [[ -e /dev/nvidia0 ]] && accels_to_test+=("nvenc")
        if [[ -n "$QSV_DEVICE" && -e "$QSV_DEVICE" ]]; then
            vendor="$(get_dri_vendor "$QSV_DEVICE" || true)"
            [[ "$vendor" == "0x8086" ]] && accels_to_test+=("qsv")
        fi
        if [[ -n "$VAAPI_DEVICE" && -e "$VAAPI_DEVICE" ]]; then
            vendor="$(get_dri_vendor "$VAAPI_DEVICE" || true)"
            case "$vendor" in
                0x8086|0x1002) accels_to_test+=("vaapi") ;;
            esac
        fi
        for n in /sys/class/video4linux/video*/name; do
            if [[ -r "$n" ]] && grep -qiE 'm2m|codec' "$n" 2>/dev/null; then
                accels_to_test+=("v4l2m2m")
                break
            fi
        done
    fi
    accels_to_test+=("software")
    local best_accel="software"
    local best_codec="h264"
    local best_speed="0"
    local best_low_power="0"
    for accel in "${accels_to_test[@]}"; do
        if [[ "$accel" != "software" ]] && test_10bit_decode "$accel"; then
            can_decode_10bit+="${accel}=1;"
        fi
        for codec in h264 hevc; do
            local encoder
            if [[ "$accel" == "software" ]]; then
                [[ "$codec" == "h264" ]] && encoder="libx264" || encoder="libx265"
            else
                encoder="${codec}_${accel}"
            fi
            grep -qw "$encoder" <<<"$encoders_list" || continue
            echo "$LOG_PREFIX Probing $encoder..." >&2
            local bench_result speed lp_speed best_of_two use_lp
            bench_result=$(bench_encoder "$encoder")
            speed="${bench_result%%:*}"
            lp_speed="${bench_result##*:}"
            if [[ -n "$speed" && "$speed" != "0" ]]; then
                results+="${encoder}=${speed}x;"
                if [[ -n "$lp_speed" && "$lp_speed" != "0" ]]; then
                    results+="${encoder}(lp)=${lp_speed}x;"
                fi
                if [[ -n "$lp_speed" ]] && awk "BEGIN {exit !($lp_speed > $speed)}"; then
                    best_of_two="$lp_speed"
                    use_lp="1"
                else
                    best_of_two="$speed"
                    use_lp="0"
                fi
                if awk "BEGIN {exit !($best_of_two > $best_speed)}"; then
                    best_speed="$best_of_two"
                    best_accel="$accel"
                    best_codec="$codec"
                    best_low_power="$use_lp"
                fi
                if [[ "$codec" == "hevc" && "$accel" != "software" ]]; then
                    if test_encoder "$encoder" "true"; then
                        results+="${encoder}_10bit=1;"
                        can_encode_10bit+="${accel}=1;"
                    fi
                fi
            else
                results+="${encoder}=0;"
            fi
        done
    done
    local supports_10bit_decode="false"
    local supports_10bit_encode="false"
    [[ "$can_decode_10bit" == *"${best_accel}=1;"* ]] && supports_10bit_decode="true"
    [[ "$can_encode_10bit" == *"${best_accel}=1;"* ]] && supports_10bit_encode="true"
    echo "BEST_ACCEL='$best_accel'"
    echo "BEST_CODEC='$best_codec'"
    echo "BEST_LOW_POWER='$best_low_power'"
    echo "SUPPORTS_10BIT_DECODE='$supports_10bit_decode'"
    echo "SUPPORTS_10BIT_ENCODE='$supports_10bit_encode'"
    echo "DECODE_10BIT='$can_decode_10bit'"
    echo "ENCODE_10BIT='$can_encode_10bit'"
    echo "ENCODERS='$results'"
    benchmark_dri_capacities "$best_accel" "$best_codec" "$best_low_power"
}

load_cache() {
    [[ -f "$CACHE_FILE" ]] || return 2
    source "$CACHE_FILE" || return 3
    local current_fp
    current_fp=$(get_hw_fingerprint)
    [[ "${HW_FINGERPRINT:-}" == "$current_fp" ]] || return 4
    return 0
}

required_cache_error() {
    local cache_status="$1"
    local error_code="capability-cache-unavailable"
    local detail="cannot be loaded"
    case "$cache_status" in
        2) error_code="capability-cache-missing"; detail="is missing" ;;
        3) error_code="capability-cache-invalid"; detail="is invalid or unreadable" ;;
        4) error_code="capability-cache-stale"; detail="does not match the current hardware or policy" ;;
    esac
    echo "$LOG_PREFIX ERROR [$error_code]: Required capability cache $detail: $CACHE_FILE. Run the integration's Rebuild Hardware Cache action or ffmpeg-smart.sh --recache-only before starting streams." >&2
}

save_cache() {
    CACHED_CAPACITY_BENCHMARK_VERSION="${DEVICE_BENCHMARK_VERSION:-}"
    CACHED_DEVICE_BENCHMARKS="${DEVICE_BENCHMARKS:-}"
    {
        echo "# ffmpeg-smart capability cache"
        echo "# Generated: $(date -Iseconds)"
        echo "HW_FINGERPRINT='$(get_hw_fingerprint)'"
        echo "DEVICE_BENCHMARK_VERSION='$CAPACITY_BENCHMARK_VERSION'"
        probe_capabilities
    } > "$CACHE_FILE"
    source "$CACHE_FILE"
}

accel_has_capability() {
    local caps="$1"
    local accel="$2"
    [[ "$caps" == *"${accel}=1;"* ]]
}

parse_bitrate() {
    local value="${1,,}"
    local number unit multiplier
    value="${value//[[:space:]]/}"
    value="${value%bps}"
    if [[ "$value" =~ ^([0-9]+([.][0-9]+)?)([kmg]?)$ ]]; then
        number="${BASH_REMATCH[1]}"
        unit="${BASH_REMATCH[3]}"
        case "$unit" in
            k) multiplier=1000 ;;
            m) multiplier=1000000 ;;
            g) multiplier=1000000000 ;;
            *) multiplier=1 ;;
        esac
        awk "BEGIN {printf \"%.0f\\n\", $number * $multiplier}"
        return 0
    fi
    return 1
}

append_reason() {
    local reason="$1"
    if [[ -n "$VIDEO_TRANSCODE_REASON" ]]; then
        VIDEO_TRANSCODE_REASON+=", $reason"
    else
        VIDEO_TRANSCODE_REASON="$reason"
    fi
}

AGENT=""
URL=""
VCODEC_OUT=""
ALLOW_10BIT=""
ALLOW_HDR=""
MAX_RES=""
MAX_CHANNELS=""
MAX_BITRATE_INPUT=""
MAX_BITRATE=""
FORCE_SDR=false
FORCE_DEINT=false
RECACHE=false
RECACHE_ONLY=false
ACCEL="__auto__"

detect_accel() {
    if [[ "$(uname -s)" == "Darwin" ]]; then
        echo "videotoolbox"; return
    fi
    if [[ -e /dev/nvidia0 ]]; then
        echo "nvenc"; return
    fi
    local vendor=""
    if [[ -n "$VAAPI_DEVICE" && -e "$VAAPI_DEVICE" ]]; then
        vendor="$(get_dri_vendor "$VAAPI_DEVICE" || true)"
        case "$vendor" in
            0x8086|0x1002) echo "vaapi"; return ;;
        esac
    fi
    if [[ -n "$QSV_DEVICE" && -e "$QSV_DEVICE" ]]; then
        vendor="$(get_dri_vendor "$QSV_DEVICE" || true)"
        [[ "$vendor" == "0x8086" ]] && { echo "qsv"; return; }
    fi
    for n in /sys/class/video4linux/video*/name; do
        [[ -r "$n" ]] && grep -qiE 'm2m|codec' "$n" && echo "v4l2m2m" && return
    done
    if [[ -n "$VAAPI_DEVICE" && -e "$VAAPI_DEVICE" ]]; then
        echo "vaapi"
    else
        echo "software"
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -user_agent) AGENT="$2"; shift 2 ;;
        -i) URL="$2"; shift 2 ;;
        -accel) ACCEL="$2"; shift 2 ;;
        -device|-dri-device|-qsv-device|-vaapi-device) shift 2 ;;
        -vc) VCODEC_OUT="$2"; shift 2 ;;
        -10bit) ALLOW_10BIT=true; shift ;;
        -hdr) ALLOW_HDR=true; shift ;;
        -maxres) MAX_RES="$2"; shift 2 ;;
        -maxchan) MAX_CHANNELS="$2"; shift 2 ;;
        -maxbr|-maxbitrate) MAX_BITRATE_INPUT="$2"; shift 2 ;;
        -sdr) FORCE_SDR=true; shift ;;
        -deint|-deinterlace) FORCE_DEINT=true; shift ;;
        --recache) RECACHE=true; shift ;;
        --recache-only) RECACHE=true; RECACHE_ONLY=true; shift ;;
        *) shift ;;
    esac
done

benchmark_lock_active() {
    local lock_pid=""
    [[ -e "$BENCHMARK_LOCK_FILE" ]] || return 1
    lock_pid="$(head -n 1 "$BENCHMARK_LOCK_FILE" 2>/dev/null || true)"
    if [[ "$lock_pid" =~ ^[1-9][0-9]*$ ]] && kill -0 "$lock_pid" 2>/dev/null; then
        return 0
    fi
    if [[ ! "$lock_pid" =~ ^[1-9][0-9]*$ ]] &&
       ! find "$BENCHMARK_LOCK_FILE" -mmin +1 -print -quit 2>/dev/null | grep -q .; then
        return 0
    fi
    rm -f -- "$BENCHMARK_LOCK_FILE"
    return 1
}

if [[ "$RECACHE_ONLY" == "true" ]]; then
    echo "$$" > "$BENCHMARK_LOCK_FILE"
    trap 'rm -f -- "$BENCHMARK_LOCK_FILE"' EXIT
elif benchmark_lock_active; then
    echo "$LOG_PREFIX Hardware benchmark in progress; refusing to start a new transcode" >&2
    exit 75
fi

if [[ -n "$MAX_RES" ]]; then
    if [[ ! "$MAX_RES" =~ ^[0-9]+$ ]] || [[ "$MAX_RES" -le 0 ]]; then
        echo "$LOG_PREFIX ERROR: -maxres must be a positive vertical resolution (for example: 720)" >&2
        exit 1
    fi
fi
if [[ -n "$MAX_CHANNELS" ]]; then
    if [[ ! "$MAX_CHANNELS" =~ ^[0-9]+$ ]] || [[ "$MAX_CHANNELS" -le 0 ]]; then
        echo "$LOG_PREFIX ERROR: -maxchan must be a positive channel count (for example: 2)" >&2
        exit 1
    fi
fi
if [[ -n "$MAX_BITRATE_INPUT" ]]; then
    MAX_BITRATE="$(parse_bitrate "$MAX_BITRATE_INPUT" || true)"
    if [[ -z "$MAX_BITRATE" || ! "$MAX_BITRATE" =~ ^[0-9]+$ || "$MAX_BITRATE" -le 0 ]]; then
        echo "$LOG_PREFIX ERROR: -maxbr/-maxbitrate must be a positive bitrate (for example: 2M, 2000k, or 2000000)" >&2
        exit 1
    fi
fi

cache_status=0
if [[ "$RECACHE" != "true" ]]; then
    load_cache 2>/dev/null || cache_status=$?
fi
if [[ "$RECACHE" != "true" && "$cache_status" -ne 0 && "$REQUIRE_CACHE" == "true" ]]; then
    required_cache_error "$cache_status"
    exit 78
fi
if [[ "$RECACHE" == "true" || "$cache_status" -ne 0 ]]; then
    save_cache
    echo "$LOG_PREFIX v$VERSION | Probed: accel=$BEST_ACCEL codec=$BEST_CODEC 10bit=$SUPPORTS_10BIT_ENCODE hdr=$SUPPORTS_10BIT_ENCODE" >&2
else
    echo "$LOG_PREFIX v$VERSION | Cached: accel=$BEST_ACCEL codec=$BEST_CODEC 10bit=$SUPPORTS_10BIT_ENCODE hdr=$SUPPORTS_10BIT_ENCODE" >&2
fi

if [[ "$RECACHE_ONLY" == "true" ]]; then
    echo "$LOG_PREFIX Cache rebuild complete" >&2
    exit 0
fi

[[ -z "$VCODEC_OUT" ]] && VCODEC_OUT="${BEST_CODEC:-h264}"
if [[ "$ACCEL" == "__auto__" ]]; then
    ACCEL="${BEST_ACCEL:-}"
    [[ -z "$ACCEL" ]] && ACCEL=$(detect_accel)
fi

# Explicit device settings always win. Otherwise use the cached per-device
# benchmark and the ffmpeg processes visible in this PID namespace.
if [[ "$(uname -s)" == "Linux" && "$DRI_DEVICE_WAS_SET" == "false" ]]; then
    SELECTED_DRI_DEVICE=""
    case "$ACCEL" in
        qsv)
            if [[ "$QSV_DEVICE_WAS_SET" == "false" ]]; then
                SELECTED_DRI_DEVICE="$(select_least_loaded_dri_device || true)"
                [[ -n "$SELECTED_DRI_DEVICE" ]] && QSV_DEVICE="$SELECTED_DRI_DEVICE"
            fi
            ;;
        vaapi)
            if [[ "$VAAPI_DEVICE_WAS_SET" == "false" ]]; then
                SELECTED_DRI_DEVICE="$(select_least_loaded_dri_device || true)"
                [[ -n "$SELECTED_DRI_DEVICE" ]] && VAAPI_DEVICE="$SELECTED_DRI_DEVICE"
            fi
            ;;
    esac
fi

SELECTED_SUPPORTS_10BIT_DECODE=false
SELECTED_SUPPORTS_10BIT_ENCODE=false
accel_has_capability "${DECODE_10BIT:-}" "$ACCEL" && SELECTED_SUPPORTS_10BIT_DECODE=true
accel_has_capability "${ENCODE_10BIT:-}" "$ACCEL" && SELECTED_SUPPORTS_10BIT_ENCODE=true
[[ -z "$ALLOW_10BIT" ]] && ALLOW_10BIT="$SELECTED_SUPPORTS_10BIT_ENCODE"
if [[ -z "$ALLOW_HDR" ]]; then
    if [[ "$VCODEC_OUT" == "hevc" && "$SELECTED_SUPPORTS_10BIT_ENCODE" == "true" ]]; then
        ALLOW_HDR=true
    else
        ALLOW_HDR=false
    fi
fi

if [[ -z "$URL" ]]; then
    echo "$LOG_PREFIX ERROR: No stream URL provided" >&2
    exit 1
fi
case "$ACCEL" in
    qsv|vaapi|nvenc|v4l2m2m|videotoolbox|software) ;;
    *) echo "$LOG_PREFIX ERROR: Unknown accel type: $ACCEL (use: qsv, vaapi, nvenc, v4l2m2m, videotoolbox, software)" >&2; exit 1 ;;
esac
case "$VCODEC_OUT" in
    h264|hevc) ;;
    *) echo "$LOG_PREFIX ERROR: Unknown video codec: $VCODEC_OUT (use: h264, hevc)" >&2; exit 1 ;;
esac

if [[ "$URL" =~ ^https?:// ]]; then
    [[ -n "$AGENT" ]] && UA_ARGS=(-user_agent "$AGENT") || UA_ARGS=()
    NET_ARGS=(-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 30 -rw_timeout 15000000)
else
    UA_ARGS=()
    NET_ARGS=()
fi

PIPE_INPUT=false
PIPE_CAPTURE=""
PROBE_TARGET="$URL"
if [[ "$URL" == "pipe:0" || "$URL" == "-" ]]; then
    PIPE_INPUT=true
    URL="pipe:0"
    PIPE_CAPTURE="$(mktemp "${TMPDIR:-/tmp}/ffmpeg-smart-input.XXXXXX.ts")"
    trap '[[ -z "$PIPE_CAPTURE" ]] || rm -f -- "$PIPE_CAPTURE"' EXIT
    capture_status=0
    timeout 4s dd of="$PIPE_CAPTURE" bs=188 status=none || capture_status=$?
    if [[ "$capture_status" != "0" && "$capture_status" != "124" && "$capture_status" != "143" ]] ||
       [[ ! -s "$PIPE_CAPTURE" ]]; then
        echo "$LOG_PREFIX ERROR: Unable to sample pipe input for probing" >&2
        exit 1
    fi
    PROBE_TARGET="$PIPE_CAPTURE"
fi

PROBE=$(ffprobe "${UA_ARGS[@]}" -v quiet -print_format json -show_streams "$PROBE_TARGET" 2>&1) || {
    echo "$LOG_PREFIX ERROR: ffprobe failed - cannot access stream" >&2
    exit 1
}

VCODEC=$(echo "$PROBE" | jq -r '.streams[] | select(.codec_type=="video") | .codec_name' | head -n1)
FPS_FRAC=$(echo "$PROBE" | jq -r '.streams[] | select(.codec_type=="video") | .r_frame_rate' | head -n1)
PIX_FMT=$(echo "$PROBE" | jq -r '.streams[] | select(.codec_type=="video") | .pix_fmt // empty' | head -n1)
COLOR_TRANSFER=$(echo "$PROBE" | jq -r '.streams[] | select(.codec_type=="video") | .color_transfer // empty' | head -n1)
FIELD_ORDER=$(echo "$PROBE" | jq -r '.streams[] | select(.codec_type=="video") | .field_order // "unknown"' | head -n1)
WIDTH=$(echo "$PROBE" | jq -r '.streams[] | select(.codec_type=="video") | .width // 0' | head -n1)
HEIGHT=$(echo "$PROBE" | jq -r '.streams[] | select(.codec_type=="video") | .height // 0' | head -n1)
VBITRATE_RAW=$(echo "$PROBE" | jq -r '.streams[] | select(.codec_type=="video") | .bit_rate // empty' | head -n1)
ACODEC=$(echo "$PROBE" | jq -r '.streams[] | select(.codec_type=="audio") | .codec_name // empty' | head -n1)
ACHANNELS=$(echo "$PROBE" | jq -r '.streams[] | select(.codec_type=="audio") | .channels // empty' | head -n1)
AUDIO_STREAM_COUNT=$(echo "$PROBE" | jq '[.streams[] | select(.codec_type=="audio")] | length')
HAS_AUDIO=false
[[ "$AUDIO_STREAM_COUNT" -gt 0 ]] && HAS_AUDIO=true

if [[ -z "$VCODEC" || "$VCODEC" == "null" ]]; then
    echo "$LOG_PREFIX ERROR: No video stream found" >&2
    exit 1
fi

SOURCE_10BIT=false
[[ "$PIX_FMT" == *"10"* ]] && SOURCE_10BIT=true
IS_HDR=false
[[ "$COLOR_TRANSFER" == "smpte2084" || "$COLOR_TRANSFER" == "arib-std-b67" ]] && IS_HDR=true
SOURCE_INTERLACED=false
case "$FIELD_ORDER" in
    tt|bb|tb|bt) SOURCE_INTERLACED=true ;;
esac

TARGET_WIDTH="$WIDTH"
TARGET_HEIGHT="$HEIGHT"
if [[ -n "$MAX_RES" && "$HEIGHT" -gt "$MAX_RES" ]]; then
    TARGET_HEIGHT="$MAX_RES"
    TARGET_WIDTH=$(( WIDTH * TARGET_HEIGHT / HEIGHT ))
    TARGET_WIDTH=$(( TARGET_WIDTH / 2 * 2 ))
    [[ "$TARGET_WIDTH" -lt 2 ]] && TARGET_WIDTH=2
fi

VIDEO_COPY_REASON=""
VIDEO_TRANSCODE_REASON=""
if [[ "$VCODEC" != "$VCODEC_OUT" ]]; then append_reason "codec ${VCODEC}->${VCODEC_OUT}"; fi
if [[ "$SOURCE_10BIT" == "true" && "$ALLOW_10BIT" != "true" ]]; then append_reason "10-bit not allowed"; fi
if [[ "$IS_HDR" == "true" ]]; then
    if [[ "$FORCE_SDR" == "true" ]]; then append_reason "HDR->SDR"; elif [[ "$ALLOW_HDR" != "true" ]]; then append_reason "HDR not allowed"; fi
fi
if [[ "$TARGET_HEIGHT" -ne "$HEIGHT" ]]; then append_reason "resolution ${WIDTH}x${HEIGHT}->${TARGET_WIDTH}x${TARGET_HEIGHT}"; fi
if [[ "$FORCE_DEINT" == "true" && "$SOURCE_INTERLACED" == "true" ]]; then append_reason "deinterlace ${FIELD_ORDER}->progressive"; fi
if [[ -n "$MAX_BITRATE" ]]; then
    if [[ "$VBITRATE_RAW" =~ ^[0-9]+$ ]]; then
        if [[ "$VBITRATE_RAW" -gt "$MAX_BITRATE" ]]; then append_reason "bitrate ${VBITRATE_RAW}>${MAX_BITRATE}"; fi
    else
        append_reason "bitrate unknown; enforce max ${MAX_BITRATE}"
    fi
fi
if [[ -z "$VIDEO_TRANSCODE_REASON" ]]; then VIDEO_COPY_REASON="matches active video policy"; fi

AUDIO_ARGS=()
AUDIO_INFO="none"
if [[ "$HAS_AUDIO" == "true" ]]; then
    AUDIO_SOURCE_CHANNELS="${ACHANNELS:-0}"
    [[ "$AUDIO_SOURCE_CHANNELS" =~ ^[0-9]+$ ]] || AUDIO_SOURCE_CHANNELS=0
    AUDIO_TARGET_CHANNELS="$AUDIO_SOURCE_CHANNELS"
    if [[ -n "$MAX_CHANNELS" ]]; then
        if [[ "$AUDIO_SOURCE_CHANNELS" -eq 0 || "$AUDIO_SOURCE_CHANNELS" -gt "$MAX_CHANNELS" ]]; then AUDIO_TARGET_CHANNELS="$MAX_CHANNELS"; fi
    fi
    [[ "$AUDIO_TARGET_CHANNELS" -gt 0 ]] || AUDIO_TARGET_CHANNELS="${MAX_CHANNELS:-2}"
    AUDIO_NEEDS_TRANSCODE=false
    [[ "$ACODEC" != "aac" ]] && AUDIO_NEEDS_TRANSCODE=true
    if [[ -n "$MAX_CHANNELS" && ( "$AUDIO_SOURCE_CHANNELS" -eq 0 || "$AUDIO_SOURCE_CHANNELS" -gt "$MAX_CHANNELS" ) ]]; then AUDIO_NEEDS_TRANSCODE=true; fi
    if [[ "$AUDIO_NEEDS_TRANSCODE" == "false" ]]; then
        AUDIO_ARGS=(-c:a copy)
        AUDIO_INFO="aac copy ${AUDIO_SOURCE_CHANNELS}ch"
    else
        CHANNEL_LAYOUT_ARGS=()
        case "$AUDIO_TARGET_CHANNELS" in
            1) ABITRATE=96000; CHANNEL_LAYOUT_ARGS=(-ac 1 -ch_layout mono) ;;
            2) ABITRATE=192000; CHANNEL_LAYOUT_ARGS=(-ac 2 -ch_layout stereo) ;;
            6) ABITRATE=384000; CHANNEL_LAYOUT_ARGS=(-ac 6 -ch_layout 5.1) ;;
            8) ABITRATE=512000; CHANNEL_LAYOUT_ARGS=(-ac 8 -ch_layout 7.1) ;;
            *) ABITRATE=$((64000 * AUDIO_TARGET_CHANNELS)); CHANNEL_LAYOUT_ARGS=(-ac "$AUDIO_TARGET_CHANNELS") ;;
        esac
        AUDIO_ARGS=(-c:a aac -b:a "$ABITRATE" "${CHANNEL_LAYOUT_ARGS[@]}" -af "aresample=async=1")
        if [[ "$AUDIO_SOURCE_CHANNELS" -gt 0 && "$AUDIO_SOURCE_CHANNELS" -ne "$AUDIO_TARGET_CHANNELS" ]]; then
            AUDIO_INFO="${ACODEC:-unknown}->aac ${ABITRATE}bps ${AUDIO_SOURCE_CHANNELS}->${AUDIO_TARGET_CHANNELS}ch"
        else
            AUDIO_INFO="${ACODEC:-unknown}->aac ${ABITRATE}bps ${AUDIO_TARGET_CHANNELS}ch"
        fi
    fi
fi

if [[ -n "$VIDEO_COPY_REASON" ]]; then
    echo "$LOG_PREFIX Detected ${WIDTH}x${HEIGHT} $VCODEC/$PIX_FMT field=${FIELD_ORDER} @ $FPS_FRAC -> copy (${VIDEO_COPY_REASON}) audio=${AUDIO_INFO}" >&2
    exec ffmpeg \
        "${UA_ARGS[@]}" \
        "${NET_ARGS[@]}" \
        -fflags +genpts+igndts+discardcorrupt \
        -err_detect ignore_err \
        -i "$URL" \
        -map 0:v:0 \
        -map 0:a:0? \
        -c:v copy \
        "${AUDIO_ARGS[@]}" \
        -avoid_negative_ts make_zero \
        -start_at_zero \
        -mpegts_copyts 0 \
        -mpegts_flags +pat_pmt_at_frames+resend_headers \
        -flush_packets 1 \
        -max_muxing_queue_size 4096 \
        -f mpegts \
        pipe:1
fi

case "$ACCEL" in
    qsv)
        if [[ -z "$QSV_DEVICE" || ! -e "$QSV_DEVICE" ]]; then echo "$LOG_PREFIX ERROR: QSV render device not available: ${QSV_DEVICE:-none}" >&2; exit 1; fi
        ;;
    vaapi)
        if [[ -z "$VAAPI_DEVICE" || ! -e "$VAAPI_DEVICE" ]]; then echo "$LOG_PREFIX ERROR: VAAPI render device not available: ${VAAPI_DEVICE:-none}" >&2; exit 1; fi
        ;;
esac

ENCODERS="$(ffmpeg -hide_banner -encoders 2>/dev/null || true)"
if [[ "$ACCEL" == "software" ]]; then
    if [[ "$VCODEC_OUT" == "hevc" ]]; then ENCODER="libx265"; TAG_ARGS="-tag:v hvc1"; else ENCODER="libx264"; TAG_ARGS=""; fi
else
    ENCODER="${VCODEC_OUT}_${ACCEL}"
    if ! grep -qw "$ENCODER" <<<"$ENCODERS"; then echo "$LOG_PREFIX ERROR: Encoder $ENCODER not available" >&2; exit 1; fi
    [[ "$VCODEC_OUT" == "hevc" ]] && TAG_ARGS="-tag:v hvc1" || TAG_ARGS=""
fi

NEED_SDR=false
[[ "$FORCE_SDR" == "true" && "$IS_HDR" == "true" ]] && NEED_SDR=true
NEED_DEINT=false
[[ "$FORCE_DEINT" == "true" && "$SOURCE_INTERLACED" == "true" ]] && NEED_DEINT=true

set_hwaccel_args() {
    case "$ACCEL" in
        qsv)
            HWACCEL_ARGS=(
                -init_hw_device "qsv=qsv:hw,child_device=$QSV_DEVICE"
                -filter_hw_device qsv
                -hwaccel qsv
                -hwaccel_device qsv
                -hwaccel_output_format qsv
            )
            ;;
        vaapi) HWACCEL_ARGS=(-hwaccel vaapi -hwaccel_output_format vaapi -vaapi_device "$VAAPI_DEVICE") ;;
        nvenc)
            if [[ "$NEED_SDR" == "true" || "$NEED_DEINT" == "true" ]]; then HWACCEL_ARGS=(); else HWACCEL_ARGS=(-hwaccel cuda -hwaccel_output_format cuda); fi
            ;;
        videotoolbox)
            if [[ "$NEED_SDR" == "true" || "$NEED_DEINT" == "true" ]]; then HWACCEL_ARGS=(); else HWACCEL_ARGS=(-hwaccel videotoolbox); fi
            ;;
        *) HWACCEL_ARGS=() ;;
    esac
}

set_encoder_opts() {
    BF_ARGS="-bf 2"
    case "$ACCEL" in
        qsv)
            if [[ "${BEST_LOW_POWER:-0}" == "1" ]]; then ACCEL_OPTS="-low_power true -look_ahead 0"; BF_ARGS="-bf 0"; else ACCEL_OPTS="-preset faster"; fi
            ;;
        vaapi)
            ACCEL_OPTS="-rc_mode VBR"
            if [[ "${BEST_LOW_POWER:-0}" == "1" ]]; then ACCEL_OPTS+=" -low_power 1"; BF_ARGS="-bf 0"; fi
            ;;
        nvenc) ACCEL_OPTS="-preset p4 -rc vbr" ;;
        videotoolbox) ACCEL_OPTS="-realtime false" ;;
        software) ACCEL_OPTS="-preset faster" ;;
        *) ACCEL_OPTS="" ;;
    esac
}

set_hwaccel_args
set_encoder_opts

OUTPUT_10BIT=false
if [[ "$SOURCE_10BIT" == "true" && "$ALLOW_10BIT" == "true" && "$VCODEC_OUT" == "hevc" && "$NEED_SDR" != "true" ]]; then OUTPUT_10BIT=true; fi
TARGET_PIX_FMT="nv12"
[[ "$OUTPUT_10BIT" == "true" ]] && TARGET_PIX_FMT="p010le"

VF_ARGS=""
PROFILE_ARGS=""
COLOR_ARGS=""

if [[ "$NEED_SDR" == "true" ]]; then
    case "$ACCEL" in
        qsv)
            QSV_VPP="w=${TARGET_WIDTH}:h=${TARGET_HEIGHT}:format=nv12:tonemap=1"
            [[ "$NEED_DEINT" == "true" ]] && QSV_VPP+=":deinterlace=advanced"
            VF_ARGS="-vf vpp_qsv=${QSV_VPP}"
            ;;
        vaapi)
            if [[ "$NEED_DEINT" == "true" ]]; then
                VF_ARGS="-vf deinterlace_vaapi=mode=motion_adaptive:rate=frame:auto=1,tonemap_vaapi=format=nv12,scale_vaapi=w=${TARGET_WIDTH}:h=${TARGET_HEIGHT}:format=nv12"
            else
                VF_ARGS="-vf tonemap_vaapi=format=nv12,scale_vaapi=w=${TARGET_WIDTH}:h=${TARGET_HEIGHT}:format=nv12"
            fi
            ;;
        *)
            SW_PREFIX=""
            [[ "$NEED_DEINT" == "true" ]] && SW_PREFIX="bwdif=mode=send_frame:parity=auto:deint=interlaced,"
            VF_ARGS="-vf ${SW_PREFIX}zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,scale=${TARGET_WIDTH}:${TARGET_HEIGHT},format=yuv420p"
            ;;
    esac
    COLOR_ARGS="-color_primaries bt709 -color_trc bt709 -colorspace bt709"
elif [[ "$NEED_DEINT" == "true" ]]; then
    case "$ACCEL" in
        qsv)
            VF_ARGS="-vf vpp_qsv=w=${TARGET_WIDTH}:h=${TARGET_HEIGHT}:format=${TARGET_PIX_FMT}:deinterlace=advanced"
            [[ "$OUTPUT_10BIT" == "true" ]] && PROFILE_ARGS="-profile:v main10"
            ;;
        vaapi)
            VF_ARGS="-vf deinterlace_vaapi=mode=motion_adaptive:rate=frame:auto=1,scale_vaapi=w=${TARGET_WIDTH}:h=${TARGET_HEIGHT}:format=${TARGET_PIX_FMT}"
            ;;
        *)
            VF_ARGS="-vf bwdif=mode=send_frame:parity=auto:deint=interlaced,scale=${TARGET_WIDTH}:${TARGET_HEIGHT}"
            if [[ "$OUTPUT_10BIT" == "true" ]]; then VF_ARGS+=",format=yuv420p10le"; elif [[ "$SOURCE_10BIT" == "true" ]]; then VF_ARGS+=",format=yuv420p"; fi
            ;;
    esac
elif [[ "$ACCEL" == "qsv" ]]; then
    VF_ARGS="-vf scale_qsv=w=${TARGET_WIDTH}:h=${TARGET_HEIGHT}:format=${TARGET_PIX_FMT}"
    [[ "$OUTPUT_10BIT" == "true" ]] && PROFILE_ARGS="-profile:v main10"
elif [[ "$ACCEL" == "vaapi" ]]; then
    VF_ARGS="-vf scale_vaapi=w=${TARGET_WIDTH}:h=${TARGET_HEIGHT}:format=${TARGET_PIX_FMT}"
elif [[ "$ACCEL" == "nvenc" ]]; then
    if [[ "$TARGET_WIDTH" -ne "$WIDTH" || "$TARGET_HEIGHT" -ne "$HEIGHT" || "$SOURCE_10BIT" == "true" ]]; then VF_ARGS="-vf scale_cuda=w=${TARGET_WIDTH}:h=${TARGET_HEIGHT}:format=${TARGET_PIX_FMT}"; fi
else
    if [[ "$TARGET_WIDTH" -ne "$WIDTH" || "$TARGET_HEIGHT" -ne "$HEIGHT" ]]; then VF_ARGS="-vf scale=${TARGET_WIDTH}:${TARGET_HEIGHT}"; fi
    if [[ "$OUTPUT_10BIT" == "true" ]]; then
        [[ -n "$VF_ARGS" ]] && VF_ARGS="${VF_ARGS},format=yuv420p10le" || VF_ARGS="-vf format=yuv420p10le"
    elif [[ "$SOURCE_10BIT" == "true" ]]; then
        [[ -n "$VF_ARGS" ]] && VF_ARGS="${VF_ARGS},format=yuv420p" || VF_ARGS="-vf format=yuv420p"
    fi
fi

HDR_ARGS=""
if [[ "$IS_HDR" == "true" && "$VCODEC_OUT" == "hevc" && "$ALLOW_HDR" == "true" && "$NEED_SDR" != "true" ]]; then
    HDR_ARGS="-color_primaries bt2020 -color_trc $COLOR_TRANSFER -colorspace bt2020nc"
fi

BASE_VBITRATE=8000000
VBITRATE=$((BASE_VBITRATE * TARGET_WIDTH * TARGET_HEIGHT / 1920 / 1080))
[[ $VBITRATE -lt 2000000 ]] && VBITRATE=2000000
if [[ -n "$MAX_BITRATE" ]]; then
    VBR_TARGET_MAX=$((MAX_BITRATE * 85 / 100))
    [[ "$VBR_TARGET_MAX" -lt 1 ]] && VBR_TARGET_MAX=1
    [[ "$VBITRATE" -gt "$VBR_TARGET_MAX" ]] && VBITRATE="$VBR_TARGET_MAX"
    MAXRATE="$MAX_BITRATE"
    BUFSIZE=$((MAX_BITRATE * 2))
else
    MAXRATE=$((VBITRATE * 125 / 100))
    BUFSIZE=$((VBITRATE * 2))
fi

if [[ "$FPS_FRAC" =~ ^([0-9]+)/([0-9]+)$ ]]; then
    NUM=${BASH_REMATCH[1]}
    DEN=${BASH_REMATCH[2]}
    if [[ $DEN -gt 0 ]]; then GOP=$(( (NUM + DEN/2) / DEN )); FPS_OUT="$FPS_FRAC"; GOP_WARN=""; else GOP=50; FPS_OUT="25/1"; GOP_WARN=" (invalid fps denominator)"; fi
else
    GOP=50
    FPS_OUT="25/1"
    GOP_WARN=" (fps parse failed)"
fi

DEVICE_INFO=""
case "$ACCEL" in qsv) DEVICE_INFO=" device=$QSV_DEVICE" ;; vaapi) DEVICE_INFO=" device=$VAAPI_DEVICE" ;; esac
PROFILE_INFO=""
[[ -n "$MAX_RES" ]] && PROFILE_INFO+=" maxres=${MAX_RES}"
[[ -n "$MAX_BITRATE" ]] && PROFILE_INFO+=" maxbr=${MAX_BITRATE} vbr=${VBITRATE}/${MAXRATE}"
[[ -n "$MAX_CHANNELS" ]] && PROFILE_INFO+=" maxchan=${MAX_CHANNELS}"
[[ "$FORCE_SDR" == "true" ]] && PROFILE_INFO+=" sdr=true"
[[ "$FORCE_DEINT" == "true" ]] && PROFILE_INFO+=" deint=true"

echo "$LOG_PREFIX Detected ${WIDTH}x${HEIGHT} $VCODEC/$PIX_FMT field=${FIELD_ORDER} @ $FPS_FRAC -> $ENCODER ${TARGET_WIDTH}x${TARGET_HEIGHT} reason=${VIDEO_TRANSCODE_REASON} GOP=$GOP${GOP_WARN} audio=${AUDIO_INFO} accel=${ACCEL}${DEVICE_INFO} 10bit=${ALLOW_10BIT} hdr=${ALLOW_HDR}${PROFILE_INFO}" >&2

# These markers are inherited by ffmpeg and let another ffmpeg-smart process
# calculate this job's load from /proc/<pid>/environ without shared state.
export FFMPEG_SMART_INPUT_WIDTH="$WIDTH"
export FFMPEG_SMART_INPUT_HEIGHT="$HEIGHT"
export FFMPEG_SMART_OUTPUT_WIDTH="$TARGET_WIDTH"
export FFMPEG_SMART_OUTPUT_HEIGHT="$TARGET_HEIGHT"
export FFMPEG_SMART_FPS_FRAC="$FPS_OUT"

run_ffmpeg() {
    exec ffmpeg \
        "${UA_ARGS[@]}" \
        "${NET_ARGS[@]}" \
        "${HWACCEL_ARGS[@]}" \
        -reinit_filter 0 \
        -fflags +genpts+igndts+discardcorrupt \
        -err_detect ignore_err \
        -i "$URL" \
        -map 0:v:0 \
        -map 0:a:0? \
        -c:v "$ENCODER" \
        $VF_ARGS \
        $PROFILE_ARGS \
        $HDR_ARGS \
        $COLOR_ARGS \
        -b:v "$VBITRATE" \
        -maxrate "$MAXRATE" \
        -bufsize "$BUFSIZE" \
        -g "$GOP" \
        $BF_ARGS \
        ${ACCEL_OPTS} \
        -fps_mode cfr \
        -r "$FPS_OUT" \
        $TAG_ARGS \
        "${AUDIO_ARGS[@]}" \
        -avoid_negative_ts make_zero \
        -start_at_zero \
        -mpegts_copyts 0 \
        -mpegts_flags +pat_pmt_at_frames+resend_headers \
        -flush_packets 1 \
        -max_muxing_queue_size 4096 \
        -f mpegts \
        pipe:1
}

if [[ "$PIPE_INPUT" == "true" ]]; then
    { cat "$PIPE_CAPTURE"; cat; } | run_ffmpeg
    ffmpeg_status="${PIPESTATUS[1]}"
    exit "$ffmpeg_status"
fi
run_ffmpeg
