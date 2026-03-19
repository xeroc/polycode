"""Channel dispatcher for routing notifications to multiple channels.

Uses the plugin system for channel discovery and creation.
"""

import logging
from typing import TYPE_CHECKING

from channels.base import BaseChannel
from channels.types import (
    ChannelConfig,
    ChannelResult,
    ChannelType,
    Notification,
)

if TYPE_CHECKING:
    from modules.channels import ChannelRegistry
    from project_manager.types import ProjectConfig

log = logging.getLogger(__name__)


class ChannelDispatcher:
    """Dispatches notifications to multiple channels via plugin system."""

    def __init__(
        self,
        configs: list[ChannelConfig],
        project_config: "ProjectConfig | None" = None,
        channel_registry: "ChannelRegistry | None" = None,
    ) -> None:
        """Initialize channel dispatcher.

        Args:
            configs: List of channel configurations.
            project_config: Project configuration (required for GitHub channel).
            channel_registry: Optional ChannelRegistry instance. If None, uses singleton.
        """
        self._configs = configs
        self._project_config = project_config
        self._channels: dict[ChannelType, BaseChannel] = {}

        if channel_registry is None:
            from modules.channels import ChannelRegistry

            self._registry = ChannelRegistry.get()
        else:
            self._registry = channel_registry

        self._initialize_channels()

    def _initialize_channels(self) -> None:
        """Initialize all enabled channels based on configs."""
        for config in self._configs:
            if not config.enabled:
                log.info(f"Channel {config.channel_type.value} is disabled, skipping")
                continue

            try:
                channel = self._create_channel(config)
                if channel:
                    self._channels[config.channel_type] = channel
                    log.info(f"Initialized channel: {config.channel_type.value}")
            except Exception as e:
                log.error(f"Failed to initialize channel {config.channel_type.value}: {e}")

    def _create_channel(self, config: ChannelConfig) -> BaseChannel | None:
        """Create a channel instance via registry.

        Args:
            config: Channel configuration.

        Returns:
            Channel instance or None if creation failed.
        """
        channel = self._registry.create_channel(
            channel_type=config.channel_type,
            config=config,
            project_config=self._project_config,
        )

        if channel is None:
            log.warning(
                f"No channel registered for type: {config.channel_type.value}. "
                f"Available: {self._registry.registered_types}"
            )

        return channel

    @property
    def channels(self) -> dict[ChannelType, BaseChannel]:
        """Get initialized channels."""
        return self._channels

    async def dispatch(
        self,
        notification: Notification,
        channel_types: list[ChannelType] | None = None,
    ) -> list[ChannelResult]:
        """Dispatch a notification to specified channels.

        Args:
            notification: The notification to send.
            channel_types: Optional list of channel types to target.
                          If None, sends to all enabled channels.

        Returns:
            List of results from each channel.
        """
        results: list[ChannelResult] = []

        if channel_types:
            target_channels = {ct: ch for ct, ch in self._channels.items() if ct in channel_types}
        else:
            target_channels = self._channels

        for channel_type, channel in target_channels.items():
            try:
                result = await channel.send(notification)
                results.append(result)
                log.info(f"Notification sent to {channel_type.value}: {'success' if result.success else 'failed'}")
            except Exception as e:
                log.error(f"Failed to send to {channel_type.value}: {e}")
                results.append(ChannelResult(success=False, channel_type=channel_type, error=str(e)))

        return results

    async def dispatch_sync(
        self,
        notification: Notification,
        channel_types: list[ChannelType] | None = None,
    ) -> list[ChannelResult]:
        """Synchronous wrapper for dispatch (for backwards compatibility).

        Args:
            notification: The notification to send.
            channel_types: Optional list of channel types to target.

        Returns:
            List of results from each channel.
        """
        return await self.dispatch(notification, channel_types)

    def is_enabled(self, channel_type: ChannelType) -> bool:
        """Check if a channel type is enabled.

        Args:
            channel_type: The channel type to check.

        Returns:
            True if channel is enabled and initialized.
        """
        return channel_type in self._channels

    async def close(self) -> None:
        """Close all channel connections."""
        for channel in self._channels.values():
            if hasattr(channel, "close"):
                await channel.close()
        self._channels.clear()
        log.info("All channels closed")
