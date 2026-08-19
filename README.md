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
- `FFmpeg Smart - Passthrough` Output Profile.
- `FFmpeg Smart - 720p 2M Stereo` Output Profile.
- `FFmpeg Smart - 1080p 8M Stereo` Output Profile.

The output profiles use native FFmpeg commands because Dispatcharr supplies output-profile input as a live MPEG-TS stream on `pipe:0`. The stream wrapper probes its input before transcoding and therefore cannot safely consume and reopen that pipe.

Profile installation is idempotent. Locked profiles, duplicate names, and same-name profiles pointing to unrelated commands are reported as conflicts rather than overwritten.

## Hardware cache

**Rebuild Hardware Cache** first creates a benchmark lock, stops active Dispatcharr transcoding streams, disconnects their current viewers, and waits for teardown to complete. New FFmpeg Smart transcodes are rejected until benchmarking ends, while proxy-only streams continue running. Both input Stream Profile transcodes and native Output Profile transcodes are detected when clearing existing work. The plugin then starts `ffmpeg-smart.sh --recache-only` in the background. This is an intentionally heavy operation: it runs real concurrent transcodes against each visible GPU. If a transcode cannot be stopped within 15 seconds, the benchmark is not started. The lock is removed automatically at completion and stale locks recover automatically. **Benchmark Status** reports current state and the last 30 log lines.

## Requirements

- Dispatcharr v0.29.0 or newer
- `bash`, `ffmpeg`, `ffprobe`, `jq`, and GNU `timeout`
- `/dev/dri/renderD*` mapped into the Dispatcharr container for QSV/VAAPI

## License

MIT
