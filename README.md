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

Every managed profile points to the bundled `ffmpeg-smart-plugin.sh` launcher. The launcher keeps mutable state in `/data/ffmpeg_smart_profiles`, enables the canonical degraded proxy option, and then executes the bundled `ffmpeg-smart.sh`. With a valid cache, Output Profiles use its pipe-safe `-i pipe:0` mode, which samples the stream for probing and prepends the sampled packets when transcoding starts. When a required scan is pending or active, the same launcher skips Smart probing and uses direct FFmpeg stream copy instead.

Every slot has an enable checkbox, editable profile name, checkboxes for 10-bit, HDR, SDR, and deinterlacing, editable additional `ffmpeg-smart` policy options, and scoped advanced FFmpeg controls. If Allow HDR and Force SDR are both checked, Force SDR takes precedence and only `-sdr` is written to the profile. Running **Install or Update Profiles** reconciles renamed or disabled managed profiles when the corresponding cleanup setting is enabled. Existing development profiles that used the native `ffmpeg` command are migrated to the script when their names match the original bundled templates.

The advanced controls retain FFmpeg Smart's hardware benefits while exposing options at the phase where FFmpeg expects them:

- **Input defaults** are placed before `-i` and normally inherit Smart's corruption/timestamp handling.
- **Stream mapping** normally selects the first video and optional first audio. Map all input streams is available when the input has one video; custom Replace mappings must explicitly select exactly one video and may add audio, subtitle, data, or attachment streams.
- **Video tuning defaults** apply only when Smart chooses to transcode video and can tune GOP, key frames, rate control, or encoder-specific behavior without replacing Smart's selected encoder or hardware filters.
- **Audio defaults** apply on both video-copy and video-transcode paths and can replace Smart's AAC/copy decision with a deliberate codec choice.
- **MPEG-TS/output defaults** apply on both paths before the fixed `-f mpegts pipe:1` contract. The existing beta.3 Additional FFmpeg options field is retained here, and a saved value with Inherit selected behaves as Add.

The current inherited value or formula is shown directly below every mode dropdown. Dispatcharr's plugin form cannot change one field when a different dropdown changes, so the adjacent options field intentionally stays blank and contains only user-owned Add/Replace text. This also prevents selecting Inherit from overwriting a saved custom value.

| Scope | Inherited default |
|---|---|
| Input | `-fflags +genpts+igndts+discardcorrupt -err_detect ignore_err` |
| Mapping | `-map 0:v:0 -map 0:a:0?` |
| Video transcode tuning | `-b:v <target> -maxrate <rate> -bufsize <buffer> -g <rounded source fps> -bf <0 or 2> <accelerator tuning> -fps_mode cfr -r <source fps> [-tag:v hvc1]`. The target is 8 Mbps at 1080p scaled by output pixels with a 2 Mbps floor. Without `-maxbr`, maxrate is 125% and buffer is 200% of target. With `-maxbr`, target is capped at 85%, maxrate equals the limit, and buffer is twice the limit. |
| Audio | No options without audio; compatible AAC uses `-c:a copy`; other audio uses `-c:a aac -b:a <rate> -ac <channels> [-ch_layout ...] -af aresample=async=1`. Rates are 96k mono, 192k stereo, 384k 5.1, 512k 7.1, or 64k per channel otherwise. |
| MPEG-TS/output | `-avoid_negative_ts make_zero -start_at_zero -mpegts_copyts 0 -mpegts_flags +pat_pmt_at_frames+resend_headers -flush_packets 1 -max_muxing_queue_size 4096`, followed by Smart-owned `-f mpegts pipe:1`. |

Each non-mapping group offers **Use FFmpeg Smart default**, **Add to default**, and **Replace default**. Replace may be intentionally blank. Fields accept normal shell-style quoting; the plugin parses with `shlex` without evaluating the text and quotes every wrapper argument independently.

For the Discord-style example, choose Replace for Input and enter `-fflags +discardcorrupt+genpts+nobuffer`; choose Map all input streams; choose Add for Video and enter `-g 60 -keyint_min 60 -sc_threshold 0 -force_key_frames 'expr:gte(t,n_forced*2)'`; choose Replace for Audio and enter `-c:a ac3`; then choose Replace for MPEG-TS/output and enter `-mpegts_flags +pat_pmt_at_frames+resend_headers+initial_discontinuity`.

Do not enter `-user_agent`, `-i`, `-c:v`, hardware/device flags, filter graphs, `-f mpegts`, or `pipe:1`: Smart owns those structural parts. Explicit profile limits still win—`-maxbr` remains the maximum bitrate and `-maxchan` remains the maximum channel count. Other expert combinations are accepted only as far as the installed FFmpeg build and selected encoder support them.

Saved settings from development versions that placed policy flags in the additional-options field remain compatible. On **Install / Update**, the plugin removes those copies, enables their matching checkboxes in persisted settings, and generates each policy flag once. Refresh the settings page after normalization to see the checkbox changes; Dispatcharr does not invoke plugins directly from its settings Save button.

The initial defaults enable Stream Profile 1 (`FFmpeg Smart`) with 10-bit and HDR allowed, and Output Profile 1 (`FFMpeg Smart - 720p Mobile`) with Force SDR, deinterlacing, `-maxres 720`, `-maxbr 2M`, and `-maxchan 2`. The remaining three slots start disabled with blank names and options.

The settings page includes a short flag reference for output codec, resolution, bitrate, audio-channel limits, acceleration, and explicit device selection.

Profile installation is idempotent. Locked profiles, duplicate names, and same-name profiles pointing to unrelated commands are reported as conflicts rather than overwritten. Adding a profile requires a full Dispatcharr restart before the new profile can be used; updating an existing managed profile applies without a restart. Removing profiles still requires a restart for the removal to fully take effect.

The plugin cannot restart Dispatcharr by itself in a standard container deployment. It runs as the unprivileged Dispatcharr service user and is intentionally not given access to the Docker host control socket.

## Hardware cache

The capability cache, probe sample, benchmark lock, PID, and log live under `/data/ffmpeg_smart_profiles`, outside the replaceable `/data/plugins/ffmpeg_smart_profiles` install directory. Plugin updates therefore cannot delete benchmark results or in-progress status. The data directory may be retained across plugin reinstalls and removed manually only when FFmpeg Smart state is no longer wanted.

FFmpeg Smart policy and hardware acceleration require a valid cache. If it is missing, unreadable, stale for the visible hardware, or being rebuilt, the launcher writes a clearly identified `[ffmpeg-smart] WARNING [degraded-proxy]` message and runs a basic `-c copy` MPEG-TS proxy. This fallback preserves the configured input, mapping, and mux scopes but does not enforce Smart video/audio constraints and does not substitute CPU transcoding. A source that cannot be remuxed into MPEG-TS may still fail with FFmpeg's native error. Run **Rebuild Hardware Cache** and check **Benchmark Status** to restore Smart processing; a viewer request never starts the disruptive benchmark automatically.

The plugin asks the canonical wrapper to validate the cache rather than treating an existing file as healthy. A missing, invalid, stale, or unverifiable cache creates a persistent, admin-only **FFmpeg Smart hardware acceleration bypassed** warning in Dispatcharr's notification center. Starting a rebuild updates the same warning with scan progress; successful validation removes it automatically. Every degraded wrapper invocation writes a new marker that reactivates the notification if an administrator dismissed it while the condition remained unresolved. This is the same database-backed notification mechanism Dispatcharr uses for account-expiration warnings, not a one-time toast.

Dispatcharr's ZIP installer does not preserve executable mode bits. When an enabled plugin is loaded after installation or update, FFmpeg Smart restores execute permission on both bundled scripts before profiles or actions use them. Managed profile commands continue executing the launcher directly rather than routing through `/bin/bash`.

**Rebuild Hardware Cache** first creates a benchmark lock, stops active Dispatcharr transcoding streams, disconnects their current viewers, and waits for teardown to complete. New managed starts use basic FFmpeg stream copy until benchmarking ends, while existing proxy-only streams continue running. Both input Stream Profile transcodes and Output Profile transcodes are detected when clearing existing work. The confirmation estimates runtime from the number of visible DRM GPUs. The plugin then starts `ffmpeg-smart-plugin.sh --recache-only` in the background. This is an intentionally heavy operation: it runs real concurrent transcodes against each visible GPU. Stream copy does not use the GPU decode, filter, or encode paths being measured; it still has small shared CPU, memory, and network costs, so unusually heavy proxy traffic can affect the host. If a transcode cannot be stopped within 15 seconds, the benchmark is not started. The lock is removed automatically at completion and stale locks recover automatically. **Benchmark Status** reports active progress and the latest log line while running, current cache validity, cached acceleration/codec and primary/secondary device details whenever available, and the last 30 log lines. Dispatcharr v0.29.0 colors a completed plugin action popup green without inspecting the returned health status, so the popup message—not its edge color—states whether a hardware recheck is required.

Because benchmark-time starts now take the degraded stream-copy path, Dispatcharr does not receive the wrapper's reserved maintenance exit status for plugin-managed profiles. If native FFmpeg cannot remux a source, Dispatcharr still handles that native process failure through its ordinary retry and alternate-stream behavior.

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
