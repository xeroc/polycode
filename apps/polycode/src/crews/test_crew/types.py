from typing import List, Optional

from pydantic import BaseModel, Field


class TestOutput(BaseModel):
    """Output from testing phase."""

    status: str = Field(description="Status: done or retry")
    results: Optional[str] = Field(default=None, description="Test results")
    failures: Optional[List[str]] = Field(default=None, description="Test failures")
