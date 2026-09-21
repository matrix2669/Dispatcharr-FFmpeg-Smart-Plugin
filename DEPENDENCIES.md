# Dependencies

## Canonical FFmpeg Adaptive runtime

- Repository: `matrix2669/ffmpeg-adaptive`
- Current recorded source: immutable work-branch commit
  `913a958fd5f9edc231c49a70539a09f611fdcc5a`, published as wrapper beta.4.
- Contract: the seven bundled runtime files are byte- and mode-pinned in
  `ffmpeg-smart-profiles/FFMPEG_SMART_SOURCE.json`; the MIT notice is shipped
  in `FFMPEG_ADAPTIVE_LICENSE`. Wrapper behavior remains owned by the canonical
  repository and is not repaired in this plugin branch.
- Synchronization: `scripts/sync-ffmpeg-smart.sh` requires an explicit ref when
  the recorded tracking ref would otherwise resolve to a different commit,
  updates the selected ref and commit together only after all files verify, and
  must be followed by the complete source check.
- The complete seven-file bundle is now synchronized to that exact commit and
  passes the online source verification and repeated unqualified-sync
  idempotence checks. Astra final review passed. Plugin tag, wrapper tag, and
  development-registry publication are immutable and passed their CI gates;
  managed update and bounded hardware validation passed.

## Plugin distribution and live state

- Plugin release: `v0.2.1-beta.5` at
  `a5c0777875056591e4e02c989993f43b3f43aa72`.
- Development registry: root/detail publication commit
  `1e55f15ba3824f85209258b6b0dd3280c554924d`; CI passed.
- Exact beta.5 tag archive SHA-256:
  `db31ce469ea52433af24cf4568463a782fced202124cdf3440c854fcf9754836`;
  native installer validation passed for
  `https://api.github.com/repos/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/zipball/v0.2.1-beta.5`.
- Official Dispatcharr v0.31.0 update installed beta.5 with no update offered,
  preserved enabled/settings state, and retained prerelease semantics. The
  benchmark started at `2026-09-21 17:45:40 UTC` with zero viewers and no
  other media, stopped zero streams, and completed at
  `2026-09-21T17:51:16.719376+00:00` with return code 0, complete outcome,
  valid cache, no PID, and no lock. VAAPI/HEVC 10-bit decode and encode were
  available; `renderD129` measured capacity 19 at 14x and `renderD128` 14 at
  11.6x. The consolidated log was 1,508,339 bytes with no stray root
  candidate/capacity/10-bit logs or `.benchmark-run` directories.
  A bounded real-hardware managed-launcher fixture generated four seconds of
  H.264, fed it via `pipe:0`, and produced a 4.025-second 720p HEVC VAAPI
  output; it decoded 120 frames with `-xerror` and no errors. It did not fetch
  a provider channel or create a Dispatcharr profile. The final `17:52:25 UTC` snapshot had zero viewers, transcodes, and
  ffmpeg/ffprobe processes, with runtime and manifest pins unchanged.

## Dispatcharr

- Integration contract: plugin discovery, `Plugin.version`, settings/actions,
  profile models, active-channel stop service, Redis transcode markers, and
  archive installation are owned by Dispatcharr.
- Recorded minimum: `v0.29.0`; official v0.31.0 compatibility and the beta.5
  managed update were reviewed and passed as described below.
- Compatibility review: official `Dispatcharr/Dispatcharr` tag `v0.31.0`,
  commit `bcbb68c4f054ee56383a41604cfcd7302b85da66`
  ([tag](https://github.com/Dispatcharr/Dispatcharr/tree/v0.31.0),
  [commit](https://github.com/Dispatcharr/Dispatcharr/commit/bcbb68c4f054ee56383a41604cfcd7302b85da66)).
  The fetched official files and the read-only live container hashes matched:
  `apps/plugins/loader.py` SHA-256
  `5b76ecc9335dcb4429bf729d9dd2c2dba65a2871874e2989c9cac531e1634a56`,
  `apps/plugins/api_views.py` SHA-256
  `a4249bd4669416e9b551ee1db94b941323757a906c11a17b84a64cad1f61f192`, and
  `apps/plugins/serializers.py` SHA-256
  `1623b004a80cb943070cbffde0da9e43f3439b2fe69bd1b9faebf2419b1b7326`.
  The review confirmed `Plugin.version` is authoritative after force reload,
  managed updates preserve enabled/settings, action/context/settings and
  Stream/Output model contracts remain compatible, native `stop_channels`
  remains available, and Redis transcode/viewer keys are unchanged. No
  minimum-version bump is required.
- The pre-update viewer/transcode snapshot was zero and the approved
  zero-viewer managed update passed. The final post-validation snapshot was
  also zero viewers/transcodes with no ffmpeg or ffprobe process; no provider
  channel was fetched and no Dispatcharr profile was created for the bounded
  fixture proof.
- Any minimum-version or live deployment change requires the compatibility
  refresh gate in `AGENT.md` before tagging or publication.
