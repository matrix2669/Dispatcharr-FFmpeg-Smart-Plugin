#!/usr/bin/env bash

FFSMART_INPUT_ARGS=()
FFSMART_MAP_ARGS=()
FFSMART_VIDEO_TUNING_ARGS=()
FFSMART_AUDIO_ARGS=()
FFSMART_MUX_ARGS=()
FFSMART_AUXILIARY_ARGS=()
FFSMART_VIDEO_POLICY_ARGS=()
FFSMART_FILTER_ARGS=()
FFSMART_HW_INPUT_ARGS=()

ffsmart_resolve_static_groups() {
    local managed_input=(-fflags +genpts+igndts+discardcorrupt -err_detect ignore_err)
    local managed_mux=(-avoid_negative_ts make_zero -start_at_zero -mpegts_copyts 0 -mpegts_flags +pat_pmt_at_frames+resend_headers -flush_packets 1 -max_muxing_queue_size 4096)
    local managed_video=(-g 60 -bf 3)
    FFSMART_INPUT_ARGS=(); [[ "$FFSMART_INPUT_MODE" == replace ]] || FFSMART_INPUT_ARGS+=("${managed_input[@]}"); FFSMART_INPUT_ARGS+=("${FFSMART_USER_INPUT_ARGS[@]}")
    FFSMART_MUX_ARGS=(); [[ "$FFSMART_MUX_MODE" == replace ]] || FFSMART_MUX_ARGS+=("${managed_mux[@]}"); FFSMART_MUX_ARGS+=("${FFSMART_USER_MUX_ARGS[@]}")
    FFSMART_VIDEO_TUNING_ARGS=(); [[ "$FFSMART_VIDEO_MODE" == replace ]] || FFSMART_VIDEO_TUNING_ARGS+=("${managed_video[@]}"); FFSMART_VIDEO_TUNING_ARGS+=("${FFSMART_USER_VIDEO_ARGS[@]}")

    FFSMART_MAP_ARGS=()
    case "$FFSMART_MAP_MODE" in
        inherit)
            FFSMART_MAP_ARGS=(-map 0:v:0 -map '0:a:0?')
            local spec
            for spec in "${FFSMART_USER_MAPS[@]}"; do FFSMART_MAP_ARGS+=( -map "$spec" ); done ;;
        add)
            FFSMART_MAP_ARGS=(-map 0:v:0 -map '0:a:0?')
            local spec
            for spec in "${FFSMART_USER_MAPS[@]}"; do FFSMART_MAP_ARGS+=( -map "$spec" ); done ;;
        replace)
            local spec
            for spec in "${FFSMART_USER_MAPS[@]}"; do FFSMART_MAP_ARGS+=( -map "$spec" ); done ;;
        all)
            FFSMART_MAP_ARGS=(-map 0) ;;
    esac
}

ffsmart_input_is_url() {
    [[ "$FFSMART_INPUT" =~ ^(https?|rtsp|rtmp|srt|udp|tcp):// ]]
}

ffsmart_input_is_http() {
    [[ "$FFSMART_INPUT" =~ ^https?:// ]]
}

ffsmart_dynamic_input_args() {
    FFSMART_DYNAMIC_INPUT_ARGS=()
    if [[ -n "$FFSMART_USER_AGENT" ]]; then
        FFSMART_DYNAMIC_INPUT_ARGS+=( -user_agent "$FFSMART_USER_AGENT" )
    fi
    if ffsmart_input_is_http; then
        FFSMART_DYNAMIC_INPUT_ARGS+=( -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 )
    fi
}

ffsmart_is_hdr_input() {
    case "$(ffsmart_lower "$FFSMART_VIDEO_COLOR_TRANSFER")" in
        smpte2084|arib-std-b67) return 0 ;;
    esac
    case "$(ffsmart_lower "$FFSMART_VIDEO_PIX_FMT")" in
        *10*|p010*) [[ "$(ffsmart_lower "$FFSMART_VIDEO_COLOR_PRIMARIES")" == bt2020 ]] && return 0 ;;
    esac
    return 1
}

ffsmart_is_interlaced_input() {
    case "$(ffsmart_lower "$FFSMART_VIDEO_FIELD_ORDER")" in
        tt|bb|tb|bt|interlaced) return 0 ;;
        *) return 1 ;;
    esac
}

ffsmart_choose_output_dimensions() {
    FFSMART_OUTPUT_HEIGHT="$FFSMART_VIDEO_HEIGHT"
    FFSMART_OUTPUT_WIDTH="$FFSMART_VIDEO_WIDTH"
    if [[ -n "$FFSMART_MAX_HEIGHT" ]] && (( FFSMART_VIDEO_HEIGHT > FFSMART_MAX_HEIGHT )); then
        FFSMART_OUTPUT_HEIGHT="$FFSMART_MAX_HEIGHT"
        FFSMART_OUTPUT_WIDTH="$(awk -v w="$FFSMART_VIDEO_WIDTH" -v h="$FFSMART_VIDEO_HEIGHT" -v oh="$FFSMART_OUTPUT_HEIGHT" 'BEGIN { ow=int((w*oh/h)/2)*2; if(ow<2)ow=2; print ow }')"
    fi
}

ffsmart_resolve_video_policy() {
    FFSMART_VIDEO_TRANSCODE=false
    FFSMART_VIDEO_REASONS=()
    FFSMART_TARGET_CODEC="${FFSMART_TARGET_CODEC:-${FFSMART_CACHE_BEST_CODEC:-h264}}"
    FFSMART_SELECTED_ACCEL="${FFSMART_ACCEL}"
    [[ "$FFSMART_SELECTED_ACCEL" != auto ]] || FFSMART_SELECTED_ACCEL="${FFSMART_CACHE_BEST_ACCEL:-software}"
    ffsmart_choose_output_dimensions

    if [[ "$(ffsmart_lower "$FFSMART_VIDEO_CODEC")" != "$FFSMART_TARGET_CODEC" ]]; then
        FFSMART_VIDEO_TRANSCODE=true; FFSMART_VIDEO_REASONS+=("codec ${FFSMART_VIDEO_CODEC:-unknown} -> $FFSMART_TARGET_CODEC")
    fi
    if [[ -n "$FFSMART_MAX_HEIGHT" ]] && (( FFSMART_VIDEO_HEIGHT > FFSMART_MAX_HEIGHT )); then
        FFSMART_VIDEO_TRANSCODE=true; FFSMART_VIDEO_REASONS+=("height $FFSMART_VIDEO_HEIGHT > $FFSMART_MAX_HEIGHT")
    fi
    if [[ -n "$FFSMART_MAX_BITRATE_BPS" ]]; then
        if [[ ! "$FFSMART_VIDEO_BITRATE" =~ ^[1-9][0-9]*$ ]]; then
            FFSMART_VIDEO_TRANSCODE=true; FFSMART_VIDEO_REASONS+=("unknown bitrate cannot prove ceiling")
        elif (( FFSMART_VIDEO_BITRATE > FFSMART_MAX_BITRATE_BPS )); then
            FFSMART_VIDEO_TRANSCODE=true; FFSMART_VIDEO_REASONS+=("bitrate $FFSMART_VIDEO_BITRATE > $FFSMART_MAX_BITRATE_BPS")
        fi
    fi
    if [[ "$FFSMART_FORCE_SDR" == true ]] && ffsmart_is_hdr_input; then
        FFSMART_VIDEO_TRANSCODE=true; FFSMART_VIDEO_REASONS+=("HDR -> SDR")
    fi
    if [[ "$FFSMART_DEINTERLACE" == true ]] && ffsmart_is_interlaced_input; then
        FFSMART_VIDEO_TRANSCODE=true; FFSMART_VIDEO_REASONS+=("interlaced -> progressive")
    fi
}

ffsmart_audio_bitrate_for_channels() {
    case "$1" in
        1) printf '96k' ;;
        2) printf '192k' ;;
        6) printf '384k' ;;
        8) printf '512k' ;;
        *) printf '%sk' "$(( $1 * 64 ))" ;;
    esac
}

ffsmart_resolve_audio_policy() {
    local managed=() out_channels="$FFSMART_AUDIO_MAX_CHANNELS" transcode=false
    if (( FFSMART_AUDIO_COUNT == 0 )); then
        FFSMART_AUDIO_ARGS=()
        return 0
    fi
    [[ "$FFSMART_AUDIO_ALL_AAC" == true ]] || transcode=true
    if [[ -n "$FFSMART_MAX_CHANNELS" ]] && (( FFSMART_AUDIO_MAX_CHANNELS > FFSMART_MAX_CHANNELS )); then
        out_channels="$FFSMART_MAX_CHANNELS"; transcode=true
    fi
    if [[ "$transcode" == false ]]; then
        managed=(-c:a copy)
    else
        (( out_channels > 0 )) || out_channels=2
        managed=(-c:a aac -b:a "$(ffsmart_audio_bitrate_for_channels "$out_channels")" -af aresample=async=1)
        if [[ -n "$FFSMART_MAX_CHANNELS" ]] && (( FFSMART_AUDIO_MAX_CHANNELS > FFSMART_MAX_CHANNELS )); then
            managed+=( -ac "$FFSMART_MAX_CHANNELS" )
        fi
    fi
    FFSMART_AUDIO_ARGS=()
    [[ "$FFSMART_AUDIO_MODE" == replace ]] || FFSMART_AUDIO_ARGS+=("${managed[@]}")
    FFSMART_AUDIO_ARGS+=("${FFSMART_USER_AUDIO_ARGS[@]}")
    if [[ -n "$FFSMART_MAX_CHANNELS" ]] && (( FFSMART_AUDIO_MAX_CHANNELS > FFSMART_MAX_CHANNELS )) && [[ "$FFSMART_AUDIO_MODE" == replace ]]; then
        FFSMART_AUDIO_ARGS+=( -ac "$FFSMART_MAX_CHANNELS" )
    fi
}

ffsmart_normal_video_bitrate() {
    local width="$1" height="$2" bitrate
    bitrate=$((8000000 * width * height / 1920 / 1080))
    (( bitrate < 2000000 )) && bitrate=2000000
    printf '%s' "$bitrate"
}

ffsmart_resolve_rate_control() {
    FFSMART_VIDEO_POLICY_ARGS=()
    local target max buffer normal
    normal="$(ffsmart_normal_video_bitrate "$FFSMART_OUTPUT_WIDTH" "$FFSMART_OUTPUT_HEIGHT")"
    if [[ -n "$FFSMART_MAX_BITRATE_BPS" ]]; then
        max="$FFSMART_MAX_BITRATE_BPS"
        target="$(( max * 85 / 100 ))"
        (( normal < target )) && target="$normal"
        buffer="$(( max * 2 ))"
        FFSMART_VIDEO_POLICY_ARGS+=( -b:v "$target" -maxrate "$max" -bufsize "$buffer" )
    else
        FFSMART_VIDEO_POLICY_ARGS+=( -b:v "$normal" -maxrate "$((normal * 6 / 5))" -bufsize "$((normal * 2))" )
    fi
    if [[ "$FFSMART_FORCE_SDR" == true ]] && ffsmart_is_hdr_input; then
        FFSMART_VIDEO_POLICY_ARGS+=( -color_primaries bt709 -color_trc bt709 -colorspace bt709 )
    fi
}

ffsmart_build_filters() {
    FFSMART_FILTER_ARGS=()
    local need_scale=false need_deint=false need_tonemap=false tenbit=false input_tenbit=false filter=""
    [[ "$FFSMART_OUTPUT_HEIGHT" != "$FFSMART_VIDEO_HEIGHT" ]] && need_scale=true
    [[ "$FFSMART_DEINTERLACE" == true ]] && ffsmart_is_interlaced_input && need_deint=true
    [[ "$FFSMART_FORCE_SDR" == true ]] && ffsmart_is_hdr_input && need_tonemap=true
    [[ "$FFSMART_VIDEO_PIX_FMT" =~ (10|p010) ]] && input_tenbit=true
    if [[ "$FFSMART_TARGET_CODEC" == hevc && "$input_tenbit" == true && "${FFSMART_SELECTED_10BIT_ENCODE:-false}" == true ]]; then
        tenbit=true
    fi

    case "$FFSMART_SELECTED_ACCEL" in
        qsv)
            local opts=()
            if [[ "$need_tonemap" == true ]]; then
                FFSMART_HW_INPUT_ARGS=(-init_hw_device "qsv=ffsmart:hw,child_device=$FFSMART_SELECTED_DEVICE" -filter_hw_device ffsmart)
                filter='zscale=t=linear:npl=100,format=gbrpf32le,tonemap=hable:desat=0,zscale=p=bt709:t=bt709:m=bt709:r=tv,format=nv12,hwupload=extra_hw_frames=64'
                FFSMART_FILTER_ARGS=(-vf "$filter")
                return 0
            fi
            [[ "$need_scale" == true ]] && opts+=("w=$FFSMART_OUTPUT_WIDTH" "h=$FFSMART_OUTPUT_HEIGHT")
            [[ "$need_deint" == true ]] && opts+=("deinterlace=advanced")
            if [[ "$tenbit" == false ]]; then opts+=("format=nv12"); else opts+=("format=p010"); fi
            filter="vpp_qsv=$(ffsmart_join_by : "${opts[@]}")"
            FFSMART_FILTER_ARGS=(-vf "$filter") ;;
        vaapi)
            local chain=()
            if [[ "$need_tonemap" == true ]]; then
                FFSMART_HW_INPUT_ARGS=(-init_hw_device "vaapi=ffsmart:$FFSMART_SELECTED_DEVICE" -filter_hw_device ffsmart)
                chain+=("zscale=t=linear:npl=100" "format=gbrpf32le" "tonemap=hable:desat=0" "zscale=p=bt709:t=bt709:m=bt709:r=tv" "format=nv12" "hwupload")
                FFSMART_FILTER_ARGS=(-vf "$(ffsmart_join_by , "${chain[@]}")")
                return 0
            fi
            [[ "$need_deint" == true ]] && chain+=("deinterlace_vaapi=mode=motion_adaptive:rate=frame")
            if [[ "$need_scale" == true ]] || { [[ "$input_tenbit" == true ]] && [[ "$tenbit" == false ]]; }; then
                if [[ "$tenbit" == true ]]; then chain+=("scale_vaapi=w=$FFSMART_OUTPUT_WIDTH:h=$FFSMART_OUTPUT_HEIGHT:format=p010"); else chain+=("scale_vaapi=w=$FFSMART_OUTPUT_WIDTH:h=$FFSMART_OUTPUT_HEIGHT:format=nv12"); fi
            fi
            if ((${#chain[@]})); then FFSMART_FILTER_ARGS=(-vf "$(ffsmart_join_by , "${chain[@]}")"); fi ;;
        *)
            local chain=()
            [[ "$need_deint" == true ]] && chain+=("bwdif=mode=send_frame:parity=auto:deint=interlaced")
            [[ "$need_tonemap" == true ]] && chain+=("zscale=t=linear:npl=100,tonemap=hable,zscale=p=bt709:t=bt709:m=bt709:r=tv")
            [[ "$need_scale" == true ]] && chain+=("scale=$FFSMART_OUTPUT_WIDTH:$FFSMART_OUTPUT_HEIGHT")
            if ((${#chain[@]})); then FFSMART_FILTER_ARGS=(-vf "$(ffsmart_join_by , "${chain[@]}")"); fi ;;
    esac
}

ffsmart_build_hardware_args() {
    FFSMART_HW_INPUT_ARGS=()
    FFSMART_ENCODER_ARGS=()
    local device="$FFSMART_SELECTED_DEVICE" encoder
    case "$FFSMART_SELECTED_ACCEL" in
        qsv)
            encoder="${FFSMART_TARGET_CODEC}_qsv"
            ffsmart_build_hardware_decode_args qsv "$device" || return
            FFSMART_HW_INPUT_ARGS=("${FFSMART_HW_DECODE_ARGS[@]}")
            FFSMART_ENCODER_ARGS=(-c:v "$encoder") ;;
        vaapi)
            encoder="${FFSMART_TARGET_CODEC}_vaapi"
            ffsmart_build_hardware_decode_args vaapi "$device" || return
            FFSMART_HW_INPUT_ARGS=("${FFSMART_HW_DECODE_ARGS[@]}")
            FFSMART_ENCODER_ARGS=(-c:v "$encoder") ;;
        nvenc)
            encoder="${FFSMART_TARGET_CODEC}_nvenc"; FFSMART_ENCODER_ARGS=(-c:v "$encoder") ;;
        videotoolbox)
            encoder="${FFSMART_TARGET_CODEC}_videotoolbox"; FFSMART_ENCODER_ARGS=(-c:v "$encoder") ;;
        v4l2m2m)
            encoder="${FFSMART_TARGET_CODEC}_v4l2m2m"; FFSMART_ENCODER_ARGS=(-c:v "$encoder") ;;
        software)
            if [[ "$FFSMART_TARGET_CODEC" == hevc ]]; then encoder=libx265; else encoder=libx264; fi
            FFSMART_ENCODER_ARGS=(-c:v "$encoder" -preset veryfast) ;;
    esac
    [[ "${FFSMART_SELECTED_LOW_POWER:-0}" == 1 && "$FFSMART_SELECTED_ACCEL" =~ ^(qsv|vaapi)$ ]] && FFSMART_ENCODER_ARGS+=( -low_power 1 )
    return 0
}

ffsmart_resolve_auxiliary_policy() {
    FFSMART_AUXILIARY_ARGS=()
    if [[ "$FFSMART_MAP_MODE" == all || "$FFSMART_AUXILIARY_COUNT" -gt 0 ]]; then
        FFSMART_AUXILIARY_ARGS=(-c:s copy -c:d copy -c:t copy)
    fi
}

ffsmart_export_workload() {
    export FFMPEG_SMART_INPUT_WIDTH="$FFSMART_VIDEO_WIDTH"
    export FFMPEG_SMART_INPUT_HEIGHT="$FFSMART_VIDEO_HEIGHT"
    export FFMPEG_SMART_OUTPUT_WIDTH="$FFSMART_OUTPUT_WIDTH"
    export FFMPEG_SMART_OUTPUT_HEIGHT="$FFSMART_OUTPUT_HEIGHT"
    export FFMPEG_SMART_FPS_FRAC="$FFSMART_VIDEO_FPS"
}

ffsmart_final_input_name() {
    if [[ "$FFSMART_IS_PIPE" == true ]]; then printf 'pipe:0'; else printf '%s' "$FFSMART_INPUT"; fi
}

ffsmart_run_command() {
    local -a command=("$@")
    local status
    if [[ "$FFSMART_IS_PIPE" != true ]] && ! ffsmart_input_is_url; then
        ffsmart_lock_release
        exec "${command[@]}"
    fi
    exec 3>&1
    set +e
    if [[ "$FFSMART_IS_PIPE" == true ]]; then
        { cat "$FFSMART_PIPE_SAMPLE"; cat; } | "${command[@]}" 2>&1 1>&3 | ffsmart_redact_diagnostics >&2
        local statuses=("${PIPESTATUS[@]}")
        status="${statuses[1]}"
        ffsmart_cleanup_pipe_sample
    else
        "${command[@]}" 2>&1 1>&3 | ffsmart_redact_diagnostics >&2
        local statuses=("${PIPESTATUS[@]}")
        status="${statuses[0]}"
    fi
    exec 3>&-
    set -e
    return "$status"
}

ffsmart_run_degraded_proxy() {
    local reason="$1" input_name
    ffsmart_warn degraded-proxy "$reason; running stream-copy proxy"
    ffsmart_write_fallback_marker
    ffsmart_dynamic_input_args
    ffsmart_resolve_static_groups
    input_name="$(ffsmart_final_input_name)"
    local command=(ffmpeg -hide_banner -nostdin "${FFSMART_DYNAMIC_INPUT_ARGS[@]}" "${FFSMART_INPUT_ARGS[@]}" -i "$input_name" "${FFSMART_MAP_ARGS[@]}" -c copy "${FFSMART_MUX_ARGS[@]}" -f mpegts pipe:1)
    ffsmart_run_command "${command[@]}"
}

ffsmart_run_normal_pipeline() {
    ffsmart_resolve_static_groups
    ffsmart_dynamic_input_args
    ffsmart_resolve_video_policy
    ffsmart_resolve_audio_policy
    ffsmart_resolve_auxiliary_policy
    ffsmart_export_workload
    local input_name
    input_name="$(ffsmart_final_input_name)"

    if [[ "$FFSMART_VIDEO_TRANSCODE" == false ]]; then
        ffsmart_log "Video copy: source satisfies codec, resolution, bitrate, HDR, and deinterlace policy"
        local command=(ffmpeg -hide_banner -nostdin "${FFSMART_DYNAMIC_INPUT_ARGS[@]}" "${FFSMART_INPUT_ARGS[@]}" "${FFSMART_PROBE_ARGS[@]}" -i "$input_name" "${FFSMART_MAP_ARGS[@]}" -c:v copy "${FFSMART_AUDIO_ARGS[@]}" "${FFSMART_AUXILIARY_ARGS[@]}" "${FFSMART_MUX_ARGS[@]}" -f mpegts pipe:1)
        ffsmart_run_command "${command[@]}"
        return
    fi

    ffsmart_log "Video transcode: $(ffsmart_join_by '; ' "${FFSMART_VIDEO_REASONS[@]}")"
    ffsmart_select_device "$FFSMART_SELECTED_ACCEL" "$FFSMART_TARGET_CODEC" || return
    ffsmart_apply_selected_device_policy
    ffsmart_build_hardware_args
    ffsmart_build_filters
    ffsmart_resolve_rate_control
    local command=(ffmpeg -hide_banner -nostdin "${FFSMART_HW_INPUT_ARGS[@]}" "${FFSMART_DYNAMIC_INPUT_ARGS[@]}" "${FFSMART_INPUT_ARGS[@]}" "${FFSMART_PROBE_ARGS[@]}" -i "$input_name" "${FFSMART_MAP_ARGS[@]}" "${FFSMART_ENCODER_ARGS[@]}" "${FFSMART_FILTER_ARGS[@]}" "${FFSMART_VIDEO_TUNING_ARGS[@]}" "${FFSMART_VIDEO_POLICY_ARGS[@]}" "${FFSMART_AUDIO_ARGS[@]}" "${FFSMART_AUXILIARY_ARGS[@]}" "${FFSMART_MUX_ARGS[@]}" -f mpegts pipe:1)
    ffsmart_run_command "${command[@]}"
}
