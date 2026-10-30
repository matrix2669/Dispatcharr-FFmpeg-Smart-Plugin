# Dispatcharr FFmpeg Smart Plugin

Native Dispatcharr plugin that bundles `ffmpeg-smart.sh`, creates managed Stream/Output Profiles, and can rebuild the GPU capability and concurrent-capacity cache from the Plugins page.

This branch prepares local test build **0.2.2-beta.2**, pinned to canonical
runtime `8156f96ce44c2ca0cb0360a8503f7862285b9f23`, with shared startup-input
controls for Stream Profiles. Compatible H.264/HEVC continue to copy unless an
active constraint requires conversion. Runtime version 0.1.0 is unchanged from beta.1:
validate the existing cache and rebuild only if required. No registry release
or live deployment is claimed by this source checkpoint.

## Installation

Add the matrix2669 plugin registry in **Plugins → Plugin Repositories**:

```text
https://raw.githubusercontent.com/matrix2669/dispatcharr-plugins/main/manifest.json
```

Install **FFmpeg Smart Profiles**, enable it, then run **Install or Update Profiles**.

The stable release is `v0.2.1`. The GitHub Release includes
`dispatcharr-ffmpeg-smart-plugin-v0.2.1.zip` and its SHA-256 checksum. The registry
uses the exact immutable tag archive. The plugin deliberately retains the tested
MIT `ffmpeg-adaptive` source pin
`913a958fd5f9edc231c49a70539a09f611fdcc5a`; publishing standalone adaptive 0.1.0
does not replace these bundled bytes or by itself require a hardware recheck.

Official Dispatcharr 0.32.0 source compatibility and isolated archive
installation/update were reviewed for this release. See
[compatibility evidence](docs/stable-compatibility-2026-10-20.md). Release
publication does not update your running Dispatcharr installation.

The preceding immutable development build `v0.2.1-beta.5` remains at
`a5c0777875056591e4e02c989993f43b3f43aa72`. Its historical managed validation
is summarized below.

The official Dispatcharr v0.31.0 managed update installed beta.5 at the
approved zero-viewer gate, offered no further update, preserved enabled state
and settings, and retained prerelease semantics for future updates. The
hardware benchmark then completed at `2026-09-21T17:51:16.719376+00:00` with
return code 0, a complete outcome, a valid canonical cache, no PID, and no
benchmark lock. It measured VAAPI/HEVC 10-bit decode and encode, with primary
`renderD129` capacity 19 at 14x and secondary `renderD128` capacity 14 at
11.6x. The consolidated log was 1,508,339 bytes and contained no stray root
candidate/capacity/10-bit logs or `.benchmark-run` directories.

A bounded real-hardware managed-launcher check generated a four-second H.264
fixture and fed it via `pipe:0`, producing a 4.025-second 720p HEVC VAAPI
output; full decode with `-xerror` measured 120 frames without errors. This was a
fixture/launcher proof, not a provider-channel fetch or Dispatcharr profile
creation. The final `2026-09-21 17:52:25 UTC` snapshot had zero viewers,
input/output transcodes, and ffmpeg/ffprobe processes, with runtime and
manifest pins unchanged.

## Managed profiles

- `FFmpeg Smart` Stream Profile, using the bundled adaptive hardware-aware wrapper.
- Up to two independently enabled and renamed Stream Profiles.
- Up to three independently enabled and renamed Output Profiles.

Every managed profile points to the bundled `ffmpeg-smart-plugin.sh` launcher. The launcher keeps mutable state in `/data/ffmpeg_smart_profiles`, enables the canonical degraded proxy option, and then executes the bundled `ffmpeg-smart.sh`. With a valid cache, Output Profiles use its pipe-safe `-i pipe:0` mode, which samples the stream for probing and prepends the sampled packets when transcoding starts. When a required scan is pending or active, the same launcher skips Smart probing and uses direct FFmpeg stream copy instead.

Every slot has an enable checkbox, editable profile name, Force SDR and Force deinterlace checkboxes, editable additional `ffmpeg-smart` policy options, and scoped advanced FFmpeg controls. HDR and 10-bit selection are automatic; Force SDR emits `-sdr` when conversion is required. Running **Install or Update Profiles** removes retired `-10bit`/`-hdr` settings and flags, moves legacy `-sdr`/`-deint` options to their checkboxes, and reconciles renamed or disabled managed profiles when the corresponding cleanup setting is enabled. Existing development profiles that used the native `ffmpeg` command are migrated to the script when their names match the original bundled templates.

The advanced controls retain FFmpeg Smart's hardware benefits while exposing options at the phase where FFmpeg expects them:

- **Input defaults** are placed before `-i` and normally inherit Smart's corruption/timestamp handling. Adaptive `-analyzeduration` and `-probesize` values are Smart-owned rather than profile overrides.
- **Stream mapping** normally selects the first video and optional first audio. Map all input streams is available when the input has one video; custom Replace mappings must explicitly select exactly one video and may add audio, subtitle, data, or attachment streams. Mapped subtitle, data, and attachment streams are copied rather than automatically encoded, but their source codec must still be compatible with MPEG-TS.
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

Do not enter `-user_agent`, `-i`, `-analyzeduration`, `-probesize`, `-c:v`, hardware/device flags, filter graphs, `-f mpegts`, or `pipe:1`: Smart owns those structural parts. Explicit profile limits still win—`-maxbr` remains the maximum bitrate and `-maxchan` remains the maximum channel count. Other expert combinations are accepted only as far as the installed FFmpeg build and selected encoder support them.

The generated wrapper command intentionally repeats `-ffmpeg-input-option` once for every safely parsed FFmpeg argument. For example, `-analyzeduration 1000000` becomes `-ffmpeg-input-option -analyzeduration -ffmpeg-input-option 1000000`; this preserves two exact argv tokens without evaluating shell text. Beginning with `0.2.1-beta.1`, Install / Update removes saved manual probe-window pairs and persists the cleaned settings because adaptive probing selects and applies the safe tier automatically.

Saved settings from development versions that placed policy flags in the additional-options field remain compatible. On **Install / Update**, the plugin removes those copies, enables their matching checkboxes in persisted settings, and generates each policy flag once. Refresh the settings page after normalization to see the checkbox changes; Dispatcharr does not invoke plugins directly from its settings Save button.

The initial defaults enable Stream Profile 1 (`FFmpeg Smart`) with automatic HDR/10-bit policy, and Output Profile 1 (`FFMpeg Smart - 720p Mobile`) with Force SDR, deinterlacing, `-maxres 720`, `-maxbr 2M`, and `-maxchan 2`. The remaining three slots start disabled with blank names and options.

The settings page includes a short flag reference for output codec, resolution, bitrate, audio-channel limits, acceleration, and explicit device selection.

Profile installation is idempotent. Locked profiles, duplicate names, and same-name profiles pointing to unrelated commands are reported as conflicts rather than overwritten. Adding a profile requires a full Dispatcharr restart before the new profile can be used; updating an existing managed profile applies without a restart. Removing profiles still requires a restart for the removal to fully take effect.

The plugin cannot restart Dispatcharr by itself in a standard container deployment. It runs as the unprivileged Dispatcharr service user and is intentionally not given access to the Docker host control socket.

## Video compatibility controls

Each Stream Profile has a **Video codecs eligible for copy** list, defaulting to
`h264,hevc`, and a **Codec when video conversion is needed** selector, defaulting
to the cached encoder preference. These are universal defaults; configure them
for the receiver and MPEG-TS codecs you actually support.

The copy list is a nonempty comma-separated list of FFprobe codec names without
spaces, such as `h264,mpeg2video`. Video copies only when every other active
constraint is satisfied. The conversion selector can retain the cached preference
or choose H.264/HEVC for unsupported input and required resolution, bitrate,
deinterlace or SDR work. Selecting a fallback does not itself force conversion
of an allowed codec. For example, `h264,mpeg2video` plus H.264 fallback preserves
compliant H.264/MPEG-2 and converts HEVC or deinterlaced/resized MPEG-2 to H.264.

Existing explicit `-vc h264|hevc` takes priority over both controls, even when
it requests a codec outside the copy list. Audio, HDR and hardware behavior keep
their existing controls. Save settings and run **Install or Update Profiles**
to persist/apply choices; the plugin does not select a global default. Output
Profiles keep their defaults and may opt in explicitly with
`--copy-codecs LIST --fallback-codec h264|hevc` in Additional options.

## Shared startup input for Stream Profiles

Each Stream Profile has a saved **Shared startup input** selector. **Off** is
used for new or unspecified settings and preserves existing input/proxy handling.
Choose **Auto** explicitly to use URL hints for shared acquisition;
**Strict** uses one shared reader for a known continuous HTTP(S) MPEG-TS source.
The reader retains startup bytes in RAM so probing and playback consume the
same media connection. Full queues pause upstream reading without dropping
media or writing it to disk. No fixed prefill wait is added.

Auto checks URL hints only: HTTP(S) `.ts` paths or `format`/`output=ts|mpegts`
query values, excluding `.m3u8` paths. It does not inspect a body to detect its
format. Opaque URLs, other protocols, custom input-option tokens and missing
Python keep legacy handling. A hinted URL that returns another format fails
without reopening the source. Strict requires continuous 188-byte MPEG-TS and
Python 3.9+; custom input options are rejected. Dedicated user-agent and URL
Basic authentication work; redirects are bounded and strip cross-origin Basic
Authorization. Python direct connections/system TLS trust are used, without
FFmpeg-specific proxy, cookie or custom-header semantics. Owned broker clients
bypass inherited proxy settings so the private token-bearing URL stays local.

The adjacent limits default to **16 MiB** of retained payload, **20 seconds**
until first output media and **30 seconds** per blocking network operation.
Allowed ranges are 1–1024 MiB and 1–300 seconds. The cap excludes process and OS
buffer overhead; it is not a media-duration target. Small caps can starve probing
until the startup deadline. Source failures never start another shared media
reader. Canonical stderr telemetry reports credential-safe startup/request and
peak-retention measurements.

Save settings and run **Install or Update Profiles** to apply them. Missing
mode settings are persisted as Off; explicit Auto/Strict selections are preserved.
Other missing defaults are added once without replacing explicit choices or custom policy
options, including `-vc`. Existing profile updates keep the usual no-restart
behavior. Output Profiles keep their existing `-i pipe:0` path and have no shared
input controls. The plugin does not select Dispatcharr's global default or alter
channel-specific assignments. Version **0.2.2-beta.2** is a local test candidate;
provider performance and default-profile rollout require separate validation.

## Hardware cache

The capability cache, probe sample, benchmark lock, PID, log, and persisted benchmark outcome live under `/data/ffmpeg_smart_profiles`, outside the replaceable `/data/plugins/ffmpeg_smart_profiles` install directory. Plugin updates therefore cannot delete benchmark results or in-progress status. The data directory may be retained across plugin reinstalls and removed manually only when FFmpeg Smart state is no longer wanted.

FFmpeg Smart policy and hardware acceleration require a valid cache. If it is missing, unreadable, stale for the visible hardware, or being rebuilt, the launcher writes a clearly identified `[ffmpeg-smart] WARNING [degraded-proxy]` message and runs a basic `-c copy` MPEG-TS proxy. This fallback preserves the configured input, mapping, and mux scopes but does not enforce Smart video/audio constraints and does not substitute CPU transcoding. A source that cannot be remuxed into MPEG-TS may still fail with FFmpeg's native error. Run **Rebuild Hardware Cache** and check **Benchmark Status** to restore Smart processing; a viewer request never starts the disruptive benchmark automatically.

The plugin asks the canonical wrapper to validate the cache rather than treating an existing file as healthy. Benchmark Status understands the canonical V2 cache records, with legacy display compatibility, for optional capability and device details; cache validity still comes only from the wrapper's `--cache-status` result. A missing, invalid, stale, or unverifiable cache creates a persistent, admin-only **FFmpeg Smart hardware acceleration bypassed** warning in Dispatcharr's notification center. Starting a rebuild updates the same warning with scan progress; successful validation removes it automatically. A failed or abandoned rebuild remains an error even if an existing cache is still valid, and its notification does not falsely claim that acceleration is being bypassed when that cache remains usable. Every degraded wrapper invocation writes a new marker that reactivates the notification if an administrator dismissed it while the condition remained unresolved. This is the same database-backed notification mechanism Dispatcharr uses for account-expiration warnings, not a one-time toast.

Dispatcharr's ZIP installer does not preserve executable mode bits. When an enabled plugin is loaded after installation or update, FFmpeg Smart restores execute permission on both bundled scripts before profiles or actions use them. Managed profile commands continue executing the launcher directly rather than routing through `/bin/bash`.

**Rebuild Hardware Cache** first creates a benchmark lock, stops active Dispatcharr transcoding streams, disconnects their current viewers, and waits for teardown to complete. New managed starts use basic FFmpeg stream copy until benchmarking ends, while existing proxy-only streams continue running. Both input Stream Profile transcodes and Output Profile transcodes are detected when clearing existing work. The confirmation estimates runtime from the number of visible DRM GPUs. The plugin then starts `ffmpeg-smart-plugin.sh --recache-only` in the background. This is an intentionally heavy operation: it runs real concurrent transcodes against each visible GPU. Stream copy does not use the GPU decode, filter, or encode paths being measured; it still has small shared CPU, memory, and network costs, so unusually heavy proxy traffic can affect the host. If a transcode cannot be stopped within 15 seconds, the benchmark is not started. The top-level recache process owns the lock until it exits; benchmark-worker and command-substitution subshells cannot clear it early. The lock is removed automatically at completion and stale locks recover automatically. **Benchmark Status** reports active progress and the latest log line while running, current cache validity, cached acceleration/codec and primary/secondary device details whenever available, and the last 30 log lines. Dispatcharr v0.29.0 colors a completed plugin action popup green without inspecting the returned health status, so the popup message—not its edge color—states whether a hardware recheck is required.

Because benchmark-time starts now take the degraded stream-copy path, Dispatcharr does not receive the wrapper's reserved maintenance exit status for plugin-managed profiles. If native FFmpeg cannot remux a source, Dispatcharr still handles that native process failure through its ordinary retry and alternate-stream behavior.

## Requirements

- Dispatcharr v0.29.0 or newer
- `bash`, `ffmpeg`, `ffprobe`, `jq`, and GNU `timeout`
- `/dev/dri/renderD*` mapped into the Dispatcharr container for QSV/VAAPI

## Bundled runtime updates

`matrix2669/ffmpeg-adaptive` is the source of truth for the modular `ffmpeg-smart.sh` runtime. The plugin records one exact source commit plus the path, SHA-256 checksum, and installed mode of the entrypoint and every shell/Python module in `ffmpeg-smart-profiles/FFMPEG_SMART_SOURCE.json`. CI verifies that the complete bundle is byte-for-byte identical to that immutable source.

The daily **Sync FFmpeg Adaptive runtime** workflow, which can also be run manually, checks the metadata's tracked `ffmpeg-adaptive` ref. When any runtime file changes, it updates the complete bundle and source metadata, runs validation, and opens a pull request for review. Existing plugin releases remain pinned and never change silently. An omitted immutable tag or commit ref is rejected if it resolves to a different recorded commit; pass an explicit ref to make that change intentionally.

To synchronize locally:

```bash
scripts/sync-ffmpeg-smart.sh
scripts/check-ffmpeg-smart-source.sh
```

## Project documentation

- `AGENT.md` defines architecture, ownership boundaries, development rules, compatibility gates, and validation.
- `BRANCHES.md` records why every current branch exists.
- `DECISIONS.md` preserves architectural rationale and superseded approaches.
- `CHANGELOG.md` records user-visible history.
- `docs/beta5-validation-2026-09-21.md` records the immutable beta.5 and
  completed managed validation evidence.
- `RELEASE.md` defines version, tag, registry, packaging, and release procedures.
- `VERSION` is the canonical plugin version and must match both plugin declarations.

The source repository uses `main` for production-ready stable code and `dev` for next-version integration. Immutable beta and completed stable tags feed the `dispatcharr-plugins:dev` registry. Stable-registry publication normally requires an explicitly approved GitHub Release; `v0.2.0` has a narrow operator-approved exception so the fully validated tag can be installed from the stable channel while Release packaging remains blocked.

Historical tags through `v0.2.1-beta.1` retain their recorded `ffmpeg-asr` provenance and must not be repackaged under a new license. Starting with `v0.2.1-beta.2`, the bundled runtime is the independently published MIT-licensed `ffmpeg-adaptive` project, so new plugin versions may use the normal Release and stable-publication gates in `RELEASE.md`.

## License

The plugin is MIT licensed. Its bundled `ffmpeg-adaptive` dependency is also MIT licensed; the dependency notice is preserved as `ffmpeg-smart-profiles/FFMPEG_ADAPTIVE_LICENSE`. Historical tags retain their original provenance.
