"""Redis channel module."""

import logging
import os

from channels.redis.channel import RedisChannel
from channels.types import ChannelType
from modules.channels import ChannelRegistry

log = logging.getLogger(__name__)

__all__ = ["RedisChannel"]


def _create_redis_channel(config, project_config):
    """Factory function for creating Redis channel instances.

    Args:
        config: ChannelConfig with Redis-specific settings in extra
        project_config: ProjectConfig (not used for Redis)

    Returns:
        RedisChannel instance
    """
    extra = config.extra or {}

    return RedisChannel(
        host=extra.get("host", os.getenv("REDIS_HOST", "localhost")),
        port=extra.get("port", int(os.getenv("REDIS_PORT", "6379"))),
        db=extra.get("db", 0),
        password=extra.get("password", os.getenv("REDIS_PASSWORD")),
        channel_name=extra.get("channel_name", "notifications"),
    )


ChannelRegistry.register(ChannelType.REDIS, _create_redis_channel)
log.debug("📡 Registered Redis channel")
