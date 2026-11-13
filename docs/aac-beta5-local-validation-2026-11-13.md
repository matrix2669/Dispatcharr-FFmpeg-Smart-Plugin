# AAC beta.5 local package preparation, 2026-11-13

Base: plugin dev `4715c24f8d9f4d52eed7554d47a117027d04c8c4`.
Proposed version: `0.2.2-beta.5`; intended future tag: `v0.2.2-beta.5`.
Canonical source: `fd6c400d49cff305df7c41a4149d2f00b80355bb`.

## Completed local checks

- Official source synchronization succeeded; repeating the same immutable ref
  reported already current. Both offline and remote checksum/mode verification
  passed for all eight runtime files. The MIT notice remains included.
- All 80 plugin tests passed after updating the two exact expected-source pin
  assertions. Python compilation, both JSON checks and all required shell syntax
  checks passed. No integration code changed beyond version and audio help.
- Comparing plugin.json to the dev base with only version/help removed found
  identical field IDs, defaults, options, actions and all other metadata.
- A real local fixture passed through `ffmpeg-smart-plugin.sh -i pipe:0` with
  an isolated software-test capability cache and added normalization. MPEG-2
  video and AC3 48-kHz 5.1(side) input produced AAC 48-kHz six-channel standard
  5.1 with ADTS configuration 6. Full audio decode and three packet-aligned late
  joins (half, third, quarter) passed strict audio decode. FFmpeg 7.1.5 was used
  for this package-path check; identical canonical runtime bytes already passed
  the documented pinned FFmpeg 8.1.2 source fixtures and independent review.
- `git diff --check` passed.

The local commit is built into an exact-commit archive and inspected separately
before delivery. Its digest and extracted-package results belong to the local
handoff evidence, not a claim that the future remote tag archive exists.

## Scope and remaining publication gates

No remote plugin/registry branch, tag, Release or updater channel has changed.
No live provider, Dispatcharr instance, profile, saved setting or installed plugin
was accessed or modified. The fixture is an actual packaged launcher/pipe path,
not a managed Dispatcharr database update or live 505 acceptance. Synthetic late
cuts can emit MPEG-2 dimension warnings while strict audio decode still succeeds.

Unknown mapping/filter graphs conservatively retain existing FFmpeg behavior;
copied malformed AAC is outside this encoding-only repair. Six separate channels
are preserved; the approved side-to-back surround-label convention is intentional.

Later publication requires explicit approval, fresh-ref/standards checks,
exact-plugin CI, immutable new-tag verification and inspection/digest of the
actual advertised tag archive, followed by the focused registry-dev update and
its exact CI. Installed-plugin update, profile reconciliation and live playback
are separate operator-owned actions. Minimum Dispatcharr v0.29.0 and the existing
supported-version contracts are unchanged; no new Dispatcharr version is tested.
