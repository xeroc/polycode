"""Project management abstraction layer."""

from .base import ProjectManager
from .flow_runner import FlowRunner
from .git_utils import get_github_repo_from_local
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
    "FlowRunner",
    "Issue",
    "IssueStatus",
    "ProjectConfig",
    "ProjectItem",
    "StatusMapping",
    "RepoWatcher",
    "get_github_repo_from_local",
]
