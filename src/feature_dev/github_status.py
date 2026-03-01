"""GitHub project status management for feature development workflow."""

import logging
import os

from github import Github

from github_issues.github_project import GitHubProjectsClient

log = logging.getLogger(__name__)

REPO_OWNER = "xeroc"
REPO_NAME = "demo"
PROJECT_NUMBER = 1


class ProjectStatusManager:
    """Manages GitHub project status updates during feature development."""

    def __init__(self) -> None:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable not set")

        self.github_client = Github(token)
        self.projects_client = GitHubProjectsClient(token, REPO_NAME)
        self._project_id: str | None = None
        self._status_field_id: str | None = None
        self._status_options: dict[str, str] | None = None

    @property
    def project_id(self) -> str:
        """Lazy-load project ID."""
        if self._project_id is None:
            self._project_id = self.projects_client.get_project_id(
                REPO_OWNER, PROJECT_NUMBER
            )
        return self._project_id

    @property
    def status_field_info(self) -> tuple[str, dict[str, str]]:
        """Lazy-load status field ID and options."""
        if self._status_field_id is None or self._status_options is None:
            self._status_field_id, self._status_options = (
                self.projects_client.get_status_field_id(self.project_id)
            )
        return self._status_field_id, self._status_options

    def get_project_item_id(self, issue_number: int) -> str | None:
        """Find project item ID by issue number.

        Args:
            issue_number: GitHub issue number.

        Returns:
            Project item ID if found, None otherwise.
        """
        items = self.projects_client.get_project_items(self.project_id)
        for item in items:
            if item.issue_number == issue_number:
                return item.project_item_id
        return None

    def update_status(self, issue_number: int, status_name: str) -> bool:
        """Update issue status in the project.

        Args:
            issue_number: GitHub issue number.
            status_name: Target status name (e.g., "Reviewing", "Done").

        Returns:
            True if successful, False otherwise.
        """
        item_id = self.get_project_item_id(issue_number)
        if not item_id:
            log.warning(f"Issue #{issue_number} not found in project")
            return False

        field_id, options = self.status_field_info
        if status_name not in options:
            log.warning(f"Status '{status_name}' not found in project options")
            return False

        success = self.projects_client.update_item_status(
            self.project_id, item_id, field_id, options[status_name]
        )
        if success:
            log.info(f"Updated issue #{issue_number} to '{status_name}'")
        return success

    def add_comment(self, issue_number: int, comment: str) -> bool:
        """Add a comment to an issue.

        Args:
            issue_number: GitHub issue number.
            comment: Comment text.

        Returns:
            True if successful, False otherwise.
        """
        try:
            repo = self.github_client.get_repo(f"{REPO_OWNER}/{REPO_NAME}")
            issue = repo.get_issue(issue_number)
            issue.create_comment(comment)
            log.info(f"Added comment to issue #{issue_number}")
            return True
        except Exception as e:
            log.error(f"Failed to add comment to issue #{issue_number}: {e}")
            return False
