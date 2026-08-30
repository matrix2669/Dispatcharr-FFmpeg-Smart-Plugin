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
| `feature/ffmpeg-adaptive-migration` | feature | active | `dev` after adaptive-probing integration | `dev` | Vendor the modular MIT wrapper, remove redundant HDR/10-bit controls, and prepare `v0.2.1-beta.2`. |

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
- Current state: synchronized with `main` at stable `v0.2.0` commit `6eb5c8c8f437dcca6802967ceb193e37f984a7c1` after the completed beta.1 through beta.11 cycle.
- Publication state: `origin/dev` and `origin/main` contain the identical stable source; beta and stable tags remain immutable.
- Last verified at: `2026-08-26`.

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
- State: active; not integrated, tagged, published, or deployed.
- Last reviewed: `2026-08-30`.

## Completed branch cleanup

On `2026-08-26`, all local and `origin` feature, fix, integration, safety, and release branches were deleted after their results were preserved in `CHANGELOG.md` and `DECISIONS.md` and their tips were verified as merged or tree-equivalent. Only `main` and `dev` remain; tags were retained.
