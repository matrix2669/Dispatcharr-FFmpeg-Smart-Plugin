#!/usr/bin/env bash

FFSMART_RENDER_NODES=()
FFSMART_DEVICE_NODES=()
FFSMART_DEVICE_SIGNATURES=()
FFSMART_DEVICE_CAPACITIES=()
FFSMART_DEVICE_SPEEDS=()
FFSMART_DEVICE_ACCELS=()
FFSMART_DEVICE_CODECS=()
FFSMART_DEVICE_LOW_POWERS=()
FFSMART_DEVICE_10BIT_DECODES=()
FFSMART_DEVICE_10BIT_ENCODES=()
FFSMART_REUSE_SIGNATURES=()
FFSMART_REUSE_CAPACITIES=()
FFSMART_REUSE_SPEEDS=()
FFSMART_REUSE_ACCELS=()
FFSMART_REUSE_CODECS=()
FFSMART_REUSE_LOW_POWERS=()
FFSMART_REUSE_10BIT_DECODES=()
FFSMART_REUSE_10BIT_ENCODES=()

ffsmart_cache_reset() {
    FFSMART_CACHE_SCHEMA_VALUE=""
    FFSMART_CACHE_FINGERPRINT=""
    FFSMART_CACHE_BEST_ACCEL=""
    FFSMART_CACHE_BEST_CODEC=""
    FFSMART_CACHE_BEST_LOW_POWER="0"
    FFSMART_CACHE_BEST_10BIT_DECODE="false"
    FFSMART_CACHE_BEST_10BIT_ENCODE="false"
    FFSMART_CACHE_PRIMARY_DEVICE="-"
    FFSMART_CACHE_SECONDARY_DEVICE="-"
    FFSMART_DEVICE_NODES=()
    FFSMART_DEVICE_SIGNATURES=()
    FFSMART_DEVICE_CAPACITIES=()
    FFSMART_DEVICE_SPEEDS=()
    FFSMART_DEVICE_ACCELS=()
    FFSMART_DEVICE_CODECS=()
    FFSMART_DEVICE_LOW_POWERS=()
    FFSMART_DEVICE_10BIT_DECODES=()
    FFSMART_DEVICE_10BIT_ENCODES=()
}

ffsmart_cache_set() {
    case "$1" in
        schema) FFSMART_CACHE_SCHEMA_VALUE="$2" ;;
        fingerprint) FFSMART_CACHE_FINGERPRINT="$2" ;;
        best_accel) FFSMART_CACHE_BEST_ACCEL="$2" ;;
        best_codec) FFSMART_CACHE_BEST_CODEC="$2" ;;
        best_low_power) FFSMART_CACHE_BEST_LOW_POWER="$2" ;;
        best_10bit_decode) FFSMART_CACHE_BEST_10BIT_DECODE="$2" ;;
        best_10bit_encode) FFSMART_CACHE_BEST_10BIT_ENCODE="$2" ;;
        primary_device) FFSMART_CACHE_PRIMARY_DEVICE="$2" ;;
        secondary_device) FFSMART_CACHE_SECONDARY_DEVICE="$2" ;;
        *) return 1 ;;
    esac
}

ffsmart_device_index() {
    local wanted="$1" index
    FFSMART_DEVICE_INDEX=-1
    for index in "${!FFSMART_DEVICE_NODES[@]}"; do
        if [[ "${FFSMART_DEVICE_NODES[$index]}" == "$wanted" ]]; then
            FFSMART_DEVICE_INDEX="$index"
            return 0
        fi
    done
    return 1
}

ffsmart_device_ensure() {
    local node="$1"
    if ffsmart_device_index "$node"; then return 0; fi
    FFSMART_DEVICE_INDEX="${#FFSMART_DEVICE_NODES[@]}"
    FFSMART_DEVICE_NODES+=("$node")
    FFSMART_DEVICE_SIGNATURES+=("")
    FFSMART_DEVICE_CAPACITIES+=("")
    FFSMART_DEVICE_SPEEDS+=("")
    FFSMART_DEVICE_ACCELS+=("")
    FFSMART_DEVICE_CODECS+=("")
    FFSMART_DEVICE_LOW_POWERS+=("0")
    FFSMART_DEVICE_10BIT_DECODES+=("false")
    FFSMART_DEVICE_10BIT_ENCODES+=("false")
}

ffsmart_device_set() {
    local field="$1" node="$2" value="$3"
    ffsmart_device_ensure "$node"
    case "$field" in
        signature) FFSMART_DEVICE_SIGNATURES[$FFSMART_DEVICE_INDEX]="$value" ;;
        capacity) FFSMART_DEVICE_CAPACITIES[$FFSMART_DEVICE_INDEX]="$value" ;;
        speed) FFSMART_DEVICE_SPEEDS[$FFSMART_DEVICE_INDEX]="$value" ;;
        accel) FFSMART_DEVICE_ACCELS[$FFSMART_DEVICE_INDEX]="$value" ;;
        codec) FFSMART_DEVICE_CODECS[$FFSMART_DEVICE_INDEX]="$value" ;;
        low_power) FFSMART_DEVICE_LOW_POWERS[$FFSMART_DEVICE_INDEX]="$value" ;;
        decode10) FFSMART_DEVICE_10BIT_DECODES[$FFSMART_DEVICE_INDEX]="$value" ;;
        encode10) FFSMART_DEVICE_10BIT_ENCODES[$FFSMART_DEVICE_INDEX]="$value" ;;
        *) return 1 ;;
    esac
}

ffsmart_device_get() {
    local field="$1" node="$2"
    ffsmart_device_index "$node" || return 1
    case "$field" in
        signature) printf '%s' "${FFSMART_DEVICE_SIGNATURES[$FFSMART_DEVICE_INDEX]}" ;;
        capacity) printf '%s' "${FFSMART_DEVICE_CAPACITIES[$FFSMART_DEVICE_INDEX]}" ;;
        speed) printf '%s' "${FFSMART_DEVICE_SPEEDS[$FFSMART_DEVICE_INDEX]}" ;;
        accel) printf '%s' "${FFSMART_DEVICE_ACCELS[$FFSMART_DEVICE_INDEX]}" ;;
        codec) printf '%s' "${FFSMART_DEVICE_CODECS[$FFSMART_DEVICE_INDEX]}" ;;
        low_power) printf '%s' "${FFSMART_DEVICE_LOW_POWERS[$FFSMART_DEVICE_INDEX]}" ;;
        decode10) printf '%s' "${FFSMART_DEVICE_10BIT_DECODES[$FFSMART_DEVICE_INDEX]}" ;;
        encode10) printf '%s' "${FFSMART_DEVICE_10BIT_ENCODES[$FFSMART_DEVICE_INDEX]}" ;;
        *) return 1 ;;
    esac
}

ffsmart_read_sysfs_value() {
    local file="$1"
    if [[ -r "$file" ]]; then tr -d '[:space:]' < "$file"; else printf '-'; fi
}

ffsmart_refresh_hardware_inventory() {
    FFSMART_RENDER_NODES=()
    local node class_path device_path vendor device revision subsystem
    shopt -s nullglob
    for node in /dev/dri/renderD*; do
        [[ -c "$node" || -e "$node" ]] || continue
        class_path="/sys/class/drm/${node##*/}"
        device_path="$(ffsmart_realpath "$class_path/device")"
        vendor="$(ffsmart_read_sysfs_value "$device_path/vendor")"
        device="$(ffsmart_read_sysfs_value "$device_path/device")"
        revision="$(ffsmart_read_sysfs_value "$device_path/revision")"
        subsystem="$(ffsmart_read_sysfs_value "$device_path/subsystem_vendor"):$(ffsmart_read_sysfs_value "$device_path/subsystem_device")"
        FFSMART_RENDER_NODES+=("$node")
        ffsmart_device_set signature "$node" "$vendor:$device:$revision:$subsystem"
    done
    shopt -u nullglob
}

ffsmart_ffmpeg_identity() {
    local ffmpeg_line ffprobe_line
    ffmpeg_line="$(ffmpeg -version 2>/dev/null | sed -n '1p' || true)"
    ffprobe_line="$(ffprobe -version 2>/dev/null | sed -n '1p' || true)"
    printf '%s|%s' "$ffmpeg_line" "$ffprobe_line"
}

ffsmart_current_fingerprint() {
    ffsmart_refresh_hardware_inventory
    {
        printf 'schema=%s\n' "$FFSMART_CACHE_SCHEMA"
        printf 'version=%s\n' "$VERSION"
        printf 'capacity_policy=%s\n' "$FFSMART_CAPACITY_POLICY"
        printf 'ffmpeg=%s\n' "$(ffsmart_ffmpeg_identity)"
        printf 'dri_override=%s\n' "$FFSMART_DRI_DEVICE"
        printf 'qsv_override=%s\n' "$FFSMART_QSV_DEVICE"
        printf 'vaapi_override=%s\n' "$FFSMART_VAAPI_DEVICE"
        local node
        for node in "${FFSMART_RENDER_NODES[@]}"; do
            printf 'node=%s|%s\n' "$node" "$(ffsmart_device_get signature "$node")"
        done
    } | ffsmart_hash_text
}

ffsmart_cache_read() {
    ffsmart_cache_reset
    [[ -e "$FFSMART_CACHE_FILE" ]] || return 2
    [[ -r "$FFSMART_CACHE_FILE" ]] || return 5
    local header="" line="" type key value signature node accel codec low_power d10 e10 capacity speed
    {
    IFS= read -r header || return 3
    [[ "$header" == "FFMPEG_SMART_CACHE_V2" ]] || return 3
    while IFS= read -r line; do
        IFS=$'\t' read -r -a fields <<< "$line"
        type="${fields[0]:-}"
        [[ -n "$type" ]] || continue
        case "$type" in
            value)
                [[ "${#fields[@]}" -eq 3 ]] || return 3
                key="${fields[1]}"; value="${fields[2]}"
                [[ "$key" =~ ^[a-z][a-z0-9_]*$ && -n "$value" ]] || return 3
                ffsmart_cache_set "$key" "$value" || return 3 ;;
            device)
                [[ "${#fields[@]}" -eq 10 ]] || return 3
                signature="${fields[1]}"; node="${fields[2]}"; accel="${fields[3]}"; codec="${fields[4]}"
                low_power="${fields[5]}"; d10="${fields[6]}"; e10="${fields[7]}"; capacity="${fields[8]}"; speed="${fields[9]}"
                [[ -n "$signature" && "$node" == /dev/dri/renderD* && -n "$accel" && -n "$codec" && "$capacity" =~ ^[1-9][0-9]*$ && "$speed" =~ ^[0-9]+([.][0-9]+)?$ ]] || return 3
                ffsmart_device_set signature "$node" "$signature"
                ffsmart_device_set accel "$node" "$accel"
                ffsmart_device_set codec "$node" "$codec"
                ffsmart_device_set low_power "$node" "$low_power"
                ffsmart_device_set decode10 "$node" "$d10"
                ffsmart_device_set encode10 "$node" "$e10"
                ffsmart_device_set capacity "$node" "$capacity"
                ffsmart_device_set speed "$node" "$speed" ;;
            *) return 3 ;;
        esac
    done
    } < "$FFSMART_CACHE_FILE"
    [[ "$FFSMART_CACHE_SCHEMA_VALUE" == "$FFSMART_CACHE_SCHEMA" ]] || return 3
    [[ -n "$FFSMART_CACHE_FINGERPRINT" && -n "$FFSMART_CACHE_BEST_ACCEL" && -n "$FFSMART_CACHE_BEST_CODEC" ]] || return 3
}

ffsmart_cache_status() {
    local read_status current
    FFSMART_CACHE_STATUS_VALUE=invalid
    if ffsmart_cache_read; then read_status=0; else read_status=$?; fi
    case "$read_status" in
        0) ;;
        2) FFSMART_CACHE_STATUS_VALUE=missing; return 78 ;;
        3) FFSMART_CACHE_STATUS_VALUE=invalid; return 78 ;;
        5) FFSMART_CACHE_STATUS_VALUE=unavailable; return 78 ;;
        *) FFSMART_CACHE_STATUS_VALUE=invalid; return 78 ;;
    esac
    current="$(ffsmart_current_fingerprint)" || { FFSMART_CACHE_STATUS_VALUE=unavailable; return 78; }
    if [[ "$FFSMART_CACHE_FINGERPRINT" != "$current" ]]; then FFSMART_CACHE_STATUS_VALUE=stale; return 78; fi
    FFSMART_CACHE_STATUS_VALUE=valid
}

ffsmart_cache_snapshot_reusable_devices() {
    FFSMART_REUSE_SIGNATURES=()
    FFSMART_REUSE_CAPACITIES=()
    FFSMART_REUSE_SPEEDS=()
    FFSMART_REUSE_ACCELS=()
    FFSMART_REUSE_CODECS=()
    FFSMART_REUSE_LOW_POWERS=()
    FFSMART_REUSE_10BIT_DECODES=()
    FFSMART_REUSE_10BIT_ENCODES=()
    ffsmart_cache_read || return 0
    local index
    for index in "${!FFSMART_DEVICE_NODES[@]}"; do
        FFSMART_REUSE_SIGNATURES+=("${FFSMART_DEVICE_SIGNATURES[$index]}")
        FFSMART_REUSE_CAPACITIES+=("${FFSMART_DEVICE_CAPACITIES[$index]}")
        FFSMART_REUSE_SPEEDS+=("${FFSMART_DEVICE_SPEEDS[$index]}")
        FFSMART_REUSE_ACCELS+=("${FFSMART_DEVICE_ACCELS[$index]}")
        FFSMART_REUSE_CODECS+=("${FFSMART_DEVICE_CODECS[$index]}")
        FFSMART_REUSE_LOW_POWERS+=("${FFSMART_DEVICE_LOW_POWERS[$index]}")
        FFSMART_REUSE_10BIT_DECODES+=("${FFSMART_DEVICE_10BIT_DECODES[$index]}")
        FFSMART_REUSE_10BIT_ENCODES+=("${FFSMART_DEVICE_10BIT_ENCODES[$index]}")
    done
}

ffsmart_cache_reuse_device() {
    local node="$1" signature="$2" index
    for index in "${!FFSMART_REUSE_SIGNATURES[@]}"; do
        [[ "${FFSMART_REUSE_SIGNATURES[$index]}" == "$signature" ]] || continue
        [[ -n "${FFSMART_REUSE_CAPACITIES[$index]}" && -n "${FFSMART_REUSE_ACCELS[$index]}" ]] || continue
        ffsmart_device_set accel "$node" "${FFSMART_REUSE_ACCELS[$index]}"
        ffsmart_device_set codec "$node" "${FFSMART_REUSE_CODECS[$index]}"
        ffsmart_device_set low_power "$node" "${FFSMART_REUSE_LOW_POWERS[$index]}"
        ffsmart_device_set decode10 "$node" "${FFSMART_REUSE_10BIT_DECODES[$index]}"
        ffsmart_device_set encode10 "$node" "${FFSMART_REUSE_10BIT_ENCODES[$index]}"
        ffsmart_device_set capacity "$node" "${FFSMART_REUSE_CAPACITIES[$index]}"
        ffsmart_device_set speed "$node" "${FFSMART_REUSE_SPEEDS[$index]}"
        return 0
    done
    return 1
}

ffsmart_cache_write() {
    local target="$FFSMART_CACHE_FILE.tmp.$$" node signature accel codec low_power d10 e10 capacity speed
    umask 077
    {
        printf 'FFMPEG_SMART_CACHE_V2\n'
        printf 'value\tschema\t%s\n' "$FFSMART_CACHE_SCHEMA"
        printf 'value\tfingerprint\t%s\n' "$FFSMART_CACHE_FINGERPRINT"
        printf 'value\tbest_accel\t%s\n' "$FFSMART_CACHE_BEST_ACCEL"
        printf 'value\tbest_codec\t%s\n' "$FFSMART_CACHE_BEST_CODEC"
        printf 'value\tbest_low_power\t%s\n' "$FFSMART_CACHE_BEST_LOW_POWER"
        printf 'value\tbest_10bit_decode\t%s\n' "$FFSMART_CACHE_BEST_10BIT_DECODE"
        printf 'value\tbest_10bit_encode\t%s\n' "$FFSMART_CACHE_BEST_10BIT_ENCODE"
        printf 'value\tprimary_device\t%s\n' "$FFSMART_CACHE_PRIMARY_DEVICE"
        printf 'value\tsecondary_device\t%s\n' "$FFSMART_CACHE_SECONDARY_DEVICE"
        for node in "${FFSMART_RENDER_NODES[@]}"; do
            capacity="$(ffsmart_device_get capacity "$node" || true)"; [[ -n "$capacity" ]] || continue
            signature="$(ffsmart_device_get signature "$node")"; accel="$(ffsmart_device_get accel "$node")"; codec="$(ffsmart_device_get codec "$node")"
            low_power="$(ffsmart_device_get low_power "$node")"; d10="$(ffsmart_device_get decode10 "$node")"; e10="$(ffsmart_device_get encode10 "$node")"; speed="$(ffsmart_device_get speed "$node")"
            printf 'device\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$signature" "$node" "$accel" "$codec" "$low_power" "$d10" "$e10" "$capacity" "$speed"
        done
    } > "$target" || { rm -f -- "$target"; ffsmart_fail 73 cache-write "Cannot write capability cache: $FFSMART_CACHE_FILE"; return 73; }
    mv -f -- "$target" "$FFSMART_CACHE_FILE" || { rm -f -- "$target"; ffsmart_fail 73 cache-write "Cannot replace capability cache: $FFSMART_CACHE_FILE"; return 73; }
}

ffsmart_cache_required_message() {
    case "$1" in
        missing) printf 'Hardware capability cache is missing' ;;
        invalid) printf 'Hardware capability cache is invalid or unreadable' ;;
        stale) printf 'Hardware capability cache does not match the current hardware or policy' ;;
        unavailable) printf 'Hardware capability cache is unavailable' ;;
        *) printf 'Hardware capability cache is unusable' ;;
    esac
}
