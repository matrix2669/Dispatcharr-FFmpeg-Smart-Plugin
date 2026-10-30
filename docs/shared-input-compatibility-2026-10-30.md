# Shared-input compatibility evidence, 2026-10-30

The parent coordinator supplied a read-only comparison of deployed Dispatcharr
0.33.0 with official source commit
`2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e` and reviewed installer atomic swap,
plugin discovery, settings/action APIs and global-default persistence. The
plugin does not invoke the global-default API. Minimum 0.29.0 is unchanged.

| Official source path | SHA-256 matched against deployed source |
|---|---|
| `apps/plugins/loader.py` | `f6ad90014f5b5f2eb25d2382e1d6c9c2749c6c69202621a445c3a56193da2fbe` |
| `apps/plugins/api_views.py` | `2f948dface3b0bdece923fdaac3d709754f1c6a65c95b3445471b0a2f9e7cb46` |
| `apps/plugins/serializers.py` | `1623b004a80cb943070cbffde0da9e43f3439b2fe69bd1b9faebf2419b1b7326` |
| `apps/plugins/models.py` | `f013c9a70afd71ffd55cc90406354a694b9b9836d905c58e3869152b13035cf7` |
| `core/models.py` | `a6098d95888fecc5de8f5ce0515a5a290178ed23cfd50839d014b304263d5afb` |
| `apps/channels/models.py` | `f76cd4a71a2997b04ce836fc3191d56755c26b88fcdfb9caec85b3c67d119f04` |
| `apps/proxy/live_proxy/redis_keys.py` | `3b7c765242b946c0ef8ea44ea9216c6c302341a93cb1e0d8c6850ee780b68759` |

The requested legacy `apps/proxy/ts_proxy/channel_manager.py` comparison path
was absent upstream; it is excluded rather than treated as a match. This source
comparison is not an installation/profile-action or live-stream result.

Canonical source `6e0a84b900db65fd4867d22c17d6b93e22fd1470` passed full CI run
[41076177782](https://github.com/matrix2669/ffmpeg-adaptive/actions/runs/41076177782).
Its runtime is byte-identical to `e1f70ff`, whose 12 shared-input methods passed
inside actual Dispatcharr with Python 3.13.17 and FFmpeg 8.1.2 as the dispatch
user in isolated temporary storage. This uses local fixtures; no provider
performance, deployed package, persisted settings or selected default is inferred.

The plugin's local test candidate is 0.2.2-beta.2. Native installation, profile
reconciliation, bounded live startup comparisons and any global-default switch
remain separate parent-owned actions. No registry/tag/Release promotion occurs.
