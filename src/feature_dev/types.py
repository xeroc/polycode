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

    issue_id: int = Field(description="issue id on github")
    task: str = Field(default="", description="Feature development task")

    repo: str = Field(default="", description="Path to repository")
    branch: str = Field(default="", description="Feature branch name")

    build_cmd: Optional[str] = Field(default=None, description="Build command")
    test_cmd: Optional[str] = Field(default=None, description="Test command")
    ci_notes: Optional[str] = Field(default=None, description="CI configuration notes")
    baseline: Optional[str] = Field(default=None, description="Baseline status")
    findings: Optional[str] = Field(
        default=None, description="Findings around stack, conventions and used patterns"
    )
    stories: Optional[List[Story]] = Field(
        default=[], description="Ordered user stories"
    )

    changes: Optional[List[str]] = Field(default=[], description="What was implemented")
    tests: Optional[List[str]] = Field(
        default=[], description="Tests that were written"
    )

    current_story: Optional[str] = Field(
        default=None, description="Current story being implemented"
    )
    completed_stories: Optional[List[Story]] = Field(
        default=[], description="Completed stories"
    )
    current_story_title: Optional[str] = Field(
        default=None, description="Current story title"
    )
    current_story_id: Optional[int] = Field(
        default=None, description="Current story ID"
    )

    verified: bool = Field(default=False, description="All stories verified")
    tested: bool = Field(default=False, description="Integration tests passed")

    pr_url: Optional[str] = Field(default=None, description="Pull request URL")
    pr_number: Optional[int] = Field(default=None, description="Pull request number")
    review_status: Optional[str] = Field(default=None, description="PR review status")
    diff: Optional[str] = Field(default=None, description="code diff")

    commit_title: Optional[str] = Field(
        default=None,
        description="Commit Message title including conventional commit prefix",
    )
    commit_message: Optional[str] = Field(
        default=None, description="The body of the commit message"
    )
    commit_footer: Optional[str] = Field(
        default=None, description="Commit message footer"
    )


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
    findings: str = Field(
        description="Findings around stack, conventions and used patterns"
    )


class ImplementOutput(BaseModel):
    """Output from implementation phase."""

    status: str = Field(default="done", description="Status")
    changes: str = Field(description="What was implemented")
    tests: str = Field(description="Tests that were written")


class VerifyOutput(BaseModel):
    """Output from verification phase."""

    status: str = Field(description="Status: done or retry")
    verified: Optional[str] = Field(default=None, description="What was confirmed")
    issues: Optional[List[str]] = Field(
        default=None, description="Issues requiring fixes"
    )


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


class CommitMessageOutput(BaseModel):
    title: str = Field(
        description="Commit Message title including conventional commit prefix"
    )
    message: str = Field(description="The body of the commit message")
    footer: str = Field(description="Commit message footer")
