# Branches

This ledger records why every current long-lived or work branch exists and preserves the context needed for review. GitHub remains authoritative for live refs, commits, pull requests, and checks.

## Maintenance rules

- Add or update a record before substantive work begins on a branch.
- Refresh observed heads and validation before using a record for review or promotion.
- Before deleting a branch, transfer user-visible results to `CHANGELOG.md` and durable rationale to `DECISIONS.md`, then remove its record.
- Treat `main` as production-ready and `dev` as next-version integration.

## Branch index

| Branch | Type | Status | Base | Target | Purpose |
|---|---|---|---|---|---|
| `main` | long-lived | active | initial project history | stable releases | Production-ready plugin source and GitHub Releases. |
| `dev` | long-lived | active | `main` | `main` | Integrate and validate the next plugin version and canonical wrapper updates. |
| `fix/persistent-state-errors` | work | active | `dev` | `dev` | Persist runtime state across plugin replacement and surface missing-cache failures clearly. |

## Branch records

### `main`

- Purpose: production-ready plugin source, stable tags, and explicitly approved GitHub Releases.
- Current release: `v0.1.0`.
- Distribution: eligible for `dispatcharr-plugins:main` only when the corresponding GitHub Release is explicitly approved.
- Last verified state: approved administrative baseline through `f3e15b6` plus the branch-ledger promotion update.
- Last verified at: `2026-08-22`.

### `dev`

- Purpose: integrate and validate the next plugin version before stable promotion to `main`.
- Base: synchronized with `main` after the approved administrative promotion.
- Intended target: `main` after future version work is reviewed and approved.
- Current state: synchronized with the approved `main` baseline; ready to integrate the next plugin version.
- Validation: 14 unit tests pass; Python compilation, plugin/source JSON, both GitHub workflow files, wrapper/synchronization shell syntax, offline and remote source-pin checks, version agreement, 14-ADR structure, referenced commits, `v0.1.0` stable-directory layout, and Git whitespace all pass. Repeating synchronization against `ffmpeg-asr/main` reports the wrapper already current and makes no additional changes.
- Publication state: the administrative baseline is promoted without creating a new plugin tag, GitHub Release, ZIP, or registry update.
- Last verified at: `2026-08-22`.

### `fix/persistent-state-errors`

- Purpose: move mutable cache/benchmark state to `/data/ffmpeg_smart_profiles`, introduce a stable plugin launcher, and make normal streams fail with an identified recovery message when the required capability cache is unavailable.
- Base: `dev` at `3993a44`.
- Intended target: `dev`.
- Canonical dependency: `ffmpeg-asr@37bd0a9b16748a28f2144981fe1f315c1f01aa8f`.
- Validation: 17 plugin unit tests and all static checks pass; the immutable source pin and repeat synchronization pass; installed-container checks preserve the existing cache/sample checksums, read status as the Dispatcharr user, migrate both managed profiles idempotently, and return exit 78 with an identified missing-cache error. The preserved legacy cache is correctly identified as stale because its fingerprint predates wrapper 1.0.0; a confirmed recache and Dispatcharr restart remain before normal live-stream validation.
- Started: `2026-08-22`.
