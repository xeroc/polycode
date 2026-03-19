"""Types for gitcore module."""

import os
from dataclasses import dataclass, field
from typing import Any

import git


@dataclass
class WorktreeConfig:
    """Configuration for git worktree operations."""

    branch_name: str
    base_branch: str = "develop"
    worktrees_dir: str | None = None
    symlink_deps: list[str] = field(
        default_factory=lambda: ["node_modules", ".venv", ".env"]
    )


@dataclass
class GitContext:
    """Context for git operations within a flow.

    Holds all the state needed for git operations during flow execution.
    """

    repo_path: str
    worktree_path: str = ""
    branch_name: str = ""
    repo_owner: str = ""
    repo_name: str = ""

    project_config: Any = None

    def __post_init__(self):
        if not self.worktree_path and self.repo_path and self.branch_name:
            self.worktree_path = self._compute_worktree_path()

    def _compute_worktree_path(self) -> str:
        if ".worktrees" in self.repo_path:
            base_path = os.path.join(self.repo_path, "..", "..")
        else:
            base_path = self.repo_path

        worktrees_dir = os.path.join(base_path, ".git", ".worktrees")
        return os.path.join(worktrees_dir, self.branch_name)

    @property
    def repo(self) -> git.Repo:
        if self.worktree_path and os.path.exists(self.worktree_path):
            return git.Repo(self.worktree_path)
        return git.Repo(self.repo_path)

    @property
    def root_repo(self) -> git.Repo:
        return git.Repo(self.repo_path)

    def get_commit_url(self, commit_sha: str) -> str:
        return (
            f"https://github.com/{self.repo_owner}/{self.repo_name}/commit/{commit_sha}"
        )

    @classmethod
    def from_flow_state(cls, state: Any) -> "GitContext":
        return cls(
            repo_path=getattr(state, "path", ""),
            worktree_path=getattr(state, "repo", ""),
            branch_name=getattr(state, "branch", ""),
            repo_owner=getattr(state, "repo_owner", "") or "",
            repo_name=getattr(state, "repo_name", "") or "",
            project_config=getattr(state, "project_config", None),
        )
