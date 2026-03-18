"""Redis channel adapter."""

import json
import logging

import redis.asyncio as redis

from channels.base import BaseChannel
from channels.types import ChannelResult, ChannelType, Notification, Reaction

log = logging.getLogger(__name__)


class RedisChannel(BaseChannel):
    """Redis pub/sub channel adapter for real-time notifications."""

    channel_type = ChannelType.REDIS

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        channel_name: str = "notifications",
    ) -> None:
        """Initialize Redis channel.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            channel_name: Pub/sub channel name
        """
        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._channel_name = channel_name
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.Redis(
                host=self._host,
                port=self._port,
                db=self._db,
                password=self._password,
                decode_responses=True,
            )
        return self._client

    async def send(self, notification: Notification) -> ChannelResult:
        """Publish a notification to Redis pub/sub.

        Args:
            notification: The notification to publish

        Returns:
            Result of the publish operation
        """
        try:
            client = await self._get_client()

            payload = {
                "content": notification.content,
                "level": notification.level.value,
                "context": notification.context,
                "metadata": notification.metadata,
            }

            message_id = await client.publish(self._channel_name, json.dumps(payload))

            return ChannelResult(
                success=True,
                channel_type=self.channel_type,
                message_id=str(message_id),
                metadata={"channel": self._channel_name},
            )

        except Exception as e:
            log.error(f"Failed to publish to Redis: {e}")
            return ChannelResult(success=False, channel_type=self.channel_type, error=str(e))

    def supports_reactions(self) -> bool:
        """Redis pub/sub doesn't support reactions."""
        return False

    def supports_threads(self) -> bool:
        """Redis pub/sub doesn't support threads."""
        return False

    async def add_reaction(self, reaction: Reaction) -> ChannelResult:
        """Add a reaction (not supported)."""
        return ChannelResult(
            success=False, channel_type=self.channel_type, error="Reactions not supported in Redis channel"
        )

    async def get_reactions(self, message_id: str) -> list[Reaction]:
        """Get reactions (not supported)."""
        return []

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
