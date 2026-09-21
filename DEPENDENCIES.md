# Dependencies

## Canonical FFmpeg Adaptive runtime

- Repository: `matrix2669/ffmpeg-adaptive`
- Current recorded source: immutable work-branch commit
  `913a958fd5f9edc231c49a70539a09f611fdcc5a`, the accepted wrapper beta.4
  candidate before its future tag is published.
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
  idempotence checks. Final Astra review, future wrapper/plugin tag, dev
  registry publication, and live beta.5 validation remain pending.

## Dispatcharr

- Integration contract: plugin discovery, `Plugin.version`, settings/actions,
  profile models, active-channel stop service, Redis transcode markers, and
  archive installation are owned by Dispatcharr.
- Recorded minimum: `v0.29.0`; the beta.5 live compatibility validation has
  not been rerun in this branch.
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
- The read-only viewer/transcode snapshot was zero, but must be repeated before
  disruptive work. Live beta.5 install, managed update, and benchmark remain
  pending Astra review and the approved zero-viewer gate; this branch claims no
  live install, stream, or benchmark result.
- Any minimum-version or live deployment change requires the compatibility
  refresh gate in `AGENT.md` before tagging or publication.
