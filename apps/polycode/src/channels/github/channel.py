"""GitHub channel adapter."""

import logging

from channels.base import BaseChannel
from channels.types import ChannelResult, ChannelType, Notification, Reaction
from project_manager import GitHubProjectManager
from project_manager.types import ProjectConfig

log = logging.getLogger(__name__)


class GitHubChannel(BaseChannel):
    """GitHub channel adapter that wraps GitHubProjectManager."""

    channel_type = ChannelType.GITHUB

    def __init__(self, project_config: ProjectConfig) -> None:
        """Initialize GitHub channel.

        Args:
            project_config: Project configuration for GitHub
        """
        self._project_manager = GitHubProjectManager(project_config)

    @property
    def project_manager(self) -> GitHubProjectManager:
        """Get the underlying GitHub project manager."""
        return self._project_manager

    async def send(self, notification: Notification) -> ChannelResult:
        """Send a notification to a GitHub issue.

        Args:
            notification: The notification containing content and context

        Returns:
            Result of the send operation
        """
        issue_id = notification.context.get("issue_id")
        if not issue_id:
            return ChannelResult(
                success=False, channel_type=self.channel_type, error="issue_id required in notification context"
            )

        try:
            # Format the content based on notification level
            formatted_content = self._format_content(notification)

            success = self._project_manager.add_comment(issue_number=int(issue_id), comment=formatted_content)

            if success:
                # Get the comment ID for the newly created comment
                comment_id = self._project_manager.get_last_comment_by_user(
                    int(issue_id), self._project_manager.bot_username
                )
                return ChannelResult(
                    success=True,
                    channel_type=self.channel_type,
                    message_id=str(comment_id) if comment_id else None,
                    metadata={"issue_id": issue_id},
                )
            return ChannelResult(success=False, channel_type=self.channel_type, error="Failed to add comment")

        except Exception as e:
            log.error(f"Failed to send GitHub notification: {e}")
            return ChannelResult(success=False, channel_type=self.channel_type, error=str(e))

    def _format_content(self, notification: Notification) -> str:
        """Format notification content with level indicator.

        Args:
            notification: The notification to format

        Returns:
            Formatted markdown content
        """
        level_emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "🚨",
            "success": "✅",
        }

        emoji = level_emoji.get(notification.level.value, "ℹ️")
        header = f"## {emoji} {notification.level.value.upper()}\n\n"

        return f"{header}{notification.content}"

    def supports_reactions(self) -> bool:
        """GitHub issues support reactions via comments."""
        return False

    def supports_threads(self) -> bool:
        """GitHub issues support threaded conversations via comments."""
        return True

    async def add_reaction(self, reaction: Reaction) -> ChannelResult:
        """Add a reaction to a GitHub comment (not supported)."""
        return ChannelResult(
            success=False, channel_type=self.channel_type, error="Reactions not supported in GitHub channel"
        )

    async def get_reactions(self, message_id: str) -> list[Reaction]:
        """Get reactions for a message (not supported)."""
        return []
