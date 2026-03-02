"""Project management abstraction layer."""

from .base import ProjectManager
from .github import GitHubProjectManager
from .types import (
    Issue,
    IssueStatus,
    ProjectConfig,
    ProjectItem,
    StatusMapping,
)
from .watcher import RepoWatcher

__all__ = [
    "ProjectManager",
    "GitHubProjectManager",
    "Issue",
    "IssueStatus",
    "ProjectConfig",
    "ProjectItem",
    "StatusMapping",
    "RepoWatcher",
]
