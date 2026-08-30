#!/usr/bin/env bash

# Shared primitives for the independently structured FFmpeg Smart runtime.

FFSMART_NAME="ffmpeg-smart"
FFSMART_CACHE_SCHEMA="2"
FFSMART_CAPACITY_POLICY="2"

ffsmart_log() {
    printf '[%s] %s\n' "$FFSMART_NAME" "$*" >&2
}

ffsmart_warn() {
    printf '[%s] WARNING [%s]: %s\n' "$FFSMART_NAME" "$1" "$2" >&2
}

ffsmart_redact_diagnostics() {
    sed -E 's#((https?|rtsp|rtmp|srt|udp|tcp)://)[^[:space:]]+#\1[redacted]#g'
}

ffsmart_fail() {
    local status="$1" code="$2" message="$3"
    printf '[%s] ERROR [%s]: %s\n' "$FFSMART_NAME" "$code" "$message" >&2
    return "$status"
}

ffsmart_configuration_error() {
    ffsmart_fail 64 configuration "$1"
}

ffsmart_is_true() {
    case "$(ffsmart_lower "$1")" in
        1|true|yes|on) return 0 ;;
        *) return 1 ;;
    esac
}

ffsmart_lower() {
    printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

ffsmart_hash_text() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 | awk '{print $1}'
    else
        cksum | awk '{print $1 ":" $2}'
    fi
}

ffsmart_realpath() {
    if command -v realpath >/dev/null 2>&1; then
        realpath "$1"
    elif command -v readlink >/dev/null 2>&1; then
        readlink -f "$1" 2>/dev/null || printf '%s\n' "$1"
    else
        printf '%s\n' "$1"
    fi
}

ffsmart_init_state() {
    local default_state
    default_state="$(cd "$(dirname "$FFSMART_ENTRYPOINT")" && pwd)"
    FFSMART_STATE_DIR="${FFMPEG_SMART_STATE_DIR:-$default_state}"
    FFSMART_CACHE_FILE="$FFSMART_STATE_DIR/.capabilities.cache"
    FFSMART_LOCK_FILE="$FFSMART_STATE_DIR/.benchmark.lock"
    FFSMART_SAMPLE_FILE="$FFSMART_STATE_DIR/probe-sample.mkv"

    if ! mkdir -p -- "$FFSMART_STATE_DIR" 2>/dev/null || [[ ! -d "$FFSMART_STATE_DIR" || ! -w "$FFSMART_STATE_DIR" ]]; then
        ffsmart_fail 73 state-directory "Cannot create or write state directory: $FFSMART_STATE_DIR"
        return 73
    fi
}

ffsmart_process_start_time() {
    local pid="$1"
    [[ -r "/proc/$pid/stat" ]] || return 1
    awk '{print $22}' "/proc/$pid/stat" 2>/dev/null
}

ffsmart_lock_is_live() {
    [[ -f "$FFSMART_LOCK_FILE" ]] || return 1
    local owner="" recorded_start="" current_start="" modified="" now=""
    read -r owner recorded_start < "$FFSMART_LOCK_FILE" || true
    if [[ "$owner" =~ ^[0-9]+$ ]] && kill -0 "$owner" 2>/dev/null; then
        if [[ -z "$recorded_start" ]]; then
            return 0
        fi
        current_start="$(ffsmart_process_start_time "$owner" || true)"
        [[ -n "$current_start" && "$current_start" == "$recorded_start" ]] && return 0
    fi
    if [[ -z "$owner" ]]; then
        if modified="$(stat -c %Y "$FFSMART_LOCK_FILE" 2>/dev/null)"; then
            now="$(date +%s)"
            (( now - modified < 60 )) && return 0
        fi
    fi
    rm -f -- "$FFSMART_LOCK_FILE"
    return 1
}

FFSMART_LOCK_OWNER_PID=""
FFSMART_LOCK_OWNER_START=""
ffsmart_lock_release() {
    [[ -n "$FFSMART_LOCK_OWNER_PID" ]] || return 0
    if (( ${BASH_SUBSHELL:-0} != 0 )); then
        return 0
    fi
    [[ -f "$FFSMART_LOCK_FILE" ]] || return 0
    local recorded="" recorded_start=""
    read -r recorded recorded_start < "$FFSMART_LOCK_FILE" || true
    [[ "$recorded" == "$FFSMART_LOCK_OWNER_PID" ]] || return 0
    [[ -z "$FFSMART_LOCK_OWNER_START" || "$recorded_start" == "$FFSMART_LOCK_OWNER_START" ]] || return 0
    rm -f -- "$FFSMART_LOCK_FILE"
}

ffsmart_exit_cleanup() {
    if type ffsmart_cleanup_pipe_sample >/dev/null 2>&1; then
        ffsmart_cleanup_pipe_sample
    fi
    ffsmart_lock_release
    return 0
}

ffsmart_lock_acquire() {
    if ffsmart_lock_is_live; then
        ffsmart_fail 75 benchmark-lock "Hardware benchmark is already in progress"
        return 75
    fi
    FFSMART_LOCK_OWNER_PID="$$"
    FFSMART_LOCK_OWNER_START="$(ffsmart_process_start_time "$FFSMART_LOCK_OWNER_PID" || true)"
    umask 077
    printf '%s%s%s\n' "$FFSMART_LOCK_OWNER_PID" "${FFSMART_LOCK_OWNER_START:+ }" "$FFSMART_LOCK_OWNER_START" > "$FFSMART_LOCK_FILE" || {
        ffsmart_fail 73 benchmark-lock "Cannot create benchmark lock: $FFSMART_LOCK_FILE"
        return 73
    }
    trap ffsmart_exit_cleanup EXIT HUP INT TERM
}

ffsmart_write_fallback_marker() {
    local marker="${FFMPEG_SMART_FALLBACK_MARKER:-}"
    [[ -n "$marker" ]] || return 0
    local marker_dir
    marker_dir="$(dirname "$marker")"
    if ! mkdir -p -- "$marker_dir" 2>/dev/null || ! printf '%s-%s-%s\n' "$(date +%s%N 2>/dev/null || date +%s)" "$$" "$RANDOM" > "$marker" 2>/dev/null; then
        ffsmart_warn fallback-marker "Could not write fallback marker: $marker"
    fi
}

ffsmart_numeric() {
    [[ "$1" =~ ^[0-9]+([.][0-9]+)?$ ]]
}

ffsmart_positive_integer() {
    [[ "$1" =~ ^[1-9][0-9]*$ ]]
}

ffsmart_parse_bitrate() {
    local input number suffix multiplier
    input="$(ffsmart_lower "$1")"
    input="${input%bps}"
    if [[ "$input" =~ ^([0-9]+([.][0-9]+)?)([kmg]?)$ ]]; then
        number="${BASH_REMATCH[1]}"
        suffix="${BASH_REMATCH[3]}"
        case "$suffix" in
            k) multiplier=1000 ;;
            m) multiplier=1000000 ;;
            g) multiplier=1000000000 ;;
            *) multiplier=1 ;;
        esac
        awk -v n="$number" -v m="$multiplier" 'BEGIN { printf "%.0f\n", n*m }'
        return 0
    fi
    return 1
}

ffsmart_fraction_to_decimal() {
    local value="$1"
    if [[ "$value" =~ ^([0-9]+)/(0*[1-9][0-9]*)$ ]]; then
        awk -v n="${BASH_REMATCH[1]}" -v d="${BASH_REMATCH[2]}" 'BEGIN { printf "%.9f", n/d }'
    elif ffsmart_numeric "$value"; then
        printf '%s' "$value"
    else
        printf '0'
    fi
}

ffsmart_join_by() {
    local separator="$1"
    shift
    local out="" value
    for value in "$@"; do
        if [[ -n "$out" ]]; then
            out+="$separator"
        fi
        out+="$value"
    done
    printf '%s' "$out"
}
