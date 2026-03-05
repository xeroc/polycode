"""GitHub project status management using ProjectManager abstraction."""

import logging
import os

from project_manager import GitHubProjectManager
from project_manager.types import ProjectConfig

log = logging.getLogger(__name__)


class ProjectStatusManager:
    """Manages project status updates during feature development."""

    def __init__(
        self,
        repo_owner: str | None = None,
        repo_name: str | None = None,
        project_identifier: str | None = None,
    ) -> None:
        """Initialize project status manager.

        Args:
            repo_owner: Repository owner (defaults to env var or xeroc)
            repo_name: Repository name (defaults to env var or demo)
            project_identifier: Project ID/number (defaults to env var or 1)

        Raises:
            ValueError: If required configuration is missing
        """
        repo_owner = repo_owner or os.environ.get("REPO_OWNER", "xeroc")
        repo_name = repo_name or os.environ.get("REPO_NAME", "demo")
        project_identifier = project_identifier or os.environ.get(
            "PROJECT_IDENTIFIER", "1"
        )

        config = ProjectConfig(
            provider="github",
            repo_owner=repo_owner,
            repo_name=repo_name,
            project_identifier=project_identifier,
        )

        self.manager = GitHubProjectManager(config)

    def update_status(self, issue_number: int, status_name: str) -> bool:
        """Update issue status in the project.

        Args:
            issue_number: Issue number
            status_name: Target status name (e.g., "Reviewing", "Done")

        Returns:
            True if successful, False otherwise
        """
        return self.manager.update_issue_status(issue_number, status_name)

    def add_comment(self, issue_number: int, comment: str) -> bool:
        """Add a comment to an issue.

        Args:
            issue_number: Issue number
            comment: Comment text

        Returns:
            True if successful, False otherwise
        """
        return self.manager.add_comment(issue_number, comment)

    def merge_pull_request(
        self,
        pr_number: int,
        commit_message: str | None = None,
        merge_method: str = "merge",
    ) -> bool:
        """Merge a pull request into its base branch.

        Args:
            pr_number: Pull request number
            commit_message: Optional custom commit message for the merge
            merge_method: Merge method - "merge", "squash", or "rebase" (default: "merge")

        Returns:
            True if successful, False otherwise
        """
        return self.manager.merge_pull_request(
            pr_number, commit_message, merge_method
        )
