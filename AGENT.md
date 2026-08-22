# AGENT.md

## Purpose

This repository owns the `FFmpeg Smart Profiles` plugin for Dispatcharr. The plugin installs and reconciles managed Stream and Output Profiles, coordinates disruptive hardware-cache rebuilds, reports benchmark status, and ships a self-contained copy of the canonical `matrix2669/ffmpeg-asr` wrapper.

## Architecture

- `ffmpeg-smart-profiles/plugin.json` declares Dispatcharr settings and actions.
- `ffmpeg-smart-profiles/plugin.py` is the Dispatcharr integration layer. It owns profile definitions, settings migration, safe database reconciliation, active-transcode coordination, benchmark lifecycle, and status reporting.
- `ffmpeg-smart-profiles/ffmpeg-smart.sh` is a vendored runtime dependency. Its canonical source is `matrix2669/ffmpeg-asr`; do not develop wrapper behavior independently in this repository.
- `ffmpeg-smart-profiles/FFMPEG_SMART_SOURCE.json` pins the wrapper's full source commit and SHA-256 checksum.
- `scripts/check-ffmpeg-smart-source.sh` verifies the local checksum and, unless `--offline` is used, the exact remote source bytes.
- `scripts/sync-ffmpeg-smart.sh` resolves a branch, tag, or full commit, replaces the vendored wrapper, and updates the pin.
- `.github/workflows/ffmpeg-smart-sync.yml` checks the canonical source and opens a reviewable update pull request.
- `.github/workflows/ffmpeg-smart-verify.yml` validates the source pin, plugin tests, JSON, Python, and shell syntax.
- `tests/test_plugin.py` covers behavior that can be isolated from Dispatcharr.
- `tests/validate_dispatcharr.py` validates the exact installed plugin layout and generated defaults inside Dispatcharr.

Data flow:

1. Dispatcharr loads `plugin.json` and `plugin.py` from the stable `ffmpeg-smart-profiles/` directory.
2. **Install or Update Profiles** converts saved settings into two possible Stream Profile slots and three possible Output Profile slots.
3. Stream Profiles pass `{streamUrl}` and `{userAgent}` to the wrapper. Output Profiles pass Dispatcharr's non-seekable MPEG-TS input as `pipe:0`.
4. The wrapper resolves stream policy, capabilities, and GPU scheduling, then returns MPEG-TS on standard output.
5. **Rebuild Hardware Cache** creates the shared benchmark lock, stops active Dispatcharr transcodes, and launches `ffmpeg-smart.sh --recache-only` in the background.
6. **Benchmark Status** reads the background PID, log, and capability cache without starting new work.

## Ownership boundaries

- This repository owns Dispatcharr integration, profile policy defaults, settings UX, maintenance orchestration, packaging, and plugin releases.
- `matrix2669/ffmpeg-asr` owns all wrapper behavior, hardware discovery, stream policy resolution, benchmarking, cache schema, and GPU scheduling.
- `matrix2669/dispatcharr-plugins` owns only which immutable plugin tag each `dev` or `main` registry channel advertises.
- The official Dispatcharr repository owns the plugin API, manifest contract, models, Redis keys, loader behavior, archive extraction, and minimum-version semantics.

## Non-negotiable rules

- Keep the plugin self-contained; the installed archive must include `ffmpeg-smart.sh` and must not depend on a Git submodule or a second repository checkout.
- Never edit the vendored wrapper as an independent implementation. Change and validate `ffmpeg-asr` first, publish its canonical commit, then synchronize this repository through the pin workflow.
- Never silently update an existing tag, Release, archive, or installed plugin version. Wrapper changes require a new plugin version before registry publication.
- Profile installation must remain idempotent and transactional. Do not overwrite locked profiles, duplicate names, or same-name profiles owned by another command.
- Keep policy normalization plugin-only. Do not require a Dispatcharr core change to migrate `-10bit`, `-hdr`, `-sdr`, `-deint`, or `-deinterlace` from Additional options into checkboxes.
- Force SDR takes precedence over Allow HDR. Generate each managed policy flag at most once.
- All managed Output Profiles must use the pipe-safe wrapper path. Do not replace them with bare `ffmpeg` templates.
- Hardware benchmarking may stop input- or output-transcoded streams, but proxy-only streams must continue. New FFmpeg Smart transcodes remain blocked until the benchmark lock clears.
- Do not give the plugin Docker-socket or host-control access merely to restart Dispatcharr. Profile changes return `restart_required` and instruct the operator to restart normally.
- Recorded GPU capacities are deployment evidence, not portable defaults. Re-measure on materially different hardware or benchmark policy.
- Preserve the current licensing boundary described in `DECISIONS.md`: the repository's MIT license covers matrix2669-authored plugin work, but it does not independently license inherited wrapper code. Do not publish a new GitHub Release or distributable plugin ZIP until the wrapper's inherited licensing is resolved.

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

## Version and distribution requirements

- `VERSION`, `Plugin.version`, `plugin.json`, the changelog version, and the Git tag must agree.
- Dispatcharr updates are version-driven. Untagged branch movement does not replace a published test build.
- `dispatcharr-plugins:dev` advertises the newest approved immutable plugin tag: a beta during testing, otherwise the latest completed stable tag.
- `dispatcharr-plugins:main` advertises only a stable version with an explicitly approved GitHub Release.
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
bash -n scripts/check-ffmpeg-smart-source.sh
bash -n scripts/sync-ffmpeg-smart.sh
scripts/check-ffmpeg-smart-source.sh --offline
```

When network access is available, also run `scripts/check-ffmpeg-smart-source.sh` against the immutable remote source. A wrapper synchronization must be idempotent when repeated against the same source ref.

Behavioral or compatibility changes additionally require applicable live Dispatcharr checks:

- native plugin discovery from the packaged directory;
- create/update/remove idempotence and conflict behavior;
- settings normalization persistence;
- a full restart after profile changes;
- a real `pipe:0` Output Profile test confirming the opening sample is preserved;
- benchmark interruption of transcodes while proxy-only streams continue;
- blocking of new wrapper transcodes while the lock exists;
- background completion, stale-PID handling, and capability status readback;
- tag archive and manual ZIP layout from a clean extraction.

## Future-agent checklist

- [ ] Read `AGENT.md`, `DECISIONS.md`, `BRANCHES.md`, `CHANGELOG.md`, and `RELEASE.md`
- [ ] Review all relevant project history and the current `ffmpeg-asr` source pin
- [ ] Confirm the branch base, intended target, and registry channel
- [ ] Refresh the branch ledger before substantive work
- [ ] Keep plugin integration changes separate from canonical wrapper changes
- [ ] If any Dispatcharr version changed, complete and record the compatibility refresh gate
- [ ] Run proportionate automated and live validation
- [ ] Verify version agreement and immutable archive layout before tagging
- [ ] Verify explicit Release approval before changing `dispatcharr-plugins:main`
