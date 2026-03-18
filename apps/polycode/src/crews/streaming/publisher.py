"""Redis publisher for CrewAI streaming tokens."""

import json
import logging

import redis

from .types import StreamConfig, StreamEvent, StreamEventType, StreamToken

log = logging.getLogger(__name__)


class StreamPublisher:
    """Publishes streaming events to Redis for Socket.IO consumption."""

    def __init__(self, config: StreamConfig | None = None):
        self.config = config or StreamConfig()
        self._client: redis.Redis | None = None

    def _get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                decode_responses=True,
            )
        return self._client

    def _channel_name(self, room: str) -> str:
        return f"{self.config.channel_prefix}:{room}"

    def publish_token(self, token: StreamToken) -> None:
        client = self._get_client()
        channel = self._channel_name(token.room)
        payload = token.model_dump()
        client.publish(channel, json.dumps(payload))

    def publish_event(self, event: StreamEvent) -> None:
        client = self._get_client()
        channel = self._channel_name(event.room)
        payload = event.model_dump()
        payload["event_type"] = payload["event_type"].value
        client.publish(channel, json.dumps(payload))

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None


_publisher: StreamPublisher | None = None


def get_publisher(config: StreamConfig | None = None) -> StreamPublisher:
    global _publisher
    if _publisher is None:
        _publisher = StreamPublisher(config)
    return _publisher


def publish_token(
    session_id: str,
    room: str,
    token: str,
    agent_role: str | None = None,
    task_id: str | None = None,
) -> None:
    publisher = get_publisher()
    publisher.publish_token(
        StreamToken(
            session_id=session_id,
            room=room,
            token=token,
            agent_role=agent_role,
            task_id=task_id,
        )
    )


def publish_event(
    session_id: str,
    room: str,
    event_type: StreamEventType,
    agent_role: str | None = None,
    task_id: str | None = None,
    data: dict | None = None,
) -> None:
    publisher = get_publisher()
    publisher.publish_event(
        StreamEvent(
            session_id=session_id,
            room=room,
            event_type=event_type,
            agent_role=agent_role,
            task_id=task_id,
            data=data or {},
        )
    )
