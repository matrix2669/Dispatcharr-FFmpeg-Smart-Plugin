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
| `feature/degraded-proxy-fallback` | feature | active | `dev` | `dev` | Preserve basic stream-copy service and re-notify after every degraded invocation while Smart capabilities are unavailable. |
| `fix/show-advanced-defaults` | fix | merged | `dev` | `dev` | Show the exact static defaults and runtime-derived default formulas beside every advanced scope control. |
| `fix/launcher-permissions-cache-status` | fix | merged | `dev` | `dev` | Make registry installs launch reliably and report cache validity rather than file existence alone. |

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
- Current state: integrates beta.6 direct-launch mode repair, authoritative cache health, persistent native maintenance notifications, and pinned canonical `ffmpeg-asr v1.1.0-beta.4` on top of the scoped advanced-option controls.
- Validation: 34 plugin unit tests, Python/JSON/shell checks, immutable wrapper source verification and idempotent synchronization, workspace reconciliation, exact tag/archive inspection, live Dispatcharr v0.29.0 notification-model and loader compatibility review, and whitespace validation pass. Installed beta.6 update validation remains pending.
- Publication state: immutable `v0.2.0-beta.6` is tagged and advertised through `dispatcharr-plugins:dev`; the live instance still has beta.5 installed. No GitHub Release, stable-registry change, or distributable ZIP is authorized.
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
- Intended target: `dev` after the canonical wrapper change is committed, pinned, synchronized, and the complete plugin gate passes.
- Scope: launcher opt-in, canonical wrapper synchronization, per-invocation fallback marker monitoring, dismissal reset, notification wording, tests, documentation, and update-description coordination.
- Exclusions: no CPU transcode fallback, automatic benchmark, Dispatcharr retry-routing or core change, stable registry, GitHub Release, or distributable ZIP.
- Related work: canonical `ffmpeg-asr` branch `feature/degraded-proxy-fallback` and registry branch `feature/ffmpeg-smart-update-disclaimer`.
- Canonical source: tagged beta.5 integration commit `4fafc8b5af300d6e47413cfb9cf8409fef7c2201`, recorded and verified at SHA-256 `c4030ee729caa002e0d6b4e68a5893bd73221be4eb72578a71a83cb3d10aa507`.
- Validation: 37 plugin tests pass, including launcher fallback, unique marker tokens, same-token deduplication, dismissal reset on later invocations, persistent-notification cleanup, and watcher lifecycle. Python/JSON/shell checks, offline and remote canonical-source verification, idempotent synchronization, workspace validation, and `git diff --check` pass. Live Dispatcharr fallback and notification reactivation remain pending.
- Started: `2026-08-26`.
