"""Channel system types."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NotificationLevel(str, Enum):
    """Severity/importance level of notification."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class ChannelType(str, Enum):
    """Supported channel types."""

    GITHUB = "github"
    REDIS = "redis"
    SLACK = "slack"
    DISCORD = "discord"
    TELEGRAM = "telegram"


class Notification(BaseModel):
    """A notification to be sent through one or more channels."""

    content: str = Field(..., description="The notification content/text")
    level: NotificationLevel = Field(default=NotificationLevel.INFO, description="Importance level")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Channel-specific context (issue_id, channel_id, etc.)"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata for routing/formatting")


class ChannelResult(BaseModel):
    """Result of sending a notification through a channel."""

    success: bool
    channel_type: ChannelType
    message_id: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChannelConfig(BaseModel):
    """Configuration for a channel."""

    channel_type: ChannelType
    enabled: bool = True
    # Channel-specific settings stored in extra
    extra: dict[str, Any] = Field(default_factory=dict)


class Reaction(BaseModel):
    """A reaction to a message."""

    message_id: str
    emoji: str
    user: str | None = None
