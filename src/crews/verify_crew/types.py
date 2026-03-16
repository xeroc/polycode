from typing import List, Optional

from pydantic import BaseModel, Field


class VerifyOutput(BaseModel):
    """Output from verification phase."""

    status: str = Field(description="Status: done or retry")
    verified: Optional[str] = Field(default=None, description="What was confirmed")
    issues: Optional[List[str]] = Field(default=None, description="Issues requiring fixes")
