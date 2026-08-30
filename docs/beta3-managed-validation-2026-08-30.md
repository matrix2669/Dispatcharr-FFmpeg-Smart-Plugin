# FFmpeg Smart Profiles beta.3 managed validation

Date: 2026-08-30

## Immutable publication

- Plugin tag: `v0.2.1-beta.3`
- Plugin commit: `dd54d4cc82a454135c4eb3b75eeeb5eb48713fe6`
- Canonical runtime: `matrix2669/ffmpeg-adaptive v0.1.0-beta.2`
- Canonical runtime commit: `4df6c12e395187fc0080f858685a3c6ebd7a8c42`
- Plugin workflow: `33333007420`, passed
- Development-registry commit:
  `50489521b1b6350bc95f300ceaf77a8bb7c372da`
- Development-registry workflow: `33333093699`, passed
- Stable plugin and registry branches were unchanged. No GitHub Release or
  manual ZIP was created.

## Managed update and profiles

Dispatcharr repository 37 refreshed the public `dev` manifest and updated
`ffmpeg_smart_profiles` from `0.2.1-beta.2` to `0.2.1-beta.3` through the native
managed install API. The plugin remained enabled.

The installed entrypoint and six modules matched every checksum and mode in
`FFMPEG_SMART_SOURCE.json`; the MIT notice matched the tagged archive. No UI
field, saved key, generated stream parameter, or generated output parameter
contained retired `-10bit` or `-hdr` controls. Reconciliation reported both
profiles unchanged, no conflicts, no restart, and no managed-profile mutation:

- Stream: `-i "{streamUrl}" -user_agent "{userAgent}" -deint`
- Output: `-i pipe:0 -maxres 720 -maxbr 2M -maxchan 2 -sdr -deint`

## Cache transition and capacity

Immediately after update, the previous beta.2 cache returned `stale` with exit
78, proving the capacity-policy fingerprint transition. The explicit rebuild
reported zero stopped active transcodes and completed normally.

The resulting schema-2 cache returned `valid` with:

| Device | Policy | Speed | Stable capacity | Rejected |
|---|---|---:|---:|---:|
| Arc A310 `/dev/dri/renderD129` | VAAPI/HEVC, low-power 1, 10-bit decode/encode | 14x | 18 | 19 |
| UHD 770 `/dev/dri/renderD128` | VAAPI/HEVC, low-power 1, 10-bit decode/encode | 11.6x | 14 | 15 |

The Arc low-power-on and low-power-off candidates tied at the displayed 14x in
this installed run, so deterministic candidate order retained low-power on.
The isolated pre-tag run had a small speed difference and retained low-power
off. This is expected benchmark variation at a policy tie; capacity, selected
codec, 10-bit support, and live behavior did not regress.

## Actual stream matrix

Current priority-zero Dispatcharr sources were run through the installed
launcher. Direct inputs were bounded by terminating the continuous capture;
finite `pipe:0` results completed normally.

| Source | Direct result | Finite pipe result | Decode/scan/timestamps |
|---|---|---|---|
| CBS 2 New York, H.264 1080p59.94 | HEVC 1920x1080 | HEVC 1280x720 | zero decode errors; zero interlaced decoded frames; monotonic nonnegative DTS |
| PIX11 New York, MPEG-2 1080i29.97 | HEVC 1920x1080 progressive | HEVC 1280x720 progressive | zero decode errors; zero interlaced decoded frames; monotonic nonnegative DTS |
| FOX 5 New York, H.264 720p59.94 | HEVC 1280x720 | HEVC 1280x720 | zero decode errors; zero interlaced decoded frames; monotonic nonnegative DTS |

The first harness pass produced valid, clean media but marked cases false when
FFprobe omitted its optional stream-level `field_order` summary for progressive
HEVC. The corrected and repeated harness inspected each decoded frame's
`interlaced_frame` value instead: 1,416/1,416 CBS direct/pipe frames, 167/167
PIX11 frames, and 1,869/1,869 FOX frames were progressive.

## Overlapping scheduler and cleanup

Three overlapping installed-wrapper jobs passed:

- CBS 2 used the Arc A310 at capacity 18.
- FOX 5 used the UHD 770 at capacity 14.
- PIX11 also used the UHD 770 with the existing FOX job counted as 888
  milli-units of load.
- Every captured output probed and decoded successfully with zero decode errors.

The final installed version was `0.2.1-beta.3`, cache status was `valid`, and
the final process audit found no FFmpeg or FFmpeg Smart process. The obsolete
isolated pre-tag checkout and its transient benchmark logs were removed from
`/dev/shm`; the managed persistent cache and log remained intact.
