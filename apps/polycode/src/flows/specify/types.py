"""Specify flow types."""

from enum import Enum
from typing import Optional

from pydantic import Field

from crews.plan_crew.types import Story
from flows.base import BaseFlowModel
from project_manager.types import IssueComment


class SpecifyStage(str, Enum):
    """Stage of specify flow."""

    STARTING = "starting"
    WAITING = "waiting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class SpecifyFlowState(BaseFlowModel):
    """State persisted between specify flow steps."""

    questions: Optional[list[str]] = Field(default=[], description="List of questions that help clarify uncertainties")
    specifications: Optional[list[str]] = Field(default=[], description="Final approved specification")
    requirements: Optional[list[str]] = Field(default=[], description="List of requirements")
    assumptions: Optional[list[str]] = Field(default=[], description="List of assumptions")

    stories: Optional[list[Story]] = Field(default=[], description="Ordered user stories")

    # Conversation state
    stage: SpecifyStage = SpecifyStage.STARTING
    conversation_history: list[IssueComment] = Field(default_factory=list)

    # Specification output
    specification_complete: bool = False
    completion_keyword: str | None = None  # "LGTM", "LFG", etc.
