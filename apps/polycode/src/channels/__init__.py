"""Communication channels system.

This module provides a unified interface for sending notifications
through multiple channels (Redis, Slack, Discord, Telegram).
"""

import logging

import pluggy

from channels.base import BaseChannel
from channels.dispatcher import ChannelDispatcher
from channels.types import (
    ChannelConfig,
    ChannelResult,
    ChannelType,
    Notification,
    NotificationLevel,
    Reaction,
)
from modules.context import ModuleContext

log = logging.getLogger(__name__)

__all__ = [
    "BaseChannel",
    "ChannelConfig",
    "ChannelDispatcher",
    "ChannelResult",
    "ChannelType",
    "Notification",
    "NotificationLevel",
    "Reaction",
    "ChannelsPolycodeModule",
]


class ChannelsPolycodeModule:
    """Channels module: built-in notification system."""

    name = "channels"
    version = "0.1.0"
    dependencies: list[str] = []

    @classmethod
    def on_load(cls, context: ModuleContext) -> None:
        """Initialize channel registry."""
        log.info("📡 Initializing channels module")

    @classmethod
    def register_hooks(cls, hook_manager: pluggy.PluginManager) -> None:
        """Register notification hooks.

        Sends notifications through configured channels at flow phases.
        Individual channel modules (redis) register themselves
        via ChannelRegistry during their import.
        """
        from channels.hooks import ChannelHooks

        hook_manager.register(ChannelHooks())
        log.info("📡 Registered channel notification hooks")

    @classmethod
    def get_models(cls) -> list[type]:
        """No ORM models for channels module."""
        return []
