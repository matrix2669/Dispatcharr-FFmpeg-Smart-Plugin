# Dispatcharr FFmpeg Smart Plugin

Native Dispatcharr plugin that bundles `ffmpeg-smart.sh`, creates managed Stream/Output Profiles, and can rebuild the GPU capability and concurrent-capacity cache from the Plugins page.

## Installation

Add the matrix2669 plugin registry in **Plugins → Plugin Repositories**:

```text
https://raw.githubusercontent.com/matrix2669/dispatcharr-plugins/main/manifest.json
```

Install **FFmpeg Smart Profiles**, enable it, then run **Install or Update Profiles**.

## Managed profiles

- `FFmpeg Smart` Stream Profile, using the bundled adaptive hardware-aware wrapper.
- Up to two independently enabled and renamed Stream Profiles.
- Up to three independently enabled and renamed Output Profiles.

Every managed profile points to the bundled `ffmpeg-smart-plugin.sh` launcher. The launcher keeps mutable state in `/data/ffmpeg_smart_profiles` and then executes the bundled `ffmpeg-smart.sh`. Output Profiles use its pipe-safe `-i pipe:0` mode, which samples the stream for probing and prepends the sampled packets when transcoding starts.

Every slot has an enable checkbox, editable profile name, checkboxes for 10-bit, HDR, SDR, and deinterlacing, plus editable additional `ffmpeg-smart` options. If Allow HDR and Force SDR are both checked, Force SDR takes precedence and only `-sdr` is written to the profile. Running **Install or Update Profiles** reconciles renamed or disabled managed profiles when the corresponding cleanup setting is enabled. Existing development profiles that used the native `ffmpeg` command are migrated to the script when their names match the original bundled templates.

Saved settings from development versions that placed policy flags in the additional-options field remain compatible. On **Install / Update**, the plugin removes those copies, enables their matching checkboxes in persisted settings, and generates each policy flag once. Refresh the settings page after normalization to see the checkbox changes; Dispatcharr does not invoke plugins directly from its settings Save button.

The initial defaults enable Stream Profile 1 (`FFmpeg Smart`) with 10-bit and HDR allowed, and Output Profile 1 (`FFMpeg Smart - 720p Mobile`) with Force SDR, deinterlacing, `-maxres 720`, `-maxbr 2M`, and `-maxchan 2`. The remaining three slots start disabled with blank names and options.

The settings page includes a short flag reference for output codec, resolution, bitrate, audio-channel limits, acceleration, and explicit device selection.

Profile installation is idempotent. Locked profiles, duplicate names, and same-name profiles pointing to unrelated commands are reported as conflicts rather than overwritten. Dispatcharr requires a full restart before directly created or updated profiles can be used, so both profile-changing actions show a confirmation warning and return a restart-required notification.

The plugin cannot restart Dispatcharr by itself in a standard container deployment. It runs as the unprivileged Dispatcharr service user and is intentionally not given access to the Docker host control socket.

## Hardware cache

The capability cache, probe sample, benchmark lock, PID, and log live under `/data/ffmpeg_smart_profiles`, outside the replaceable `/data/plugins/ffmpeg_smart_profiles` install directory. Plugin updates therefore cannot delete benchmark results or in-progress status. The data directory may be retained across plugin reinstalls and removed manually only when FFmpeg Smart state is no longer wanted.

Managed profiles require a valid cache. If it is missing, unreadable, or stale for the visible hardware, the launcher exits with code 78 and writes a clearly identified `[ffmpeg-smart] ERROR [capability-cache-...]` message to FFmpeg's stderr. Run **Rebuild Hardware Cache** and check **Benchmark Status** before retrying the stream. This avoids an unexplained media-probe or hardware failure and does not start an automatic, disruptive benchmark from a viewer request.

**Rebuild Hardware Cache** first creates a benchmark lock, stops active Dispatcharr transcoding streams, disconnects their current viewers, and waits for teardown to complete. New FFmpeg Smart transcodes are rejected until benchmarking ends, while proxy-only streams continue running. Both input Stream Profile transcodes and Output Profile transcodes are detected when clearing existing work. The confirmation estimates runtime from the number of visible DRM GPUs. The plugin then starts `ffmpeg-smart-plugin.sh --recache-only` in the background. This is an intentionally heavy operation: it runs real concurrent transcodes against each visible GPU. If a transcode cannot be stopped within 15 seconds, the benchmark is not started. The lock is removed automatically at completion and stale locks recover automatically. **Benchmark Status** reports active progress and the latest log line while running, cached acceleration/codec and primary/secondary device details whenever available, and the last 30 log lines.

## Requirements

- Dispatcharr v0.29.0 or newer
- `bash`, `ffmpeg`, `ffprobe`, `jq`, and GNU `timeout`
- `/dev/dri/renderD*` mapped into the Dispatcharr container for QSV/VAAPI

## Bundled wrapper updates

`matrix2669/ffmpeg-asr` is the source of truth for `ffmpeg-smart.sh`. The plugin records the exact source commit and SHA-256 checksum in `ffmpeg-smart-profiles/FFMPEG_SMART_SOURCE.json`. CI verifies that the bundled copy is byte-for-byte identical to that immutable source.

The daily **Sync FFmpeg Smart wrapper** workflow, which can also be run manually, checks `ffmpeg-asr/main`. When the wrapper changes, it updates the bundled copy and source metadata, runs validation, and opens a pull request for review. Existing plugin releases remain pinned and never change silently.

To synchronize locally:

```bash
scripts/sync-ffmpeg-smart.sh main
scripts/check-ffmpeg-smart-source.sh
```

## Project documentation

- `AGENT.md` defines architecture, ownership boundaries, development rules, compatibility gates, and validation.
- `BRANCHES.md` records why every current branch exists.
- `DECISIONS.md` preserves architectural rationale and superseded approaches.
- `CHANGELOG.md` records user-visible history.
- `RELEASE.md` defines version, tag, registry, packaging, and release procedures.
- `VERSION` is the canonical plugin version and must match both plugin declarations.

The source repository uses `main` for production-ready Releases and `dev` for next-version integration. Immutable beta and completed stable tags feed the `dispatcharr-plugins:dev` registry. The stable registry changes only after an explicitly approved GitHub Release.

The existing `v0.1.0` Release predates the inherited-wrapper licensing review. New GitHub Releases and distributable plugin ZIPs remain blocked until the licensing of the inherited `ffmpeg-smart.sh` source is explicitly resolved; see `DECISIONS.md` and `RELEASE.md`.

## License

matrix2669-authored plugin code is MIT licensed. The bundled wrapper retains the licensing provenance of its canonical `ffmpeg-asr` source; see `DECISIONS.md` for the current distribution boundary.
