from typing import List, Optional

from pydantic import BaseModel, Field

from flowbase import BaseFlowModel


class Story(BaseModel):
    """Individual user story."""

    id: int = Field(description="Story ID")
    title: str = Field(description="Story title")
    description: str = Field(description="Story description")
    iteration: int = Field(
        default=0, description="Current Ralph loop iteration for this story"
    )
    completed: bool = Field(
        default=False, description="Whether story passed Ralph loop"
    )
    errors: List[str] = Field(
        default_factory=list, description="Errors from previous iterations"
    )


class RalphLoopState(BaseFlowModel):
    stories: Optional[List[Story]] = Field(
        default=[], description="Ordered user stories"
    )
    agent_output: Optional[str] = Field(default="", description="ralph agent output")
    build_success: bool = Field(default=False, description="Build passed")
    test_success: bool = Field(default=False, description="Build passed")


class RalphOutput(BaseModel):
    changes: str = Field(description="What was implemented")
    title: str = Field(description="Commit title with conventional prefix")
    message: str = Field(description="Commit message body")
    footer: str = Field(default="", description="Commit footer")


class PlanOutput(BaseModel):
    """Output from planning phase."""

    stories: List[Story] = Field(description="Ordered user stories")

    build_cmd: str = Field(description="Build command")
    test_cmd: str = Field(description="Test command")
