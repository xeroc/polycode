"""GitHub-specific project manager implementation."""

import logging
import os

import github

from .base import ProjectManager
from .github_projects_client import GitHubProjectsClient
from .types import Issue, ProjectConfig, ProjectItem

log = logging.getLogger(__name__)


class GitHubProjectManager(ProjectManager):
    """GitHub Projects V2 implementation of ProjectManager."""

    def __init__(self, config: ProjectConfig) -> None:
        """Initialize GitHub project manager.

        Args:
            config: Project configuration

        Raises:
            ValueError: If token is not provided
        """
        super().__init__(config)

        token = config.token or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise ValueError(
                "GitHub token must be provided via config or GITHUB_TOKEN env var"
            )

        self.token = token
        self.github_client = github.Github(auth=github.Auth.Token(token))
        self.projects_client = GitHubProjectsClient(token, config.repo_name)

        self._project_id: str | None = None
        self._status_field_id: str | None = None
        self._status_options: dict[str, str] | None = None

    @property
    def project_id(self) -> str:
        """Lazy-load project ID."""
        if self._project_id is None:
            project_number = int(self.config.project_identifier)
            self._project_id = self.projects_client.get_project_id(
                self.config.repo_owner, project_number
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

    def get_open_issues(self) -> list[Issue]:
        """Get all open issues from the repository.

        Returns:
            List of open issues
        """
        repo = self.github_client.get_repo(
            f"{self.config.repo_owner}/{self.config.repo_name}"
        )
        issues: list[Issue] = []

        for issue in repo.get_issues(state="open"):
            issues.append(
                Issue(
                    id=issue.number,
                    number=issue.number,
                    title=issue.title,
                    body=issue.body,
                    node_id=issue.node_id,
                    url=issue.html_url,
                    labels=[label.name for label in issue.labels],
                )
            )

        return issues

    def get_project_items(self) -> list[ProjectItem]:
        """Get all items in the project.

        Returns:
            List of project items
        """
        items = self.projects_client.get_project_items(self.project_id)
        return [
            ProjectItem(
                id=item.project_item_id,
                issue_number=item.issue_number,
                title=item.title,
                body=item.body,
                status=item.status,
            )
            for item in items
        ]

    def add_issue_to_project(self, issue: Issue) -> str | None:
        """Add an issue to the project.

        Args:
            issue: Issue to add

        Returns:
            Project item ID if successful, None otherwise
        """
        if not issue.node_id:
            log.warning(f"Issue #{issue.number} has no node_id")
            return None

        try:
            item_id = self.projects_client.add_issue_to_project(
                self.project_id, issue.node_id
            )
            log.info(f"Added issue #{issue.number} to project")
            return item_id
        except Exception as e:
            log.error(f"Failed to add issue #{issue.number} to project: {e}")
            return None

    def update_issue_status(self, issue_number: int, status: str) -> bool:
        """Update the status of an issue in the project.

        Args:
            issue_number: Issue number
            status: New status value (provider-specific)

        Returns:
            True if successful, False otherwise
        """
        item = self.find_project_item(issue_number)
        if not item:
            log.warning(f"Issue #{issue_number} not found in project")
            return False

        field_id, options = self.status_field_info
        if status not in options:
            log.warning(
                f"Status '{status}' not found in project options: {list(options.keys())}"
            )
            return False

        success = self.projects_client.update_item_status(
            self.project_id, item.id, field_id, options[status]
        )
        if success:
            log.info(f"Updated issue #{issue_number} to '{status}'")
        return success

    def add_comment(self, issue_number: int, comment: str) -> bool:
        """Add a comment to an issue.

        Args:
            issue_number: Issue number
            comment: Comment text

        Returns:
            True if successful, False otherwise
        """
        try:
            repo = self.github_client.get_repo(
                f"{self.config.repo_owner}/{self.config.repo_name}"
            )
            issue = repo.get_issue(issue_number)
            issue.create_comment(comment)
            log.info(f"Added comment to issue #{issue_number}")
            return True
        except Exception as e:
            log.error(f"Failed to add comment to issue #{issue_number}: {e}")
            return False

    def merge_pull_request(
        self,
        pr_number: int,
        commit_message: str | None = None,
        merge_method: str = "merge",
    ) -> bool:
        """Merge a pull request into its base branch (typically develop).

        Args:
            pr_number: Pull request number
            commit_message: Optional custom commit message for the merge
            merge_method: Merge method - "merge", "squash", or "rebase" (default: "merge")

        Returns:
            True if successful, False otherwise
        """
        try:
            repo = self.github_client.get_repo(
                f"{self.config.repo_owner}/{self.config.repo_name}"
            )
            pr = repo.get_pull(pr_number)

            if pr.merged:
                log.warning(f"Pull request #{pr_number} is already merged")
                return True

            if pr.state != "open":
                log.error(
                    f"Pull request #{pr_number} is not open (state: {pr.state})"
                )
                return False

            if commit_message:
                result = pr.merge(
                    commit_message=commit_message, merge_method=merge_method
                )
            else:
                result = pr.merge(merge_method=merge_method)

            if result.merged:
                log.info(
                    f"Successfully merged pull request #{pr_number} "
                    f"into {pr.base.ref} using {merge_method}"
                )
                return True
            else:
                log.error(
                    f"Failed to merge pull request #{pr_number}: {result.message}"
                )
                return False

        except Exception as e:
            log.error(f"Failed to merge pull request #{pr_number}: {e}")
            return False
