# Branches

This ledger records why every current branch exists and preserves the context needed for review. GitHub remains authoritative for live refs, commits, pull requests, and checks.

## Maintenance rules

- Add or update a record before substantive work begins on a branch.
- Refresh observed heads and validation before using a record for review or promotion.
- Before deleting a branch, transfer user-visible results to `CHANGELOG.md` and durable rationale to `DECISIONS.md`, then remove its record.
- Treat `main` as production-ready and `dev` as next-version integration.

## Branch index

| Branch | Type | Status | Base | Target | Purpose |
|---|---|---|---|---|---|
| `main` | long-lived | active | initial project history | stable tags | Production-ready plugin source and stable tags. |
| `dev` | long-lived | active | `main` | `main` | Integrate and validate the next plugin version and canonical wrapper updates. |
| `feature/adaptive-input-probing` | feature | integrated | `dev` | `dev` | Pin canonical adaptive probing, migrate manual probe settings, and prepare `v0.2.1-beta.1`. |
| `feature/ffmpeg-adaptive-migration` | feature | published | `dev` after adaptive-probing integration | `dev` | Vendor the modular MIT wrapper, remove redundant HDR/10-bit controls, and prepare `v0.2.1-beta.2`. |
| `docs/ffmpeg-smart-beta2-live-validation` | documentation | integrated | `dev` at `3c7b07c` | `dev` | Record development publication and managed live-validation evidence. |
| `fix/ffmpeg-adaptive-beta2-fidelity` | fix | published | `dev` at `bcf767c` | `dev` | Pin the corrected wrapper beta, invalidate the superseded capacity policy, and prepare `v0.2.1-beta.3`. |
| `docs/ffmpeg-smart-beta3-live-validation` | documentation | integrated | `dev` at `dd54d4c` | `dev` | Record beta.3 publication and managed installed validation without moving its tag. |
| `fix/benchmark-outcome-beta5` | fix | active | `dev` at `38f7d17` | `dev` | Reviewed beta.5 plugin, wrapper, development-registry, zero-viewer managed update, and completed bounded hardware validation. Stable/main promotion, GitHub Release, unrelated work, and branch deletion remain excluded. |
| `feature/stable-v0.2.1-2026-10-20` | feature | stable release preparation | `dev@35ecaefd` | `dev`, then `main` | Release 0.2.1 while retaining the tested immutable runtime. |
| `feature/shared-input-reservoir` | feature | review accepted; beta publication approved | `9ffe9d4` | `dev` | Package the canonical shared-input reader and persisted per-Stream Profile controls for local 0.2.2-beta.2 testing. |

| `feature/simplify-profile-controls` | feature | implementation | `origin/dev@3b7f554` | `dev` | Simplify beta.3 codec selection and automatic shared input with fixed bounds; no publication. |

## Branch records

### `main`

- Purpose: production-ready plugin source and approved stable releases.
- Pre-promotion head: `6654a202e286f4c8b80d7845040880f76862d1f2`;
  historical stable v0.2.0 remains immutable.
- Approved stable target: v0.2.1 from the reviewed beta.5 behavior, with
  version-only metadata changes and immutable ffmpeg-adaptive pin
  `913a958fd5f9edc231c49a70539a09f611fdcc5a`.
- Normal Release-backed publication replaces the historical v0.2.0 registry
  exception. Historical artifacts are not repackaged or relicensed.
- Validation and publication: see the stable release record and CI/release
  metadata; no live installation or deployment is part of this release.

### `dev`

- Purpose: integrate plugin and canonical-wrapper changes before stable promotion.
- Base and target: `main`.
- Current immutable runtime/release source is reviewed beta.5 commit
  `a5c0777875056591e4e02c989993f43b3f43aa72`; plugin tag
  `v0.2.1-beta.5`, wrapper beta.4, and development-registry publication are
  immutable and their CI gates passed. Documentation-only follow-ups may
  advance remote `dev` without changing that source. The earlier beta.4
  preparation commit `38f7d17...` and its defects remain historical
  negative-control evidence.
- Publication state: beta.5 dev publication, approved zero-viewer managed
  update, and bounded hardware validation are complete. The benchmark returned
  zero with complete outcome, valid cache, no PID/lock, and the fixture/pipe
  proof passed; no provider channel was fetched and no Dispatcharr profile was
  created. `main` remains stable-only.
- Last verified at: `2026-09-21`.

### `feature/adaptive-input-probing`

- Purpose: package canonical metadata-validated adaptive probing without duplicating wrapper behavior in the plugin.
- Base and target: `dev` at `6654a202e286f4c8b80d7845040880f76862d1f2`; target `dev` after live beta validation.
- Canonical source: `ffmpeg-asr v1.1.1-beta.1` commit `ecc64244dae2c0e80761da6f16be92d95b91d29a`, SHA-256 `785a2ffe283452006ffa50d36e12fd2a013f54e0bd233f6d3c8d87f8a46f0f71`.
- Scope: immutable wrapper pin, profile-setting migration, documentation, decision record, tests, beta tag, development registry, and live test deployment.
- State: integrated into local `dev` as the base for the standalone-wrapper
  migration; its tag and development deployment remain immutable historical
  evidence.
- Last reviewed: `2026-08-27`.

### `feature/ffmpeg-adaptive-migration`

- Purpose: move the plugin's pinned canonical runtime from the prior
  `ffmpeg-asr` beta to the modular MIT-licensed `ffmpeg-adaptive` beta without
  changing accepted stream behavior.
- Base and target: `dev` after merging `feature/adaptive-input-probing`; target
  `dev` after automated, archive, and managed Dispatcharr validation.
- Canonical source: `ffmpeg-adaptive v0.1.0-beta.1` commit
  `80d648bbb0f93c45d5a7198bd7bf9260e9febd32`.
- Scope: multi-file source pin/check/sync, bundled `lib/` runtime, removal and
  migration of retired HDR/10-bit settings and flags, version `0.2.1-beta.2`,
  tests, documentation, beta tag, development registry, and live test
  deployment.
- Out of scope: wrapper behavior changes, Stream Sort, stable promotion, and
  stable-registry publication.
- State: published as immutable `v0.2.1-beta.2` at
  `3c7b07cfe2d56540cd319179ef7c0d02318d2d38`. Source workflow `33320334916`,
  extracted-archive validation, development-registry workflow `33320510384`,
  and the managed Dispatcharr update pass.
- Managed validation: the installed seven-file runtime and MIT dependency notice
  match the tag; obsolete HDR/10-bit UI fields, saved keys, and options are
  absent; a second profile reconciliation is idempotent. The schema-2 cache
  selects VAAPI/H.264 with low-power disabled and measured capacities of 15 on
  `/dev/dri/renderD129` and 11 on `/dev/dri/renderD128`.
- Live validation: the priority-zero CBS 2 New York 1080p59.94 H.264 source,
  PIX11 New York 1080i29.97 MPEG-2 source, and FOX 5 New York 720p59.94 H.264
  source all pass the managed Stream Profile and finite `pipe:0` Output Profile.
  The interlaced source becomes progressive H.264 automatically; every Output
  Profile result is progressive 720p H.264 with monotonic, nonnegative DTS and a
  successful full-video decode. Final viewer counts and FFmpeg process audit are
  both zero.
- Last reviewed: `2026-08-30`.

### `docs/ffmpeg-smart-beta2-live-validation`

- Purpose: preserve exact source, registry, installed-runtime, migration, cache,
  actual-stream, and final process/viewer evidence for `v0.2.1-beta.2`.
- Base and target: `dev` at
  `3c7b07cfe2d56540cd319179ef7c0d02318d2d38`; target `dev`.
- Scope: `BRANCHES.md` and `CHANGELOG.md` only.
- Out of scope: runtime or manifest changes, new versions or tags, stable
  promotion, GitHub Release, stable registry, Stream Sort, and branch deletion.
- State: integrated into `dev` at
  `6902670a597d4281516f222689f38ef16f3d5b87`; the remote documentation branch is
  retained and no branch deletion is authorized.
- Last reviewed: `2026-08-30`.

### `fix/ffmpeg-adaptive-beta2-fidelity`

- Purpose: package the corrected `ffmpeg-adaptive v0.1.0-beta.2` runtime after
  pre-tag testing found that beta.1's benchmark command could under-report
  usable hardware capabilities and its unbounded capacity search could
  overcommit the host.
- Base and target: `dev` at
  `bcf767c5e7560f587f32e9a6e3aa0dce8a5a20e0`; target `dev` after source,
  archive, registry, and managed Dispatcharr validation.
- Canonical source: `ffmpeg-adaptive v0.1.0-beta.2` commit
  `4df6c12e395187fc0080f858685a3c6ebd7a8c42`.
- Scope: synchronize the complete modular runtime, advance the plugin beta,
  record the corrected benchmark/capacity contract, publish only through the
  development registry, update the managed test installation, rebuild its
  stale cache, and repeat actual 1080p, 1080i, 720p, `pipe:0`, and multi-GPU
  scheduling validation.
- Out of scope: Stream Sort, stable promotion, GitHub Release or manual ZIP,
  stable-registry publication, and branch deletion.
- State: integrated into `dev` at
  `dd54d4cc82a454135c4eb3b75eeeb5eb48713fe6` and published as immutable
  `v0.2.1-beta.3`. Plugin workflow `33333007420`, development-registry
  workflow `33333093699`, managed repository 37 update, valid-cache rebuild,
  actual-stream matrix, and overlapping scheduler validation pass.
- Managed result: the installed seven-file bundle pins
  `ffmpeg-adaptive v0.1.0-beta.2`; profile reconciliation was idempotent with
  no retired HDR/10-bit fields or flags. The cache selected VAAPI/HEVC and
  measured `/dev/dri/renderD129` at 18/reject 19 and
  `/dev/dri/renderD128` at 14/reject 15, both with low-power enabled for this
  run and 10-bit decode/encode available.
- Live result: priority-zero 1080p59.94, MPEG-2 1080i29.97, and 720p59.94
  sources passed direct and finite `pipe:0` paths with expected HEVC
  resolutions, zero decode errors, zero interlaced decoded output frames, and
  monotonic nonnegative DTS. Three overlapping streams used both GPUs and
  decoded cleanly. Final cache remained valid and no media process remained.
- Evidence: `docs/beta3-managed-validation-2026-08-30.md`.
- Last reviewed: `2026-08-30`.

### `docs/ffmpeg-smart-beta3-live-validation`

- Purpose: preserve exact source, registry, installed-runtime, cache-boundary,
  actual-stream, decoded-frame, scheduler, cleanup, and final-process evidence
  for `v0.2.1-beta.3` without changing the tagged runtime.
- Base and target: `dev` at
  `dd54d4cc82a454135c4eb3b75eeeb5eb48713fe6`; target `dev`.
- Scope: `BRANCHES.md`, `CHANGELOG.md`, `DECISIONS.md`, and
  `docs/beta3-managed-validation-2026-08-30.md` only.
- Out of scope: runtime or manifest changes, a new version or tag, stable
  promotion, GitHub Release or manual ZIP, stable registry, Stream Sort, and
  branch deletion.
- State: integrated into `dev` at
  `659098e74aeaddb1bca57a776e55b8da8b0b58a5`; the remote documentation
  branch is retained and no branch deletion is authorized.
- Last reviewed: `2026-08-30`.

### `fix/benchmark-outcome-beta5`

- Purpose: correct the beta.4 benchmark lifecycle and release metadata before
  and document the reviewed beta.5 development release and live validation.
- Base and target: remote `dev` at
  `38f7d17ca1698343cd5ca4dc82e29edb237400d2`; target `dev` after parent
  review and wrapper synchronization.
- Scope: plugin benchmark outcome persistence and admission, status and
  notification semantics, version agreement, source-sync ref/commit contract,
  tests, CI shell gates, and owned records.
- Canonical source pin: the complete seven-file bundle is synchronized to
  published wrapper beta.4 commit
  `913a958fd5f9edc231c49a70539a09f611fdcc5a`. Plugin tag
  `v0.2.1-beta.5` is commit `a5c0777875056591e4e02c989993f43b3f43aa72`; the
  development registry publication, zero-viewer managed update, and bounded
  hardware validation passed their gates. The benchmark returned zero with a
  complete outcome, valid cache, no PID/lock, and the fixture/pipe proof
  passed; no provider channel or Dispatcharr profile was used.
- Excluded: stable/main promotion, GitHub Release or manual stable ZIP,
  unrelated project work, and branch deletion.
- Validation: 69 plugin unit tests, Python compilation, JSON checks, shell
  syntax, offline source verification, exact archive validation, managed update,
  completed benchmark, and bounded hardware fixture/pipe proof pass.
- Evidence: `docs/beta5-validation-2026-09-21.md`; the bounded proof is not a
  provider-channel or Dispatcharr-profile validation.
- Last reviewed: `2026-09-21`.

## Completed branch cleanup

On `2026-08-26`, all feature, fix, integration, safety, and release branches
that existed at that time were deleted after their results were preserved in
`CHANGELOG.md` and `DECISIONS.md` and their tips were verified as merged or
tree-equivalent. Tags were retained. The later branches listed above belong to
the `v0.2.1` beta cycle.

### `feature/stable-v0.2.1-2026-10-20`

- Base `dev@35ecaefd58bc640ce4d1c01bee5c1dfcbd8082b3`; target dev then main.
- Authority: operator approval on 2026-10-20 to finish promotion and release.
- Scope: 0.2.1 version sources, validator identity, current source-compatibility
  evidence, stable changelog and manual-install ZIP/checksum.
- Preserve the complete seven-file runtime, source manifest, dependency license
  and launcher bytes from beta.5. Do not run the force-pushing sync workflow.
- Required gates: all plugin tests, Python/JSON/shell/source checks, official
  0.32.0 isolated clean install and overwrite update, package extraction,
  independent review, dev/main/tag CI and downloaded-asset verification.
- Excluded: live updates, settings/profile actions, streams, restarts,
  deployments, force pushes and branch deletion.

## fix/conditional-video-transcode — 2026-10-29

- Base: dev@7f5b775; target: dev; isolated test delivery, no integration authorized.
- Scope: pin reviewed canonical passthrough-first video policy; package distinct
  0.2.2-beta.1 test build; preserve plugin settings/profile definitions.
- User authorized build/install and channel458 TiVo retest. No registry/tag/release.
- Validation: complete plugin gates, immutable source checks, independent review,
  native installation and constrained live458 test.

### `feature/shared-input-reservoir`

- Created: 2026-10-30; base `9ffe9d4`; target `dev` after separate acceptance.
- Scope: synchronize canonical `8156f96ce44c2ca0cb0360a8503f7862285b9f23`,
  package its Python helper, expose per-Stream Profile off/auto/strict controls
  and bounded settings, prepare local test candidate 0.2.2-beta.2 and private ZIP.
- Excluded: tags, registry, release, source promotion, remote push, installation,
  provider acquisition and global default-profile changes. Output pipe unchanged.
- Validation: 78 unit tests, Python compile, JSON, Bash syntax, ShellCheck
  0.11.0, offline and exact online eight-file source checks passed. Repeated
  explicit-SHA sync preserved all bytes and modes. A private ZIP is built from
  the committed tree and inspected for exact metadata, helper presence/mode and
  archive layout at handoff. No plugin CI, live/provider, installation or
  default-profile result is claimed; those remain parent-owned follow-up work.
- Decision closure and contradiction/chat-independence review completed against
  ADR-030. Per-stream controls and transport limits are explicit; no global or
  channel profile assignments change. Generic codec compatibility controls are recorded in ADR-031; no
  receiver-specific mode is introduced.

- Generic codec-policy follow-up (2026-10-30): synchronize canonical
  `0482acf6e695f95e5c1952777f2e044afd961f87`; expose per-Stream copy-codec
  allowlist and fallback selection. Universal defaults remain H.264/HEVC copy
  plus cached conversion preference. No receiver-specific product mode or
  Output default changes. All 82 unit tests, compile/JSON/Bash/ShellCheck and
  online/offline eight-file source checks passed. Repeated final-SHA sync
  preserved bytes and modes. ADR-031 closes defaults, precedence and persistence;
  contradiction/chat-independence review completed. Private package is rebuilt
  from the exact final committed tree and inspected at handoff. Canonical CI and
  plugin CI/review/live acceptance remain separately recorded parent-owned gates.

- Review repair round 1: change missing/new shared-input modes to Off while
  retaining explicit Auto/Strict settings and generic codec controls; synchronize
  the canonical broker proxy-isolation repair. Validate proxy-only legacy
  acquisition through a recording proxy without initial no_proxy. All 83 unit
  tests, compile/JSON/Bash/ShellCheck, offline/online eight-file checks and
  repeated exact-SHA sync passed. ADR-032 supersedes the earlier Auto default
  and records the scoped broker proxy isolation. Explicit Auto/Strict settings,
  generic codecs and Output defaults remain intact. Final private ZIP is built
  from the committed tree and inspected at handoff; reviewer verification and
  exact-SHA CI remain parent-coordinated acceptance gates.

### `feature/simplify-profile-controls`

- Created: 2026-10-30; exact base `3b7f554c0aac64391768e4920178cacd6a15da8c`.
- Scope: beta.3 candidate, cached/preferred copy semantics, remove conversion
  fallback/shared-input tuning UI, automatic conservative shared input, fixed
  64-MiB payload and 10-second startup guard, independent 30-second network guard.
- UI decision: the user selected a blank-default text field after confirming
  official Field.jsx lacks multiselect. No core change or checkbox substitute.
  Blank follows preferred cache; explicit lists normalize mpeg2 spelling.
- Canonical changes precede exact-source sync; no independent vendored edits.
- Excluded: live/provider access, installation, settings/profile operations,
  registry, tags/releases and dev/main promotion. Canonical exact source is
  `137103b0b5d2ed2f21976c65be2cd5bc816dbdb6`; full local runtime gates passed.
  All 80 plugin unit tests pass after official sync, including the proxy-only
  legacy fixture that intentionally failed against the prior source pin.
  Compile/JSON/Bash/ShellCheck and exact offline/online source gates passed.
  Exact canonical CI run `41090068901` passed for this source. Repeated sync and
  private-package inspection complete at handoff. No live/provider or database
  operation occurred. ADR-033 records resolved text-field UX, old-settings/CSV
  migration, fixed bounds and independent timing semantics; contradiction and
  chat-independence review completed. Plugin CI/review remain acceptance gates.

Beta.3 publication receipt (2026-10-30): feature implementation b3f1155 is now
integrated into dev and tagged v0.2.2-beta.3; development registry be7f633 points
to that exact immutable source. Publication-status documentation follows on the
owning branch; installed/live acceptance remains operator-owned.

### `fix/opaque-ts-auto`

- Created 2026-10-30 from `dev@f04fb72e83e55fe6d589f5c0509d658a27153016`; target dev.
- Scope: package canonical response-based Auto detection for opaque HTTP TS
  sources as candidate 0.2.2-beta.4, preserving generic policy and fixed bounds.
- Validate exact source pins, full plugin gates, independent review and isolated
  live startup captures; installation stays on the normal Dispatcharr updater.
- No tag, registry publication, direct installation, profile/default changes,
  source integration, stable release or branch removal in this checkpoint.
- Canonical pin `bb834684eb2c513e832c43ba6dbc773d5af10cbc` passed full
  local validation (20 shared-input tests) and independent canonical review.
  Plugin local validation passed all 80 unit tests, compile/JSON/syntax and
  offline/online pin checks; repeat sync made no changes. Exact CI and isolated
  live capture evidence remain parent-owned closeout gates.

- Publication approved by the owner on 2026-10-30. This supersedes the earlier
  no-tag/no-registry/no-integration restriction for beta.4 only. Advance dev to
  the exact validated publication commit and create immutable v0.2.2-beta.4.
  Direct installation, stable main/Release and branch removal remain excluded.
