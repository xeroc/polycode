"""Gitcore module - Git operations for Polycode flows.

This module provides git functionality (clone, checkout, worktree, commit, push)
as a pluggable module that integrates with the Polycode plugin system.
"""

from gitcore.module import GitcoreModule
from gitcore.operations import (
    GitOperations,
    cleanup_worktree,
    clone_repository,
    commit_changes,
    create_worktree,
    get_commit_url,
    list_git_tree,
    push_repo,
    sanitize_branch_name,
    setup_develop_branch,
    symlink_packages,
)
from gitcore.types import GitContext, WorktreeConfig

__all__ = [
    "GitOperations",
    "GitcoreModule",
    "GitContext",
    "WorktreeConfig",
    "clone_repository",
    "setup_develop_branch",
    "create_worktree",
    "symlink_packages",
    "commit_changes",
    "push_repo",
    "cleanup_worktree",
    "get_commit_url",
    "list_git_tree",
    "sanitize_branch_name",
]
