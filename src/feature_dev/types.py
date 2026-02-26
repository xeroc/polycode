from typing import List, Optional

from pydantic import BaseModel, Field


class Story(BaseModel):
    """Individual user story."""

    id: int = Field(description="Story ID")
    title: str = Field(description="Story title")
    description: str = Field(description="Story description")
    acceptance_criteria: List[str] = Field(description="Acceptance criteria")


class FeatureDevState(BaseModel):
    """State for feature development workflow."""

    task: str = Field(default="", description="Feature development task")

    repo: str = Field(default="", description="Path to repository")
    branch: str = Field(default="", description="Feature branch name")

    build_cmd: Optional[str] = Field(default=None, description="Build command")
    test_cmd: Optional[str] = Field(default=None, description="Test command")
    ci_notes: Optional[str] = Field(default=None, description="CI configuration notes")
    baseline: Optional[str] = Field(default=None, description="Baseline status")
    stories: Optional[List[Story]] = Field(default=None, description="Ordered user stories")

    changes: Optional[str] = Field(default=None, description="What was implemented")
    tests: Optional[str] = Field(default=None, description="Tests that were written")

    current_story: Optional[str] = Field(default=None, description="Current story being implemented")
    completed_stories: Optional[List[Story]] = Field(default=[], description="Completed stories")
    current_story_title: Optional[str] = Field(default=None, description="Current story title")
    current_story_id: Optional[int] = Field(default=None, description="Current story ID")

    verified: bool = Field(default=False, description="All stories verified")
    tested: bool = Field(default=False, description="Integration tests passed")

    pr_url: Optional[str] = Field(default=None, description="Pull request URL")
    review_status: Optional[str] = Field(default=None, description="PR review status")


class PlanOutput(BaseModel):
    """Output from planning phase."""

    status: str = Field(default="done", description="Status")
    repo: str = Field(description="Repository path")
    branch: str = Field(description="Feature branch name")
    stories: List[Story] = Field(description="Ordered user stories")


class SetupOutput(BaseModel):
    """Output from setup phase."""

    status: str = Field(default="done", description="Status")
    build_cmd: str = Field(description="Build command")
    test_cmd: str = Field(description="Test command")
    ci_notes: Optional[str] = Field(default=None, description="CI configuration notes")
    baseline: str = Field(description="Baseline status")


class ImplementOutput(BaseModel):
    """Output from implementation phase."""

    status: str = Field(default="done", description="Status")
    changes: str = Field(description="What was implemented")
    tests: str = Field(description="Tests that were written")


class VerifyOutput(BaseModel):
    """Output from verification phase."""

    status: str = Field(description="Status: done or retry")
    verified: Optional[str] = Field(default=None, description="What was confirmed")
    issues: Optional[List[str]] = Field(default=None, description="Issues requiring fixes")


class TestOutput(BaseModel):
    """Output from testing phase."""

    status: str = Field(description="Status: done or retry")
    results: Optional[str] = Field(default=None, description="Test results")
    failures: Optional[List[str]] = Field(default=None, description="Test failures")


class ReviewOutput(BaseModel):
    """Output from review phase."""

    status: str = Field(description="Status: done or retry")
    decision: str = Field(description="Decision: approved or changes_requested")
    feedback: Optional[List[str]] = Field(default=None, description="Review feedback")
