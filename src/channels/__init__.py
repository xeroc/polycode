"""Communication channels system.

This module provides a unified interface for sending notifications
through multiple channels (GitHub, Redis, Slack, Discord, Telegram).
"""

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

__all__ = [
    "BaseChannel",
    "ChannelConfig",
    "ChannelDispatcher",
    "ChannelResult",
    "ChannelType",
    "Notification",
    "NotificationLevel",
    "Reaction",
]
