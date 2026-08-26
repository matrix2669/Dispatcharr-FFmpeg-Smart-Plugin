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
| `feature/additional-ffmpeg-options` | feature | merged | `dev` | `dev` | Add per-profile raw FFmpeg arguments and correct apply-profile restart feedback. |
| `feature/scoped-ffmpeg-options` | feature | merged | `dev` | `dev` | Expose phase-scoped Smart FFmpeg defaults and expert overrides for every managed profile. |
| `feature/degraded-proxy-fallback` | feature | merged | `dev` | `dev` | Preserve basic stream-copy service and re-notify after every degraded invocation while Smart capabilities are unavailable. |
| `fix/show-advanced-defaults` | fix | merged | `dev` | `dev` | Show the exact static defaults and runtime-derived default formulas beside every advanced scope control. |
| `fix/launcher-permissions-cache-status` | fix | merged | `dev` | `dev` | Make registry installs launch reliably and report cache validity rather than file existence alone. |
| `fix/beta7-canonical-validation` | fix | merged | `dev` | `dev` | Repin beta.7 behavior to the corrective green canonical wrapper tag without moving published tags. |
| `fix/persistent-fallback-reactivation` | fix | merged | `dev` | `dev` | Restore dismissed degraded warnings in the notification center instead of showing only a toast. |
| `fix/authoritative-notification-refresh` | fix | merged | `dev` | `dev` | Refresh the browser from Dispatcharr's authoritative notification API after persistent-warning reactivation. |

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
- Current state: integrates the beta.10 authoritative persistent-notification refresh correction with degraded stream-copy fallback, launcher mode repair, authoritative cache health, scoped advanced options, and pinned canonical `ffmpeg-asr v1.1.0-beta.6`.
- Validation: 37 plugin unit tests, Python/JSON/shell checks, exact offline and remote wrapper verification, official Dispatcharr v0.29.0 notification-refresh and plugin-action UI contract review, workspace validation, feature workflow run `33018546999`, and `git diff --check` pass. Dev/tag workflows, immutable beta.10 archive inspection, development-registry validation/publication, and installed beta.10 validation remain pending.
- Publication state: corrective immutable `v0.2.0-beta.10` and `dispatcharr-plugins:dev` publication are pending; beta.9 remains immutable and advertised until replacement. No GitHub Release, stable-registry change, or distributable ZIP is authorized.
- Last verified at: `2026-08-26`.

### `feature/additional-ffmpeg-options`

- Purpose: add a separate Additional FFmpeg options field to every managed profile and make Install or Update report a restart only when it creates a profile.
- Base: current `dev` at `ef35687`.
- Intended target: `dev` after the canonical wrapper change is committed, synchronized, and validated.
- Result: plugin source commit `ca1e3b2` merged into `dev` at `1a9f201`; annotated tag `v0.2.0-beta.3` resolves to reviewed integration commit `59f1c20`.
- Scope: plugin settings/schema mirrors, profile parameter generation, conditional restart results, tests, user/developer documentation, decision history, and the immutable wrapper source pin.
- Exclusions: removal restart behavior, hardware-cache policy, registry publication, version/tag changes, and GitHub Release creation.
- Related work: canonical `ffmpeg-asr` branch `feature/additional-ffmpeg-options`.
- Validation: 20 plugin unit tests, generated-profile and settings-schema parity checks, Python/JSON/shell validation, exact comparison with canonical `ffmpeg-asr v1.1.0-beta.2`, offline and remote source-pin verification, repeat synchronization, tag-archive layout, and `git diff --check` pass for `v0.2.0-beta.3`; the published `dev` workflow completed successfully.
- Last verified at: `2026-08-25`.

### `feature/scoped-ffmpeg-options`

- Purpose: replace the single Additional FFmpeg options field with Smart-only input, mapping, video-tuning, audio, and MPEG-TS/mux controls that inherit, add to, or replace the applicable managed defaults.
- Base: `dev` at `3966268`.
- Intended target: `dev` after the canonical wrapper contract is implemented, committed, synchronized, and validated.
- Result: plugin source commit `10afa0d` merged into `dev` at `c16aca5`; annotated tag `v0.2.0-beta.4` resolves to reviewed integration commit `08ce3c5`.
- Scope: settings/schema mirrors, per-profile mode and option generation, legacy-field migration, structural-option validation, effective-command guidance, tests, user/developer documentation, decision history, and the immutable wrapper source pin.
- Exclusions: no native/custom FFmpeg profile mode, no bypass of hardware or encoder selection, no change to restart semantics, cache policy, Dispatcharr compatibility floor, stable registry, GitHub Releases, or distributable ZIPs.
- Related work: canonical `ffmpeg-asr` branch `feature/scoped-ffmpeg-options`.
- Validation: 25 plugin unit tests, generated-profile/settings-schema parity, scoped mode and mapping constraints, structural-option rejection, update-without-restart regression checks, canonical wrapper validation, Python/JSON/shell checks, exact offline and remote source-pin verification, repeat synchronization, tag-archive layout, and `git diff --check` pass for `v0.2.0-beta.4`; the published tag resolves correctly and the `dev` workflow completed successfully.
- Last verified at: `2026-08-25`.

### `fix/show-advanced-defaults`

- Purpose: make each Inherit choice understandable without requiring users to inspect the wrapper source or infer what Replace removes.
- Base: `dev` at `1de8e3c`.
- Intended target: `dev` as a new immutable beta after plugin-only UI/documentation validation.
- Result: plugin source commit `c1f2dbe` merged into `dev` at `42a0da0`; annotated tag `v0.2.0-beta.5` resolves to reviewed integration commit `6fb786d` and is advertised through `dispatcharr-plugins:dev`.
- Scope: advanced-field help text, managed-default reference documentation, schema parity tests, version/release metadata, and the durable UI decision.
- Exclusions: no dropdown-driven sibling-field mutation because Dispatcharr exposes no dependent-field hook; no wrapper behavior, saved-option migration, profile-generation, hardware policy, stable registry, GitHub Release, or Dispatcharr core change.
- Related work: canonical defaults remain owned by pinned `ffmpeg-asr v1.1.0-beta.3`.
- Validation: 26 plugin unit tests, exact default text for all five profile slots, generated settings-schema parity, Python/JSON/shell checks, offline and remote source-pin verification, existing profile-generation regressions, tag archive/runtime layout inspection, and `git diff --check` pass. The published tag dereferences to `6fb786d`, the exact GitHub archive reports beta.5, and the `dev` verification workflow completed successfully.
- Last verified at: `2026-08-25`.

### `fix/launcher-permissions-cache-status`

- Purpose: correct a registry reinstall that left bundled scripts non-executable and a Benchmark Status result that reported an existing but hardware-stale cache as healthy.
- Base: `dev` at `01a6820` after refreshing GitHub and reconciling workspace standards revision `sha256:6456d4a722cfca0a03e6bce3d698208c844a114953c62d0fe757789d48f1c794`.
- Intended target: `dev`, followed by approved immutable tag `v0.2.0-beta.6`, `dispatcharr-plugins:dev` publication, and installed-plugin validation.
- Result: source commit `a2af6ce` merged into `dev` at `45e6e5a`; annotated tag `v0.2.0-beta.6` resolves to reviewed integration commit `e9e7554` and is advertised through `dispatcharr-plugins:dev`.
- Scope: direct launcher mode repair, authoritative cache-validity status, persistent native cache-maintenance notifications, canonical wrapper beta.4 synchronization, regression tests, user/developer guidance, and beta.6 metadata.
- Exclusions: no automatic disruptive benchmark, no Dispatcharr request-routing or failover core change, no stable registry, GitHub Release, or distributable ZIP.
- Reported evidence: after a plugin reinstall the scripts lacked execute permission; a normal stream then emitted the wrapper's hardware-stale cache error, while Benchmark Status treated the cache as valid because the file still existed.
- Validation: 34 plugin unit tests pass, including a simulated `0644` ZIP extraction, enabled-plugin load repair to `0755`, direct launcher execution, canonical cache-status handling, persistent-notification create/clear behavior, and profile restart semantics. Python/JSON/shell checks, immutable beta.4 wrapper verification and idempotent synchronization, workspace reconciliation, exact tag/archive inspection, GitHub workflows, and `git diff --check` pass. The live beta.5 instance and cached pre-publication registry state were verified separately; beta.6 installation remains pending.
- Started: `2026-08-26`.

### `feature/degraded-proxy-fallback`

- Purpose: use the canonical wrapper's opt-in degraded stream-copy proxy whenever the required cache is unusable or a hardware benchmark is active, while keeping the cause visible in Dispatcharr's persistent notification center.
- Base: `dev` at `1b902d8be3def5c28e45aa6a2df5a5161ce810db` after refreshing project governance and remote state.
- Intended target: `dev`, followed by approved immutable tag `v0.2.0-beta.7` and `dispatcharr-plugins:dev` publication.
- Scope: launcher opt-in, canonical wrapper synchronization, per-invocation fallback marker monitoring, dismissal reset, notification wording, tests, documentation, and update-description coordination.
- Exclusions: no CPU transcode fallback, automatic benchmark, Dispatcharr retry-routing or core change, stable registry, GitHub Release, or distributable ZIP.
- Related work: canonical `ffmpeg-asr` branch `feature/degraded-proxy-fallback` and registry branch `feature/ffmpeg-smart-update-disclaimer`.
- Canonical source: tagged beta.5 integration commit `4fafc8b5af300d6e47413cfb9cf8409fef7c2201`, recorded and verified at SHA-256 `c4030ee729caa002e0d6b4e68a5893bd73221be4eb72578a71a83cb3d10aa507`.
- Result: finalized source commit `61a36f27b546f9f94fdf3b0a3283463ca5da3e42` merged into `dev` at `a982b08`; immutable tag `v0.2.0-beta.7` resolves to `600ba14572ab48f4d920c2cfd7ad4ac9fffce787` and was advertised through `dispatcharr-plugins:dev` before the corrective beta.8 repin.
- Validation: 37 plugin tests pass for beta.7, including launcher fallback, unique marker tokens, same-token deduplication, dismissal reset on later invocations, persistent-notification cleanup, and watcher lifecycle. Python/JSON/shell checks, offline and remote canonical-source verification, idempotent synchronization, workspace validation, and `git diff --check` pass. Live Dispatcharr fallback and notification reactivation remain pending.
- Started: `2026-08-26`.

### `fix/beta7-canonical-validation`

- Purpose: preserve the approved degraded fallback behavior while repinning the plugin to the corrective canonical wrapper tag whose Linux validation passes.
- Base: `dev` at `600ba14572ab48f4d920c2cfd7ad4ac9fffce787` after immutable plugin beta.7 and canonical wrapper beta.5 were published.
- Intended target: `dev`, followed by corrective immutable plugin tag `v0.2.0-beta.8` and `dispatcharr-plugins:dev` publication.
- Scope: exact canonical wrapper commit/checksum synchronization, beta.8 version and release metadata, changelog, tests, and branch ledger.
- Exclusions: no plugin fallback, notification, profile, scan, hardware, FFmpeg command, Dispatcharr compatibility, stable registry, GitHub Release, or distributable ZIP behavior change; do not move or replace published beta.7.
- Related work: canonical `ffmpeg-asr v1.1.0-beta.6` at `aeff09204000f58aa6fdd3a14781935f77a0823a`, created after beta.5 workflows exposed a stale scoped-command test expectation.
- Result: source commit `e75d017` merged into `dev` at `5e5f5e6`; immutable tag `v0.2.0-beta.8` resolves to reviewed integration commit `5309b16ae2440f36238fa5a5426cf2e2ecc9f918` and is advertised through `dispatcharr-plugins:dev`.
- Validation: all 37 plugin tests, Python compilation, JSON parsing, shell syntax, exact offline and remote canonical-source verification, idempotent synchronization, workspace validation, feature run `33015666374`, dev run `33015773661`, tag run `33015811503`, immutable archive/source-pin inspection, registry run `33016050222`, public raw-manifest agreement, and `git diff --check` pass. Installed-update validation remains pending.
- Started: `2026-08-26`.

### `fix/persistent-fallback-reactivation`

- Purpose: correct the live beta.8 behavior where a new degraded fallback invocation produced a toast but did not immediately restore a dismissed persistent notification-center entry.
- Base: `dev` at `bd4ece75c8e6a0dd5e1e96e0ddd316a7b7f01400` after refreshing the exact published beta.8 development head.
- Intended target: `dev`, followed by corrective immutable tag `v0.2.0-beta.9` and `dispatcharr-plugins:dev` publication.
- Scope: explicit active notification WebSocket serialization, dismissal-reactivation regression coverage, beta.9 metadata, changelog, ADR-021 clarification, and this branch ledger.
- Exclusions: no canonical wrapper, fallback routing, FFmpeg command, cache, benchmark, profile, hardware, stable registry, GitHub Release, distributable ZIP, or Dispatcharr core change.
- Dispatcharr evidence: official `v0.29.0` commit `d9abece081c9edf637d4c3fdd41443eb993a3c08` stores notifications durably but its model-to-WebSocket payload omits `is_dismissed`; the frontend merges by notification key and therefore preserves an old `true` value while independently showing a high-priority toast.
- Result: source commit `1cbd609` merged into `dev` at `8aab22b`; immutable tag `v0.2.0-beta.9` resolves to reviewed integration commit `d25b44b8999dba3aaeb82e264fb75335bbcacc88` and is advertised through `dispatcharr-plugins:dev`.
- Validation: official Dispatcharr v0.29.0 model/WebSocket/store review, all 37 plugin tests including explicit `is_dismissed: false` reactivation, Python compilation, JSON parsing, shell syntax, exact offline and remote canonical-source verification, idempotent synchronization, workspace validation, feature run `33017167703`, dev run `33017278257`, tag run `33017320109`, immutable archive inspection, registry run `33017533957`, public raw-manifest agreement, complete-diff review, and `git diff --check` pass. Installed beta.9 reactivation remains pending; live beta.8 already confirms degraded stream-copy service itself works.
- Started: `2026-08-26`.

### `fix/authoritative-notification-refresh`

- Purpose: correct live beta.9 behavior where dismissal rows are removed successfully but the persistent warning does not reappear in the browser until a manual refresh, and clarify the green action-completion toast shown for an unhealthy cache result.
- Base: `dev` at `7a6c9c87463db72be200bd14e6c9e75a9453beed` after refreshing the published beta.9 plugin and development registry heads.
- Intended target: `dev`, followed by corrective immutable tag `v0.2.0-beta.10` and `dispatcharr-plugins:dev` publication.
- Scope: Dispatcharr's built-in notification-refresh event, load/status/fallback dismissal reactivation, regression coverage, status-result wording, beta.10 metadata, changelog, ADR-021 correction, and this branch ledger.
- Exclusions: no canonical wrapper, fallback routing, FFmpeg command, cache-validity policy, benchmark behavior, profile, hardware, Dispatcharr core, stable registry, GitHub Release, or distributable ZIP change.
- Dispatcharr evidence: official `v0.29.0` commit `d9abece081c9edf637d4c3fdd41443eb993a3c08` handles `notifications_cleared` by fetching the authoritative notification API, while plugin action HTTP success is colored green without inspecting `result.status`.
- Reported evidence: installed beta.9 restores the database-backed warning only after a browser refresh; a post-install Benchmark Status check reports the recheck requirement but Dispatcharr gives the successful action request a green toast edge.
- Result: source commit `2aa812a30bb949e877bbbae64cfd9b51d7ed69a2` merged into `dev` at `15caf3a1df554544a47bf67643eabd5f0dbe6eee`; this reviewed integration is the candidate source for corrective `v0.2.0-beta.10`.
- Validation: all 37 plugin tests, Python compilation, JSON parsing, shell syntax, exact offline and remote canonical-source verification, workspace validation, official Dispatcharr v0.29.0 notification-refresh and plugin-action UI contract review, feature workflow run `33018546999`, complete-diff review, and `git diff --check` pass. Dev/tag workflows, immutable tag/archive, registry publication, and installed beta.10 validation remain pending.
- Started: `2026-08-26`.
