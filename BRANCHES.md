# Branches

This ledger records why every current long-lived or work branch exists and preserves the context needed for review. GitHub remains authoritative for live refs, commits, pull requests, and checks.

## Maintenance rules

- Add or update a record before substantive work begins on a branch.
- Refresh observed heads and validation before using a record for review or promotion.
- Before deleting a branch, transfer user-visible results to `CHANGELOG.md` and durable rationale to `DECISIONS.md`, then remove its record.
- Treat `main` as production-ready and `dev` as next-version integration after the workflow migration is approved.

## Branch index

| Branch | Type | Status | Base | Target | Purpose |
|---|---|---|---|---|---|
| `main` | long-lived | active | initial project history | stable releases | Production-ready plugin source and GitHub Releases. |
| `dev-test` | long-lived | active | `main` | superseded by `dev` | Historical development branch pending migration to the standalone `dev` convention. |
| `feature/complete-project-documentation` | feature | active | `dev-test` | `dev` | Reconstruct complete project guidance, decisions, release history, and standalone workflow from all available evidence. |

## Branch records

### `main`

- Purpose: production-ready plugin source, stable tags, and explicitly approved GitHub Releases.
- Current release: `v0.1.0`.
- Distribution: eligible for `dispatcharr-plugins:main` only when the corresponding GitHub Release is explicitly approved.
- Last verified head: `e823c477778faed06e226035ab9dcf922a867841`.
- Last verified at: `2026-08-22`.

### `dev-test`

- Purpose: historical development and testing branch created before the standalone workflow was standardized.
- Planned disposition: replace with `dev` after this documentation and workflow migration is approved; do not preserve both names.
- Last verified head: `e823c477778faed06e226035ab9dcf922a867841`.
- Last verified at: `2026-08-22`.

### `feature/complete-project-documentation`

- Purpose: reconstruct the plugin's complete operating guidance, architectural decisions, branch lifecycle, release process, and history from all available ChatGPT, Codex, Git, implementation, validation, release, registry, and related-project evidence.
- Base: `dev-test` at `e823c477778faed06e226035ab9dcf922a867841`.
- Intended target: the replacement `dev` branch, followed by review and promotion to `main` only with approval.
- In scope: `AGENT.md`, `BRANCHES.md`, `CHANGELOG.md`, `DECISIONS.md`, `RELEASE.md`, `VERSION`, focused README/workflow corrections, validation coverage, and the reviewable canonical wrapper synchronization discovered by source-pin validation.
- Out of scope: runtime policy changes, plugin version publication, new tags or Releases, registry publication, and silent wrapper synchronization.
- History under review: all available related ChatGPT and Codex tasks; complete repository history; the canonical `ffmpeg-asr` decisions and implementation; `dispatcharr-plugins` distribution policy; current source pin, tests, workflows, and v0.1.0 archive history.
- Key changes: reconstructed 14 ADRs and the complete project documentation set; prepared `dev-test` to `dev` workflow migration; retargeted wrapper-update PRs to `dev`; added version/layout validation; prevented byte-identical sync noise; synchronized the vendored wrapper to canonical `ffmpeg-asr@d521be2` after validation found its internal semantic-version update.
- Validation: 14 unit tests pass; Python compilation, plugin/source JSON, both GitHub workflow files, wrapper/synchronization shell syntax, offline and remote source-pin checks, version agreement, 14-ADR structure, referenced commits, `v0.1.0` stable-directory layout, and Git whitespace all pass. Repeating synchronization against `ffmpeg-asr/main` reports the wrapper already current and makes no additional changes.
- Last verified head: `e823c477778faed06e226035ab9dcf922a867841`.
- Last verified at: `2026-08-22`.
