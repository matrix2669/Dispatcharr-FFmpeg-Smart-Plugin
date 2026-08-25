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
- Last verified state: approved administrative baseline through `f3e15b6` plus the branch-ledger promotion update.
- Last verified at: `2026-08-22`.

### `dev`

- Purpose: integrate and validate the next plugin version before stable promotion to `main`.
- Base: synchronized with `main` after the approved administrative promotion.
- Intended target: `main` after future version work is reviewed and approved.
- Current state: integrates persistent external state and required-cache errors for corrected candidate `v0.2.0-beta.2`, plus mandatory workspace standards reconciliation guidance.
- Validation: 17 unit tests, Python/JSON/shell checks, immutable wrapper pin verification, repeat synchronization, and stable runtime layout pass. Dispatcharr's managed dev-registry update from recorded `0.1.0` to `0.2.0-beta.2` preserved external cache/sample checksums across plugin-directory replacement. Missing/stale caches return identified exit-78 errors. A confirmed plugin recache measured A310 capacity 18 and UHD 770 capacity 15; a full restart rediscovered beta.2; and a 10-second 4K30 MPEG-TS `pipe:0` test produced complete 1280×720 HEVC output at approximately 1.83 Mbps.
- Publication state: immutable corrected beta tag and `dispatcharr-plugins:dev` advertisement only; no GitHub Release or distributable ZIP is authorized.
- Last verified at: `2026-08-25`.
