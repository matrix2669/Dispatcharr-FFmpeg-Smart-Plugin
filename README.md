# Dispatcharr FFmpeg Smart Plugin

Native Dispatcharr plugin that bundles `ffmpeg-smart.sh`, creates managed Stream/Output Profiles, and can rebuild the GPU capability and concurrent-capacity cache from the Plugins page.

## Development installation

Add the development registry in **Plugins → Plugin Repositories**:

```text
https://raw.githubusercontent.com/matrix2669/dispatcharr-plugins/dev-test/manifest.json
```

Install **FFmpeg Smart Profiles**, enable it, then run **Install or Update Profiles**.

## Managed profiles

- `FFmpeg Smart` Stream Profile, using the bundled adaptive hardware-aware wrapper.
- Up to two independently enabled and renamed Stream Profiles.
- Up to three independently enabled and renamed Output Profiles.

Every managed profile points to the bundled `ffmpeg-smart.sh`. Output Profiles use its pipe-safe `-i pipe:0` mode, which samples the stream for probing and prepends the sampled packets when transcoding starts.

Every slot has an enable checkbox, editable profile name, checkboxes for 10-bit, HDR, SDR, and deinterlacing, plus editable additional `ffmpeg-smart` options. If Allow HDR and Force SDR are both checked, Force SDR takes precedence and only `-sdr` is written to the profile. Running **Install or Update Profiles** reconciles renamed or disabled managed profiles when the corresponding cleanup setting is enabled. Existing development profiles that used the native `ffmpeg` command are migrated to the script when their names match the original bundled templates.

Saved settings from development versions that placed policy flags in the additional-options field remain compatible. On **Install / Update**, the plugin removes those copies, enables their matching checkboxes in persisted settings, and generates each policy flag once. Refresh the settings page after normalization to see the checkbox changes; Dispatcharr does not invoke plugins directly from its settings Save button.

The initial defaults enable Stream Profile 1 (`FFmpeg Smart`) with 10-bit and HDR allowed, and Output Profile 1 (`FFMpeg Smart - 720p Mobile`) with Force SDR, deinterlacing, `-maxres 720`, `-maxbr 2M`, and `-maxchan 2`. The remaining three slots start disabled with blank names and options.

The settings page includes a short flag reference for output codec, resolution, bitrate, audio-channel limits, acceleration, and explicit device selection.

Profile installation is idempotent. Locked profiles, duplicate names, and same-name profiles pointing to unrelated commands are reported as conflicts rather than overwritten. Dispatcharr requires a full restart before directly created or updated profiles can be used, so both profile-changing actions show a confirmation warning and return a restart-required notification.

The plugin cannot restart Dispatcharr by itself in a standard container deployment. It runs as the unprivileged Dispatcharr service user and is intentionally not given access to the Docker host control socket.

## Hardware cache

**Rebuild Hardware Cache** first creates a benchmark lock, stops active Dispatcharr transcoding streams, disconnects their current viewers, and waits for teardown to complete. New FFmpeg Smart transcodes are rejected until benchmarking ends, while proxy-only streams continue running. Both input Stream Profile transcodes and Output Profile transcodes are detected when clearing existing work. The confirmation estimates runtime from the number of visible DRM GPUs. The plugin then starts `ffmpeg-smart.sh --recache-only` in the background. This is an intentionally heavy operation: it runs real concurrent transcodes against each visible GPU. If a transcode cannot be stopped within 15 seconds, the benchmark is not started. The lock is removed automatically at completion and stale locks recover automatically. **Benchmark Status** reports active progress and the latest log line while running, cached acceleration/codec and primary/secondary device details whenever available, and the last 30 log lines.

## Requirements

- Dispatcharr v0.29.0 or newer
- `bash`, `ffmpeg`, `ffprobe`, `jq`, and GNU `timeout`
- `/dev/dri/renderD*` mapped into the Dispatcharr container for QSV/VAAPI

## License

MIT
