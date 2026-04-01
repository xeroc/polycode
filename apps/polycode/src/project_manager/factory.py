"""Factory for creating ProjectManager instances based on provider."""

from project_manager.base import ProjectManager
from project_manager.types import ProjectConfig


class ProjectManagerFactory:
    """Factory for creating ProjectManager instances based on provider."""

    @staticmethod
    def create(config: ProjectConfig) -> ProjectManager:
        """Create ProjectManager based on config.provider.

        Args:
            config: Project configuration with provider field

        Returns:
            ProjectManager instance (GitHubProjectManager, JiraProjectManager, etc.)

        Raises:
            ValueError: If provider is unsupported
        """
        provider = config.provider.lower()

        if provider == "github":
            from project_manager.github import GitHubProjectManager

            return GitHubProjectManager(config)
        elif provider == "jira":
            # from project_manager.jira import JiraProjectManager  # FUTURE
            #
            # return JiraProjectManager(config)
            raise NotImplementedError()
        elif provider == "gitlab":
            # from project_manager.gitlab import GitLabProjectManager  # FUTURE
            #
            # return GitLabProjectManager(config)
            raise NotImplementedError()
        else:
            raise ValueError(f"Unsupported provider: {provider}")
