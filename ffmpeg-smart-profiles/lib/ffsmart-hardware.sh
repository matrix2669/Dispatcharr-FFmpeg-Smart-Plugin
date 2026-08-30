#!/usr/bin/env bash

ffsmart_encoder_available() {
    ffmpeg -hide_banner -encoders 2>/dev/null | awk '{print $2}' | grep -Fxq -- "$1"
}

ffsmart_decoder_available() {
    ffmpeg -hide_banner -decoders 2>/dev/null | awk '{print $2}' | grep -Fxq -- "$1"
}

FFSMART_HW_DECODE_ARGS=()
ffsmart_build_hardware_decode_args() {
    local accel="$1" node="$2"
    FFSMART_HW_DECODE_ARGS=()
    case "$accel" in
        qsv)
            FFSMART_HW_DECODE_ARGS=(
                -init_hw_device "qsv=ffsmart:hw,child_device=$node"
                -filter_hw_device ffsmart
                -hwaccel qsv
                -hwaccel_output_format qsv
            ) ;;
        vaapi)
            FFSMART_HW_DECODE_ARGS=(
                -init_hw_device "vaapi=ffsmart:$node"
                -filter_hw_device ffsmart
                -hwaccel vaapi
                -hwaccel_device ffsmart
                -hwaccel_output_format vaapi
            ) ;;
        software) ;;
        *) return 1 ;;
    esac
}

ffsmart_ensure_benchmark_samples() {
    local h264="$FFSMART_STATE_DIR/benchmark-h264.mkv"
    local hevc10="$FFSMART_STATE_DIR/benchmark-hevc10.mkv"
    if [[ ! -s "$h264" ]]; then
        ffsmart_log "Generating bounded H.264 benchmark sample"
        ffmpeg -hide_banner -loglevel error -nostdin \
            -f lavfi -i 'testsrc2=size=1920x1080:rate=30000/1001' \
            -f lavfi -i 'sine=frequency=1000:sample_rate=48000' \
            -t 4 -c:v libx264 -preset veryfast -pix_fmt yuv420p -g 60 \
            -c:a aac -b:a 192k -y "$h264" || {
                ffsmart_fail 69 benchmark-sample "Could not generate H.264 benchmark sample"
                return 69
            }
    fi
    if [[ ! -s "$hevc10" ]] && ffsmart_encoder_available libx265; then
        ffsmart_log "Generating bounded HEVC Main10 benchmark sample"
        ffmpeg -hide_banner -loglevel error -nostdin \
            -f lavfi -i 'testsrc2=size=1920x1080:rate=30000/1001' \
            -t 4 -c:v libx265 -preset ultrafast -pix_fmt yuv420p10le \
            -x265-params log-level=error -an -y "$hevc10" || rm -f -- "$hevc10"
    fi
    FFSMART_H264_SAMPLE="$h264"
    FFSMART_HEVC10_SAMPLE="$hevc10"
}

FFSMART_BENCH_CMD=()
ffsmart_build_benchmark_command() {
    local node="$1" accel="$2" codec="$3" low_power="$4" duration="$5"
    local encoder filter source="$FFSMART_H264_SAMPLE" surface_format=nv12
    if [[ -s "$FFSMART_HEVC10_SAMPLE" ]]; then
        source="$FFSMART_HEVC10_SAMPLE"
        [[ "$codec" == hevc ]] && surface_format=p010
    fi
    FFSMART_BENCH_CMD=(ffmpeg -hide_banner -nostdin -stats -stream_loop -1 -i "$source" -map 0:v:0 -an -t "$duration")
    case "$accel" in
        qsv)
            encoder="${codec}_qsv"
            filter="vpp_qsv=format=$surface_format"
            ffsmart_build_hardware_decode_args "$accel" "$node" || return 1
            FFSMART_BENCH_CMD=(ffmpeg -hide_banner -nostdin -stats \
                "${FFSMART_HW_DECODE_ARGS[@]}" \
                -stream_loop -1 -i "$source" -map 0:v:0 -an -t "$duration" \
                -vf "$filter" -c:v "$encoder") ;;
        vaapi)
            encoder="${codec}_vaapi"
            filter="scale_vaapi=format=$surface_format"
            ffsmart_build_hardware_decode_args "$accel" "$node" || return 1
            FFSMART_BENCH_CMD=(ffmpeg -hide_banner -nostdin -stats \
                "${FFSMART_HW_DECODE_ARGS[@]}" -stream_loop -1 -i "$source" \
                -map 0:v:0 -an -t "$duration" -vf "$filter" -c:v "$encoder") ;;
        software)
            if [[ "$codec" == hevc ]]; then encoder=libx265; else encoder=libx264; fi
            FFSMART_BENCH_CMD+=( -c:v "$encoder" -preset ultrafast ) ;;
        *) return 1 ;;
    esac
    if [[ "$low_power" == 1 ]]; then
        FFSMART_BENCH_CMD+=( -low_power 1 )
    fi
    [[ "$codec" == hevc && "$surface_format" == p010 ]] && FFSMART_BENCH_CMD+=( -profile:v main10 )
    FFSMART_BENCH_CMD+=( -b:v 4500k -maxrate 6000k -bufsize 12000k -f null - )
}

ffsmart_extract_speed() {
    local log_file="$1" speed
    speed="$(tr '\r' '\n' < "$log_file" | sed -n 's/.*speed=[[:space:]]*\([0-9.]*\)x.*/\1/p' | tail -n 1)"
    [[ -n "$speed" ]] || speed=0
    printf '%s' "$speed"
}

ffsmart_benchmark_candidate() {
    local node="$1" accel="$2" codec="$3" low_power="$4" duration="${5:-5}"
    local log_file="$FFSMART_STATE_DIR/candidate-${node##*/}-${accel}-${codec}-${low_power}.log" speed
    ffsmart_build_benchmark_command "$node" "$accel" "$codec" "$low_power" "$duration" || return 1
    if "${FFSMART_BENCH_CMD[@]}" > /dev/null 2> "$log_file"; then
        speed="$(ffsmart_extract_speed "$log_file")"
        awk -v s="$speed" 'BEGIN { exit !(s > 0) }' || return 1
        printf '%s' "$speed"
        return 0
    fi
    return 1
}

ffsmart_probe_10bit() {
    local node="$1" accel="$2" direction="$3" log_file="$FFSMART_STATE_DIR/10bit-${node##*/}-${accel}-${direction}.log"
    [[ -s "$FFSMART_HEVC10_SAMPLE" ]] || return 1
    case "$accel:$direction" in
        qsv:decode)
            ffmpeg -hide_banner -loglevel error -nostdin \
                -init_hw_device "qsv=ffsmart:hw,child_device=$node" -filter_hw_device ffsmart \
                -hwaccel qsv -hwaccel_output_format qsv -c:v hevc_qsv \
                -i "$FFSMART_HEVC10_SAMPLE" -map 0:v:0 -frames:v 30 -f null - > /dev/null 2> "$log_file" ;;
        qsv:encode)
            ffmpeg -hide_banner -loglevel error -nostdin \
                -init_hw_device "qsv=ffsmart:hw,child_device=$node" -filter_hw_device ffsmart \
                -i "$FFSMART_HEVC10_SAMPLE" -map 0:v:0 -frames:v 30 \
                -vf 'format=p010le,hwupload=extra_hw_frames=64' -c:v hevc_qsv -profile:v main10 -f null - > /dev/null 2> "$log_file" ;;
        vaapi:decode)
            ffmpeg -hide_banner -loglevel error -nostdin -vaapi_device "$node" \
                -hwaccel vaapi -hwaccel_device "$node" -hwaccel_output_format vaapi \
                -i "$FFSMART_HEVC10_SAMPLE" -map 0:v:0 -frames:v 30 -f null - > /dev/null 2> "$log_file" ;;
        vaapi:encode)
            ffmpeg -hide_banner -loglevel error -nostdin -vaapi_device "$node" \
                -i "$FFSMART_HEVC10_SAMPLE" -map 0:v:0 -frames:v 30 \
                -vf 'format=p010le,hwupload' -c:v hevc_vaapi -profile:v main10 -f null - > /dev/null 2> "$log_file" ;;
        *) return 1 ;;
    esac
}

ffsmart_capacity_level_stable() {
    local node="$1" accel="$2" codec="$3" low_power="$4" level="$5" duration="$6"
    local min_speed="${CONCURRENCY_MIN_SPEED:-1.2}" pids=() logs=() index status=0 speed log
    local wall_timeout="${CONCURRENCY_WALL_TIMEOUT:-$((duration + 30))}" watchdog_pid timeout_marker
    ffsmart_positive_integer "$wall_timeout" || wall_timeout=$((duration + 30))
    timeout_marker="$FFSMART_STATE_DIR/.capacity-timeout.$$"
    rm -f -- "$timeout_marker"
    for ((index=1; index<=level; index++)); do
        log="$FFSMART_STATE_DIR/capacity-${node##*/}-${level}-${index}.log"
        ffsmart_build_benchmark_command "$node" "$accel" "$codec" "$low_power" "$duration" || return 1
        "${FFSMART_BENCH_CMD[@]}" > /dev/null 2> "$log" &
        pids+=("$!")
        logs+=("$log")
    done
    (
        watchdog_sleep=""
        trap '[[ -z "$watchdog_sleep" ]] || kill "$watchdog_sleep" 2>/dev/null || true; exit 0' TERM INT
        sleep "$wall_timeout" &
        watchdog_sleep="$!"
        wait "$watchdog_sleep" || exit 0
        trap - TERM INT
        printf 'timeout\n' > "$timeout_marker"
        ffsmart_log "Capacity probe deadline node=$node level=$level wall=${wall_timeout}s"
        for index in "${pids[@]}"; do kill -TERM "$index" 2>/dev/null || true; done
        sleep 2
        for index in "${pids[@]}"; do kill -KILL "$index" 2>/dev/null || true; done
    ) &
    watchdog_pid="$!"
    for index in "${!pids[@]}"; do
        if ! wait "${pids[$index]}"; then
            status=1
        fi
        speed="$(ffsmart_extract_speed "${logs[$index]}")"
        if ! awk -v s="$speed" -v m="$min_speed" 'BEGIN { exit !(s >= m) }'; then
            status=1
        fi
    done
    if kill -0 "$watchdog_pid" 2>/dev/null; then
        kill "$watchdog_pid" 2>/dev/null || true
    fi
    wait "$watchdog_pid" 2>/dev/null || true
    if [[ -e "$timeout_marker" ]]; then
        status=1
        rm -f -- "$timeout_marker"
    fi
    return "$status"
}

ffsmart_next_capacity_upper_level() {
    local current="$1" maximum="$2" next
    next=$((current + (current + 1) / 2))
    (( next > maximum )) && next="$maximum"
    printf '%s' "$next"
}

FFSMART_PATH_SPEED=0
FFSMART_PATH_LOW_POWER=0
ffsmart_benchmark_device_path() {
    local node="$1" accel="$2" codec="$3" low_power speed
    FFSMART_PATH_SPEED=0
    FFSMART_PATH_LOW_POWER=0
    ffsmart_encoder_available "${codec}_${accel}" || return 1
    for low_power in 1 0; do
        if speed="$(ffsmart_benchmark_candidate "$node" "$accel" "$codec" "$low_power" 5)"; then
            ffsmart_log "Common-path candidate node=$node accel=$accel codec=$codec low_power=$low_power speed=${speed}x"
            if awk -v a="$speed" -v b="$FFSMART_PATH_SPEED" 'BEGIN { exit !(a>b) }'; then
                FFSMART_PATH_SPEED="$speed"
                FFSMART_PATH_LOW_POWER="$low_power"
            fi
        fi
    done
    awk -v s="$FFSMART_PATH_SPEED" 'BEGIN { exit !(s>0) }'
}

ffsmart_measure_capacity() {
    local node="$1" accel="$2" codec="$3" low_power="$4" speed="$5"
    local short="${CONCURRENCY_SHORT_DURATION:-10}" confirm="${CONCURRENCY_CONFIRM_DURATION:-30}" max="${CONCURRENCY_MAX_STREAMS:-48}"
    local guess highest=0 unstable=0 level midpoint
    guess="$(awk -v s="$speed" 'BEGIN { n=int(s); if(n<1)n=1; print n }')"
    (( guess > max )) && guess="$max"
    level="$guess"
    while (( level >= 1 )); do
        ffsmart_log "Capacity probe node=$node level=$level duration=${short}s"
        if ffsmart_capacity_level_stable "$node" "$accel" "$codec" "$low_power" "$level" "$short"; then
            highest="$level"
            break
        fi
        unstable="$level"
        level=$((level / 2))
    done
    (( highest > 0 )) || highest=1
    if (( unstable == 0 )); then
        level="$(ffsmart_next_capacity_upper_level "$highest" "$max")"
        while (( level > highest )); do
            ffsmart_log "Capacity upper-bound node=$node level=$level duration=${short}s"
            if ffsmart_capacity_level_stable "$node" "$accel" "$codec" "$low_power" "$level" "$short"; then
                highest="$level"
                (( highest == max )) && break
                level="$(ffsmart_next_capacity_upper_level "$highest" "$max")"
            else
                unstable="$level"
                break
            fi
        done
    fi
    if (( unstable == 0 && highest < max )); then
        unstable="$max"
    fi
    while (( unstable > highest + 1 )); do
        midpoint=$(((highest + unstable) / 2))
        ffsmart_log "Capacity binary-search node=$node level=$midpoint duration=${short}s"
        if ffsmart_capacity_level_stable "$node" "$accel" "$codec" "$low_power" "$midpoint" "$short"; then
            highest="$midpoint"
        else
            unstable="$midpoint"
        fi
    done
    if (( highest == 0 )); then
        ffsmart_log "Capacity floor node=$node level=1 duration=${short}s"
        if ffsmart_capacity_level_stable "$node" "$accel" "$codec" "$low_power" "$level" "$short"; then
            highest=1
        fi
    fi
    ffsmart_log "Capacity confirmation node=$node stable=$highest duration=${confirm}s"
    ffsmart_capacity_level_stable "$node" "$accel" "$codec" "$low_power" "$highest" "$confirm" || {
        while (( highest > 1 )); do
            highest=$((highest - 1))
            ffsmart_capacity_level_stable "$node" "$accel" "$codec" "$low_power" "$highest" "$confirm" && break
        done
    }
    if (( highest < max )); then
        ffsmart_log "Capacity rejection confirmation node=$node level=$((highest + 1)) duration=${confirm}s"
        if ffsmart_capacity_level_stable "$node" "$accel" "$codec" "$low_power" "$((highest + 1))" "$confirm"; then
            highest=$((highest + 1))
        fi
    fi
    printf '%s' "$highest"
}

ffsmart_rebuild_cache() {
    local force_rebenchmark="${1:-true}"
    ffsmart_lock_acquire || return
    ffsmart_ensure_benchmark_samples || return
    if [[ "$force_rebenchmark" == true ]]; then
        FFSMART_REUSE_SIGNATURES=()
    else
        ffsmart_cache_snapshot_reusable_devices
    fi
    ffsmart_refresh_hardware_inventory

    local node accel codec low_power speed best_speed=0 best_node="" best_accel=software best_codec=h264 best_low_power=0
    local d10 e10 capacity compatible_nodes=0
    local sorted=()
    for node in "${FFSMART_RENDER_NODES[@]}"; do
        local node_best_speed=0 node_best_accel="" node_best_codec="" node_best_low=0
        if [[ "$force_rebenchmark" != true ]] && ffsmart_cache_reuse_device "$node" "$(ffsmart_device_get signature "$node")"; then
            node_best_speed="$(ffsmart_device_get speed "$node")"
            node_best_accel="$(ffsmart_device_get accel "$node")"
            node_best_codec="$(ffsmart_device_get codec "$node")"
            node_best_low="$(ffsmart_device_get low_power "$node")"
            ffsmart_log "Reused hardware result node=$node signature=$(ffsmart_device_get signature "$node") accel=$node_best_accel codec=$node_best_codec capacity=$(ffsmart_device_get capacity "$node")"
        fi
        if [[ -z "$node_best_accel" ]]; then
        for accel in qsv vaapi; do
            [[ "$accel" == qsv ]] && [[ "$(ffsmart_device_get signature "$node")" == 0x8086:* ]] || [[ "$accel" == vaapi ]] || continue
            for codec in hevc h264; do
                ffsmart_encoder_available "${codec}_${accel}" || continue
                for low_power in 1 0; do
                    if speed="$(ffsmart_benchmark_candidate "$node" "$accel" "$codec" "$low_power" 5)"; then
                        ffsmart_log "Candidate node=$node accel=$accel codec=$codec low_power=$low_power speed=${speed}x"
                        if awk -v a="$speed" -v b="$node_best_speed" 'BEGIN { exit !(a>b) }'; then
                            node_best_speed="$speed"; node_best_accel="$accel"; node_best_codec="$codec"; node_best_low="$low_power"
                        fi
                    fi
                done
            done
        done
        fi
        [[ -n "$node_best_accel" ]] || continue
        ((compatible_nodes += 1))
        ffsmart_device_set accel "$node" "$node_best_accel"
        ffsmart_device_set codec "$node" "$node_best_codec"
        ffsmart_device_set low_power "$node" "$node_best_low"
        ffsmart_device_set speed "$node" "$node_best_speed"
        if awk -v a="$node_best_speed" -v b="$best_speed" 'BEGIN { exit !(a>b) }'; then
            best_speed="$node_best_speed"; best_node="$node"; best_accel="$node_best_accel"; best_codec="$node_best_codec"; best_low_power="$node_best_low"
        fi
    done

    if [[ -n "$best_node" ]]; then
        for node in "${FFSMART_RENDER_NODES[@]}"; do
            accel="$(ffsmart_device_get accel "$node" || true)"; [[ -n "$accel" ]] || continue
            codec="$(ffsmart_device_get codec "$node" || true)"
            if [[ "$accel" != "$best_accel" || "$codec" != "$best_codec" ]]; then
                if ffsmart_benchmark_device_path "$node" "$best_accel" "$best_codec"; then
                    ffsmart_device_set accel "$node" "$best_accel"
                    ffsmart_device_set codec "$node" "$best_codec"
                    ffsmart_device_set low_power "$node" "$FFSMART_PATH_LOW_POWER"
                    ffsmart_device_set speed "$node" "$FFSMART_PATH_SPEED"
                    ffsmart_device_set capacity "$node" ""
                    ffsmart_log "Aligned device node=$node accel=$best_accel codec=$best_codec low_power=$FFSMART_PATH_LOW_POWER speed=${FFSMART_PATH_SPEED}x"
                else
                    ffsmart_log "Device node=$node has no working common path accel=$best_accel codec=$best_codec; retaining its independent best path"
                fi
            fi
        done
        best_speed=0
        for node in "${FFSMART_RENDER_NODES[@]}"; do
            ffsmart_device_matches_policy "$node" "$best_accel" "$best_codec" || continue
            speed="$(ffsmart_device_get speed "$node")"
            if awk -v a="$speed" -v b="$best_speed" 'BEGIN { exit !(a>b) }'; then
                best_speed="$speed"
                best_node="$node"
                best_low_power="$(ffsmart_device_get low_power "$node")"
            fi
        done
    fi

    for node in "${FFSMART_RENDER_NODES[@]}"; do
        accel="$(ffsmart_device_get accel "$node" || true)"; [[ -n "$accel" ]] || continue
        if ffsmart_probe_10bit "$node" "$accel" decode; then d10=true; else d10=false; fi
        if ffsmart_probe_10bit "$node" "$accel" encode; then e10=true; else e10=false; fi
        ffsmart_device_set decode10 "$node" "$d10"
        ffsmart_device_set encode10 "$node" "$e10"
    done

    if (( compatible_nodes > 1 )); then
        for node in "${FFSMART_RENDER_NODES[@]}"; do
            accel="$(ffsmart_device_get accel "$node" || true)"; [[ -n "$accel" ]] || continue
            [[ -n "$(ffsmart_device_get capacity "$node" || true)" ]] && continue
            capacity="$(ffsmart_measure_capacity "$node" "$accel" "$(ffsmart_device_get codec "$node")" "$(ffsmart_device_get low_power "$node")" "$(ffsmart_device_get speed "$node")")"
            ffsmart_device_set capacity "$node" "$capacity"
        done
    else
        for node in "${FFSMART_RENDER_NODES[@]}"; do
            accel="$(ffsmart_device_get accel "$node" || true)"; [[ -n "$accel" ]] || continue
            [[ -n "$(ffsmart_device_get capacity "$node" || true)" ]] && continue
            capacity="$(awk -v s="$(ffsmart_device_get speed "$node")" 'BEGIN { n=int(s); if(n<1)n=1; print n }')"
            ffsmart_device_set capacity "$node" "$capacity"
        done
    fi

    if [[ -z "$best_node" ]]; then
        if ffsmart_encoder_available libx265; then best_codec=hevc; else best_codec=h264; fi
        best_accel=software; best_low_power=0; best_speed=1
    fi

    local ranked=() entry
    for node in "${FFSMART_RENDER_NODES[@]}"; do
        capacity="$(ffsmart_device_get capacity "$node" || true)"; [[ -n "$capacity" ]] || continue
        ranked+=("$capacity|$(ffsmart_device_get speed "$node")|$node")
    done
    if ((${#ranked[@]})); then
        sorted=()
        while IFS= read -r entry; do sorted+=("$entry"); done < <(printf '%s\n' "${ranked[@]}" | sort -t'|' -k1,1nr -k2,2nr)
        FFSMART_CACHE_PRIMARY_DEVICE="${sorted[0]##*|}"
        if ((${#sorted[@]} > 1)); then FFSMART_CACHE_SECONDARY_DEVICE="${sorted[1]##*|}"; else FFSMART_CACHE_SECONDARY_DEVICE="-"; fi
    else
        FFSMART_CACHE_PRIMARY_DEVICE="-"; FFSMART_CACHE_SECONDARY_DEVICE="-"
    fi
    FFSMART_CACHE_SCHEMA_VALUE="$FFSMART_CACHE_SCHEMA"
    FFSMART_CACHE_BEST_ACCEL="$best_accel"
    FFSMART_CACHE_BEST_CODEC="$best_codec"
    FFSMART_CACHE_BEST_LOW_POWER="$best_low_power"
    if [[ -n "$best_node" ]]; then
        FFSMART_CACHE_BEST_10BIT_DECODE="$(ffsmart_device_get decode10 "$best_node")"
        FFSMART_CACHE_BEST_10BIT_ENCODE="$(ffsmart_device_get encode10 "$best_node")"
    else
        FFSMART_CACHE_BEST_10BIT_DECODE=false
        FFSMART_CACHE_BEST_10BIT_ENCODE=false
    fi
    FFSMART_CACHE_FINGERPRINT="$(ffsmart_current_fingerprint)"
    ffsmart_cache_write
    ffsmart_log "Capability cache rebuilt: accel=$best_accel codec=$best_codec primary=$FFSMART_CACHE_PRIMARY_DEVICE secondary=$FFSMART_CACHE_SECONDARY_DEVICE"
}

ffsmart_job_load_milli() {
    local pid="$1" env_file="/proc/$pid/environ" width_in="" height_in="" width_out="" height_out="" fps=""
    [[ -r "$env_file" ]] || { printf '1000'; return; }
    while IFS='=' read -r key value; do
        case "$key" in
            FFMPEG_SMART_INPUT_WIDTH) width_in="$value" ;;
            FFMPEG_SMART_INPUT_HEIGHT) height_in="$value" ;;
            FFMPEG_SMART_OUTPUT_WIDTH) width_out="$value" ;;
            FFMPEG_SMART_OUTPUT_HEIGHT) height_out="$value" ;;
            FFMPEG_ADAPTIVE_FPS_FRAC|FFMPEG_SMART_FPS_FRAC) fps="$value" ;;
        esac
    done < <(tr '\0' '\n' < "$env_file")
    if ! ffsmart_positive_integer "${width_in:-0}" || ! ffsmart_positive_integer "${height_in:-0}" || ! ffsmart_positive_integer "${width_out:-0}" || ! ffsmart_positive_integer "${height_out:-0}"; then
        printf '1000'; return
    fi
    local fps_dec
    fps_dec="$(ffsmart_fraction_to_decimal "$fps")"
    awk -v wi="$width_in" -v hi="$height_in" -v wo="$width_out" -v ho="$height_out" -v f="$fps_dec" 'BEGIN { a=wi*hi*f; b=wo*ho*f; m=(a>b?a:b); printf "%.0f", 1000*m/(1920*1080*30) }'
}

ffsmart_device_matches_policy() {
    local node="$1" accel="$2" codec="$3"
    [[ "$(ffsmart_device_get accel "$node" 2>/dev/null || true)" == "$accel" ]] || return 1
    [[ "$(ffsmart_device_get codec "$node" 2>/dev/null || true)" == "$codec" ]]
}

ffsmart_select_device() {
    local accel="$1" codec="${2:-}" explicit="" primary secondary node pid fd target load capacity util best_util="" selected=""
    local has_exact=false has_accel=false node_accel="" node_codec=""
    case "$accel" in
        qsv) explicit="${FFSMART_QSV_DEVICE:-${FFSMART_DRI_DEVICE:-}}" ;;
        vaapi) explicit="${FFSMART_VAAPI_DEVICE:-${FFSMART_DRI_DEVICE:-}}" ;;
    esac
    if [[ -n "$explicit" ]]; then
        [[ -e "$explicit" ]] || { ffsmart_configuration_error "Configured device does not exist: $explicit"; return 64; }
        FFSMART_SELECTED_DEVICE="$explicit"
        ffsmart_log "Using explicit $accel device: $explicit"
        return 0
    fi
    primary="${FFSMART_CACHE_PRIMARY_DEVICE:--}"
    secondary="${FFSMART_CACHE_SECONDARY_DEVICE:--}"
    [[ "$primary" != - ]] || { FFSMART_SELECTED_DEVICE=""; return 0; }

    local primary_load=0 secondary_load=0
    shopt -s nullglob
    for pid_path in /proc/[0-9]*; do
        pid="${pid_path##*/}"
        [[ -r "$pid_path/comm" ]] || continue
        [[ "$(<"$pid_path/comm")" == ffmpeg ]] || continue
        target=""
        for fd in "$pid_path"/fd/*; do
            node="$(readlink "$fd" 2>/dev/null || true)"
            if [[ "$node" == "$primary" || "$node" == "$secondary" ]]; then target="$node"; break; fi
        done
        [[ -n "$target" ]] || continue
        load="$(ffsmart_job_load_milli "$pid")"
        if [[ "$target" == "$primary" ]]; then primary_load=$((primary_load + load)); else secondary_load=$((secondary_load + load)); fi
    done
    shopt -u nullglob

    for node in "$primary" "$secondary"; do
        [[ "$node" != - ]] || continue
        node_accel="$(ffsmart_device_get accel "$node" 2>/dev/null || true)"
        node_codec="$(ffsmart_device_get codec "$node" 2>/dev/null || true)"
        [[ "$node_accel" == "$accel" ]] && has_accel=true
        [[ "$node_accel" == "$accel" && "$node_codec" == "$codec" ]] && has_exact=true
    done

    for node in "$primary" "$secondary"; do
        [[ "$node" != - ]] || continue
        node_accel="$(ffsmart_device_get accel "$node" 2>/dev/null || true)"
        node_codec="$(ffsmart_device_get codec "$node" 2>/dev/null || true)"
        if [[ "$has_exact" == true ]]; then
            [[ "$node_accel" == "$accel" && "$node_codec" == "$codec" ]] || continue
        elif [[ "$has_accel" == true ]]; then
            [[ "$node_accel" == "$accel" ]] || continue
        fi
        if [[ "$node_accel" == "$accel" && "$node_codec" == "$codec" ]]; then
            capacity="$(ffsmart_device_get capacity "$node" || printf '1')"
        else
            capacity=1
        fi
        if [[ "$node" == "$primary" ]]; then load="$primary_load"; else load="$secondary_load"; fi
        util="$(awk -v l="$load" -v c="$capacity" 'BEGIN { printf "%.9f", l/(c*1000) }')"
        if [[ -z "$selected" ]] || awk -v a="$util" -v b="$best_util" 'BEGIN { exit !(a<b) }'; then
            selected="$node"; best_util="$util"
        fi
    done
    if [[ -z "$selected" ]]; then
        ffsmart_fail 78 capability-cache-incompatible "Capability cache has no selectable device; rebuild the hardware cache"
        return 78
    fi
    FFSMART_SELECTED_DEVICE="$selected"
    if [[ "$selected" == "$primary" ]]; then load="$primary_load"; else load="$secondary_load"; fi
    if ffsmart_device_matches_policy "$selected" "$accel" "$codec"; then
        capacity="$(ffsmart_device_get capacity "$selected" || printf '1')"
    else
        capacity=1
        ffsmart_warn unmeasured-device-policy "No device capacity was measured for accelerator=$accel codec=$codec; scheduling $selected conservatively at capacity=1"
    fi
    ffsmart_log "Automatic device selection: $selected load=${load}m capacity=$capacity utilization=$best_util"
}

ffsmart_apply_selected_device_policy() {
    local node="${FFSMART_SELECTED_DEVICE:-}" cached_accel="" cached_codec=""
    FFSMART_SELECTED_LOW_POWER=0
    FFSMART_SELECTED_10BIT_ENCODE=false
    [[ "$FFSMART_SELECTED_ACCEL" =~ ^(qsv|vaapi)$ ]] || return 0
    if [[ -n "$node" ]]; then
        cached_accel="$(ffsmart_device_get accel "$node" 2>/dev/null || true)"
        cached_codec="$(ffsmart_device_get codec "$node" 2>/dev/null || true)"
    fi
    if [[ "$cached_accel" == "$FFSMART_SELECTED_ACCEL" && "$cached_codec" == "$FFSMART_TARGET_CODEC" ]]; then
        FFSMART_SELECTED_LOW_POWER="$(ffsmart_device_get low_power "$node" 2>/dev/null || printf '0')"
        FFSMART_SELECTED_10BIT_ENCODE="$(ffsmart_device_get encode10 "$node" 2>/dev/null || printf 'false')"
    else
        ffsmart_warn selected-device-unmeasured "Device $node was not measured for accelerator=$FFSMART_SELECTED_ACCEL codec=$FFSMART_TARGET_CODEC; using conservative encoder capabilities"
    fi
    ffsmart_log "Selected device policy: device=$node accel=$FFSMART_SELECTED_ACCEL codec=$FFSMART_TARGET_CODEC low_power=$FFSMART_SELECTED_LOW_POWER encode10=$FFSMART_SELECTED_10BIT_ENCODE"
}
