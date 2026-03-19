from typing import List, Optional
from pydantic import BaseModel, Field


class ImplementOutput(BaseModel):
    """Output from implementation phase."""

    status: str = Field(default="done", description="Status")
    changes: str = Field(description="What was implemented")
    tests: str = Field(description="Tests that were written")

    title: str = Field(description="Commit Message title including conventional commit prefix")
    message: str = Field(description="The body of commit message")
    footer: str = Field(description="Commit message footer")


class TaskTemplate(BaseModel):
    name: str = Field(description="Task name (e.g., implement_task)")
    description: str = Field(description="Task description template")
    expected_output: str = Field(description="Expected output description")
    agent: str = Field(default="developer", description="Agent to assign")
    context: Optional[List[str]] = Field(default=None, description="List of task names this depends on")
    output_pydantic: Optional[str] = Field(default=None, description="Pydantic model name for structured output")
