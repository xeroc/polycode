from typing import List, Optional

from pydantic import BaseModel, Field


class BugFixState(BaseModel):
    """State for bug fix workflow with full type safety."""

    task: str = Field(default="", description="Bug report description")

    repo: str = Field(default="", description="Path to repository")
    branch: str = Field(default="", description="Bugfix branch name")
    severity: str = Field(default="", description="Severity: critical|high|medium|low")
    affected_area: str = Field(default="", description="Affected files/modules")
    reproduction: str = Field(default="", description="Reproduction steps")
    problem_statement: str = Field(default="", description="Clear problem description")

    root_cause: Optional[str] = Field(default=None, description="Root cause analysis")
    fix_approach: Optional[str] = Field(default=None, description="Proposed fix approach")

    build_cmd: Optional[str] = Field(default=None, description="Build command")
    test_cmd: Optional[str] = Field(default=None, description="Test command")
    baseline: Optional[str] = Field(default=None, description="Baseline status")

    changes: Optional[str] = Field(default=None, description="Changes made")
    regression_test: Optional[str] = Field(default=None, description="Regression test added")

    verified: bool = Field(default=False, description="Fix verified")
    issues: List[str] = Field(default_factory=list, description="Issues found during verification")

    pr_url: Optional[str] = Field(default=None, description="Pull request URL")

    retry_count: int = Field(default=0, description="Number of retries")
    max_retries: int = Field(default=3, description="Maximum retries allowed")
