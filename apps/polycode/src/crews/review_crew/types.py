from typing import Literal

from pydantic import BaseModel, Field


class ReviewerFeedback(BaseModel):
    """Feedback from individual reviewer persona."""

    reviewer_name: str = Field(description="Name of the reviewer persona")
    reviewer_role: str = Field(description="Role/specialty of the reviewer")
    decision: Literal["approved", "changes_requested", "blocked"] = Field(description="Individual review decision")
    feedback: list[str] = Field(default=[], description="Review feedback items")
    doc_improvements: list[str] = Field(default=[], description="Suggested doc improvements")


class ReviewOutput(BaseModel):
    """Aggregated multi-persona review output."""

    overall_decision: Literal["approved", "changes_requested", "blocked"] = Field(
        description="Aggregated decision across all reviewers"
    )
    status: str = Field(description="Status: done or retry")
    reviewer_feedback: list[ReviewerFeedback] = Field(default=[], description="Feedback from each reviewer persona")
    required_changes: list[str] = Field(default=[], description="Changes required before approval")
    doc_improvements: list[str] = Field(default=[], description="Doc improvements suggested during review")
