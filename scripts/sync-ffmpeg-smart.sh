#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$REPO_ROOT/ffmpeg-smart-profiles"
SOURCE_METADATA="$RUNTIME_DIR/FFMPEG_SMART_SOURCE.json"
SOURCE_REF="${1:-$(jq -r '.tracking_ref // "main"' "$SOURCE_METADATA")}"

sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

validate_relative_path() {
    local path="$1"
    if [[ -z "$path" || "$path" == /* || "$path" == *".."* ]]; then
        echo "Invalid bundled runtime path: $path" >&2
        exit 1
    fi
}

for command_name in curl git jq; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Required command not found: $command_name" >&2
        exit 1
    fi
done

source_repo="$(jq -r '.repository' "$SOURCE_METADATA")"
recorded_commit="$(jq -r '.commit' "$SOURCE_METADATA")"
source_git_url="https://github.com/$source_repo.git"

if [[ "$SOURCE_REF" =~ ^[0-9a-f]{40}$ ]]; then
    source_commit="$SOURCE_REF"
else
    source_commit="$(git ls-remote "$source_git_url" "refs/heads/$SOURCE_REF" | awk 'NR == 1 {print $1}')"
    if [[ -z "$source_commit" ]]; then
        source_commit="$(git ls-remote "$source_git_url" "refs/tags/$SOURCE_REF^{}" | awk 'NR == 1 {print $1}')"
    fi
    if [[ -z "$source_commit" ]]; then
        source_commit="$(git ls-remote "$source_git_url" "refs/tags/$SOURCE_REF" | awk 'NR == 1 {print $1}')"
    fi
fi

if [[ ! "$source_commit" =~ ^[0-9a-f]{40}$ ]]; then
    echo "Unable to resolve $source_repo ref '$SOURCE_REF' to a commit" >&2
    exit 1
fi

temp_dir="$(mktemp -d)"
trap 'rm -rf "$temp_dir"' EXIT
metadata_copy="$temp_dir/FFMPEG_SMART_SOURCE.json"
cp "$SOURCE_METADATA" "$metadata_copy"
changed=false

while IFS= read -r entry; do
    source_path="$(printf '%s' "$entry" | jq -r '.path')"
    file_mode="$(printf '%s' "$entry" | jq -r '.mode')"
    recorded_sha="$(printf '%s' "$entry" | jq -r '.sha256')"
    validate_relative_path "$source_path"
    if [[ ! "$file_mode" =~ ^0(644|755)$ ]]; then
        echo "Runtime mode must be 0644 or 0755: $source_path" >&2
        exit 1
    fi

    source_copy="$temp_dir/runtime/$source_path"
    mkdir -p "$(dirname "$source_copy")"
    source_url="https://raw.githubusercontent.com/$source_repo/$source_commit/$source_path"
    curl --fail --silent --show-error --location "$source_url" --output "$source_copy"
    bash -n "$source_copy"
    source_sha="$(sha256_file "$source_copy")"

    if [[ "$recorded_sha" != "$source_sha" ]] || \
        ! cmp -s "$source_copy" "$RUNTIME_DIR/$source_path" 2>/dev/null; then
        changed=true
    fi

    next_metadata="$temp_dir/metadata-next.json"
    jq --arg path "$source_path" --arg sha256 "$source_sha" \
        '(.files[] | select(.path == $path).sha256) = $sha256' \
        "$metadata_copy" >"$next_metadata"
    mv "$next_metadata" "$metadata_copy"
done < <(jq -c '.files[]' "$SOURCE_METADATA")

if [[ "$recorded_commit" != "$source_commit" ]]; then
    changed=true
fi

if [[ "$changed" == false ]]; then
    echo "Bundled FFmpeg Adaptive runtime is already current at $source_commit"
    exit 0
fi

while IFS= read -r entry; do
    source_path="$(printf '%s' "$entry" | jq -r '.path')"
    file_mode="$(printf '%s' "$entry" | jq -r '.mode')"
    mkdir -p "$(dirname "$RUNTIME_DIR/$source_path")"
    install -m "$file_mode" "$temp_dir/runtime/$source_path" "$RUNTIME_DIR/$source_path"
done < <(jq -c '.files[]' "$SOURCE_METADATA")

next_metadata="$temp_dir/metadata-final.json"
jq --arg commit "$source_commit" '.commit = $commit' \
    "$metadata_copy" >"$next_metadata"
mv "$next_metadata" "$SOURCE_METADATA"

echo "Synced FFmpeg Adaptive runtime from $source_repo@$source_commit"
echo "Files: $(jq -r '.files | length' "$SOURCE_METADATA")"
