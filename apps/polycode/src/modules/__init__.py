"""Polycode module system."""

from modules.channels import ChannelRegistry
from modules.context import ModuleContext
from modules.hooks import (
    FlowHookSpec,
    FlowPhase,
    get_plugin_manager,
    hookimpl,
    hookspec,
)
from modules.protocol import PolycodeModule
from modules.registry import ModuleRegistry

__all__ = [
    "ModuleContext",
    "ChannelRegistry",
    "FlowHookSpec",
    "FlowPhase",
    "get_plugin_manager",
    "hookimpl",
    "hookspec",
    "PolycodeModule",
    "ModuleRegistry",
]
