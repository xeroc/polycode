"""Common types for project management."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class IssueStatus(str, Enum):
    """Standardized issue status values."""

    TODO = "todo"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    REVIEWING = "reviewing"
    DONE = "done"
    BLOCKED = "blocked"


class Issue(BaseModel):
    """Generic issue representation."""

    id: int
    number: int
    title: str
    body: str | None = None
    node_id: str | None = None
    url: str | None = None
    labels: list[str] = []


class ProjectItem(BaseModel):
    """Generic project item representation."""

    id: str
    issue_number: int
    title: str
    body: str | None = None
    status: str | None = None
    issue_id: int | None = None


class StatusMapping(BaseModel):
    """Maps standardized statuses to provider-specific values."""

    todo: str = "Todo"
    ready: str = "Ready"
    in_progress: str = "In progress"
    reviewing: str = "In review"
    done: str = "Done"
    blocked: str = "Blocked"

    def to_provider_status(self, status: IssueStatus) -> str:
        """Convert standardized status to provider-specific value."""
        return getattr(self, status.value)

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "StatusMapping":
        """Create mapping from dictionary."""
        return cls(
            todo=data.get("todo", "Todo"),
            ready=data.get("ready", "Ready"),
            in_progress=data.get("in_progress", "In progress"),
            reviewing=data.get("reviewing", "In review"),
            done=data.get("done", "Done"),
            blocked=data.get("blocked", "Blocked"),
        )


class ProjectConfig(BaseModel):
    """Configuration for a project manager."""

    provider: str
    repo_owner: str
    repo_name: str
    project_identifier: Optional[str] = None
    status_mapping: StatusMapping = StatusMapping()
    token: str | None = None
    extra: dict[str, Any] = {}


class IssueComment(BaseModel):
    username: str
    body: str
    id: int
