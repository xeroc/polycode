from typing import Optional

from pydantic import Field

from crews.plan_crew.types import Story
from flowbase import BaseFlowModel


class FeatureDevState(BaseFlowModel):
    """State for feature development workflow."""

    id: str = Field(default="", description="unique id")

    build_cmd: Optional[str] = Field(default=None, description="Build command")
    test_cmd: Optional[str] = Field(default=None, description="Test command")
    ci_notes: Optional[str] = Field(default=None, description="CI configuration notes")
    baseline: Optional[str] = Field(default=None, description="Baseline status")
    findings: Optional[str] = Field(
        default=None,
        description="Findings around stack, conventions and used patterns",
    )
    stories: Optional[list[Story]] = Field(default=[], description="Ordered user stories")

    changes: Optional[list[str]] = Field(default=[], description="What was implemented")
    tests: Optional[list[str]] = Field(default=[], description="Tests that were written")
    current_story: Optional[str] = Field(default=None, description="Current story being implemented")
    completed_stories: Optional[list[Story]] = Field(default=[], description="Completed stories")

    current_story_title: Optional[str] = Field(default=None, description="Current story title")
    current_story_id: Optional[int] = Field(default=None, description="Current story ID")
    verified: bool = Field(default=False, description="All stories verified")
    tested: bool = Field(default=False, description="Integration tests passed")

    review_status: Optional[str] = Field(default=None, description="PR review status")
    diff: Optional[str] = Field(default=None, description="code diff")
