"""Project management abstraction layer."""

from .base import ProjectManager
from .flow_runner import FlowRunner
from .git_utils import get_github_repo_from_local
from .github import GitHubProjectManager
from .github_conversation import GitHubConversationManager
from .module import ProjectManagerModule
from .types import (
    Issue,
    IssueStatus,
    ProjectConfig,
    ProjectItem,
    StatusMapping,
)

__all__ = [
    "ProjectManager",
    "GitHubProjectManager",
    "GitHubConversationManager",
    "FlowRunner",
    "ProjectManagerModule",
    "Issue",
    "IssueStatus",
    "ProjectConfig",
    "ProjectItem",
    "StatusMapping",
    "get_github_repo_from_local",
]
