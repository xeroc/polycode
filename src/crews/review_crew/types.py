from typing import List, Optional

from pydantic import BaseModel, Field


class ReviewOutput(BaseModel):
    """Output from review phase."""

    status: str = Field(description="Status: done or retry")
    decision: str = Field(description="Decision: approved or changes_requested")
    feedback: Optional[List[str]] = Field(default=None, description="Review feedback")
