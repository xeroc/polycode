"""Specify flow types."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from crews.plan_crew.types import Story
from flows.base import BaseFlowModel


class SpecifyStage(str, Enum):
    """Stage of specify flow."""

    STARTING = "starting"
    WAITING = "waiting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class SpecifyFlowState(BaseFlowModel):
    """State persisted between specify flow steps."""

    question: Optional[str] = Field(default="", description="List of questions that help clarify uncertainties")
    stories: Optional[list[Story]] = Field(default=[], description="Ordered user stories")

    # Conversation state
    stage: SpecifyStage = SpecifyStage.STARTING
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    last_processed_comment_id: int | None = None

    # Specification output
    specification_complete: bool = False
    completion_keyword: str | None = None  # "LGTM", "LFG", etc.


class SpecifyOutput(BaseModel):
    """Output from specify flow."""

    stories: list[dict[str, Any]]
    repo_owner: str
    repo_name: str
    issue_id: int
    conversation_history: list[dict[str, Any]]
    specification_summary: str
