from typing import Optional

from pydantic import Field

from crews.plan_crew.types import Story
from flowbase import BaseFlowModel


class RalphLoopState(BaseFlowModel):
    stories: Optional[list[Story]] = Field(default=[], description="Ordered user stories")
    agent_output: Optional[str] = Field(default="", description="ralph agent output")
    build_success: bool = Field(default=False, description="Build passed")
    test_success: bool = Field(default=False, description="Build passed")

    planning_comment_id: Optional[int] = Field(default=None, description="ID of the planning progress comment")
    commit_urls: dict[int, str] = Field(default_factory=dict, description="Story ID to commit URL mapping")
