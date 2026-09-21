# FFmpeg Smart beta.5 validation — 2026-09-21

Status: immutable release, managed update, benchmark, and bounded hardware
fixture validation passed. This record does not claim provider-channel fetch or
Dispatcharr profile-creation validation.

## Immutable artifacts

- Plugin tag: `v0.2.1-beta.5` at
  `a5c0777875056591e4e02c989993f43b3f43aa72`.
- Wrapper beta.4: `913a958fd5f9edc231c49a70539a09f611fdcc5a`.
- Plugin CI: tag workflow `35631993818` and development workflow `35631991578`
  passed.
- Wrapper CI: original workflows `35631984969` and `35631983498` were false
  positives caused by ShellCheck 0.9; reviewed CI-only definition
  `10a6e4b8e16b66857df3b03a7bb6d0bb88fc9929`, run `35633440274`, passed the
  exact `913a958` source with the full suite under ShellCheck 0.11.
- Development registry publication: commit
  `1e55f15ba3824f85209258b6b0dd3280c554924d`, CI `35633913052` passed for the
  root/detail manifests.
- Exact plugin tag ZIP:
  `https://api.github.com/repos/matrix2669/Dispatcharr-FFmpeg-Smart-Plugin/zipball/v0.2.1-beta.5`
  SHA-256 `db31ce469ea52433af24cf4568463a782fced202124cdf3440c854fcf9754836`;
  native installer validation passed. All seven bundled runtime hashes match
  the immutable source manifest.

## Dispatcharr compatibility and managed update

- Official Dispatcharr `v0.31.0`, commit
  `bcbb68c4f054ee56383a41604cfcd7302b85da66`, remains the reviewed API
  contract; the live loader/API/serializer hashes matched the fetched source.
- At the approved zero-viewer gate, the managed update installed beta.5, no
  further update was offered, enabled/settings state was preserved, and
  `installed_version_is_prerelease` remained false so future updates remain
  available.

## Live benchmark and bounded hardware proof

- Start time: `2026-09-21 17:45:40 UTC`.
- Pre-start viewers and other media: zero.
- Active streams stopped: zero.
- Completed at `2026-09-21T17:51:16.719376+00:00` with return code 0,
  persisted outcome `complete`, valid canonical cache, no PID, and no
  benchmark lock.
- Capabilities: VAAPI/HEVC 10-bit decode and encode; primary `renderD129`
  capacity 19 at 14x, secondary `renderD128` capacity 14 at 11.6x.
- `benchmark-latest.log` was 1,508,339 bytes. No root candidate/capacity/10-bit
  logs or `.benchmark-run` directories remained.
- A bounded real-hardware managed-launcher fixture generated four seconds of
  H.264, fed it via `pipe:0`, and produced a 4.025-second 720p HEVC VAAPI
  output; full `-xerror` decode measured 120 frames with no errors. No provider
  channel was fetched and no Dispatcharr profile was created.
- Final snapshot at `2026-09-21 17:52:25 UTC`: zero viewers, input/output
  transcodes, ffmpeg/ffprobe processes, with runtime and manifest beta.5/pin
  `913a958fd5f9edc231c49a70539a09f611fdcc5a` unchanged.
