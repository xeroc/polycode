"""Base channel interface."""

from abc import ABC, abstractmethod
from typing import ClassVar

from channels.types import ChannelResult, ChannelType, Notification, Reaction


class BaseChannel(ABC):
    """Abstract base class for all communication channels."""

    channel_type: ClassVar[ChannelType]

    @abstractmethod
    async def send(self, notification: Notification) -> ChannelResult:
        """Send a notification through this channel.

        Args:
            notification: The notification to send

        Returns:
            Result indicating success/failure
        """
        ...

    @abstractmethod
    def supports_reactions(self) -> bool:
        """Whether this channel supports message reactions."""
        ...

    @abstractmethod
    def supports_threads(self) -> bool:
        """Whether this channel supports threaded conversations."""
        ...

    async def add_reaction(self, reaction: Reaction) -> ChannelResult:
        """Add a reaction to a message (optional)."""
        return ChannelResult(
            success=False, channel_type=self.channel_type, error="Reactions not supported by this channel"
        )

    async def get_reactions(self, message_id: str) -> list[Reaction]:
        """Get reactions for a message (optional)."""
        return []

    async def close(self) -> None:
        """Close channel resources (optional).

        Override this method if your channel needs cleanup.
        """
