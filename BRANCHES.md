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

## Branch records

### `main`

- Purpose: production-ready plugin source, stable tags, and explicitly approved GitHub Releases.
- Current release: `v0.1.0`.
- Distribution: eligible for `dispatcharr-plugins:main` only when the corresponding GitHub Release is explicitly approved.
- Last verified head: `e823c477778faed06e226035ab9dcf922a867841`.
- Last verified at: `2026-08-22`.

### `dev`

- Purpose: integrate and validate the next plugin version before stable promotion to `main`.
- Base: `main` at `e823c477778faed06e226035ab9dcf922a867841`.
- Intended target: `main` after explicit review and approval.
- Current state: contains the approved documentation reconstruction, standalone workflow migration, validation coverage, source-sync refinement, and canonical wrapper synchronization from commit `e7e34a8` plus branch-ledger cleanup.
- Validation: 14 unit tests pass; Python compilation, plugin/source JSON, both GitHub workflow files, wrapper/synchronization shell syntax, offline and remote source-pin checks, version agreement, 14-ADR structure, referenced commits, `v0.1.0` stable-directory layout, and Git whitespace all pass. Repeating synchronization against `ffmpeg-asr/main` reports the wrapper already current and makes no additional changes.
- Publication state: no new plugin tag, GitHub Release, ZIP, or registry update has been created.
- Last verified at: `2026-08-22`.
