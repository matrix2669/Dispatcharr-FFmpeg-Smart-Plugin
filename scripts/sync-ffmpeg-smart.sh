#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_METADATA="$REPO_ROOT/ffmpeg-smart-profiles/FFMPEG_SMART_SOURCE.json"
BUNDLED_SCRIPT="$REPO_ROOT/ffmpeg-smart-profiles/ffmpeg-smart.sh"
SOURCE_REF="${1:-main}"

sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

for command_name in curl git jq; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Required command not found: $command_name" >&2
        exit 1
    fi
done

source_repo="$(jq -r '.repository' "$SOURCE_METADATA")"
source_path="$(jq -r '.path' "$SOURCE_METADATA")"
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
source_copy="$temp_dir/ffmpeg-smart.sh"
metadata_copy="$temp_dir/FFMPEG_SMART_SOURCE.json"
source_url="https://raw.githubusercontent.com/$source_repo/$source_commit/$source_path"

curl --fail --silent --show-error --location "$source_url" --output "$source_copy"
bash -n "$source_copy"
source_sha="$(sha256_file "$source_copy")"

install -m 0755 "$source_copy" "$BUNDLED_SCRIPT"
jq \
    --arg commit "$source_commit" \
    --arg sha256 "$source_sha" \
    '.commit = $commit | .sha256 = $sha256' \
    "$SOURCE_METADATA" >"$metadata_copy"
mv "$metadata_copy" "$SOURCE_METADATA"

echo "Synced ffmpeg-smart.sh from $source_repo@$source_commit"
echo "SHA-256: $source_sha"
