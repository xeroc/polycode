"""Retro module data models."""

from datetime import UTC, datetime
from typing import Optional

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(UTC)


class ActionableItem(BaseModel):
    """Actionable improvement suggestion."""

    title: str = Field(description="Short title of improvement")
    description: str = Field(description="Detailed explanation")
    priority: str = Field(default="medium", description="Priority: high, medium, low")


class RetroEntry(BaseModel):
    """Structured retrospective for a flow/story execution.

    Stored in git-notes for transportability, mirrored in PostgreSQL
    for querying and pattern analysis.
    """

    commit_sha: str = Field(description="Git commit SHA")

    flow_id: str = Field(description="Flow execution UUID")

    story_id: Optional[int] = Field(default=None, description="Story ID if flow-based")

    story_title: Optional[str] = Field(default=None, description="Story title if flow-based")

    repo_owner: str = Field(description="GitHub repository owner")
    repo_name: str = Field(description="GitHub repository name")

    timestamp: datetime = Field(default_factory=_now, description="When retro was generated")

    retro_type: str = Field(description="Type: success, failure, partial, anomaly")

    what_worked: list[str] = Field(default_factory=list, description="What went well")

    what_failed: list[str] = Field(default_factory=list, description="What didn't work")

    root_causes: list[str] = Field(default_factory=list, description="Root causes identified")

    actionable_improvements: list[ActionableItem] = Field(default_factory=list, description="Concrete improvements")

    time_to_completion_seconds: Optional[int] = Field(default=None, description="Duration in seconds")

    retry_count: int = Field(default=0, description="Retry iterations")

    test_coverage_impact: Optional[float] = Field(default=None, description="Test coverage change percentage")

    build_duration_ms: Optional[int] = Field(default=None, description="Build duration in milliseconds")

    test_duration_ms: Optional[int] = Field(default=None, description="Test duration in milliseconds")


class RetroQuery(BaseModel):
    """Query parameters for retrospectives."""

    repo_owner: Optional[str] = None
    repo_name: Optional[str] = None
    retro_type: Optional[str] = None
    since: Optional[datetime] = None
    limit: int = Field(default=50, description="Max results")
