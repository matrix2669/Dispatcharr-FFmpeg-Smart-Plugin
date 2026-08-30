#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$REPO_ROOT/ffmpeg-smart-profiles"
SOURCE_METADATA="$RUNTIME_DIR/FFMPEG_SMART_SOURCE.json"

sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

file_mode() {
    if stat -c '%a' "$1" >/dev/null 2>&1; then
        stat -c '%a' "$1"
    else
        stat -f '%Lp' "$1"
    fi
}

validate_relative_path() {
    local path="$1"
    if [[ -z "$path" || "$path" == /* || "$path" == *".."* ]]; then
        echo "Invalid bundled runtime path: $path" >&2
        exit 1
    fi
}

metadata_contains_path() {
    local required_path="$1"
    jq -e --arg path "$required_path" \
        '.files | any(.path == $path)' "$SOURCE_METADATA" >/dev/null
}

verify_entrypoint_modules() {
    local entrypoint="$RUNTIME_DIR/ffmpeg-smart.sh"
    local required_path
    while IFS= read -r required_path; do
        [[ -n "$required_path" ]] || continue
        if ! metadata_contains_path "$required_path"; then
            echo "Entrypoint module is not pinned in source metadata: $required_path" >&2
            exit 1
        fi
    done < <(sed -n 's@^source "$FFSMART_ROOT/\([^"]*\.sh\)"@\1@p' "$entrypoint")
}

for command_name in jq; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Required command not found: $command_name" >&2
        exit 1
    fi
done
if [[ "${1:-}" != "--offline" ]] && ! command -v curl >/dev/null 2>&1; then
    echo "Required command not found: curl" >&2
    exit 1
fi

source_repo="$(jq -r '.repository' "$SOURCE_METADATA")"
source_commit="$(jq -r '.commit' "$SOURCE_METADATA")"
file_count="$(jq -r '.files | length' "$SOURCE_METADATA")"

if [[ ! "$source_commit" =~ ^[0-9a-f]{40}$ ]]; then
    echo "Source commit must be a full 40-character Git SHA" >&2
    exit 1
fi
if [[ ! "$file_count" =~ ^[1-9][0-9]*$ ]]; then
    echo "Source metadata must pin at least one runtime file" >&2
    exit 1
fi

while IFS= read -r entry; do
    source_path="$(printf '%s' "$entry" | jq -r '.path')"
    expected_mode="$(printf '%s' "$entry" | jq -r '.mode')"
    expected_sha="$(printf '%s' "$entry" | jq -r '.sha256')"
    validate_relative_path "$source_path"
    if [[ ! "$expected_sha" =~ ^[0-9a-f]{64}$ ]]; then
        echo "Source SHA-256 must contain 64 lowercase hexadecimal characters: $source_path" >&2
        exit 1
    fi
    if [[ ! "$expected_mode" =~ ^0(644|755)$ ]]; then
        echo "Runtime mode must be 0644 or 0755: $source_path" >&2
        exit 1
    fi

    bundled_path="$RUNTIME_DIR/$source_path"
    if [[ ! -f "$bundled_path" ]]; then
        echo "Bundled runtime file is missing: $source_path" >&2
        exit 1
    fi
    actual_sha="$(sha256_file "$bundled_path")"
    if [[ "$actual_sha" != "$expected_sha" ]]; then
        echo "Bundled runtime file does not match its recorded SHA-256: $source_path" >&2
        echo "expected: $expected_sha" >&2
        echo "actual:   $actual_sha" >&2
        exit 1
    fi
    if [[ "0$(file_mode "$bundled_path")" != "$expected_mode" ]]; then
        echo "Bundled runtime file mode does not match metadata: $source_path" >&2
        exit 1
    fi
    bash -n "$bundled_path"
done < <(jq -c '.files[]' "$SOURCE_METADATA")

verify_entrypoint_modules

if [[ "${1:-}" == "--offline" ]]; then
    echo "Bundled FFmpeg Adaptive runtime ($file_count files) matches recorded checksums"
    exit 0
fi

temp_dir="$(mktemp -d)"
trap 'rm -rf "$temp_dir"' EXIT

while IFS= read -r entry; do
    source_path="$(printf '%s' "$entry" | jq -r '.path')"
    expected_sha="$(printf '%s' "$entry" | jq -r '.sha256')"
    source_copy="$temp_dir/$source_path"
    mkdir -p "$(dirname "$source_copy")"
    source_url="https://raw.githubusercontent.com/$source_repo/$source_commit/$source_path"
    curl --fail --silent --show-error --location "$source_url" --output "$source_copy"

    source_sha="$(sha256_file "$source_copy")"
    if [[ "$source_sha" != "$expected_sha" ]] || \
        ! cmp -s "$source_copy" "$RUNTIME_DIR/$source_path"; then
        echo "Bundled runtime file differs from $source_repo@$source_commit: $source_path" >&2
        exit 1
    fi
done < <(jq -c '.files[]' "$SOURCE_METADATA")

echo "Bundled FFmpeg Adaptive runtime matches $source_repo@$source_commit"
