#!/usr/bin/env bash

ffsmart_cli_defaults() {
    FFSMART_INPUT=""
    FFSMART_USER_AGENT=""
    FFSMART_ACCEL="auto"
    FFSMART_TARGET_CODEC=""
    FFSMART_MAX_HEIGHT=""
    FFSMART_MAX_BITRATE=""
    FFSMART_MAX_CHANNELS=""
    FFSMART_FORCE_SDR=false
    FFSMART_DEINTERLACE=false
    FFSMART_RECACHE=false
    FFSMART_RECACHE_ONLY=false
    FFSMART_CACHE_STATUS_ONLY=false

    FFSMART_DRI_DEVICE="${DRI_DEVICE:-}"
    FFSMART_QSV_DEVICE="${QSV_DEVICE:-}"
    FFSMART_VAAPI_DEVICE="${VAAPI_DEVICE:-}"
    FFSMART_DRI_EXPLICIT=false
    FFSMART_QSV_EXPLICIT=false
    FFSMART_VAAPI_EXPLICIT=false

    FFSMART_INPUT_MODE="inherit"
    FFSMART_MAP_MODE="inherit"
    FFSMART_VIDEO_MODE="inherit"
    FFSMART_AUDIO_MODE="inherit"
    FFSMART_MUX_MODE="inherit"
    FFSMART_USER_INPUT_ARGS=()
    FFSMART_USER_MAPS=()
    FFSMART_USER_VIDEO_ARGS=()
    FFSMART_USER_AUDIO_ARGS=()
    FFSMART_USER_MUX_ARGS=()
}

ffsmart_need_value() {
    local option="$1" remaining="$2"
    if (( remaining < 2 )); then
        ffsmart_configuration_error "$option requires a value"
        return 64
    fi
}

ffsmart_parse_cli() {
    while (( $# )); do
        case "$1" in
            -i)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_INPUT="$2"; shift 2 ;;
            -user_agent|-user-agent)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_USER_AGENT="$2"; shift 2 ;;
            -accel)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_ACCEL="$(ffsmart_lower "$2")"; shift 2 ;;
            -device|-dri-device)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_DRI_DEVICE="$2"; FFSMART_DRI_EXPLICIT=true; shift 2 ;;
            -qsv-device)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_QSV_DEVICE="$2"; FFSMART_QSV_EXPLICIT=true; shift 2 ;;
            -vaapi-device)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_VAAPI_DEVICE="$2"; FFSMART_VAAPI_EXPLICIT=true; shift 2 ;;
            -vc)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_TARGET_CODEC="$(ffsmart_lower "$2")"; shift 2 ;;
            -maxres)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_MAX_HEIGHT="$2"; shift 2 ;;
            -maxbr)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_MAX_BITRATE="$2"; shift 2 ;;
            -maxchan)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_MAX_CHANNELS="$2"; shift 2 ;;
            -sdr)
                FFSMART_FORCE_SDR=true; shift ;;
            -deint)
                FFSMART_DEINTERLACE=true; shift ;;
            -ffmpeg-input-mode)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_INPUT_MODE="$(ffsmart_lower "$2")"; shift 2 ;;
            -ffmpeg-input-option)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_USER_INPUT_ARGS+=("$2"); shift 2 ;;
            -ffmpeg-map-mode)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_MAP_MODE="$(ffsmart_lower "$2")"; shift 2 ;;
            -ffmpeg-map)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_USER_MAPS+=("$2"); shift 2 ;;
            -ffmpeg-video-mode)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_VIDEO_MODE="$(ffsmart_lower "$2")"; shift 2 ;;
            -ffmpeg-video-option)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_USER_VIDEO_ARGS+=("$2"); shift 2 ;;
            -ffmpeg-audio-mode)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_AUDIO_MODE="$(ffsmart_lower "$2")"; shift 2 ;;
            -ffmpeg-audio-option)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_USER_AUDIO_ARGS+=("$2"); shift 2 ;;
            -ffmpeg-mux-mode)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_MUX_MODE="$(ffsmart_lower "$2")"; shift 2 ;;
            -ffmpeg-mux-option|-ffmpeg-option)
                ffsmart_need_value "$1" "$#" || return
                FFSMART_USER_MUX_ARGS+=("$2"); shift 2 ;;
            --recache)
                FFSMART_RECACHE=true; shift ;;
            --recache-only)
                FFSMART_RECACHE=true; FFSMART_RECACHE_ONLY=true; shift ;;
            --cache-status)
                FFSMART_CACHE_STATUS_ONLY=true; shift ;;
            -h|--help)
                FFSMART_SHOW_HELP=true; shift ;;
            --)
                shift
                (( $# == 0 )) || {
                    ffsmart_configuration_error "Unexpected positional arguments: $*"
                    return 64
                } ;;
            *)
                ffsmart_configuration_error "Unknown option: $1"
                return 64 ;;
        esac
    done
}

ffsmart_validate_mode() {
    local name="$1" mode="$2" allow_all="${3:-false}"
    case "$mode" in
        inherit|add|replace) return 0 ;;
        all) [[ "$allow_all" == true ]] && return 0 ;;
    esac
    ffsmart_configuration_error "$name mode must be inherit, add, replace${allow_all:+, or all}"
}

ffsmart_reserved_advanced_arg() {
    local scope="$1" arg="$2"
    case "$arg" in
        -i|-f|-filter_complex|-filter_complex_script|-lavfi|-progress|-report)
            return 0 ;;
    esac
    case "$scope" in
        input)
            case "$arg" in
                -analyzeduration|-probesize|-hwaccel*|-init_hw_device|-filter_hw_device|-vaapi_device|-qsv_device|-device) return 0 ;;
            esac ;;
        map)
            case "$arg" in -map|-map_channel) return 0 ;; esac ;;
        video)
            case "$arg" in -c:v|-codec:v|-vcodec|-vf|-filter:v|-filter_script:v|-hwaccel*|-init_hw_device|-filter_hw_device) return 0 ;; esac ;;
        audio)
            case "$arg" in -c:v|-codec:v|-vcodec|-vf|-filter:v|-map|-f) return 0 ;; esac ;;
        mux)
            case "$arg" in -i|-map|-c:v|-codec:v|-vcodec|-vf|-filter:v|-c:a|-codec:a|-acodec|-f|pipe:*|-) return 0 ;; esac ;;
    esac
    return 1
}

ffsmart_validate_advanced_scope() {
    local scope="$1" arg
    shift
    for arg in "$@"; do
        if ffsmart_reserved_advanced_arg "$scope" "$arg"; then
            ffsmart_configuration_error "Argument $arg is owned by FFmpeg Smart and is invalid in the $scope scope"
            return 64
        fi
    done
}

ffsmart_validate_advanced_args() {
    ffsmart_validate_advanced_scope input "${FFSMART_USER_INPUT_ARGS[@]}" || return
    ffsmart_validate_advanced_scope video "${FFSMART_USER_VIDEO_ARGS[@]}" || return
    ffsmart_validate_advanced_scope audio "${FFSMART_USER_AUDIO_ARGS[@]}" || return
    ffsmart_validate_advanced_scope mux "${FFSMART_USER_MUX_ARGS[@]}" || return
}

ffsmart_validate_maps() {
    local video_positive=0 spec base
    if [[ "$FFSMART_MAP_MODE" == all ]]; then
        return 0
    fi
    if [[ "$FFSMART_MAP_MODE" == replace && ${#FFSMART_USER_MAPS[@]} -eq 0 ]]; then
        ffsmart_configuration_error "Replacement mapping must select exactly one video stream"
        return 64
    fi
    for spec in "${FFSMART_USER_MAPS[@]}"; do
        base="${spec%?}"
        [[ "$spec" == *\? ]] || base="$spec"
        if [[ "$base" == -*v* ]]; then
            ffsmart_configuration_error "Negative video mappings are not supported"
            return 64
        fi
        if [[ "$base" != -* && "$base" != *:* ]]; then
            ffsmart_configuration_error "Positive mappings must use typed stream specifiers"
            return 64
        fi
        if [[ "$base" != -* && "$base" =~ (^|:)v(:|$) ]]; then
            ((video_positive += 1))
        elif [[ "$base" != -* && ! "$base" =~ (^|:)(a|s|d|t)(:|$) ]]; then
            ffsmart_configuration_error "Positive mappings must identify video, audio, subtitle, data, or attachment streams"
            return 64
        fi
    done
    if [[ "$FFSMART_MAP_MODE" == replace && "$video_positive" -ne 1 ]]; then
        ffsmart_configuration_error "Replacement mapping must select exactly one video stream"
        return 64
    fi
    if [[ "$FFSMART_MAP_MODE" == add && "$video_positive" -gt 0 ]]; then
        ffsmart_configuration_error "Additive mapping cannot add another video stream"
        return 64
    fi
}

ffsmart_validate_cli() {
    case "$FFSMART_ACCEL" in auto|qsv|vaapi|nvenc|videotoolbox|v4l2m2m|software) ;; *) ffsmart_configuration_error "Unsupported accelerator: $FFSMART_ACCEL"; return 64 ;; esac
    if [[ -n "$FFSMART_TARGET_CODEC" && "$FFSMART_TARGET_CODEC" != h264 && "$FFSMART_TARGET_CODEC" != hevc ]]; then
        ffsmart_configuration_error "-vc must be h264 or hevc"
        return 64
    fi
    [[ -z "$FFSMART_MAX_HEIGHT" ]] || ffsmart_positive_integer "$FFSMART_MAX_HEIGHT" || { ffsmart_configuration_error "-maxres must be a positive integer"; return 64; }
    [[ -z "$FFSMART_MAX_CHANNELS" ]] || ffsmart_positive_integer "$FFSMART_MAX_CHANNELS" || { ffsmart_configuration_error "-maxchan must be a positive integer"; return 64; }
    if [[ -n "$FFSMART_MAX_BITRATE" ]]; then
        FFSMART_MAX_BITRATE_BPS="$(ffsmart_parse_bitrate "$FFSMART_MAX_BITRATE")" || { ffsmart_configuration_error "Invalid bitrate: $FFSMART_MAX_BITRATE"; return 64; }
    else
        FFSMART_MAX_BITRATE_BPS=""
    fi
    ffsmart_validate_mode input "$FFSMART_INPUT_MODE" false || return
    ffsmart_validate_mode map "$FFSMART_MAP_MODE" true || return
    ffsmart_validate_mode video "$FFSMART_VIDEO_MODE" false || return
    ffsmart_validate_mode audio "$FFSMART_AUDIO_MODE" false || return
    ffsmart_validate_mode mux "$FFSMART_MUX_MODE" false || return
    ffsmart_validate_advanced_args || return
    ffsmart_validate_maps || return

    if [[ "$FFSMART_CACHE_STATUS_ONLY" == true && "$FFSMART_RECACHE" == true ]]; then
        ffsmart_configuration_error "--cache-status cannot be combined with --recache or --recache-only"
        return 64
    fi
    if [[ "$FFSMART_RECACHE_ONLY" != true && "$FFSMART_CACHE_STATUS_ONLY" != true && -z "$FFSMART_INPUT" ]]; then
        ffsmart_configuration_error "An input is required; use -i INPUT"
        return 64
    fi
}

ffsmart_show_help() {
    cat <<'EOF'
Usage: ffmpeg-smart.sh -i INPUT [options]

Normalizes one video program to MPEG-TS on stdout. Use --cache-status to inspect
capability state or --recache-only to rebuild it without an input.
EOF
}
