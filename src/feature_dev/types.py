from typing import List, Optional

from pydantic import BaseModel, Field


class FeatureDevState(BaseModel):
    """State for feature development workflow."""

    task: str = Field(default="", description="Feature development task")

    repo: str = Field(default="", description="Path to repository")
    branch: str = Field(default="", description="Feature branch name")

    user_stories: List[str] = Field(default_factory=list, description="Ordered user stories")
    current_story_index: int = Field(default=0, description="Current story being implemented")

    build_cmd: Optional[str] = Field(default=None, description="Build command")
    test_cmd: Optional[str] = Field(default=None, description="Test command")
    baseline: Optional[str] = Field(default=None, description="Baseline status")

    implemented_stories: List[str] = Field(default_factory=list, description="Completed stories")
    current_changes: Optional[str] = Field(default=None, description="Current implementation changes")

    verified: bool = Field(default=False, description="All stories verified")
    tested: bool = Field(default=False, description="Integration tests passed")

    pr_url: Optional[str] = Field(default=None, description="Pull request URL")
    review_status: Optional[str] = Field(default=None, description="PR review status")
