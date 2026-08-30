#!/usr/bin/env bash
set -eo pipefail

VERSION="0.1.0-beta.2"
FFSMART_ENTRYPOINT="${BASH_SOURCE[0]}"
FFSMART_ROOT="$(cd "$(dirname "$FFSMART_ENTRYPOINT")" && pwd)"

# shellcheck source=lib/ffsmart-common.sh
source "$FFSMART_ROOT/lib/ffsmart-common.sh"
# shellcheck source=lib/ffsmart-cli.sh
source "$FFSMART_ROOT/lib/ffsmart-cli.sh"
# shellcheck source=lib/ffsmart-cache.sh
source "$FFSMART_ROOT/lib/ffsmart-cache.sh"
# shellcheck source=lib/ffsmart-hardware.sh
source "$FFSMART_ROOT/lib/ffsmart-hardware.sh"
# shellcheck source=lib/ffsmart-probe.sh
source "$FFSMART_ROOT/lib/ffsmart-probe.sh"
# shellcheck source=lib/ffsmart-policy.sh
source "$FFSMART_ROOT/lib/ffsmart-policy.sh"

ffsmart_main() {
    local cache_state cache_status fallback_mode require_cache=false
    FFSMART_SHOW_HELP=false
    ffsmart_cli_defaults
    ffsmart_parse_cli "$@" || return

    if [[ "$FFSMART_SHOW_HELP" == true ]]; then
        ffsmart_show_help
        return 0
    fi
    ffsmart_validate_cli || return
    ffsmart_init_state || return

    fallback_mode="${FFMPEG_SMART_CACHE_FALLBACK:-none}"
    case "$fallback_mode" in
        none|proxy) ;;
        *) ffsmart_configuration_error "FFMPEG_SMART_CACHE_FALLBACK must be none or proxy"; return 64 ;;
    esac
    ffsmart_is_true "${FFMPEG_SMART_REQUIRE_CACHE:-false}" && require_cache=true

    if [[ "$FFSMART_CACHE_STATUS_ONLY" == true ]]; then
        set +e
        ffsmart_cache_status
        cache_status=$?
        set -e
        cache_state="$FFSMART_CACHE_STATUS_VALUE"
        printf 'FFMPEG_SMART_CACHE_STATUS=%s\n' "$cache_state"
        return "$cache_status"
    fi

    if [[ "$FFSMART_RECACHE" == true ]]; then
        ffsmart_rebuild_cache true || return
        if [[ "$FFSMART_RECACHE_ONLY" == true ]]; then
            return 0
        fi
    elif ffsmart_lock_is_live; then
        if [[ "$fallback_mode" == proxy ]]; then
            ffsmart_run_degraded_proxy "Hardware benchmark is in progress"
            return
        fi
        ffsmart_log "Hardware benchmark in progress"
        return 75
    fi

    set +e
    ffsmart_cache_status
    cache_status=$?
    set -e
    cache_state="$FFSMART_CACHE_STATUS_VALUE"
    if [[ "$cache_status" -ne 0 ]]; then
        if [[ "$require_cache" == true ]]; then
            if [[ "$fallback_mode" == proxy ]]; then
                ffsmart_run_degraded_proxy "$(ffsmart_cache_required_message "$cache_state")"
                return
            fi
            ffsmart_fail 78 "capability-cache-$cache_state" "$(ffsmart_cache_required_message "$cache_state"). Use Rebuild Hardware Cache or run --recache-only. Cache: $FFSMART_CACHE_FILE"
            return 78
        fi
        ffsmart_log "Capability cache is $cache_state; rebuilding before media startup"
        ffsmart_rebuild_cache false || return
    fi

    ffsmart_prepare_probe_input || return
    trap ffsmart_exit_cleanup EXIT HUP INT TERM
    ffsmart_adaptive_probe || return
    if [[ "$FFSMART_MAP_MODE" == all && "$FFSMART_VIDEO_COUNT" -ne 1 ]]; then
        ffsmart_configuration_error "Map-all requires exactly one input video stream; found $FFSMART_VIDEO_COUNT"
        return 64
    fi
    ffsmart_run_normal_pipeline
}

ffsmart_main "$@"
