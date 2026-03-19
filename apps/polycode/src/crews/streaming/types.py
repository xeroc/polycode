"""Types for CrewAI LLM streaming."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from channels.stream.config import StreamConfig


class StreamEventType(str, Enum):
    """Types of streaming events."""

    TOKEN = "token"
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    TASK_START = "task_start"
    TASK_END = "task_end"
    CREW_START = "polycode_start"
    CREW_END = "polycode_end"
    ERROR = "error"


class StreamToken(BaseModel):
    """A single token from LLM stream."""

    session_id: str = Field(..., description="Session/flow identifier")
    room: str = Field(..., description="Repo Room (repo_owner/repo_name)")
    token: str = Field(..., description="The token text")
    agent_role: str | None = Field(default=None, description="Agent generating the token")
    task_id: str | None = Field(default=None, description="Current task ID")


class StreamEvent(BaseModel):
    """A streaming event (non-token)."""

    session_id: str
    room: str
    event_type: StreamEventType
    agent_role: str | None = None
    task_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


__all__ = ["StreamConfig", "StreamEvent", "StreamEventType", "StreamToken"]
