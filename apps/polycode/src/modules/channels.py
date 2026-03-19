"""Channel registry and plugin protocol.

Channels are communication adapters (GitHub, Redis, Slack, etc.) that
send notifications during flow execution. The registry allows modules
to register channel implementations dynamically.
"""

import logging
from typing import TYPE_CHECKING, Callable

from channels.types import ChannelType

if TYPE_CHECKING:
    from channels.base import BaseChannel
    from channels.types import ChannelConfig
    from project_manager.types import ProjectConfig

log = logging.getLogger(__name__)


ChannelFactory = Callable[["ChannelConfig", "ProjectConfig | None"], "BaseChannel"]


class ChannelRegistry:
    """Registry for channel implementations.

    Channels register factory functions that create channel instances
    from configuration. This allows modules to provide new channel types
    without modifying core code.

    Usage:

        # In a module's register_hooks():
        from modules.channels import ChannelRegistry

        def create_slack_channel(config, project_config):
            return SlackChannel(
                token=config.extra.get("token"),
                channel_id=config.extra.get("channel_id"),
            )

        ChannelRegistry.register(ChannelType.SLACK, create_slack_channel)
    """

    _instance: "ChannelRegistry | None" = None
    _factories: dict[ChannelType, ChannelFactory] = {}

    @classmethod
    def get(cls) -> "ChannelRegistry":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def register(cls, channel_type: ChannelType, factory: ChannelFactory) -> None:
        """Register a channel factory.

        Args:
            channel_type: The channel type enum value.
            factory: Callable that creates a channel instance.
        """
        cls._factories[channel_type] = factory
        log.info(f"📡 Registered channel: {channel_type.value}")

    @classmethod
    def unregister(cls, channel_type: ChannelType) -> None:
        """Unregister a channel type (for testing)."""
        cls._factories.pop(channel_type, None)

    @classmethod
    def reset(cls) -> None:
        """Clear all registrations (for testing)."""
        cls._factories.clear()
        cls._instance = None

    @property
    def registered_types(self) -> list[str]:
        """Get list of registered channel type names."""
        return [ct.value for ct in self._factories.keys()]

    def create_channel(
        self,
        channel_type: ChannelType,
        config: "ChannelConfig",
        project_config: "ProjectConfig | None" = None,
    ) -> "BaseChannel | None":
        """Create a channel instance from config.

        Args:
            channel_type: The channel type to create.
            config: Channel configuration.
            project_config: Optional project configuration.

        Returns:
            Channel instance or None if type not registered.
        """
        factory = self._factories.get(channel_type)
        if factory is None:
            log.warning(f"⚠️ No factory registered for channel type: {channel_type.value}")
            return None

        try:
            channel = factory(config, project_config)
            log.debug(f"📡 Created channel instance: {channel_type.value}")
            return channel
        except Exception as e:
            log.error(f"🚨 Failed to create channel {channel_type.value}: {e}")
            return None
