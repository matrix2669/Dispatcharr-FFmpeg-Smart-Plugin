# Release Process

## Version rules

- Use Semantic Versioning in root `VERSION`, `Plugin.version`, and `ffmpeg-smart-profiles/plugin.json`.
- Prefix Git tags with `v`; store versions without `v` in files.
- Use `MAJOR.MINOR.PATCH-beta.N` for test tags and increment `N` for every published beta of the same target version.
- Use a normal `MAJOR.MINOR.PATCH` tag when feature or fix work is completed.
- Never move a published tag, replace an advertised archive, or mutate an existing Release. Corrections receive a new version.
- A wrapper change always requires a new plugin version before registry publication, even if no Python code changed.

## Required validation

Run the complete automated gate from `AGENT.md`, including tests, compilation, JSON checks, shell syntax, and offline source-pin verification. With network access, verify the pinned bytes against the immutable `ffmpeg-asr` commit.

Also verify, as applicable:

- the synchronization command is idempotent against the intended canonical ref;
- plugin discovery and generated profile defaults in the supported Dispatcharr version;
- profile installation/update/removal conflict and restart behavior;
- a real Output Profile through `pipe:0` when the wrapper changed;
- recache maintenance coordination when plugin orchestration changed;
- the exact tag archive contains `ffmpeg-smart-profiles/plugin.json`, `plugin.py`, executable `ffmpeg-smart.sh`, and `FFMPEG_SMART_SOURCE.json` beneath the stable plugin directory;
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

## GitHub Release and stable registry

New Releases and distributable ZIPs are currently blocked by the inherited-wrapper licensing decision in `DECISIONS.md`. The existing v0.1.0 Release is historical and does not waive this gate.

After licensing is explicitly resolved:

1. Record the license source, copyright holder authorization, attribution, and compatibility decision.
2. Obtain explicit user approval to publish this exact stable tag as a GitHub Release.
3. Build `dispatcharr-ffmpeg-smart-plugin-vMAJOR.MINOR.PATCH.zip` with this layout:

   ```text
   ffmpeg-smart-profiles/
   ├── FFMPEG_SMART_SOURCE.json
   ├── ffmpeg-smart.sh
   ├── plugin.json
   └── plugin.py
   ```

4. Produce a SHA-256 checksum and validate installation from a clean extraction.
5. Publish a normal GitHub Release from the existing immutable tag with release notes, the ZIP, and its checksum.
6. Make a focused `dispatcharr-plugins:main` update referencing the exact released tag, commit, version, minimum Dispatcharr version, and verified archive.
7. Validate a clean install and an update through the stable registry.

GitHub's automatic source archives do not replace the documented manual ZIP for users who install without the registry. The registry may continue using its verified immutable tag archive when that matches Dispatcharr's installation contract.
