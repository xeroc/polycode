"""Gitcore module implementation for the Polycode plugin system."""

import logging
from typing import Any

import pluggy

from gitcore.hooks import GitcoreHooks
from modules.context import ModuleContext

log = logging.getLogger(__name__)


class GitcoreModule:
    """Gitcore module: Git operations as a built-in Polycode module.

    This module provides git functionality (clone, checkout, worktree, commit, push)
    to flows via the GitOperations class. It doesn't register any hooks by default,
    but provides the git infrastructure for other flows to use.
    """

    name = "gitcore"
    version = "0.1.0"
    dependencies: list[str] = []

    @classmethod
    def on_load(cls, context: ModuleContext) -> None:
        """Initialize gitcore module.

        Currently just logs initialization. Git operations are available
        via the gitcore.operations module without any setup required.
        """
        log.info(f"📦 Gitcore module loaded (v{cls.version})")

    @classmethod
    def register_hooks(cls, hook_manager: pluggy.PluginManager) -> None:
        """Register gitcore hooks.

        Gitcore doesn't register lifecycle hooks by default, but modules
        can extend it to add git-related hooks.
        """
        hook_manager.register(GitcoreHooks())
        log.info("🏹 Registered GitModuleHooks")

    @classmethod
    def get_models(cls) -> list[type]:
        """Return ORM models for this module.

        Gitcore doesn't define any database models.
        """
        return []

    @classmethod
    def get_tasks(cls) -> list[dict[str, Any]]:
        """Return Celery task definitions for this module."""
        return []
