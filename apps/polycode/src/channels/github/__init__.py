"""GitHub channel module."""

import logging

from channels.github.channel import GitHubChannel
from channels.types import ChannelType
from modules.channels import ChannelRegistry

log = logging.getLogger(__name__)

__all__ = ["GitHubChannel"]


def _create_github_channel(config, project_config):
    """Factory function for creating GitHub channel instances.

    Args:
        config: ChannelConfig with GitHub-specific settings
        project_config: ProjectConfig for GitHub API access

    Returns:
        GitHubChannel instance
    """
    if not project_config:
        raise ValueError("GitHub channel requires project_config")

    return GitHubChannel(project_config)


ChannelRegistry.register(ChannelType.GITHUB, _create_github_channel)
log.debug("📡 Registered GitHub channel")
