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

## Branch records

### `main`

- Purpose: production-ready plugin source and stable tags.
- Current stable tag: `v0.2.0` at `6eb5c8c8f437dcca6802967ceb193e37f984a7c1`.
- Canonical source: bundled wrapper pins `ffmpeg-asr v1.1.0` commit `448837f4f6267de1c6705cb670bcdb0c6991614f` with SHA-256 `56cb036d803237b32d17fa0bf33bf200b3a07a43a0ca5309a4849eb561801627`.
- Distribution state: the stable tag is advertised through `dispatcharr-plugins:main` under the explicitly approved version-specific exception; no GitHub Release or distributable ZIP is authorized until inherited-wrapper licensing is resolved.
- Validation: 39 plugin tests, Python/JSON/shell checks, exact canonical-source verification, immutable archive layout and executable-mode checks, installed fallback/notification behavior, completed 18/15 hardware capacity scan, and four-stream Map All validation pass.
- Last verified at: `2026-08-26`.

### `dev`

- Purpose: integrate plugin and canonical-wrapper changes before stable promotion.
- Base and target: `main`.
- Current state: `v0.2.1-beta.3` is tagged at
  `dd54d4cc82a454135c4eb3b75eeeb5eb48713fe6`, published through `origin/dev`,
  advertised by the development registry, and validated in managed Dispatcharr.
- Publication state: corrective beta source, development-registry publication,
  installed update, cache rebuild, actual Stream/Output Profile checks, and
  overlapping multi-GPU scheduling pass; `origin/main` remains the immutable
  `v0.2.0` stable source.
- Last verified at: `2026-08-30`.

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

## Completed branch cleanup

On `2026-08-26`, all feature, fix, integration, safety, and release branches
that existed at that time were deleted after their results were preserved in
`CHANGELOG.md` and `DECISIONS.md` and their tips were verified as merged or
tree-equivalent. Tags were retained. The later branches listed above belong to
the `v0.2.1` beta cycle.
