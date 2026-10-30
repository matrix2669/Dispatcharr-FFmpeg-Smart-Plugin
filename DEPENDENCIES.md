# Dependencies

## Canonical FFmpeg Adaptive runtime

- Beta.3 feature candidate pins `matrix2669/ffmpeg-adaptive` commit
  `137103b0b5d2ed2f21976c65be2cd5bc816dbdb6`, runtime 0.1.0, via the official
  synchronization workflow. Eight files (entrypoint, six shell modules and the
  Python shared-input helper) remain byte/mode-pinned with the MIT notice.
- `--copy-codecs preferred` resolves the validated current H.264/HEVC cache
  preference dynamically. Named lists normalize case/token whitespace and accept
  public `mpeg2` plus legacy `mpeg2video`. Explicit `-vc` remains highest priority;
  processing constraints can force conversion using the cached encoder.
- Canonical Auto now preserves legacy acquisition when any nonempty case variant
  of HTTP/HTTPS/ALL/FTP/SOCKS proxy configuration exists, in addition to existing
  custom-input, HLS/opaque URL, protocol and Python gates. No body is acquired to
  decide. Explicit standalone Off/Strict and advanced fallback CLI remain valid.
- The plugin removes dedicated conversion/shared-input tuning controls and uses
  internal conservative Auto only for HTTP(S). Its fixed payload/startup bounds
  are 64 MiB / 10 seconds, with an independent internal 30-second network guard.
  These are not inherited Dispatcharr settings. Owned broker clients retain
  proxy isolation; legacy jobs keep their transport environment.
- Python 3.9+, POSIX process groups and private IPv4 loopback remain required only
  for selected shared input. Unsupported acquisition retains legacy semantics;
  no media reconnect or disk spool is introduced.
- Full canonical local validation passed, including both cache preferences,
  preferred/list/alias validation, cache admission/degraded policy, explicit
  codec/filter precedence, proxy-aware Auto and all 14 shared-input methods.
  Bounded cancellation fixtures cover probing and playback under 10/30-second
  guards, without a general live-failover claim. Exact canonical CI
  [41090068901](https://github.com/matrix2669/ffmpeg-adaptive/actions/runs/41090068901)
  passed at `137103b0b5d2ed2f21976c65be2cd5bc816dbdb6`. Final plugin CI,
  independent review and installation/playback acceptance remain separate gates.
- Repeated sync and offline/online source checks must cover every file and mode.
  The published beta.2 plugin at `3b7f554c0aac64391768e4920178cacd6a15da8c`
  retains canonical `8156f96ce44c2ca0cb0360a8503f7862285b9f23`; its tag/archive
  are immutable and are not replaced by beta.3 feature work.
- Runtime/cache schema, version and fingerprint inputs remain unchanged. Continue
  using canonical `--cache-status` rather than forging fingerprints or assuming
  capability evidence transfers between machines.

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

## 2026-10-20 stable compatibility refresh

Official Dispatcharr v0.32.0 at c52bf87acb7ff2d787d6dcfb9fe3d39999585912 was
compared with the v0.31.0 baseline. Eleven selected live application source
hashes matched official 0.32.0. No affected contract incompatibility was found;
minimum v0.29.0 is unchanged. See docs/stable-compatibility-2026-10-20.md.
The plugin's runtime source pin remains 913a958fd5f9edc231c49a70539a09f611fdcc5a,
independent of the standalone adaptive 0.1.0 release.

## 2026-10-30 Dispatcharr 0.33.0 compatibility evidence

The parent coordinator compared official `Dispatcharr/Dispatcharr` commit
`2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e` (version 0.33.0) against deployed
files: loader, plugin API views, serializers/models, core models, channel models
and live-proxy Redis keys matched their exact SHA-256 values. It reviewed atomic
installer swap/discovery and settings/action/default-profile contracts. The
legacy `apps/proxy/ts_proxy/channel_manager.py` path was absent upstream and is
not claimed as verified. Minimum Dispatcharr 0.29.0 remains unchanged.
See `docs/shared-input-compatibility-2026-10-30.md` for the evidence boundary.
Plugin candidate native installation, profile reconciliation and actual provider
streams are pending parent-owned validation; no deployment is claimed here.

## Beta.3 settings/timing compatibility

Official Dispatcharr 0.33.0 at `2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e`
`frontend/src/components/Field.jsx` supports string/select/boolean/number fields
but no multiselect. The user selected a blank-default string field, avoiding core
changes or a checkbox substitute. Existing source hashes/minimum-version evidence
remain applicable to that field contract; minimum 0.29.0 is unchanged.
The official input manager's startup-no-data switch can use 8 seconds while
alternatives exist and disables that short clock when alternatives are exhausted.
The wrapper's independent watchdog and network guard are not configuration
inheritance, and no live settings or forced database query is used in this task.
