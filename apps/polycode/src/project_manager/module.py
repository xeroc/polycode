"""Project management module implementation for the Polycode plugin system."""

import logging

import pluggy

from modules.context import ModuleContext

log = logging.getLogger(__name__)


class ProjectManagerModule:
    """Project management module for flow lifecycle integration.

    This module provides GitHub-specific operations (PR creation, merging,
    issue management) as a plugin that responds to flow lifecycle hooks.
    It bridges the gap between generic flow phases and provider-specific
    project management operations.
    """

    name = "project_manager"
    version = "0.1.0"
    dependencies: list[str] = []

    @classmethod
    def on_load(cls, context: ModuleContext) -> None:
        """Initialize project manager module.

        The module doesn't require any special initialization - the
        project manager factory is created when hooks are registered.
        """
        log.info(f"📦 Project manager module loaded (v{cls.version})")

    @classmethod
    def register_hooks(cls, hook_manager: pluggy.PluginManager) -> None:
        """Register project management hooks.

        Creates and registers ProjectManagerHooks with a factory function
        that instantiates the appropriate ProjectManager based on config.
        """
        from project_manager import GitHubProjectManager
        from project_manager.hooks import ProjectManagerHooks

        def project_manager_factory(config):
            """Factory function to create project manager based on provider."""
            provider = getattr(config, "provider", "github")
            if provider == "github":
                return GitHubProjectManager(config)
            raise ValueError(f"Unknown project manager provider: {provider}")

        hook_manager.register(ProjectManagerHooks(project_manager_factory))
        log.info("🏹 Registered ProjectManagerHooks")

    @classmethod
    def get_models(cls) -> list[type]:
        """Return ORM models for this module.

        Project manager doesn't define any database models.
        """
        return []
