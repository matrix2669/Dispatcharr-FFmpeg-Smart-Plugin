# Changelog

All notable user-visible changes to FFmpeg Smart Profiles are documented here.

## [Unreleased]

## [0.2.0-beta.2] - 2026-08-22

### Changed

- Republish the persistent-state candidate with corrected canonical-wrapper source documentation and complete registry-update, recache, restart, and `pipe:0` validation evidence.

## [0.2.0-beta.1] - 2026-08-22

### Added

- Add a plugin launcher that identifies missing, invalid, and hardware-stale capability caches as `ffmpeg-smart` errors with recovery guidance.
- Add exact `ffmpeg-asr` source metadata with a full commit and SHA-256 checksum.
- Add offline/remote source verification, idempotent synchronization tooling, daily/manual update checks, and reviewable synchronization pull requests.
- Add complete project guidance, branch tracking, architecture decisions, release rules, and a canonical `VERSION` file.

### Changed

- Store the capability cache, probe sample, benchmark lock, PID, and log under persistent `/data/ffmpeg_smart_profiles` state instead of the replaceable plugin install directory.
- Point new and existing managed profiles at the launcher while continuing to recognize legacy direct `ffmpeg-smart.sh` profiles for migration and removal.
- Adopt the standalone `main`/`dev` source workflow and retire the historical `dev-test` branch after migration verification.
- Target automated canonical-wrapper update pull requests at `dev` for normal integration and review.
- Avoid source-pin-only pull requests when `ffmpeg-asr` advances without changing the wrapper bytes.
- Synchronize the bundled wrapper to `ffmpeg-asr@d0793ca2b121e82b50267ede5d810893bcca027f` (`v1.1.0-beta.1`) with persistent-state and required-cache support.
- Update GitHub workflows to the current official checkout action used by the repository.
- Require a fresh official Dispatcharr contract review whenever the supported, minimum, tested, or deployed Dispatcharr version changes.
- Record the inherited-wrapper licensing gate for future Releases and distributable ZIPs.

## [0.1.0] - 2026-08-19

### Added

- Native Dispatcharr plugin with Install or Update Profiles, Remove Managed Profiles, Rebuild Hardware Cache, and Benchmark Status actions.
- Two configurable Stream Profile slots and three configurable Output Profile slots with enable controls, editable names, and Additional options.
- Per-profile controls for 10-bit, HDR, forced SDR, and conditional deinterlacing.
- Default `FFmpeg Smart` Stream Profile with 10-bit and HDR allowed.
- Default `FFMpeg Smart - 720p Mobile` Output Profile with a 720p ceiling, 2 Mbps maximum video bitrate, stereo maximum, forced SDR, and deinterlacing.
- Background hardware capability and real-concurrency cache rebuilds with GPU-count-based runtime estimates.
- Benchmark status reporting for progress, recent logs, cached acceleration/codec, 10-bit support, devices, measured speeds, and capacities.

### Changed

- Route all managed Stream and Output Profiles through the bundled hardware-aware wrapper.
- Support Dispatcharr Output Profiles through the wrapper's non-seekable `pipe:0` capture-and-reinsert path.
- Replace fixed native-FFmpeg presets with configurable wrapper-backed profile slots.
- Normalize legacy policy flags from Additional options into persisted checkboxes; Force SDR overrides Allow HDR.
- Migrate known legacy native-FFmpeg Output Profiles when names and command ownership match.
- Package runtime files beneath the stable `ffmpeg-smart-profiles/` install directory.

### Safety

- Keep profile installation and removal transactional, idempotent, lock-aware, and ownership-aware.
- Require a full Dispatcharr restart after profile changes and a browser refresh after settings normalization.
- Stop active input/output transcodes before benchmarking while leaving proxy-only streams running.
- Block new FFmpeg Smart transcodes during benchmarking with a shared lock and recover stale locks automatically.
- Validate benchmark PIDs against process state and the exact recache command before reporting them as active.

### Validation

- Passed plugin unit tests and installed native-plugin discovery/profile checks on Dispatcharr `v0.29.0`.
- Verified repeat profile installation without duplicates.
- Verified a 10-second 4K MPEG-TS Output Profile input through `pipe:0` produced the complete 10-second constrained output without losing the opening sample.
- Verified plugin-triggered cache rebuilds, transcode interruption, new-transcode blocking, proxy continuity, and status readback.
- Recorded final live capacity evidence at the canonical wrapper's 1.2x threshold: Arc A310 18 and UHD 770 15. These values are environment-specific and are not plugin defaults.
- Verified the `v0.1.0` tagged tree installs from the stable plugin directory.

[Unreleased]: https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/compare/v0.2.0-beta.2...HEAD
[0.2.0-beta.2]: https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/compare/v0.2.0-beta.1...v0.2.0-beta.2
[0.2.0-beta.1]: https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/compare/v0.1.0...v0.2.0-beta.1
[0.1.0]: https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/releases/tag/v0.1.0
