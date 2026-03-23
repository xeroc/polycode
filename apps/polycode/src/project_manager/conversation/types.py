"""Conversation-driven specification flow models."""

from enum import Enum
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from flows.base import BaseFlowModel

if TYPE_CHECKING:
    from crews.plan_crew.types import Story


class ConversationStage(str, Enum):
    """Stages of the conversation flow."""

    INIT = "init"
    SPEC_ELCITATION = "spec_elicitation"
    SPEC_APPROVAL = "spec_approval"
    STORY_BREAKDOWN = "story_breakdown"
    STORY_APPROVAL = "story_approval"
    RALPH_INIT = "ralph_init"
    RALPH_EXECUTION = "ralph_execution"
    COMPLETED = "completed"


class ConversationMessage(BaseModel):
    """A message in the conversation."""

    author: str = Field(description="Message author ('user' or 'llm')")
    content: str = Field(description="Message content")
    timestamp: Optional[str] = Field(default=None, description="ISO timestamp")


class NewCommentInput(BaseModel):
    """Input when a new comment is received."""

    comment_id: int
    author: str
    content: str
    thumbs_up: bool = False


class ReactionInput(BaseModel):
    """Input when a thumbs up reaction is detected."""

    comment_id: int
    reaction: str


class ConversationFlowState(BaseFlowModel):
    """State for conversation flow."""

    stage: ConversationStage = Field(default=ConversationStage.INIT)
    messages: list[ConversationMessage] = Field(default_factory=list, description="Conversation history")
    specification: Optional[str] = Field(default=None, description="Final approved specification")
    requirements: list[str] = Field(default_factory=list)
    stories: list["Story"] = Field(default_factory=list, description="User stories")
    approved_story_id: Optional[int] = Field(default=None, description="ID of story to execute next")
    ralph_output: Optional[str] = Field(default=None, description="Ralph agent output")
    build_success: bool = Field(default=False)
    test_success: bool = Field(default=False)
    last_comment_id: Optional[int] = Field(default=None, description="Last comment ID we posted")
    thumbs_up_given: bool = Field(default=False, description="User gave thumbs up")
