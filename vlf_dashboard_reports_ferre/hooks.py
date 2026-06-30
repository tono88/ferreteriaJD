# -*- coding: utf-8 -*-
from .models.preset_registry import VlfDashboardPresetRegistry


def post_init_hook(env):
    VlfDashboardPresetRegistry(env).apply_presets()
