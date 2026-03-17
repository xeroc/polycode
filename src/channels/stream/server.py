"""Socket.IO server that bridges Redis pub/sub to websockets."""

import asyncio
import json
import logging
from typing import Any

import redis.asyncio as aioredis
import socketio

from channels.stream.config import StreamConfig

log = logging.getLogger(__name__)


class StreamServer:
    """Socket.IO server that subscribes to Redis and streams to clients.

    Architecture:
        CrewAI (Celery) --> Redis Pub/Sub --> StreamServer --> Socket.IO --> Browser

    Rooms are named by repo: "owner/repo"
    """

    def __init__(
        self,
        config: StreamConfig | None = None,
        cors_origins: str = "*",
    ):
        self.config = config or StreamConfig()
        self.cors_origins = cors_origins

        self.sio = socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins=cors_origins,
        )
        self._redis: aioredis.Redis | None = None
        self._pubsub: Any = None
        self._running = False
        self._task: asyncio.Task | None = None

        self._setup_handlers()

    def _setup_handlers(self):
        @self.sio.event
        async def connect(sid, environ):
            log.info(f"Client connected: {sid}")
            await self.sio.emit("connected", {"sid": sid}, to=sid)

        @self.sio.event
        async def disconnect(sid):
            log.info(f"Client disconnected: {sid}")

        @self.sio.event
        async def join_room(sid, data: dict[str, Any]):
            room = data.get("room")
            if room:
                await self.sio.enter_room(sid, room)
                log.info(f"Client {sid} joined room: {room}")
                await self.sio.emit("joined", {"room": room}, to=sid)

        @self.sio.event
        async def leave_room(sid, data: dict[str, Any]):
            room = data.get("room")
            if room:
                await self.sio.leave_room(sid, room)
                log.info(f"Client {sid} left room: {room}")

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                decode_responses=True,
            )
        return self._redis

    def _channel_pattern(self) -> str:
        return f"{self.config.channel_prefix}:*"

    async def _subscribe_loop(self):
        redis = await self._get_redis()
        pubsub = redis.pubsub()
        self._pubsub = pubsub
        await pubsub.psubscribe(self._channel_pattern())
        log.info(f"Subscribed to Redis pattern: {self._channel_pattern()}")

        try:
            async for message in pubsub.listen():
                if not self._running:
                    break

                if message["type"] not in ("pmessage", "message"):
                    continue

                channel = message.get("channel", "")
                if isinstance(channel, bytes):
                    channel = channel.decode()

                data = message.get("data")
                if not data or data == 1:
                    continue

                if isinstance(data, bytes):
                    data = data.decode()

                try:
                    payload = json.loads(data)
                    room = payload.get("room")
                    if room:
                        await self.sio.emit("stream", payload, to=room)
                except json.JSONDecodeError:
                    log.warning(f"Invalid JSON in stream message: {data[:100]}")

        except asyncio.CancelledError:
            log.info("Subscribe loop cancelled")
        except Exception as e:
            log.error(f"Error in subscribe loop: {e}", exc_info=True)

    async def start(self):
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._subscribe_loop())
        log.info("StreamServer started")

    async def stop(self):
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None

        if self._redis:
            await self._redis.close()
            self._redis = None

        log.info("StreamServer stopped")

    def asgi_app(self, other_app=None):
        return socketio.ASGIApp(self.sio, other_app)


_server: StreamServer | None = None


def get_server(config: StreamConfig | None = None, cors_origins: str = "*") -> StreamServer:
    global _server
    if _server is None:
        _server = StreamServer(config=config, cors_origins=cors_origins)
    return _server
