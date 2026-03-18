from typing import List, Optional

from pydantic import BaseModel, Field


class Story(BaseModel):
    """Individual user story."""

    id: int = Field(description="Story ID")
    title: str = Field(description="Story title")
    description: str = Field(description="Story description")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Acceptance criteria")
    iteration: int = Field(default=0, description="Current Ralph loop iteration for this story")
    completed: bool = Field(default=False, description="Whether story passed Ralph loop")
    errors: List[str] = Field(default_factory=list, description="Errors from previous iterations")


class PlanOutput(BaseModel):
    """Output from planning phase."""

    stories: List[Story] = Field(description="Ordered user stories")

    build_cmd: str = Field(description="Build command")
    test_cmd: str = Field(description="Test command")
    ci_notes: Optional[str] = Field(default=None, description="CI configuration notes")
    baseline: str = Field(description="Baseline status")
    findings: str = Field(description="Findings around stack, conventions and used patterns")
    purpose: Optional[str] = Field(default=None, description="Short description of what the repo does")
    tech_stack: Optional[List[str]] = Field(
        default=None,
        description="Primary languages, Key frameworks, Main dependencies",
    )
    architecture: Optional[str] = Field(default=None, description="High-level architecture pattern and organization")
    entry_points: Optional[List[str]] = Field(default=None, description="Paths to main application starts")
    configuration: Optional[List[str]] = Field(default=None, description="Paths to config files")
    documentation: Optional[List[str]] = Field(default=None, description="Paths to key docs")
