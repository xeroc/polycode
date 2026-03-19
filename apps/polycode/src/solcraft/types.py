from typing import List, Optional

from pydantic import BaseModel, Field

from flowbase import BaseFlowModel


class Story(BaseModel):
    id: int = Field(description="Story ID")
    title: str = Field(description="Story title")
    description: str = Field(description="Story description")
    acceptance_criteria: List[str] = Field(description="Acceptance criteria")


class PlanOutput(BaseModel):
    stories: List[Story] = Field(description="Ordered user stories")
    build_cmd: str = Field(description="Build command")
    test_cmd: str = Field(description="Test command")
    ci_notes: Optional[str] = Field(default=None, description="CI configuration notes")
    baseline: str = Field(description="Baseline status")
    findings: str = Field(description="Findings around stack, conventions and used patterns")
    purpose: str = Field(description="Short description of what the repo does")
    tech_stack: List[str] = Field(description="Primary languages, Key frameworks, Main dependencies")
    architecture: str = Field(description="High-level architecture pattern and organization")
    entry_points: List[str] = Field(description="Paths to main application starts")
    configuration: List[str] = Field(description="Paths to config files")
    documentation: List[str] = Field(description="Paths to key docs")


class ImplementOutput(BaseModel):
    status: str = Field(default="done", description="Status")
    changes: str = Field(description="What was implemented")
    tests: str = Field(description="Tests that were written")
    title: str = Field(description="Commit Message title including conventional commit prefix")
    message: str = Field(description="The body of commit message")
    footer: str = Field(description="Commit message footer")


class SolcraftState(BaseFlowModel):
    id: str = Field(default="", description="unique id")
    build_cmd: Optional[str] = Field(default=None, description="Build command")
    test_cmd: Optional[str] = Field(default=None, description="Test command")
    ci_notes: Optional[str] = Field(default=None, description="CI configuration notes")
    baseline: Optional[str] = Field(default=None, description="Baseline status")
    findings: Optional[str] = Field(
        default=None,
        description="Findings around stack, conventions and used patterns",
    )
    stories: Optional[List[Story]] = Field(default=[], description="Ordered user stories")
    changes: Optional[List[str]] = Field(default=[], description="What was implemented")
    tests: Optional[List[str]] = Field(default=[], description="Tests that were written")
    current_story: Optional[str] = Field(default=None, description="Current story being implemented")
    completed_stories: Optional[List[Story]] = Field(default=[], description="Completed stories")
    current_story_title: Optional[str] = Field(default=None, description="Current story title")
    current_story_id: Optional[int] = Field(default=None, description="Current story ID")
    verified: bool = Field(default=False, description="All stories verified")
    tested: bool = Field(default=False, description="Integration tests passed")
    review_status: Optional[str] = Field(default=None, description="PR review status")
    diff: Optional[str] = Field(default=None, description="code diff")
    task_templates: Optional[List[str]] = Field(default=None, description="Paths to task template markdown files")


class TaskTemplate(BaseModel):
    name: str = Field(description="Task name (e.g., implement_task)")
    description: str = Field(description="Task description template")
    expected_output: str = Field(description="Expected output description")
    agent: str = Field(default="developer", description="Agent to assign")
    context: Optional[List[str]] = Field(default=None, description="List of task names this depends on")
    output_pydantic: Optional[str] = Field(default=None, description="Pydantic model name for structured output")
