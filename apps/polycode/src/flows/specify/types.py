"""Specify flow types."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from flows.base import BaseFlowModel
from crews.plan_crew.types import Story


class SpecifyStage(str, Enum):
    """Stage of specify flow."""

    STARTING = "starting"
    WAITING = "waiting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class SpecifyFlowState(BaseFlowModel):
    """State persisted between specify flow steps."""

    # Identifiers
    flow_uuid: str
    issue_number: int
    issue_author: str
    issue_title: str

    stories: Optional[list[Story]] = Field(default=[], description="Ordered user stories")

    # Conversation state
    stage: SpecifyStage = SpecifyStage.STARTING
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    last_processed_comment_id: int | None = None

    # Specification output
    specification_complete: bool = False
    completion_keyword: str | None = None  # "LGTM", "LFG", etc.

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Error tracking
    retry_count: int = 0
    last_error: str | None = None


class SpecifyOutput(BaseModel):
    """Output from specify flow."""

    stories: list[dict[str, Any]]
    repo_owner: str
    repo_name: str
    issue_id: int
    conversation_history: list[dict[str, Any]]
    specification_summary: str
