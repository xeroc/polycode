"""Conversation crew types."""

from pydantic import BaseModel, Field


class SpecOutput(BaseModel):
    """Output from specification elicitation."""

    questions: list[str] = Field(description="List of questions that help clarify uncertainties")
    specifications: list[str] = Field(description="Final approved specification")
    requirements: list[str] = Field(description="List of requirements")
    assumptions: list[str] = Field(description="List of assumptions")
