#!/usr/bin/env bash

FFSMART_PROBE_INPUT=""
FFSMART_PROBE_TIER=""
FFSMART_PROBE_ARGS=()
FFSMART_PIPE_SAMPLE=""
FFSMART_IS_PIPE=false

ffsmart_capture_pipe_sample() {
    FFSMART_PIPE_SAMPLE="$(mktemp "$FFSMART_STATE_DIR/pipe-sample.XXXXXX.ts")" || {
        ffsmart_fail 73 pipe-sample "Could not create pipe sample"
        return 73
    }
    if command -v timeout >/dev/null 2>&1; then
        timeout --signal=TERM 4 dd bs=65536 of="$FFSMART_PIPE_SAMPLE" status=none 2>/dev/null || {
            local status=$?
            [[ "$status" -eq 124 || "$status" -eq 143 ]] || return "$status"
        }
    else
        dd bs=65536 count=64 of="$FFSMART_PIPE_SAMPLE" status=none 2>/dev/null || true
    fi
    [[ -s "$FFSMART_PIPE_SAMPLE" ]] || {
        ffsmart_fail 65 pipe-sample "No media was received on stdin"
        return 65
    }
    FFSMART_PROBE_INPUT="$FFSMART_PIPE_SAMPLE"
    FFSMART_IS_PIPE=true
}

ffsmart_prepare_probe_input() {
    case "$FFSMART_INPUT" in
        -|pipe:0)
            ffsmart_capture_pipe_sample ;;
        *)
            FFSMART_PROBE_INPUT="$FFSMART_INPUT" ;;
    esac
}

ffsmart_probe_value() {
    local line="$1" wanted="$2" part
    IFS='|' read -r -a parts <<< "$line"
    for part in "${parts[@]}"; do
        if [[ "$part" == "$wanted="* ]]; then
            printf '%s' "${part#*=}"
            return 0
        fi
    done
    return 1
}

ffsmart_reset_media_info() {
    FFSMART_VIDEO_COUNT=0
    FFSMART_VIDEO_CODEC=""
    FFSMART_VIDEO_PROFILE=""
    FFSMART_VIDEO_PIX_FMT=""
    FFSMART_VIDEO_WIDTH=0
    FFSMART_VIDEO_HEIGHT=0
    FFSMART_VIDEO_FPS="0/1"
    FFSMART_VIDEO_FIELD_ORDER="unknown"
    FFSMART_VIDEO_BITRATE=0
    FFSMART_VIDEO_COLOR_SPACE=""
    FFSMART_VIDEO_COLOR_TRANSFER=""
    FFSMART_VIDEO_COLOR_PRIMARIES=""
    FFSMART_AUDIO_COUNT=0
    FFSMART_AUDIO_ALL_AAC=true
    FFSMART_AUDIO_MAX_CHANNELS=0
    FFSMART_AUDIO_SAMPLE_RATE=0
    FFSMART_AUDIO_SUMMARY=""
    FFSMART_AUXILIARY_COUNT=0
}

ffsmart_parse_probe_output() {
    local file="$1" line type codec width height pix channels rate profile index stream_key seen
    local seen_streams=()
    ffsmart_reset_media_info
    while IFS= read -r line; do
        [[ -n "$line" ]] || continue
        type="$(ffsmart_probe_value "$line" codec_type || true)"
        codec="$(ffsmart_probe_value "$line" codec_name || true)"
        index="$(ffsmart_probe_value "$line" index || true)"
        stream_key="${index:-unknown}:$type"
        seen=false
        for entry in "${seen_streams[@]}"; do
            [[ "$entry" == "$stream_key" ]] && { seen=true; break; }
        done
        [[ "$seen" == true ]] && continue
        seen_streams+=("$stream_key")
        case "$type" in
            video)
                ((FFSMART_VIDEO_COUNT += 1))
                if (( FFSMART_VIDEO_COUNT == 1 )); then
                    width="$(ffsmart_probe_value "$line" width || true)"
                    height="$(ffsmart_probe_value "$line" height || true)"
                    pix="$(ffsmart_probe_value "$line" pix_fmt || true)"
                    FFSMART_VIDEO_CODEC="$codec"
                    FFSMART_VIDEO_PROFILE="$(ffsmart_probe_value "$line" profile || true)"
                    FFSMART_VIDEO_PIX_FMT="$pix"
                    FFSMART_VIDEO_WIDTH="${width:-0}"
                    FFSMART_VIDEO_HEIGHT="${height:-0}"
                    FFSMART_VIDEO_FPS="$(ffsmart_probe_value "$line" r_frame_rate || true)"
                    FFSMART_VIDEO_FIELD_ORDER="$(ffsmart_probe_value "$line" field_order || true)"
                    FFSMART_VIDEO_BITRATE="$(ffsmart_probe_value "$line" bit_rate || true)"
                    FFSMART_VIDEO_COLOR_SPACE="$(ffsmart_probe_value "$line" color_space || true)"
                    FFSMART_VIDEO_COLOR_TRANSFER="$(ffsmart_probe_value "$line" color_transfer || true)"
                    FFSMART_VIDEO_COLOR_PRIMARIES="$(ffsmart_probe_value "$line" color_primaries || true)"
                fi ;;
            audio)
                ((FFSMART_AUDIO_COUNT += 1))
                channels="$(ffsmart_probe_value "$line" channels || true)"
                rate="$(ffsmart_probe_value "$line" sample_rate || true)"
                profile="$(ffsmart_probe_value "$line" profile || true)"
                [[ "$codec" == aac ]] || FFSMART_AUDIO_ALL_AAC=false
                [[ "$channels" =~ ^[0-9]+$ ]] || channels=0
                [[ "$rate" =~ ^[0-9]+$ ]] || rate=0
                (( channels > FFSMART_AUDIO_MAX_CHANNELS )) && FFSMART_AUDIO_MAX_CHANNELS="$channels"
                (( rate > FFSMART_AUDIO_SAMPLE_RATE )) && FFSMART_AUDIO_SAMPLE_RATE="$rate"
                FFSMART_AUDIO_SUMMARY+="${codec:-unknown}/${channels}/${rate}/${profile:-unknown};" ;;
            subtitle|data|attachment)
                ((FFSMART_AUXILIARY_COUNT += 1)) ;;
        esac
    done < "$file"
}

ffsmart_probe_metadata_complete() {
    (( FFSMART_VIDEO_COUNT >= 1 )) || return 1
    [[ -n "$FFSMART_VIDEO_CODEC" && -n "$FFSMART_VIDEO_PIX_FMT" ]] || return 1
    [[ "$FFSMART_VIDEO_WIDTH" =~ ^[1-9][0-9]*$ && "$FFSMART_VIDEO_HEIGHT" =~ ^[1-9][0-9]*$ ]] || return 1
    if (( FFSMART_AUDIO_COUNT > 0 )); then
        [[ "$FFSMART_AUDIO_SUMMARY" != *"unknown/"* ]] || return 1
        local entry codec channels rate profile
        IFS=';' read -r -a audio_entries <<< "$FFSMART_AUDIO_SUMMARY"
        for entry in "${audio_entries[@]}"; do
            [[ -n "$entry" ]] || continue
            IFS='/' read -r codec channels rate profile <<< "$entry"
            [[ -n "$codec" && "$codec" != unknown && "$channels" =~ ^[1-9][0-9]*$ && "$rate" =~ ^[1-9][0-9]*$ ]] || return 1
        done
    fi
}

ffsmart_run_probe_tier() {
    local tier="$1" duration="$2" size="$3" output_file="$4"
    local command=(ffprobe -v error)
    if [[ -n "$duration" ]]; then
        command+=( -analyzeduration "$duration" -probesize "$size" )
    fi
    command+=( -show_entries 'stream=index,codec_type,codec_name,profile,pix_fmt,width,height,r_frame_rate,field_order,bit_rate,color_space,color_transfer,color_primaries,channels,sample_rate' -of 'compact=p=0:nk=0' "$FFSMART_PROBE_INPUT" )
    FFSMART_PROBE_PROCESS_FAILED=false
    if ! "${command[@]}" > "$output_file" 2> "$output_file.stderr"; then
        FFSMART_PROBE_PROCESS_FAILED=true
        ffsmart_fail 1 "input-probe-$tier" "ffprobe failed; probe limits were not escalated"
        return 1
    fi
    ffsmart_parse_probe_output "$output_file"
    ffsmart_probe_metadata_complete
}

ffsmart_adaptive_probe() {
    local tier duration size output_file="$FFSMART_STATE_DIR/probe-result.$$"
    local tiers=('fast|1000000|1000000' 'expanded|2000000|2000000' 'default||') record
    for record in "${tiers[@]}"; do
        IFS='|' read -r tier duration size <<< "$record"
        if ffsmart_run_probe_tier "$tier" "$duration" "$size" "$output_file"; then
            FFSMART_PROBE_TIER="$tier"
            FFSMART_PROBE_ARGS=()
            if [[ -n "$duration" ]]; then FFSMART_PROBE_ARGS=( -analyzeduration "$duration" -probesize "$size" ); fi
            if [[ -n "$duration" ]]; then
                ffsmart_log "Input probe selected tier=$tier analyzeduration=$duration probesize=$size"
            else
                ffsmart_log "Input probe selected tier=default analyzeduration=default probesize=default"
            fi
            rm -f -- "$output_file" "$output_file.stderr"
            return 0
        fi
        local status=1
        if [[ "$FFSMART_PROBE_PROCESS_FAILED" == true ]]; then
            rm -f -- "$output_file" "$output_file.stderr"
            return "$status"
        fi
        if [[ "$tier" == default ]]; then
            ffsmart_fail 1 input-probe-default "ffprobe returned incomplete selected-stream metadata"
            rm -f -- "$output_file" "$output_file.stderr"
            return 1
        fi
        if [[ "$tier" == fast ]]; then
            ffsmart_log "Input probe metadata incomplete; retrying tier=expanded"
        else
            ffsmart_log "Input probe metadata incomplete; retrying tier=default"
        fi
        rm -f -- "$output_file" "$output_file.stderr"
    done
}

ffsmart_cleanup_pipe_sample() {
    [[ -n "$FFSMART_PIPE_SAMPLE" ]] && rm -f -- "$FFSMART_PIPE_SAMPLE"
    return 0
}
