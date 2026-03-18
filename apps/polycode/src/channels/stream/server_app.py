"""Standalone Socket.IO streaming server.

This server bridges Redis pub/sub to Socket.IO clients.

Run with:
    uv run python -m channels.stream.server_app

Architecture:
    CrewAI (Celery) --> Redis Pub/Sub --> This Server --> Socket.IO --> Browser
"""

import logging

import uvicorn
from fastapi import FastAPI

from channels.stream.server import get_server
from crews.streaming.types import StreamConfig

log = logging.getLogger(__name__)

app = FastAPI(title="Polycode Stream Server", version="1.0.0")


@app.get("/")
async def root():
    return {"name": "polycode-stream-server", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


stream_config = StreamConfig()
stream_server = get_server(config=stream_config)
asgi_app = stream_server.asgi_app(app)


@app.on_event("startup")
async def startup():
    await stream_server.start()
    log.info("Stream server started")


@app.on_event("shutdown")
async def shutdown():
    await stream_server.stop()
    log.info("Stream server stopped")


def run():
    uvicorn.run(
        "channels.stream.server_app:asgi_app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )


if __name__ == "__main__":
    run()
