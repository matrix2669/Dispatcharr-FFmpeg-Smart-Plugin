# AGENT.md

## Workspace Standards Reconciliation Gate

Before any substantive work, locate the maintained local `matrix2669/workspace` checkout and run `<workspace>/scripts/reconcile-standards --check .` from this repository root. The workspace `AI-INSTRUCTIONS.md`, `AGENT-STANDARD.md`, and Git history must be available.

If `WORKSPACE-STANDARDS.yaml` is missing, pending, or stale, stop project work and run `<workspace>/scripts/reconcile-standards --diff .`. Review the standards change against this complete `AGENT.md`, `DECISIONS.md`, code/configuration contracts, dependencies, `BRANCHES.md`, `RELEASE.md`, upstream requirements when applicable, and related projects.

A contradiction blocks work. Ask focused follow-up questions to establish whether the changed standard, proposed work, new answer, or older accepted decision is authoritative; never choose silently. Record project-decision supersessions in `DECISIONS.md` and realign every affected artifact. Only after no contradiction remains, run `<workspace>/scripts/reconcile-standards --apply --confirm-reviewed-no-conflicts .`.

Missing workspace standards or Git history is a hard block. Standards exceptions require explicit user authorization and must be stated in a dedicated section of this file with exact scope, rationale, authority, approval date, and review/removal trigger; `DECISIONS.md` cannot waive workspace standards.

## Workspace Standards Exception: v0.2.0 stable registry without a Release

- Exact scope: only plugin tag `v0.2.0` may be advertised through `matrix2669/dispatcharr-plugins:main` without a GitHub Release. The registry must reference the immutable tag archive and exact source commit. This does not authorize a GitHub Release, manual ZIP, checksum asset, license claim, any other plugin version, or any other registry entry.
- Rationale: the complete beta.11 cycle passed automated, archive, installed, hardware, fallback, notification, and custom-option validation, and the operator explicitly wants that exact completed build in the stable Dispatcharr channel while continuing to withhold Release packaging until inherited-wrapper licensing is resolved.
- Authority: explicit user direction in Codex on `2026-08-26`: promote both source branches and tags and update the stable manifest, but do not create a Release until the license is resolved.
- Approval date: `2026-08-26`.
- Review/removal trigger: reviewed on `2026-08-30` when the new MIT runtime resolved licensing for later versions. Retain this record while `v0.2.0` remains the stable-registry build; remove the active exception after the stable channel returns to a Release-backed version or FFmpeg Smart is withdrawn from `main`. It cannot be reused for a correction or later version.


## Purpose

This repository owns the `FFmpeg Smart Profiles` plugin for Dispatcharr. The plugin installs and reconciles managed Stream and Output Profiles, coordinates disruptive hardware-cache rebuilds, reports benchmark status, and ships a self-contained copy of the canonical `matrix2669/ffmpeg-adaptive` runtime.

## Architecture

- `ffmpeg-smart-profiles/plugin.json` declares Dispatcharr settings and actions.
- `ffmpeg-smart-profiles/plugin.py` is the Dispatcharr integration layer. It owns profile definitions, settings migration, safe database reconciliation, active-transcode coordination, benchmark lifecycle, and status reporting.
- `ffmpeg-smart-profiles/ffmpeg-smart-plugin.sh` is the plugin-specific launcher. It selects persistent state under `/data/ffmpeg_smart_profiles`, requires an operator-built cache for normal streams, and executes the canonical wrapper.
- `ffmpeg-smart-profiles/ffmpeg-smart.sh` and `ffmpeg-smart-profiles/lib/*.sh` are one vendored modular runtime dependency. Their canonical source is `matrix2669/ffmpeg-adaptive`; do not develop wrapper behavior independently in this repository.
- `ffmpeg-smart-profiles/FFMPEG_SMART_SOURCE.json` pins every runtime file to one full source commit, SHA-256 checksum, and installed mode. `FFMPEG_ADAPTIVE_LICENSE` preserves the dependency's MIT notice.
- `scripts/check-ffmpeg-smart-source.sh` verifies the complete local bundle and, unless `--offline` is used, every exact remote source file.
- `scripts/sync-ffmpeg-smart.sh` resolves a branch, tag, or full commit, replaces the complete vendored runtime, and updates its pins.
- `.github/workflows/ffmpeg-smart-sync.yml` checks the canonical source and opens a reviewable update pull request.
- `.github/workflows/ffmpeg-smart-verify.yml` validates the source pin, plugin tests, JSON, Python, and shell syntax.
- `tests/test_plugin.py` covers behavior that can be isolated from Dispatcharr.
- `tests/validate_dispatcharr.py` validates the exact installed plugin layout and generated defaults inside Dispatcharr.

Data flow:

1. Dispatcharr loads `plugin.json` and `plugin.py` from the stable `ffmpeg-smart-profiles/` directory.
2. **Install or Update Profiles** converts saved settings into two possible Stream Profile slots and three possible Output Profile slots.
3. Stream Profiles pass `{streamUrl}` and `{userAgent}` to the launcher. Output Profiles pass Dispatcharr's non-seekable MPEG-TS input as `pipe:0`.
4. The launcher sets persistent state and required-cache policy, then the wrapper resolves stream policy, capabilities, and GPU scheduling and returns MPEG-TS on standard output.
5. **Rebuild Hardware Cache** creates the shared benchmark lock, stops active Dispatcharr transcodes, and launches `ffmpeg-smart-plugin.sh --recache-only` in the background.
6. **Benchmark Status** reads the background PID, log, and capability cache from `/data/ffmpeg_smart_profiles` without starting new work.

## Ownership boundaries

- This repository owns Dispatcharr integration, profile policy defaults, settings UX, maintenance orchestration, packaging, and plugin releases.
- `matrix2669/ffmpeg-adaptive` owns all wrapper behavior, hardware discovery, stream policy resolution, benchmarking, cache schema, and GPU scheduling.
- `matrix2669/dispatcharr-plugins` owns only which immutable plugin tag each `dev` or `main` registry channel advertises.
- The official Dispatcharr repository owns the plugin API, manifest contract, models, Redis keys, loader behavior, archive extraction, and minimum-version semantics.

## Non-negotiable rules

- Keep the plugin self-contained; the installed archive must include `ffmpeg-smart.sh`, every pinned `lib/*.sh` module, and the dependency's MIT notice, and must not depend on a Git submodule or a second repository checkout.
- Keep mutable runtime state outside the replaceable plugin directory. The launcher, plugin status, and recache orchestration must share `/data/ffmpeg_smart_profiles` unless an explicit test override is supplied.
- Never edit the vendored runtime as an independent implementation. Change and validate `ffmpeg-adaptive` first, publish its canonical commit, then synchronize this repository through the pin workflow.
- Never silently update an existing tag, Release, archive, or installed plugin version. Wrapper changes require a new plugin version before registry publication.
- Profile installation must remain idempotent and transactional. Do not overwrite locked profiles, duplicate names, or same-name profiles owned by another command.
- Keep policy normalization plugin-only. Remove retired `-10bit` and `-hdr` settings and flags, and migrate `-sdr`, `-deint`, or `-deinterlace` from Additional options into the remaining checkboxes without requiring a Dispatcharr core change.
- Keep advanced FFmpeg settings aligned with the canonical wrapper's input, mapping, transcode-video, audio, and MPEG-TS/mux scopes. Parse fields with `shlex.split`, quote each wrapper argument independently, retain the beta.3 `*_ffmpeg_options` IDs as mux fields, and never expose a full custom command or wrapper-owned input, hardware, encoder, filter, format, or output controls.
- Show each advanced scope's complete inherited default or runtime-derived formula in the mode field's help text. Keep the adjacent options field blank for user-owned Add/Replace text; Dispatcharr does not provide a dependent-field hook that can safely populate it when the mode changes.
- HDR and 10-bit selection remain automatic. Only Force SDR and Force deinterlace generate managed policy flags, at most once each.
- All managed Output Profiles must use the pipe-safe wrapper path. Do not replace them with bare `ffmpeg` templates.
- Hardware benchmarking may stop input- or output-transcoded streams, but proxy-only streams must continue. New managed starts use canonical degraded stream copy until the benchmark lock clears and must not use GPU decode, filtering, or encoding.
- Do not give the plugin Docker-socket or host-control access merely to restart Dispatcharr. Profile creation and removal return `restart_required` and instruct the operator to restart normally; in-place updates do not require a restart.
- Recorded GPU capacities are deployment evidence, not portable defaults. Re-measure on materially different hardware or benchmark policy.
- Preserve the dependency notice for the MIT-licensed `ffmpeg-adaptive` runtime. New plugin versions that contain only the independently licensed runtime may proceed through normal Release gates; this does not retroactively relicense or authorize repackaging historical tags that bundled the inherited `ffmpeg-asr` source.

## Development workflow

This is a standalone Dispatcharr plugin:

- `main` is production-ready and contains explicitly approved Releases.
- `dev` integrates the next version.
- short-lived `feature/*` and `fix/*` branches start from and return to `dev`.
- the historical `dev-test` branch is retired when the `dev` migration is approved and verified.
- immutable beta tags use `vMAJOR.MINOR.PATCH-beta.N` on tested `dev` commits.
- completed stable tags use `vMAJOR.MINOR.PATCH`; a completed tag does not require a GitHub Release.

Record every current branch in `BRANCHES.md` before substantive work. Before deleting a branch, transfer user-visible results to `CHANGELOG.md` and durable rationale to `DECISIONS.md`, then remove the live branch record.

The synchronization workflow targets `dev`. Wrapper-update pull requests must pass plugin validation and human review. Promote the exact tested plugin state to `main`; do not bypass `dev` by silently syncing canonical wrapper changes into production.

## Session completion and remote continuity

GitHub is the authoritative continuation source. Start by fetching `origin` and resume from the exact remote head of the branch that owns the change. A repository-change request authorizes checkpoint commits and pushes to an isolated feature or fix branch. Before ending or handing off a session, preserve unrelated work, update branch/decision/validation records, run the applicable gates, commit every in-scope committable change, push every local commit, and verify through a fresh remote query that the exact GitHub head matches the intended local checkpoint. Incomplete work is pushed as explicit WIP with failures or unavailable validation recorded; never commit credentials, runtime state, excluded artifacts, or unrelated changes merely to clean the worktree.

The checkpoint does not authorize merging into `dev` or `main`, synchronizing a new canonical wrapper into a release, tagging, changing a registry channel, releasing, distributing a ZIP, deploying, force-pushing, or deleting a branch. Report the work branch, `dev` integration, source pin, tag, registry, Release, and deployment states separately.

## Version and distribution requirements

- `VERSION`, `Plugin.version`, `plugin.json`, the changelog version, and the Git tag must agree.
- Dispatcharr updates are version-driven. Untagged branch movement does not replace a published test build.
- `dispatcharr-plugins:dev` advertises the newest approved immutable plugin tag: a beta during testing, otherwise the latest completed stable tag.
- `dispatcharr-plugins:main` normally advertises only a stable version with an explicitly approved GitHub Release; the dedicated `v0.2.0` exception above is the sole current waiver.
- A stable tag may exist in `dev` without a GitHub Release or `main` registry publication.
- Never merge the registry's `dev` channel wholesale into its `main` channel; registry publication is a focused metadata change.
- Follow `RELEASE.md` and inspect the exact tagged archive layout before publication.

## Dispatcharr compatibility refresh gate

The current recorded minimum is Dispatcharr `v0.29.0`. Whenever the supported, minimum, tested, or deployed Dispatcharr version changes, revalidate this plugin and its registry manifest against the matching current revision of the official Dispatcharr repository before tagging or publishing.

Record the Dispatcharr version or tag, exact commit, repository URL, and review date. Inspect at minimum:

- plugin discovery and `plugin.json` field/action schema;
- `Plugin.run`, settings persistence, and action result behavior;
- `StreamProfile`, `OutputProfile`, locking, and restart behavior;
- Redis keys and native channel-stop APIs used for active transcodes;
- registry and per-plugin manifest fields and version comparison;
- archive download, extraction, plugin-directory discovery, and minimum-version handling;
- installation and update behavior for the proposed archive.

Treat a `min_dispatcharr_version` change or an upgrade of the validation instance as a version change. If the matching official revision cannot be verified, stop publication rather than relying on cached assumptions.

## Validation

For every change, run:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile ffmpeg-smart-profiles/plugin.py tests/validate_dispatcharr.py
python3 -m json.tool ffmpeg-smart-profiles/plugin.json >/dev/null
python3 -m json.tool ffmpeg-smart-profiles/FFMPEG_SMART_SOURCE.json >/dev/null
bash -n ffmpeg-smart-profiles/ffmpeg-smart.sh
for module in ffmpeg-smart-profiles/lib/*.sh; do bash -n "$module"; done
bash -n ffmpeg-smart-profiles/ffmpeg-smart-plugin.sh
bash -n scripts/check-ffmpeg-smart-source.sh
bash -n scripts/sync-ffmpeg-smart.sh
scripts/check-ffmpeg-smart-source.sh --offline
```

When network access is available, also run `scripts/check-ffmpeg-smart-source.sh` against the immutable remote source. A wrapper synchronization must be idempotent when repeated against the same source ref.

Behavioral or compatibility changes additionally require applicable live Dispatcharr checks:

- native plugin discovery from the packaged directory;
- create/update/remove idempotence and conflict behavior;
- settings normalization persistence;
- a full restart after profile creation or removal, plus an in-place update check that confirms no restart is requested;
- a real `pipe:0` Output Profile test confirming the opening sample is preserved;
- benchmark interruption of transcodes while proxy-only streams continue;
- degraded stream-copy routing for new managed starts while the benchmark lock exists, without GPU decode/filter/encode use;
- background completion, stale-PID handling, and capability status readback;
- tag archive and manual ZIP layout from a clean extraction.

## Future-agent checklist

- [ ] Read `AGENT.md`, `DECISIONS.md`, `BRANCHES.md`, `CHANGELOG.md`, and `RELEASE.md`
- [ ] Review all relevant project history and the current `ffmpeg-adaptive` source pin
- [ ] Confirm the branch base, intended target, and registry channel
- [ ] Refresh the branch ledger before substantive work
- [ ] Keep plugin integration changes separate from canonical wrapper changes
- [ ] If any Dispatcharr version changed, complete and record the compatibility refresh gate
- [ ] Run proportionate automated and live validation
- [ ] Verify version agreement and immutable archive layout before tagging
- [ ] Verify explicit Release approval before changing `dispatcharr-plugins:main`
