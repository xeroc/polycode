"""Conversation crew types."""

from pydantic import BaseModel, Field


class SpecOutput(BaseModel):
    """Output from specification elicitation."""

    specification: str = Field(description="Final approved specification")
    requirements: list[str] = Field(description="List of requirements")
    assumptions: list[str] = Field(description="List of assumptions")
