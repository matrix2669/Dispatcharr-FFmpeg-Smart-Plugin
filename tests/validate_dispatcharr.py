"""Rollback-only integration validation for a locally installed plugin."""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dispatcharr.settings")
sys.path.insert(0, "/app")

import django

django.setup()

from django.db import transaction

from apps.plugins.loader import PluginManager
from apps.plugins.models import PluginConfig
from core.models import OutputProfile, StreamProfile


PLUGIN_KEY = "ffmpeg_smart_profiles"


manager = PluginManager.get()
registry = manager.discover_plugins(sync_db=True, force_reload=True)
discovered = registry[PLUGIN_KEY]
assert discovered.name == "FFmpeg Smart Profiles"
assert discovered.version == "0.1.0-dev.1"

with transaction.atomic():
    config = PluginConfig.objects.get(key=PLUGIN_KEY)
    config.enabled = True
    config.save(update_fields=["enabled"])

    loaded = manager.discover_plugins(
        sync_db=False,
        force_reload=True,
        release_connections=False,
    )[PLUGIN_KEY]
    assert loaded.loaded

    context = {"settings": {}, "logger": None}
    first = loaded.instance.run("install_profiles", {}, context)
    assert first["status"] == "ok"
    assert len(first["created"]) == 4, first
    assert StreamProfile.objects.filter(name="FFmpeg Smart").count() == 1
    assert OutputProfile.objects.filter(name__startswith="FFmpeg Smart - ").count() == 3

    second = loaded.instance.run("install_profiles", {}, context)
    assert second["status"] == "ok"
    assert len(second["unchanged"]) == 4, second

    transaction.set_rollback(True)

print("Dispatcharr plugin discovery and idempotent profile install passed")
