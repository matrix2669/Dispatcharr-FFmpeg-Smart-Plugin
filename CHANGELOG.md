# Changelog

All notable user-visible changes to FFmpeg Smart Profiles are documented here.

## [Unreleased]

## [0.2.1-beta.3] - 2026-08-30

### Changed

- Pin the complete canonical runtime to `matrix2669/ffmpeg-adaptive
  v0.1.0-beta.2` at exact commit
  `4df6c12e395187fc0080f858685a3c6ebd7a8c42`.
- Make runtime and benchmark hardware-decode paths identical, retain each
  device's measured low-power and 10-bit encode policy at stream time, and
  schedule capacity only on devices measured for the selected
  accelerator/codec pair.
- Advance the capacity-policy fingerprint so beta.2 installations require a
  fresh hardware rebuild instead of reusing measurements made with the
  superseded benchmark policy.
- Bound each capacity probe by a wall-clock deadline and grow upper-bound
  searches by 50 percent, preventing a failed high-concurrency probe from
  indefinitely overcommitting the host.

### Validation

- Require all plugin tests, Python/JSON/shell checks, exact local and remote
  seven-file source verification, repeat-sync idempotence, and clean tag-archive
  layout and mode checks before development-registry publication.
- The canonical wrapper's isolated pre-tag test selected one common
  VAAPI/HEVC policy across both GPUs, measured Arc A310 capacity 18 and UHD 770
  capacity 14, and rejected the next levels 19 and 15. The historical
  like-for-like result was 18/15; the earlier beta.2 plugin result of 15/11 is
  superseded because its benchmark path did not match runtime hardware decode.
- The canonical wrapper also passed current Dispatcharr 1080p59.94,
  1080i29.97, and 720p59.94 inputs through direct and finite `pipe:0` paths,
  produced progressive output for the interlaced source, decoded without
  errors, preserved monotonic nonnegative DTS, and scheduled overlapping work
  across both GPUs.

## [0.2.1-beta.2] - 2026-08-30

### Added

- Bundle the complete seven-file `ffmpeg-adaptive` runtime with one immutable commit, per-file SHA-256 and mode pins, remote byte verification, and the dependency's MIT notice.

### Changed

- Move the canonical runtime to `matrix2669/ffmpeg-adaptive v0.1.0-beta.1` at exact commit `80d648bbb0f93c45d5a7198bd7bf9260e9febd32` while preserving the accepted adaptive probing behavior.
- Remove redundant per-profile Allow 10-bit and Allow HDR controls because both behaviors are automatic; retain Force SDR and Force deinterlace.
- During Install / Update, remove retired saved 10-bit/HDR fields and `-10bit`/`-hdr` options, migrate `-sdr`/`-deint`/`-deinterlace` into the remaining controls, and preserve unrelated options.
- Allow new plugin versions containing the independently published MIT runtime to use the normal Release gate while retaining the original provenance of historical inherited-wrapper tags.

### Validation

- Require complete source checksum/mode verification, source-sync idempotence, 42 plugin tests, Python/JSON/shell checks, exact archive layout, managed settings migration, cache rebuild, `pipe:0`, and representative actual 1080p, 1080i, and 720p stream checks before stable promotion.
- Passed all 42 source tests and clean-tag archive checks, installed the exact
  seven-file runtime and MIT dependency notice through the development registry,
  removed all retired HDR/10-bit fields and values, and confirmed a second
  managed-profile reconciliation makes no changes.
- Rebuilt a valid schema-2 cache selecting VAAPI/H.264 with low-power disabled;
  the live host measured capacity 15 on `/dev/dri/renderD129` and 11 on
  `/dev/dri/renderD128`. These values are environment measurements, not plugin
  defaults or a strict comparison with historical HEVC fixtures.
- Passed managed Stream and finite `pipe:0` Output Profile checks against current
  priority-zero 1080p59.94 H.264, 1080i29.97 MPEG-2, and 720p59.94 H.264
  Dispatcharr sources. The interlaced input automatically became progressive
  H.264, all Output Profile results were progressive 720p H.264, all FFmpeg
  decode commands exited successfully, and every result had monotonic,
  nonnegative DTS. The direct 1080p stream-copy sample retained 260 transient
  decoder diagnostics from joining the live H.264 source mid-GOP; its decode
  completed successfully and the downstream transcoded Output Profile decoded
  without diagnostics.
- Confirmed zero live, VOD, and catch-up viewers before and after testing and no
  remaining FFmpeg process after the harness completed.

## [0.2.1-beta.1] - 2026-08-27

### Added

- Bundle canonical adaptive input probing with metadata validation and 1-second/1-MB, 2-second/2-MB, then native-default tiers.

### Changed

- Synchronize the bundled wrapper to canonical `ffmpeg-asr v1.1.1-beta.1` at exact commit `ecc64244dae2c0e80761da6f16be92d95b91d29a` and SHA-256 `785a2ffe283452006ffa50d36e12fd2a013f54e0bd233f6d3c8d87f8a46f0f71`.
- Remove and persistently normalize saved manual `-analyzeduration` and `-probesize` input settings when profiles are installed or updated because the canonical wrapper now owns both values.
- Clarify in the Install / Update confirmation that updates do not require a restart, but a browser refresh may be needed to display settings changes.

### Validation

- Require canonical source/checksum, plugin schema, profile generation, saved-setting migration, packaging, and live HDHomeRun plus CSPAN3 HE-AACv2 checks before development-channel publication.

## [0.2.0] - 2026-08-26

### Added

- Add fixed, configurable managed Stream and Output Profile slots with policy checkboxes, safe reconciliation, and update-without-restart behavior for existing profiles.
- Add safely quoted phase-scoped advanced FFmpeg Smart controls, inherited-default guidance, all-stream and typed custom mapping, and persistent runtime state outside replaceable plugin files.
- Add authoritative hardware-cache status, persistent Dispatcharr scan notifications, direct executable-mode repair, and basic stream-copy fallback while a required scan is pending or active.

### Fixed

- Restore dismissed persistent fallback notifications immediately through Dispatcharr's authoritative notification refresh.
- Preserve compatible mapped subtitle, data, and attachment streams and keep benchmark fallback authoritative until the top-level recache completes.

### Changed

- Synchronize the bundled wrapper to canonical stable `ffmpeg-asr v1.1.0` at exact commit `448837f4f6267de1c6705cb670bcdb0c6991614f` and SHA-256 `56cb036d803237b32d17fa0bf33bf200b3a07a43a0ca5309a4849eb561801627`.

### Validation

- Promote the fully validated beta.11 tree without plugin behavior changes. All 39 tests, live two-GPU recheck and fallback, persistent notification lifecycle, scoped custom strings, `pipe:0`, and four-stream Map All with copied DVB subtitle pass.
- Publish only the immutable stable tag and the explicitly approved stable-registry metadata. No GitHub Release or distributable ZIP is created while inherited-wrapper licensing remains unresolved.

## [0.2.0-beta.11] - 2026-08-26

### Fixed

- Preserve MPEG-TS-compatible subtitle, data, and attachment streams selected by Map All or typed mappings by explicitly stream-copying those auxiliary stream types on normal Smart video-copy and video-transcode paths.
- Keep the hardware benchmark lock present until the top-level recache process exits so new managed starts reliably use degraded stream copy for the complete recheck instead of returning to normal Smart policy after a benchmark subshell exits.

### Changed

- Synchronize the bundled wrapper to canonical `ffmpeg-asr v1.1.0-beta.7` at exact commit `6a735d61113646153aef5bf1a1c0a5667b1331e9` and SHA-256 `51e981c57b6cc7757d5f2a4cb7322ea913238f15119ab50fbf61eb2ae89d3d5d`.
- Clarify Map All's auxiliary-stream copy and MPEG-TS compatibility boundary in every mapping field.

## [0.2.0-beta.10] - 2026-08-26

### Fixed

- Make notification reactivation immediately visible without a browser refresh by clearing stored dismissals and broadcasting Dispatcharr's built-in authoritative notification-list refresh after plugin load, a manual status check, each new degraded fallback invocation, and notification removal.
- Clarify that the green edge on Dispatcharr v0.29.0's Benchmark Status popup means the read-only plugin action completed; the popup message remains authoritative for whether a hardware recheck is required.

## [0.2.0-beta.9] - 2026-08-26

### Fixed

- Attempt to restore a dismissed degraded-mode warning in Dispatcharr's notification center immediately after every new fallback invocation by sending `is_dismissed: false` in the websocket notification payload. Live validation found that the durable database state changed, but the browser still required a refresh; beta.10 replaces this merge-only approach.

## [0.2.0-beta.8] - 2026-08-26

### Fixed

- Repin the bundled wrapper to corrective canonical `ffmpeg-asr v1.1.0-beta.6`, whose Linux validation accounts for the degraded proxy command path and passes without moving the immutable beta.5 tag.

### Changed

- Synchronize the bundled wrapper to exact commit `aeff09204000f58aa6fdd3a14781935f77a0823a` at SHA-256 `03a5bdc63437fa907353356602d83defba2f46e833a1334b1980deec5103dfb1`; fallback runtime behavior is unchanged from plugin beta.7.

## [0.2.0-beta.7] - 2026-08-26

### Added

- Keep managed streams available through a basic FFmpeg `-c copy` proxy while the hardware cache is missing, invalid, stale, unavailable, or being rebuilt.
- Re-display the persistent degraded-mode notification after every new fallback invocation if an administrator dismissed it while the condition remained unresolved.

### Changed

- Synchronize the bundled wrapper to canonical `ffmpeg-asr@4fafc8b5af300d6e47413cfb9cf8409fef7c2201` (`v1.1.0-beta.5`) with opt-in degraded proxy and invocation-marker support.
- Explain that FFmpeg Smart policy and hardware acceleration are bypassed until a required capability scan succeeds.

### Safety

- Use stream copy only during degraded operation; do not silently substitute CPU transcoding or alter the GPU benchmark policy.

## [0.2.0-beta.6] - 2026-08-26

### Added

- Add persistent Dispatcharr notification-center warnings when the hardware cache needs a scan and while a rebuild is active; clear the warning automatically after successful validation.

### Fixed

- Restore bundled script execute permissions immediately when an enabled plugin is loaded after Dispatcharr's ZIP installer strips archive mode bits.
- Validate cache health through the canonical wrapper so a hardware-stale cache cannot be reported as healthy merely because its file exists.
- Report missing, invalid, stale, inconsistent, and unavailable caches as actionable Benchmark Status errors while labeling any parsed stale capabilities as previous and unusable.

### Changed

- Synchronize the bundled wrapper to `ffmpeg-asr@fb990e9879eddf879fa6a57eaf76f0bc6040de50` (`v1.1.0-beta.4`) with the authoritative read-only cache-status contract.

### Known limitations

- Dispatcharr v0.29.0 treats benchmark-lock exit status 75 as a normal stream failure and can retry alternate streams; the persistent in-progress notification clarifies maintenance, but clean non-retryable handling requires Dispatcharr core support.

## [0.2.0-beta.5] - 2026-08-25

### Fixed

- Show the exact inherited input, mapping, and MPEG-TS defaults directly below every matching mode dropdown.
- Show the complete runtime-derived video and audio default formulas, including bitrate, GOP, accelerator-tuning, AAC, channel-layout, and profile-ceiling behavior.
- Keep editable option fields reserved for user-owned Add/Replace text because Dispatcharr cannot populate a sibling field when a dropdown changes.

### Validation

- Passed 26 plugin unit tests, settings-schema parity, Python/JSON/shell checks, immutable wrapper source verification, and whitespace validation.

## [0.2.0-beta.4] - 2026-08-25

### Added

- Add per-profile Smart controls for input defaults, stream mapping, transcode-video tuning, audio defaults, and MPEG-TS/output defaults.
- Add Inherit, Add, and Replace modes for each FFmpeg group plus a Map all input streams mode.

### Changed

- Synchronize the bundled wrapper to `ffmpeg-asr@4addad2a156846c7db53db10c426784acc2ba55b` (`v1.1.0-beta.3`) with scoped copy/transcode argument placement and structural ownership checks.
- Retain existing beta.3 Additional FFmpeg option values as additive MPEG-TS/output settings so saved development profiles carry forward without manual migration.

### Safety

- Keep URL, dynamic user-agent, hardware/device setup, video encoder, hardware filters, final MPEG-TS format, and `pipe:1` destination under FFmpeg Smart ownership.
- Require exactly one mapped video stream per Smart job and keep explicit `-maxbr` and `-maxchan` limits as hard ceilings after expert overrides.

### Validation

- Passed 25 plugin unit tests, canonical wrapper validation, Python/JSON/shell checks, settings-schema parity, immutable-source checksum verification, and whitespace validation.

## [0.2.0-beta.3] - 2026-08-25

### Added

- Add a separate Additional FFmpeg options field to every managed profile and preserve each parsed argument through the canonical wrapper without shell evaluation.

### Changed

- Synchronize the bundled wrapper to `ffmpeg-asr@6659e1bd3d747fa81d2a79b4ed64ea75e58698ff` (`v1.1.0-beta.2`) with repeatable, output-scoped `-ffmpeg-option` support.

### Fixed

- Report a required Dispatcharr restart when profile application creates a profile, while allowing ordinary updates to apply without a restart; removal restart behavior is unchanged.

### Validation

- Passed 20 plugin unit tests, Python/JSON/shell checks, offline and remote immutable-source verification, exact local canonical-source comparison, repeat synchronization, and whitespace validation.

## [0.2.0-beta.2] - 2026-08-22

### Changed

- Republish the persistent-state candidate with corrected canonical-wrapper source documentation and complete registry-update, recache, restart, and `pipe:0` validation evidence.

### Validation

- Updated the installed test plugin through Dispatcharr's managed dev-registry path from recorded version `0.1.0`; capability-cache and probe-sample checksums remained identical across directory replacement.
- Rebuilt the two-GPU cache through the plugin action at the 1.2x stability floor: Arc A310 capacity 18 and UHD 770 capacity 15.
- Restarted Dispatcharr and verified beta.2 discovery, persisted settings/management metadata, and a complete 10-second 4K30 MPEG-TS `pipe:0` input producing 10 seconds of 1280×720 HEVC output at approximately 1.83 Mbps through the A310.

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

[Unreleased]: https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/compare/v0.2.1-beta.3...HEAD
[0.2.1-beta.3]: https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/compare/v0.2.1-beta.2...v0.2.1-beta.3
[0.2.1-beta.2]: https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/compare/v0.2.1-beta.1...v0.2.1-beta.2
[0.2.1-beta.1]: https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/compare/v0.2.0...v0.2.1-beta.1
[0.2.0]: https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/compare/v0.2.0-beta.11...v0.2.0
[0.2.0-beta.6]: https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/compare/v0.2.0-beta.5...v0.2.0-beta.6
[0.2.0-beta.5]: https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/compare/v0.2.0-beta.4...v0.2.0-beta.5
[0.2.0-beta.4]: https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/compare/v0.2.0-beta.3...v0.2.0-beta.4
[0.2.0-beta.3]: https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/compare/v0.2.0-beta.2...v0.2.0-beta.3
[0.2.0-beta.2]: https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/compare/v0.2.0-beta.1...v0.2.0-beta.2
[0.2.0-beta.1]: https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/compare/v0.1.0...v0.2.0-beta.1
[0.1.0]: https://github.com/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/releases/tag/v0.1.0
