#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_METADATA="$REPO_ROOT/ffmpeg-smart-profiles/FFMPEG_SMART_SOURCE.json"
BUNDLED_SCRIPT="$REPO_ROOT/ffmpeg-smart-profiles/ffmpeg-smart.sh"

sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

for command_name in curl jq; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Required command not found: $command_name" >&2
        exit 1
    fi
done

source_repo="$(jq -r '.repository' "$SOURCE_METADATA")"
source_path="$(jq -r '.path' "$SOURCE_METADATA")"
source_commit="$(jq -r '.commit' "$SOURCE_METADATA")"
expected_sha="$(jq -r '.sha256' "$SOURCE_METADATA")"

if [[ ! "$source_commit" =~ ^[0-9a-f]{40}$ ]]; then
    echo "Source commit must be a full 40-character Git SHA" >&2
    exit 1
fi
if [[ ! "$expected_sha" =~ ^[0-9a-f]{64}$ ]]; then
    echo "Source SHA-256 must contain 64 lowercase hexadecimal characters" >&2
    exit 1
fi

actual_sha="$(sha256_file "$BUNDLED_SCRIPT")"
if [[ "$actual_sha" != "$expected_sha" ]]; then
    echo "Bundled ffmpeg-smart.sh does not match its recorded SHA-256" >&2
    echo "expected: $expected_sha" >&2
    echo "actual:   $actual_sha" >&2
    exit 1
fi

bash -n "$BUNDLED_SCRIPT"

if [[ "${1:-}" == "--offline" ]]; then
    echo "Bundled ffmpeg-smart.sh matches the recorded source checksum"
    exit 0
fi

temp_dir="$(mktemp -d)"
trap 'rm -rf "$temp_dir"' EXIT
source_copy="$temp_dir/ffmpeg-smart.sh"
source_url="https://raw.githubusercontent.com/$source_repo/$source_commit/$source_path"
curl --fail --silent --show-error --location "$source_url" --output "$source_copy"

source_sha="$(sha256_file "$source_copy")"
if [[ "$source_sha" != "$expected_sha" ]] || ! cmp -s "$source_copy" "$BUNDLED_SCRIPT"; then
    echo "Bundled ffmpeg-smart.sh differs from $source_repo@$source_commit" >&2
    exit 1
fi

echo "Bundled ffmpeg-smart.sh matches $source_repo@$source_commit"
