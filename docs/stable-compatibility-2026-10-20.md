# Stable 0.2.1 compatibility review — 2026-10-20

## Exact scope

Official Dispatcharr repository: https://github.com/Dispatcharr/Dispatcharr.
Baseline v0.31.0: `bcbb68c4f054ee56383a41604cfcd7302b85da66`.
Reviewed v0.32.0: `c52bf87acb7ff2d787d6dcfb9fe3d39999585912`.
The official tag was refreshed before publication. Eleven selected live source
files matched official 0.32.0 hashes during the authorized read-only audit.
No live install, update, settings/profile action, stream or restart was performed.

## Contract comparison

- Plugin loader changes only discovery logging. Discovery, schema normalization,
  run(action_id, params, context), settings/defaults and dictionary results remain
  compatible (apps/plugins/loader.py:299,543,701).
- Plugin models, serializers, tasks and API views are byte-identical between
  0.31.0 and 0.32.0. ZIP selection/extraction/key sanitization, managed update,
  version/minimum checks and prerelease handling are unchanged
  (apps/plugins/api_views.py:36,127,1196).
- Stream/Output Profile fields and build_command remain compatible. New locked
  profile enforcement is respected because this plugin skips locked profiles
  before updating or deleting them (core/models.py:79,177; plugin.py:_upsert_profile).
- OutputProfileManager and RedisKeys are byte-identical, preserving pipe:0 input,
  MPEG-TS stdout, transcode_active and output:mpegts:p<id>:state coordination
  (apps/proxy/live_proxy/output/profile/manager.py;
  apps/proxy/live_proxy/redis_keys.py:89,119).
- ChannelService.stop_channels is structurally unchanged (line 603).
  ProxyServer.get_instance retains the same interface; its change removes
  redundant imports (apps/proxy/live_proxy/server.py:38).
- SystemNotification and send_notification_dismissed/send_websocket_update are
  structurally unchanged (core/models.py:932; core/utils.py:536,1138).

Conclusion: no affected incompatibility identified. Minimum Dispatcharr v0.29.0
is unchanged. Source compatibility does not claim fresh live behavior validation.

## Live source identities (SHA-256)

| Source | SHA-256 |
|---|---|
| apps/plugins/loader.py | 56719c412bc2bc6eb9b71f096798d4f40cd8f166b4351920cb66ca6fa82fb3b3 |
| apps/plugins/api_views.py | a4249bd4669416e9b551ee1db94b941323757a906c11a17b84a64cad1f61f192 |
| apps/plugins/models.py | 55602caaf25a135bf4ba33355e721843425464e94a2fdc91783727eeef0093fb |
| apps/plugins/serializers.py | 1623b004a80cb943070cbffde0da9e43f3439b2fe69bd1b9faebf2419b1b7326 |
| apps/plugins/tasks.py | 19bf9f0d06491280b331615cd17c76b0ce56c0e5ee67f91f10a512823d1284ab |
| core/models.py | 2788a07dc0a05b6fffc7c5863e53b68843ccfa1ed1a4f0f4b97551678f63be65 |
| core/utils.py | 38a1dddeffd78661889f917ecab1d242db1ed7f901aa9775adb26334b477567b |
| apps/proxy/live_proxy/services/channel_service.py | 88bcaa20c6437d561003fd2f5ead9427265192d9713ad1509c3bb8c67a8c7f61 |
| apps/proxy/live_proxy/server.py | 3a0f6b3e4eaa6303148430e7102ce0cd80ddbb483fb93266e8f3cf2b06814537 |
| apps/proxy/live_proxy/redis_keys.py | a4dc6310efc3962a6c73068f864ef62654372c5c5e781fd1b7f39c8b6cf26858 |
| apps/proxy/live_proxy/output/profile/manager.py | b09276e8aee35c06d4a75503811c98c3e5d0eb93ef98dd4e10fdfda16e1663cb |

## Package and update evidence

The release gate uses exact official 0.32.0 installer helpers in isolated
TemporaryDirectory storage to check clean installation and beta.5-to-stable
overwrite, sanitized key ffmpeg_smart_profiles, Python/JSON version, generated
profile defaults, executable-mode repair, all seven pinned runtime hashes,
MIT notice and preservation of external runtime state. Run against both the
manual-install ZIP and downloaded immutable registry tag archive. Final checksums
and outcomes are recorded in GitHub Release notes and the publication report.
The historical hardware/pipe proof remains in beta5-validation-2026-09-21.md.
