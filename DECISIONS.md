# Architecture Decisions

This file records the durable decisions that govern `matrix2669/Dispatcharr-FFmpeg-Smart-Plugin`. It was reconstructed on 2026-08-22 from all available related ChatGPT and Codex history, the complete repository history, the current implementation and tests, the `v0.1.0` archive, the `ffmpeg-asr` source and decisions, the `dispatcharr-plugins` distribution contract, and recorded live Dispatcharr validation.

Conversation proposals are evidence, not decisions by themselves. When an idea changed during implementation, the accepted decision below reflects the behavior the user approved and that survives in the current code. Superseded approaches are named so they are not accidentally restored.

## Evidence index

- ChatGPT `FFMpeg-ASR`: `6a810a36-bf2c-83ea-bf41-b144d16ca1fb`
- ChatGPT `FFmpeg Dispatcharr Profile`: `6a78daaa-d420-83ea-ac4d-b1d50eb7a257`
- ChatGPT `Mobile Streaming Profile Setup`: `6a7ee9a4-b990-83ea-b656-d98cad0343e1`
- ChatGPT `Dispatcharr Xtream Output Profile`: `6a7ef76b-8c18-83ea-b5a3-0c59383f4563`
- ChatGPT `Simplify Plugin Versioning`: `6a898c9e-1ffc-83ea-8fcc-b44788fea3c0`
- Codex `Add multi-GPU FFmpeg-ASR selection`: `01a01a9f-e65a-7ac3-95d0-430c44a35b16`
- Codex `Update standalone release workflow`: `01a02969-01f0-7803-8031-37f7f4f2803c`
- Repository commits: `fbdffa3` through `e823c47`
- Related source: `matrix2669/ffmpeg-asr`
- Distribution repository: `matrix2669/dispatcharr-plugins`

---

# ADR-001: Operate as a standalone Dispatcharr plugin with `main` and `dev`

## Status

Accepted; supersedes the historical `dev-test` source branch

## Date

2026-08-22

## Decision

Use the workspace standalone lifecycle:

- `main` is production-ready plugin source and the line for explicitly approved GitHub Releases.
- `dev` integrates the next plugin version.
- short-lived `feature/*` and `fix/*` branches start from and merge into `dev`.
- tested beta builds are immutable `vMAJOR.MINOR.PATCH-beta.N` tags on `dev`.
- completed stable builds use normal Semantic Version tags; a completed tag may remain unreleased.
- retire the historical `dev-test` branch after `dev` is created, consumers and automation are verified, and its durable history is recorded.

## Reason

The plugin is independently owned, versioned, tested, and released. The old branch name came from the registry's former testing channel and mixed distribution terminology with source integration. Tags are the immutable version mechanism; permanent version branches and a source `dev-test` branch are unnecessary.

## Alternatives considered

- Keep `dev-test` permanently. Rejected because the standardized standalone source branch is `dev` and the registry channel has also been renamed.
- Use one branch per plugin version. Rejected because tags preserve immutable versions without branch clutter.
- Apply the upstream-fork production-overlay model. Rejected because this repository is not an upstream contribution fork.

## Consequences

Automation and documentation target `dev` for incoming work. `main` and `dev` are synchronized after stable promotion. Branch intent is recorded in `BRANCHES.md`; deleted work branches do not remain in that ledger after their results move to the changelog and decisions.

## Provenance

- ChatGPT `Simplify Plugin Versioning`
- Workspace ADR-008 and ADR-009
- Current migration task: Codex `Update standalone release workflow`

---

# ADR-002: Keep Dispatcharr integration separate from wrapper behavior

## Status

Accepted

## Date

2026-08-19

## Decision

This repository owns the native Dispatcharr integration and profile-level defaults. `matrix2669/ffmpeg-asr` owns `ffmpeg-smart.sh` behavior.

The plugin may decide:

- which profile slots exist and their defaults;
- how settings become wrapper arguments;
- how profiles are safely created, updated, migrated, or removed;
- how disruptive recaching is coordinated with Dispatcharr;
- how status and operator warnings are presented.

The plugin must not maintain an independent fork of wrapper logic. Wrapper fixes begin in `ffmpeg-asr`, are validated there, and arrive here through the pinned synchronization workflow.

## Reason

Hardware discovery, transcoding policy, pipe capture, cache schema, and scheduling are already complex in the canonical source. Duplicating their development would cause drift and ambiguous ownership. Dispatcharr-specific orchestration does not belong in the general wrapper.

## Alternatives considered

- Let the plugin copy evolve independently. Rejected because identical files had already started to depend on manual coordination.
- Move plugin orchestration into `ffmpeg-asr`. Rejected because stopping Dispatcharr channels and persisting plugin settings are consumer-specific.
- Modify Dispatcharr core for plugin policy behavior. Rejected by the user; plugin-only integration is sufficient.

## Consequences

Cross-repository changes are deliberately staged. The plugin can change profile defaults without changing the wrapper's global defaults, while any wrapper byte change requires a new source pin and a new plugin version before distribution.

## Provenance

- Commits: `fbdffa3`, `d371587`
- Codex `Add multi-GPU FFmpeg-ASR selection`
- Related `ffmpeg-asr` ADR-003 and ADR-013

---

# ADR-003: Vendor the wrapper and pin its immutable source

## Status

Accepted

## Date

2026-08-19

## Decision

Ship a self-contained executable copy at `ffmpeg-smart-profiles/ffmpeg-smart.sh`. Record its canonical repository, path, full 40-character commit, and SHA-256 checksum in `FFMPEG_SMART_SOURCE.json`.

Provide two explicit controls:

- `check-ffmpeg-smart-source.sh` verifies the bundled checksum locally and can compare it byte-for-byte with the immutable remote source.
- `sync-ffmpeg-smart.sh` resolves a requested branch, tag, or full commit; downloads the exact canonical file; validates shell syntax; installs it executable; and updates the pin.

A daily/manual workflow checks `ffmpeg-asr/main` and opens a pull request against plugin `dev` only when the bytes change. Documentation-only or otherwise byte-identical canonical commits leave the existing immutable pin unchanged. Human review and normal plugin release/version rules still apply.

## Reason

Dispatcharr installations and release archives must work without cloning another repository. At the same time, a mutable branch or unrecorded copy cannot prove which wrapper was tested and shipped.

## Alternatives considered

- Git submodule. Rejected because normal GitHub archives and Dispatcharr installation do not reliably include submodule contents.
- Download the wrapper at plugin runtime. Rejected because installs would no longer be self-contained or reproducible and could change without a plugin version update.
- Silently commit scheduled updates to `main`. Rejected because wrapper changes can alter transcoding behavior and must be reviewable.
- Record only a semantic tag. Rejected because the full commit and checksum provide stronger byte-level provenance.

## Consequences

CI can reject drift. The synchronization workflow needs repository-level permission for Actions to create pull requests; GitHub exposes creation and approval as one combined setting, which the user explicitly approved. Existing Releases remain immutable even after the canonical wrapper advances.

## Provenance

- Commits: `d371587`, `e823c47`
- Canonical pin at adoption: `ffmpeg-asr@1422797653e82034b4726e331fd971969534913c`
- Manual no-change workflow run: `32291058931`

---

# ADR-004: Use fixed, configurable profile slots

## Status

Accepted; supersedes dynamic-template exploration

## Date

2026-08-19

## Decision

Expose exactly two Stream Profile slots and three Output Profile slots in the current settings model. Every slot has:

- an enable checkbox;
- an editable name;
- per-profile 10-bit, HDR, SDR, and deinterlace controls;
- an editable Additional options field.

The initial defaults enable:

- Stream Profile 1, `FFmpeg Smart`, with 10-bit and HDR allowed;
- Output Profile 1, `FFMpeg Smart - 720p Mobile`, with `-maxres 720 -maxbr 2M -maxchan 2 -sdr -deint`.

All other slots start disabled and blank.

## Reason

Dispatcharr's current plugin settings schema does not provide a native add/remove repeater. A multiline custom mini-language could support arbitrary templates but would reduce discoverability, validation quality, and UI guidance. The user explicitly chose a fixed amount with checkboxes and renameable fields.

## Alternatives considered

- Dynamically add profile form sections. Rejected because the plugin UI does not expose a repeater.
- One multiline field containing unlimited templates. Explored, then rejected in favor of clear fixed controls.
- Hard-code profiles with no customization. Rejected because names and policy needs vary by deployment.

## Consequences

Increasing the slot count requires a schema and migration change. Additional options remain available for advanced wrapper flags, but input and maintenance flags are reserved for the plugin.

## Provenance

- Commit: `31539fb`
- Codex user direction: “fixed amount with check boxes and fields. 2 for stream profiles and 3 for output profiles”

---

# ADR-005: Make profile reconciliation safe, transactional, and idempotent

## Status

Accepted

## Date

2026-08-19

## Decision

Create, update, migrate, and remove profiles inside database transactions. A repeated installation with unchanged settings creates no duplicates.

The plugin may update a same-name profile only when it is unlocked and already points to `ffmpeg-smart.sh`, or when it is a known legacy native-FFmpeg template explicitly covered by migration. It reports conflicts rather than overwriting:

- locked profiles;
- duplicate names;
- same-name profiles owned by another command;
- changes when updates are disabled.

When cleanup is enabled, disabled or renamed managed profiles may be removed only if unlocked. Remove Managed Profiles follows the same ownership and lock boundaries.

## Reason

Profiles are shared Dispatcharr configuration, not private plugin files. A convenient installer must not seize unrelated profiles, overwrite an operator's locked definition, or leave half-applied state after an error.

## Alternatives considered

- Unconditionally update by name. Rejected because names are not proof of ownership.
- Delete and recreate all definitions on every run. Rejected because it breaks references and ignores locks.
- Require manual profile creation. Rejected because the plugin exists to provide consistent tested definitions.

## Consequences

Conflicts require operator resolution. Legacy migration remains narrowly named and command-aware. Any new managed profile type needs equivalent ownership and idempotence tests.

## Provenance

- Initial commit: `fbdffa3`
- Configuration commit: `31539fb`
- Current implementation: `_install_profiles`, `_upsert_profile`, and `_remove_profiles`

---

# ADR-006: Keep policy controls plugin-only and normalize legacy options

## Status

Accepted

## Date

2026-08-19

## Decision

Represent `-10bit`, `-hdr`, `-sdr`, and `-deint` as persisted per-profile checkboxes. During Install or Update Profiles, detect those flags—including the `-deinterlace` alias—in Additional options, remove the duplicates, enable the corresponding controls, and persist the normalized settings.

Generate each policy flag at most once. When Allow HDR and Force SDR are both true, emit only `-sdr`. An unchecked 10-bit or HDR checkbox does not force those capabilities off; it leaves the wrapper's automatic hardware policy in control unless the competing SDR constraint is enabled.

Do not normalize on the settings Save action because Dispatcharr does not invoke the plugin there. Tell the operator to refresh the settings page after Install or Update so persisted checkbox changes become visible.

## Reason

Early development versions placed policy flags in free-form text. Adding controls without migration would produce duplicates and ambiguous precedence. The user required the compatibility logic to remain entirely within the plugin rather than changing Dispatcharr core.

## Alternatives considered

- Reject legacy settings and require manual cleanup. Rejected because a safe automatic migration exists.
- Change Dispatcharr's settings-save pipeline. Rejected by scope and user direction.
- Emit both `-hdr` and `-sdr` and let the wrapper decide. Rejected because the plugin can produce an unambiguous policy.

## Consequences

Install or Update Profiles is both a reconciliation and settings-migration action. Disabled draft slots with invalid quoting do not block unrelated enabled profiles; enabled definitions still receive normal validation.

## Provenance

- Commit: `b5f7402`
- Twelve unit tests plus installed-container validation recorded before v0.1.0

---

# ADR-007: Route every managed profile through the pipe-safe wrapper

## Status

Accepted; supersedes native-FFmpeg Output Profile templates

## Date

2026-08-19

## Decision

Both Stream and Output Profiles execute the bundled `ffmpeg-smart.sh`.

- Stream Profiles use `-i "{streamUrl}" -user_agent "{userAgent}"`.
- Output Profiles use `-i pipe:0` because Dispatcharr supplies a live MPEG-TS stream through standard input.

The canonical wrapper's pipe mode captures an initial sample, probes it once, and prepends the captured packets to the continuing input so probing does not discard the opening content. The plugin must not substitute a bare `ffmpeg` command for an Output Profile merely to avoid this input constraint.

## Reason

The initial plugin safely avoided calling a seek/probe-oriented wrapper on non-seekable input and therefore created native-FFmpeg Output Profiles. That meant Output Profiles bypassed hardware policy, cache, device selection, and future wrapper improvements. The dedicated capture-and-reinsert design made the shared behavior correct.

## Alternatives considered

- Reopen `pipe:0` after probing. Rejected because consumed bytes cannot be reread.
- Keep native-FFmpeg Output Profiles permanently. Superseded because they bypass the smart wrapper.
- Skip probing for piped input. Rejected because conditional policy needs source metadata.

## Consequences

Pipe behavior is a cross-repository contract. Any wrapper sync that changes capture, probing, or standard-input handling requires an end-to-end Dispatcharr Output Profile test that confirms complete output duration and preserved opening content.

## Provenance

- Plugin commit: `31539fb`
- Canonical source commit: `ffmpeg-asr@1422797`
- Live validation: 10-second 4K MPEG-TS pipe input produced the complete 10-second 720p output

---

# ADR-008: Treat hardware recaching as coordinated maintenance

## Status

Accepted

## Date

2026-08-19

## Decision

Before launching a full hardware-cache rebuild:

1. create `.benchmark.lock` beside the wrapper;
2. use Dispatcharr's native services to stop active channels that have input Stream Profile or Output Profile transcodes;
3. deduplicate channels that have both markers;
4. leave proxy-only channels running;
5. wait up to 15 seconds for selected transcodes to disappear;
6. abort safely and clear the lock if teardown or launch fails;
7. run `ffmpeg-smart.sh --recache-only` only after the GPU workload is clear.

While the lock exists, new FFmpeg Smart transcodes refuse to start with temporary-failure exit status 75. The wrapper owns automatic lock removal at benchmark completion or termination and stale-lock recovery.

## Reason

Real concurrent-capacity measurement intentionally saturates every visible GPU. Existing or newly starting transcodes would corrupt the measurement and may buffer viewers. Proxy streams do not consume the FFmpeg hardware path and should not be interrupted.

## Alternatives considered

- Kill FFmpeg processes directly. Rejected because Dispatcharr owns viewer and channel cleanup.
- Stop every active channel. Rejected because proxy-only viewers are unaffected by GPU benchmarking.
- Benchmark alongside production transcodes. Rejected because results would be invalid and service quality would suffer.
- Deactivate profiles during the benchmark. Rejected because a shared runtime lock is simpler and covers new wrapper invocations directly.

## Consequences

Recaching is an operator-confirmed disruptive action. Redis and Dispatcharr's native channel service are runtime dependencies for safe coordination. Changes to Dispatcharr's Redis keys or stop API trigger compatibility review.

## Provenance

- Commit: `ee4b933`
- Canonical wrapper coordination: `ffmpeg-asr@23fe80f`
- Installed validation: transcodes stopped, new wrapper call returned 75, proxy-only stream remained

---

# ADR-009: Run recaching in the background and report authoritative status

## Status

Accepted

## Date

2026-08-19

## Decision

Launch `--recache-only` as a detached background process with its PID and combined output recorded under `runtime/`. Benchmark Status must:

- distinguish idle, running, complete, and error states;
- validate that a PID is non-zombie and its command line is this exact wrapper with `--recache-only`;
- show the latest progress line during a run;
- retain the latest 30 log lines;
- show cached acceleration, codec, 10-bit support, primary/secondary devices, capacities, and speeds whenever available, including while a new run is active.

The confirmation estimate is derived from visible DRM GPU count. Status checks are read-only and must not trigger a benchmark.

## Reason

Full concurrent benchmarking takes minutes and cannot safely block a normal plugin action request. A PID number alone is not authoritative because the process may have exited, become a zombie, or been reused.

## Alternatives considered

- Run synchronously. Rejected because the action would block for the full benchmark.
- Report only the log. Rejected because operators need cached capability and device context.
- Treat `kill(pid, 0)` as sufficient. Rejected because it misclassifies zombies and reused PIDs.
- Automatically refresh Dispatcharr's profile UI. Rejected because the current frontend stores do not listen for plugin profile-change events.

## Consequences

Runtime PID, log, cache, and lock files are ignored state, not release content. Any status-schema change needs unit and installed-plugin validation.

## Provenance

- Commits: `fbdffa3`, `1974182`
- Recorded installed capabilities: VAAPI/HEVC, Arc A310 capacity 18, UHD 770 capacity 15 at the final 1.2x policy

---

# ADR-010: Require explicit restart and operator feedback after profile changes

## Status

Superseded by ADR-016

## Date

2026-08-19

## Decision

Install/Update and Remove actions require confirmation, return `restart_required`, and clearly state that a full Dispatcharr restart is necessary before changes fully take effect. Settings normalization also tells the operator to refresh the browser to display the new checkbox state.

Do not grant the plugin access to the Docker host socket or another host-control mechanism to restart Dispatcharr itself.

## Reason

Directly created or modified profiles are not fully usable until Dispatcharr reloads them, and the frontend cannot be refreshed through the current plugin API. Automatic container control would materially expand privileges for a convenience feature.

## Alternatives considered

- Present profile changes as immediately active. Rejected by installed behavior.
- Have the plugin restart its container. Rejected because the normal unprivileged plugin should not control Docker or the host.
- Omit confirmation. Rejected because profile removal can affect channel assignments and installation creates a required maintenance step.

## Consequences

Operators perform restart and browser refresh explicitly. Compatibility review must revisit this decision if Dispatcharr later adds an official profile reload or frontend refresh API.

## Provenance

- Commits: `1974182`, `875ca20`

## Supersession

ADR-016 preserves restart requirements for profile creation and removal but supersedes the claim that an in-place update requires a restart.

---

# ADR-011: Package the plugin under a stable install directory

## Status

Accepted

## Date

2026-08-19

## Decision

The tagged tree and installable archive contain runtime files beneath the stable `ffmpeg-smart-profiles/` directory:

```text
ffmpeg-smart-profiles/
├── FFMPEG_SMART_SOURCE.json
├── ffmpeg-smart-plugin.sh
├── ffmpeg-smart.sh
├── plugin.json
└── plugin.py
```

Repository documentation, tests, and synchronization tooling may exist outside that directory, but Dispatcharr runtime identity must not depend on GitHub's commit-specific outer archive directory.

Inspect the exact tag archive before any registry update or Release. A manual Release ZIP, once legally permitted, must preserve the same top-level plugin directory.

## Reason

The first v0.1.0 candidate left runtime files at repository root, which would make the installed directory derive from GitHub's generated archive name rather than the plugin's stable identity. The tag was corrected before registry publication.

## Alternatives considered

- Keep runtime files at repository root. Rejected because archive extraction would produce an unstable install path.
- Depend on registry-side repackaging. Rejected because the plugin source tag should itself be structurally installable and independently verifiable.

## Consequences

Packaging tests must inspect paths, not merely file contents. `v0.1.0` points to commit `1581f3f`, which contains the stable directory. Published tags must never be moved again; corrections use a new version.

## Provenance

- Commits: `cfdedbd`, `1581f3f`
- Tag: `v0.1.0`
- Registry source commit: `1581f3ffb78c5a77ce642759ee166c8902b16a6e`

---

# ADR-012: Separate completed tags, GitHub Releases, and registry channels

## Status

Accepted

## Date

2026-08-22

## Decision

Use three distinct publication concepts:

- a Git tag is the immutable source version;
- a GitHub Release is explicit approval for general release distribution and human-facing assets/notes;
- `dispatcharr-plugins` selects which immutable build each Dispatcharr channel advertises.

For this plugin:

- `dispatcharr-plugins:dev` advertises the newest approved tag, beta while testing is active and otherwise the latest completed stable tag;
- `dispatcharr-plugins:main` changes only after explicit user approval of a normal GitHub Release;
- Dispatcharr's update trigger requires a version increment, so moving a source branch without a new version is not a test publication;
- advertised tags and artifacts are immutable; corrections receive a new Semantic Version.

The historical `v0.1.0` tag and Release remain recorded. Future tags follow the new workflow.

## Reason

Testing needs reproducible version progression, while general release readiness is a separate decision. Treating every stable-looking tag as a public Release would collapse those approval boundaries; following a moving branch would not reliably trigger Dispatcharr updates.

## Alternatives considered

- Point the registry at `dev`. Rejected because branches move and Dispatcharr relies on version changes.
- Create a prerelease for every beta. Superseded for Dispatcharr plugins; beta tags go to the `dev` registry without a GitHub Release.
- Add every completed stable tag to the stable registry. Rejected because completion and general Release approval are distinct.

## Consequences

Version metadata must agree across `VERSION`, both plugin declarations, changelog, tag, Release, and registry. Registry `main` publication is always a focused metadata change, never a wholesale merge from the registry's `dev` branch.

## Provenance

- ChatGPT `Simplify Plugin Versioning`
- Workspace standalone release standard
- `dispatcharr-plugins` ADR-002 and ADR-003

---

# ADR-013: Revalidate the official Dispatcharr contract on version changes

## Status

Accepted

## Date

2026-08-22

## Decision

Whenever the supported, minimum, tested, or deployed Dispatcharr version changes, refresh the matching official Dispatcharr repository revision and revalidate both plugin behavior and registry requirements before tagging or publishing.

Record the version/tag, exact commit, URL, and review date. Recheck plugin manifest fields/actions, settings persistence, models and locks, native channel-stop APIs and Redis keys, archive extraction and plugin discovery, version comparison, minimum-version behavior, and installation/update behavior.

A change to `min_dispatcharr_version` or the live validation instance is a version change. Cached knowledge is not sufficient publication evidence.

## Reason

Dispatcharr owns every consumer-side API on which this plugin depends. A plugin can remain internally tested while becoming incompatible because model fields, Redis state, loader rules, or manifest handling changed upstream.

## Alternatives considered

- Validate only when a failure is reported. Rejected because an incompatible tag may already have reached installed systems.
- Trust the registry validator indefinitely. Rejected because it validates the recorded contract, not future Dispatcharr behavior.
- Review only `plugin.json`. Rejected because runtime orchestration also depends on Python models, services, Redis, and archive installation.

## Consequences

Compatibility changes may require synchronized updates to this repository, `dispatcharr-plugins`, tests, and documentation. Publication stops when the official matching revision cannot be verified.

## Provenance

- User direction in Codex `Update standalone release workflow`
- `dispatcharr-plugins` ADR-006
- Current recorded minimum and live validation baseline: Dispatcharr `v0.29.0`

---

# ADR-014: Do not infer a license for inherited wrapper code

## Status

Accepted; blocks new GitHub Releases and distributable ZIPs until resolved

## Date

2026-08-22

## Decision

The repository's MIT license applies to matrix2669-authored plugin code and documentation. It does not by itself grant permission for inherited `ffmpeg-smart.sh` code whose upstream source did not declare a license.

Preserve the historical fact that plugin `v0.1.0` was already tagged, released, and placed in the stable registry before this licensing review. Do not treat that past publication as permission for additional distribution.

Until the upstream copyright holder explicitly licenses the inherited wrapper:

- normal and beta tags may preserve internal version history and support the existing `dev` channel decision;
- do not create a new GitHub Release or attach a distributable plugin ZIP containing that wrapper;
- do not claim that adding an MIT file retroactively licenses the inherited material.

After upstream licensing is explicit, record the license and attribution, verify compatibility with the plugin's MIT terms, and publish only a new immutable version.

## Reason

Copyright permission cannot be inferred from public source availability, a fork, or the license selected for newly authored surrounding code. This plugin vendors the entire wrapper, so its distribution boundary includes the unresolved inherited material.

## Alternatives considered

- Assume the plugin MIT license covers every bundled file. Rejected because the plugin author cannot grant rights they may not own.
- Delete or rewrite historical Release records. Rejected because that would obscure what occurred and would not undo prior distribution.
- Keep publishing because v0.1.0 already exists. Rejected because a past mistake is not authorization for repetition.

## Consequences

Release preparation includes a licensing gate before packaging. Registry and documentation may continue to describe the existing v0.1.0 state accurately. A future source synchronization does not resolve licensing merely because it uses a matrix2669 commit.

## Provenance

- Related `ffmpeg-asr` ADR-015
- `ffmpeg-asr` licensing review and upstream MIT-license contribution attempt
- Existing plugin tag: `v0.1.0` at `1581f3f`

---

# ADR-015: Keep mutable runtime state outside the plugin install directory

## Status

Accepted

## Date

2026-08-22

## Decision

Store the capability cache, probe sample, benchmark lock, background PID, and benchmark log beneath `/data/ffmpeg_smart_profiles`, not beneath `/data/plugins/ffmpeg_smart_profiles`.

Managed profiles execute `ffmpeg-smart-plugin.sh`. This small plugin-owned launcher sets the persistent state directory, requires a valid prebuilt cache for normal stream requests, and then executes the vendored canonical wrapper. The plugin continues recognizing legacy profiles that point directly at `ffmpeg-smart.sh`, so **Install or Update Profiles** can migrate them.

When the cache is missing, unreadable, or stale for the current hardware or benchmark policy, the canonical wrapper exits before probing media with exit code 78 and one `[ffmpeg-smart] ERROR [capability-cache-...]` message that directs the operator to **Rebuild Hardware Cache**. Explicit recache commands remain allowed. Do not manufacture a malformed FFmpeg command merely to obtain an FFmpeg-branded error.

## Reason

Dispatcharr replaces the complete plugin install directory during an update. Cache and benchmark files stored there were therefore deleted even though they represented installation state rather than plugin code. An explicit wrapper error is more attributable and actionable than allowing the stream to fail later during probing or hardware initialization.

## Alternatives considered

- Keep state in the plugin directory and restore it after updates. Rejected because the old directory may already be gone before new plugin code runs.
- Automatically benchmark when a viewer starts a stream. Rejected because benchmarking is disruptive, stops active transcodes, and must remain an explicit confirmed action.
- Emit an intentionally invalid FFmpeg invocation. Rejected because it hides the real owner and can produce misleading diagnostics.

## Consequences

Plugin removal does not automatically delete persistent FFmpeg Smart state. Operators may remove `/data/ffmpeg_smart_profiles` manually after uninstalling when they no longer need it. The launcher and plugin status paths must remain aligned, and packaging tests must include the launcher. Existing installations should copy a still-available legacy cache into the persistent directory before their first update to this implementation or rebuild it afterward.

## Provenance

- Canonical wrapper: `ffmpeg-asr@37bd0a9b16748a28f2144981fe1f315c1f01aa8f`
- User-reported plugin update state loss on 2026-08-22

---

# ADR-016: Restart only for profile creation or removal

## Status

Accepted

## Date

2026-08-25

## Decision

**Install or Update Profiles** must distinguish the changes it actually applies:

- creating any managed profile returns `restart_required: true` and tells the operator to restart before using the newly added profile;
- updating existing managed profiles in place returns `restart_required: false` when no profile was created or removed and states that the update is available without a restart;
- removing a disabled or renamed managed profile during reconciliation returns `restart_required: true`, consistent with the dedicated removal action;
- an unchanged or conflict-only result does not request a restart.

The action confirmation must no longer imply that updates require a restart. It states that adding a profile requires a full restart and that updates work without one. **Remove Managed Profiles** keeps its existing restart confirmation and result behavior.

## Reason

Installed behavior established that Dispatcharr applies changes saved to an existing profile without reloading the application. Only adding a profile requires discovery during startup. Keeping the blanket warning made routine option changes look more disruptive than they are.

Removal remains restart-gated because deleting a profile can affect loaded profile state and channel assignments, and the 2026-08-25 operator correction addressed additions versus updates rather than removal semantics.

## Alternatives considered

- Keep requiring a restart after every update. Rejected because it contradicts observed update behavior and the operator requirement.
- Never request a restart from Install or Update. Rejected because newly created profiles are not usable until Dispatcharr restarts, and optional cleanup may also remove profiles.
- Restart Dispatcharr from the plugin. Rejected because the plugin remains intentionally unprivileged and has no host-control access.

## Consequences

The result payload is conditional on the created, updated, and removed lists. Tests must cover each state independently and mixed reconciliation results must remain restart-gated when they contain a creation or removal.

## Provenance

- Operator requirement review: 2026-08-25
- Supersedes: ADR-010 only for in-place update behavior

---

# ADR-017: Expose advanced FFmpeg options separately from wrapper policy

## Status

Accepted

## Date

2026-08-25

## Decision

Give each of the two Stream Profile slots and three Output Profile slots a separate Additional FFmpeg options string field. Keep the existing Additional options field exclusively for `ffmpeg-smart` wrapper policy.

Parse the FFmpeg field with Python `shlex.split` without shell evaluation. Generate one safely quoted `-ffmpeg-option <token>` pair for every parsed token, preserving order and values containing spaces or shell metacharacters. Invalid quoting blocks the enabled profile definition with an attributable validation error.

The canonical wrapper owns placement: advanced arguments follow its managed output settings and precede the fixed `-f mpegts pipe:1`. The plugin documents that advanced settings can override managed FFmpeg values and does not promise compatibility with the selected encoder or filters.

## Reason

The existing Additional options field configures the wrapper's stable policy surface. Mixing raw FFmpeg switches into that field would make ownership ambiguous and the wrapper previously ignored unknown flags. A separate field gives advanced operators an explicit escape hatch while retaining deterministic, injection-resistant argument handling.

## Alternatives considered

- Put raw FFmpeg switches into the existing Additional options field. Rejected because wrapper flags and downstream FFmpeg arguments have different owners and validation rules.
- Store one already-quoted shell fragment in the profile. Rejected because nested parsing would be ambiguous and could require unsafe evaluation.
- Add a checkbox or plugin field for every FFmpeg feature. Rejected because the FFmpeg option surface is large, encoder-specific, and evolves independently.

## Consequences

The Python field list and `plugin.json` settings must remain identical. Wrapper synchronization is mandatory before the plugin change can be considered complete, and tests must confirm exact generated token boundaries across the plugin-to-wrapper handoff.

## Provenance

- Operator requirement review: 2026-08-25
- Canonical decision: `ffmpeg-asr` ADR-017

---

# ADR-018: Expose phase-scoped advanced options without a custom FFmpeg mode

## Status

Accepted; supersedes ADR-017's single Additional FFmpeg output field

## Date

2026-08-25

## Decision

Keep every managed profile on the bundled FFmpeg Smart launcher. Do not expose a full custom/native FFmpeg command because it would bypass Smart's hardware discovery, device scheduling, adaptive video copy/transcode decision, selected encoder, and hardware filter construction.

Give each of the two Stream Profile slots and three Output Profile slots five scoped advanced groups that match canonical `ffmpeg-asr` ADR-018:

1. Input defaults: `inherit`, `add`, or `replace`, placed before `-i` but after Smart-owned user-agent, reconnect, and hardware input setup.
2. Stream mapping: `inherit`, `add`, `replace`, or `all`. Custom values use `-map <typed specifier>` pairs or bare typed specifiers. Add may add only non-video mappings because the inherited group already selects one video; Replace must contain exactly one positive video selector; runtime validation rejects selectors that resolve to multiple videos.
3. Video tuning defaults: `inherit`, `add`, or `replace`, used only on the video-transcode path and unable to replace the Smart-owned video encoder or filter graph.
4. Audio defaults: `inherit`, `add`, or `replace`, used on both video-copy and video-transcode paths. Replace is an explicit expert choice to bypass normal AAC/copy selection.
5. MPEG-TS/output defaults: `inherit`, `add`, or `replace`, used on both paths before Smart's fixed `-f mpegts pipe:1` output.

Parse every options field with `shlex.split` and emit one independently quoted repeatable wrapper argument per token. Reject invalid quoting and wrapper-owned structural tokens before profile reconciliation. An options value with the default `inherit` mode behaves as `add` so saved settings remain useful.

Retain the existing beta.3 `*_ffmpeg_options` field IDs as the MPEG-TS/output text fields and add `*_ffmpeg_options_mode`. This carries saved beta.3 values forward as additive mux options. New scopes use distinct IDs.

Explicit wrapper policy remains authoritative after expert settings: `-maxbr` stays a hard bitrate ceiling and `-maxchan` stays a hard channel ceiling. The plugin does not promise that other advanced options are supported by every FFmpeg build or selected encoder.

## Reason

FFmpeg option placement is phase-sensitive. A single final-output field cannot safely express pre-input flags, mapping replacement, transcode-only encoder tuning, or audio behavior on both copy and transcode paths. Matching the canonical wrapper's scoped model makes the effective ownership predictable without discarding its hardware-aware purpose.

## Alternatives considered

- Expose the complete Discord command as a custom profile. Rejected because its `-c:v copy` and native command structure bypass Smart's hardware-aware path.
- Make the entire generated FFmpeg command editable as one default. Rejected because the encoder, devices, filters, and copy/transcode choice are resolved dynamically per stream and deployment.
- Keep only the beta.3 final-output field. Superseded because it cannot place several common advanced switches correctly and did not apply on the video-copy path.
- Add a dedicated field for every FFmpeg switch. Rejected because the option surface is build- and encoder-specific and changes independently.

## Consequences

`Plugin.fields` and `plugin.json` must remain exact mirrors. Tests must cover the complete five-slot schema, mode migration, quoting and metacharacter boundaries, generated order, empty replacement groups, mapping constraints, structural rejection, copy/transcode placement in the pinned canonical wrapper, and update-without-restart behavior.

The existing restart decision remains unchanged: creating or removing profiles requires restart feedback, while updating existing profiles does not.

## Provenance

- Operator advanced-options review: 2026-08-25
- Canonical wrapper: `ffmpeg-asr` ADR-018 and `v1.1.0-beta.3`
- Supersedes: plugin ADR-017

---

# ADR-019: Display inherited defaults without mutating expert option fields

## Status

Accepted

## Date

2026-08-25

## Decision

Show the inherited value or exact runtime-derived formula in the help text beneath every advanced mode dropdown for all five managed profile slots. The displayed contracts are:

1. Input: `-fflags +genpts+igndts+discardcorrupt -err_detect ignore_err`.
2. Mapping: `-map 0:v:0 -map 0:a:0?`.
3. Video transcode tuning: `-b:v <target> -maxrate <rate> -bufsize <buffer> -g <rounded source fps> -bf <0 or 2> <accelerator tuning> -fps_mode cfr -r <source fps> [-tag:v hvc1]`. The target starts at 8 Mbps for 1920x1080, scales by output pixel count, and has a 2 Mbps floor. Without `-maxbr`, maxrate is 125 percent and buffer is 200 percent of target. With `-maxbr`, target is capped at 85 percent of the limit, maxrate equals the limit, and buffer is twice the limit. B-frame and accelerator arguments remain hardware-derived.
4. Audio: no arguments when audio is absent; compatible AAC uses `-c:a copy`; other audio uses AAC with asynchronous resampling and 96 kbps mono, 192 kbps stereo, 384 kbps 5.1, 512 kbps 7.1, or 64 kbps per channel for other layouts. An explicit `-maxchan` ceiling remains authoritative.
5. MPEG-TS/output: `-avoid_negative_ts make_zero -start_at_zero -mpegts_copyts 0 -mpegts_flags +pat_pmt_at_frames+resend_headers -flush_packets 1 -max_muxing_queue_size 4096`, followed by Smart-owned `-f mpegts pipe:1`.

Keep adjacent options fields blank by default and use them only for user-owned Add/Replace text. Do not prefill them with managed values. As of the reviewed Dispatcharr plugin form, each field receives only its own `onChange` callback and the manifest schema has no dependency or computed-value hook, so a mode selection cannot safely repopulate a sibling input. Prefilling would also turn managed defaults into saved user data, duplicate additive flags, risk stale video/audio values, and overwrite custom text when toggling modes.

Revisit this presentation if Dispatcharr adds an official dependent-field or computed-placeholder contract that can preserve saved custom values. Until then, mode help text is the authoritative in-UI default reference and the README mirrors it.

## Reason

Inherit, Add, and Replace are not understandable unless the user can see what Inherit supplies and what Replace removes. Static input, mapping, and mux values can be shown exactly. Video and audio must be described as formulas because their concrete arguments depend on the source stream, profile limits, and selected accelerator at runtime.

## Alternatives considered

- Populate the options field when the mode dropdown changes. Rejected because the current Dispatcharr plugin field API has no cross-field change hook.
- Set the options field's manifest default to the managed arguments. Rejected because backend default merging would make managed values indistinguishable from user input and could duplicate them in Add mode.
- Show only examples. Rejected because an example does not identify the actual inherited contract.

## Consequences

The Python and JSON field schemas must contain identical default help text. Tests must cover all five scopes across all five profile slots. Wrapper-default changes require synchronized UI help, README documentation, decision text, and regression expectations in a new plugin version.

## Provenance

- Operator defaults-visibility correction: 2026-08-25
- Dispatcharr `frontend/src/components/Field.jsx` and plugin settings schema reviewed 2026-08-25
- Canonical wrapper defaults: pinned `ffmpeg-asr v1.1.0-beta.3`

---

# ADR-020: Repair installed script modes and surface authoritative cache maintenance

## Status

Accepted

## Date

2026-08-26

## Decision

Keep managed Stream and Output Profiles executing `ffmpeg-smart-plugin.sh` directly. On every enabled plugin load, idempotently restore the execute bits on both bundled shell scripts before Dispatcharr can use managed profiles. Repeat the repair before plugin-owned profile reconciliation and cache rebuild actions. Do not change generated profile commands to `/bin/bash` as a permanent workaround.

Use canonical `ffmpeg-asr --cache-status` as the sole cache-validity authority. **Benchmark Status** reports `complete` only when that command returns `valid`; missing, invalid, stale, inconsistent, or unavailable validation reports `error` and instructs the operator to run **Rebuild Hardware Cache**. A running rebuild remains `running`. Parsed capabilities from a non-valid cache may be shown only as previous, unusable details.

Create one persistent, admin-only Dispatcharr `SystemNotification` with notification key `ffmpeg-smart-hardware-cache`:

- a missing, invalid, stale, or unverifiable cache creates or updates a high-priority **FFmpeg Smart hardware scan required** warning;
- an active plugin-started rebuild changes it to **FFmpeg Smart hardware scan in progress**;
- successful post-rebuild validation deletes the notification and sends Dispatcharr's dismissal update so it leaves the notification center;
- the fixed unresolved-condition key prevents duplicates, while deletion after recovery also deletes old dismissals so a future hardware change can create a visible warning again.

The WebSocket update is only an immediate UI refresh. The database-backed `SystemNotification` is the durable notice, matching Dispatcharr's account-expiration notification mechanism.

Keep the wrapper's benchmark lock refusal and exit status `75`. The live Dispatcharr `v0.29.0` request path has no veto-capable pre-stream plugin hook and treats this intentional maintenance exit as an ordinary source failure, including retries, alternate-stream cycling, and `channel_error` events. The persistent in-progress notification makes the maintenance cause visible but does not claim to change that routing behavior. Clean non-retryable maintenance handling with HTTP 503/Retry-After semantics requires a separately reviewed Dispatcharr core contract; do not emulate it by disabling profiles, emitting placeholder media, or holding arbitrary viewer processes open.

## Reason

Dispatcharr's ZIP installer writes every member to a newly opened file and does not restore archive mode bits. A reinstall therefore changed the bundled scripts from executable to data files even though the Git tree and ZIP recorded `0755`. Registry installation immediately force-reloads enabled plugins, giving the plugin a reliable point to repair its own files before direct profile execution.

The same incident exposed a second ownership error: file existence was presented as a healthy cache although the wrapper rejected its hardware fingerprint. A persistent native warning is required because an operator should not need to discover the rebuild requirement from an invisible stream-process error.

## Alternatives considered

- Run every managed profile through `/bin/bash`. Rejected as a long-term workaround because it hides incorrect installation state and changes the generated command contract.
- Depend only on ZIP executable metadata. Rejected because Dispatcharr `v0.29.0` discards it during extraction.
- Infer validity by parsing the cache in Python. Rejected because hardware fingerprinting belongs to canonical `ffmpeg-asr` ADR-019.
- Use a one-time toast. Rejected because the warning must persist and be dismissible in Dispatcharr's normal notification center.
- Wait behind the benchmark lock or synthesize a maintenance MPEG-TS stream. Rejected because Dispatcharr timeouts, client lifecycle, and benchmark isolation make those behaviors misleading and fragile.

## Consequences

The plugin must be enabled for its load-time repair and notifications to run; managed profiles are supported only while their owning plugin is enabled. Packaging validation must simulate a `0644` extraction, import the installed plugin, verify both scripts become `0755`, and execute the launcher directly. Cache-status tests must cover valid and every non-valid state. Notification tests must cover required, running, deduplication, dismissal reset, and automatic removal after successful validation.

Until Dispatcharr adds non-retryable maintenance handling, benchmark-time viewer requests can still produce retry/failover and reliability events. Publication notes must not describe the plugin notification as a request-routing block.

## Provenance

- Operator reports: stripped executable bits, stale-cache false health, and a viewer start during a hardware scan, 2026-08-26
- Live Dispatcharr `v0.29.0` evidence: scan PID `10972` began at `19:12:05Z`; a new viewer requested a managed channel at `19:12:29Z`; the benchmark lock caused rapid retries and alternate-stream cycling until the scan completed
- Canonical decision: `ffmpeg-asr` ADR-019
