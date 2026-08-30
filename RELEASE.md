# Release Process

## Version rules

- Use Semantic Versioning in root `VERSION`, `Plugin.version`, and `ffmpeg-smart-profiles/plugin.json`.
- Prefix Git tags with `v`; store versions without `v` in files.
- Use `MAJOR.MINOR.PATCH-beta.N` for test tags and increment `N` for every published beta of the same target version.
- Use a normal `MAJOR.MINOR.PATCH` tag when feature or fix work is completed.
- Never move a published tag, replace an advertised archive, or mutate an existing Release. Corrections receive a new version.
- A wrapper change always requires a new plugin version before registry publication, even if no Python code changed.

## Required validation

Run the complete automated gate from `AGENT.md`, including tests, compilation, JSON checks, shell syntax, and offline source-pin verification. With network access, verify every pinned runtime file against the immutable `ffmpeg-adaptive` commit.

Also verify, as applicable:

- the synchronization command is idempotent against the intended canonical ref;
- plugin discovery and generated profile defaults in the supported Dispatcharr version;
- profile installation/update/removal conflict and restart behavior;
- a real Output Profile through `pipe:0` when the wrapper changed;
- recache maintenance coordination when plugin orchestration changed;
- the exact tag archive contains `ffmpeg-smart-profiles/plugin.json`, `plugin.py`, executable `ffmpeg-smart.sh`, every pinned `lib/*.sh` module with its recorded mode, `FFMPEG_SMART_SOURCE.json`, and `FFMPEG_ADAPTIVE_LICENSE` beneath the stable plugin directory;
- the registry metadata references the exact tag and full commit.

If the supported, minimum, tested, or deployed Dispatcharr version changed, complete the official-repository compatibility refresh gate in `AGENT.md` before continuing.

## Beta tag and testing channel

1. Integrate the intended work into `dev` and complete required validation.
2. Set the beta version consistently in `VERSION`, `Plugin.version`, and `plugin.json`.
3. Finalize the matching changelog section for the test build.
4. Commit the exact tested state on `dev` and create the immutable `vMAJOR.MINOR.PATCH-beta.N` tag.
5. Push the tag without creating a GitHub prerelease.
6. Update only `dispatcharr-plugins:dev` to the exact tag, commit, version, and archive URL.
7. Validate an actual Dispatcharr update from the previous advertised version.

Untagged `dev` commits are development state and do not replace a published test build because Dispatcharr update detection is version-driven.

## Completed stable tag

1. Confirm feature/fix work and its test cycle are complete on `dev`.
2. Replace the beta version with the final `MAJOR.MINOR.PATCH` consistently in every version source.
3. Promote the exact tested state to `main` without unrelated changes.
4. Run the complete release validation again on `main`.
5. Create and push the immutable normal tag `vMAJOR.MINOR.PATCH`.
6. Point `dispatcharr-plugins:dev` at this latest completed tag if it is the newest approved build.
7. Synchronize `dev` with the completed stable state before the next cycle.

A completed stable tag does not automatically authorize a GitHub Release or `dispatcharr-plugins:main` publication.

Historical exception: the user explicitly approved plugin `v0.2.0` for focused `dispatcharr-plugins:main` publication without a GitHub Release on `2026-08-26`, while continuing to prohibit a Release and distributable ZIP for that inherited-wrapper build. This exception remains limited to the exact immutable `v0.2.0` tag/archive and commit and cannot authorize a correction or later version.

## GitHub Release and stable registry

New versions bundling the pinned MIT-licensed `ffmpeg-adaptive` runtime may proceed through the normal Release gate below. Historical tags that bundled inherited `ffmpeg-asr` source retain their original provenance and must not be repackaged under this permission.

1. Verify the exact tag bundles only the recorded MIT `ffmpeg-adaptive` files and preserves `FFMPEG_ADAPTIVE_LICENSE`.
2. Obtain explicit user approval to publish this exact stable tag as a GitHub Release.
3. Build `dispatcharr-ffmpeg-smart-plugin-vMAJOR.MINOR.PATCH.zip` with this layout:

   ```text
   ffmpeg-smart-profiles/
   ├── FFMPEG_ADAPTIVE_LICENSE
   ├── FFMPEG_SMART_SOURCE.json
   ├── ffmpeg-smart-plugin.sh
   ├── ffmpeg-smart.sh
   ├── lib/
   │   ├── ffsmart-cache.sh
   │   ├── ffsmart-cli.sh
   │   ├── ffsmart-common.sh
   │   ├── ffsmart-hardware.sh
   │   ├── ffsmart-policy.sh
   │   └── ffsmart-probe.sh
   ├── plugin.json
   └── plugin.py
   ```

4. Produce a SHA-256 checksum and validate installation from a clean extraction.
5. Publish a normal GitHub Release from the existing immutable tag with release notes, the ZIP, and its checksum.
6. Make a focused `dispatcharr-plugins:main` update referencing the exact released tag, commit, version, minimum Dispatcharr version, and verified archive.
7. Validate a clean install and an update through the stable registry.

GitHub's automatic source archives do not replace the documented manual ZIP for users who install without the registry. The registry may continue using its verified immutable tag archive when that matches Dispatcharr's installation contract.
