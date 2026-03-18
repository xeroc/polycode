"""Shared configuration types for streaming (no heavy imports)."""

from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict


class StreamConfig(BaseModel):
    """Configuration for Redis-based streaming."""

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    channel_prefix: str = "polycode_stream"

    model_config = SettingsConfigDict(
        extra="ignore", env_file=".env", case_sensitive=True
    )


settings = StreamConfig()
