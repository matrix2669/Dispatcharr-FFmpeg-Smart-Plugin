# Local beta.6 composition and selected-mode validation, 2026-11-13

Plugin base: published dev `57bef76032ed33300fbcecdd424df4174c099d79`.
Local canonical source: `c7e53605242e611961ad4c3578d5c2c6d26234cf`.
Proposed plugin version: `0.2.2-beta.6`; no tag is created or published.

## Actual changes

The reported Add graph `aresample=async=1,dynaudnorm=f=150:g=15` now retains
one-to-one side-to-standard-5.1 pan plus exactly the selected resampler and
normalizer. Supported simple combinations preserve order and explicit sampling
choices; unsupported eligible side graphs fail with credential-safe guidance
before encoding. Copy and expert Replace remain explicit, with no second encoder.

UI Inherit now ignores stored scoped option/mapping text before parsing,
validation and input probe-option normalization. Add/Replace continue forwarding
and validating selected text. Mapping All retains its existing custom-text rule;
blank Replace retains its meaning. Dormant saved text is preserved. This changes
future generated commands only when the operator reconciles profiles; no live
profile was accessed or changed here. Canonical expert CLI semantics are separate.

## Completed local checks

- Canonical full scripts/validate.sh passed with ShellCheck 0.11 and host FFmpeg
  7.1.5, including all 20 shared-input methods. The corrected cancellation fixture
  remains readiness-based; no deadline assertion was weakened.
- Pinned FFmpeg 8.1.2 policy/real fixtures passed for the actual combined graph,
  mixed side/back/stereo, both sample rates, three packet-aligned joins, distinct
  six-channel routing and native AAC-copy identity.
- Additional real 7.1.5 fixtures passed normalization plus volume, reordered
  explicit 44.1-kHz resampling plus anull, and async/min_hard_comp/first_pts options.
  Captured actual output argv showed one encoder invocation and one effective
  resampler per output. Explicit 44.1-kHz output remained 44.1 kHz with six channels.
- All 85 plugin tests passed. Public Stream/Output generators cover populated and
  malformed boxes across all four scopes and selected modes, mapping modes,
  saved-text preservation and blank Replace. Required compilation/JSON/syntax and
  offline source checksum/mode checks passed.
- Comparison with the base excluding version/help text found all settings IDs,
  defaults, choices, actions and other plugin metadata unchanged.
- All eight runtime files were staged from the exact local canonical Git commit
  with Git-declared modes and hashes. Repeating staging changed zero files.
  Only the canonical policy module changed among vendored runtime contents.

The first plugin worker run found checked-out file modes 0711 versus declared
0755 (decimal457 versus493), not a file-count or concurrent-runtime-edit defect.
Checkout ran under umask0077; restoring declared package modes corrected the
fixture setup. Full tests then passed without product permission-policy changes.

## Limits and delivery boundary

The bounded graph grammar does not implement arbitrary FFmpeg quoting/escaping,
branched graphs, unknown filters or layout-changing options. Such eligible side
AAC graphs require the explicit configuration guidance or expert Replace mode.
Already-malformed copied AAC remains outside this encoding-only repair.
Synthetic MPEG-TS cuts can emit video dimension diagnostics while strict audio
decode succeeds; no uninterrupted arbitrary-cut video or live505 acceptance is
claimed. Bash3 compatibility is syntax/review based, not execution under Bash3.

The canonical successor is intentionally unpublished. Online source verification
and normal remote sync idempotency remain pending approved canonical publication;
offline Git-object staging is not described as remote verification. Independent
completed-result review and exact local package/registry artifacts are recorded
separately in the handoff evidence after this checkpoint. No push, tag, registry
promotion, install, live-setting action or deployment is authorized in this phase.
