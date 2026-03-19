"""GitHub-specific project manager implementation."""

import logging
from typing import cast

import github
from github.Repository import Repository

from .base import ProjectManager
from .config import settings
from .github_projects_client import GitHubProjectsClient
from .types import Issue, ProjectConfig, ProjectItem

log = logging.getLogger(__name__)


class GitHubProjectManager(ProjectManager):
    """GitHub Projects V2 implementation of ProjectManager."""

    github_client: github.Github
    repo: Repository

    def __repr__(self):
        return f"ProjectManager(github, repo={self.repo.url})"

    def __init__(self, config: ProjectConfig) -> None:
        """Initialize GitHub project manager.

        Args:
            config: Project configuration

        Raises:
            ValueError: If token is not provided
        """
        super().__init__(config)

        token = config.token or settings.GITHUB_TOKEN
        if not token:
            raise ValueError("GitHub token must be provided via config or GITHUB_TOKEN env var")

        self.token = token
        self.github_client = github.Github(auth=github.Auth.Token(token))
        self.projects_client = GitHubProjectsClient(token, config.repo_name)
        self.repo = self.github_client.get_repo(f"{self.config.repo_owner}/{self.config.repo_name}")
        self._project_id: str | None = None
        self._status_field_id: str | None = None
        self._status_options: dict[str, str] | None = None
        self._bot_username: str | None = None

    @property
    def bot_username(self) -> str:
        """Get the authenticated bot username."""
        if self._bot_username is None:
            self._bot_username = self.github_client.get_user().login
        return self._bot_username

    def get_comments(self, issue_number: int) -> list:
        """Get all comments for an issue.

        Args:
            issue_number: Issue number

        Returns:
            List of comments
        """
        try:
            issue = self.repo.get_issue(issue_number)
            return list(issue.get_comments())
        except Exception as e:
            log.error(f"Failed to get comments for issue #{issue_number}: {e}")
            return []

    def get_last_comment_by_user(self, issue_number: int, username: str) -> int | None:
        """Get the last comment ID by a specific user.

        Args:
            issue_number: Issue number
            username: GitHub username

        Returns:
            Comment ID if found, None otherwise
        """
        try:
            comments = self.get_comments(issue_number)
            for comment in reversed(comments):
                if comment.user and comment.user.login == username:
                    return comment.id
            return None
        except Exception as e:
            log.error(f"Failed to get last comment by {username} on issue #{issue_number}: {e}")
            return None

    def update_comment(self, issue_number: int, comment_id: int, body: str) -> bool:
        """Update an existing comment.

        Args:
            issue_number: Issue number
            comment_id: Comment ID to update
            body: New comment body

        Returns:
            True if successful, False otherwise
        """
        try:
            issue = self.repo.get_issue(issue_number)
            for comment in issue.get_comments():
                if comment.id == comment_id:
                    comment.edit(body)
                    log.info(f"Updated comment {comment_id} on issue #{issue_number}")
                    return True
            log.warning(f"Comment {comment_id} not found on issue #{issue_number}")
            return False
        except Exception as e:
            log.error(f"Failed to update comment {comment_id} on issue #{issue_number}: {e}")
            return False

    @property
    def project_id(self) -> str:
        """Lazy-load project ID."""
        if self._project_id is None:
            project_number = int(self.config.project_identifier) if self.config.project_identifier else None
            self._project_id = self.projects_client.get_project_id(self.config.repo_owner, project_number)
        return self._project_id

    @property
    def status_field_info(self) -> tuple[str, dict[str, str]]:
        """Lazy-load status field ID and options."""
        if self._status_field_id is None or self._status_options is None:
            self._status_field_id, self._status_options = self.projects_client.get_status_field_id(self.project_id)
        return self._status_field_id, self._status_options

    def get_open_issues(self) -> list[Issue]:
        """Get all open issues from the repository.

        Returns:
            List of open issues
        """
        issues: list[Issue] = []

        for issue in self.repo.get_issues(state="open"):
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
            item_id = self.projects_client.add_issue_to_project(self.project_id, issue.node_id)
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
            log.warning(f"Status '{status}' not found in project options: {list(options.keys())}")
            return False

        success = self.projects_client.update_item_status(self.project_id, item.id, field_id, options[status])
        if success:
            log.info(f"Updated issue #{issue_number} to '{status}'")
        return success

    def get_issue(self, issue_number: int) -> Issue:
        return cast(Issue, self.repo.get_issue(issue_number))

    def add_comment(self, issue_number: int, comment: str) -> bool:
        """Add a comment to an issue.

        Args:
            issue_number: Issue number
            comment: Comment text

        Returns:
            True if successful, False otherwise
        """
        try:
            issue = self.repo.get_issue(issue_number)
            issue.create_comment(comment)
            log.info(f"Added comment to issue #{issue_number}")
            return True
        except Exception as e:
            log.error(f"Failed to add comment to issue #{issue_number}: {e}")
            return False

    def has_label(self, issue_number: int, label_name: str) -> bool:
        """Check if a pull request has a specific label.

        Args:
            pr_number: Pull request number
            label_name: Name of the label to check for

        Returns:
            True if the label is present on the PR, False otherwise
        """
        try:
            pr = self.repo.get_issue(issue_number)

            # Check if any label matches the requested label name
            for label in pr.labels:
                if label.name == label_name:
                    log.info(f"Pull request #{issue_number} has label '{label_name}'")
                    return True

            log.info(f"Pull request #{issue_number} does not have label '{label_name}'")
            return False

        except github.UnknownObjectException:
            log.warning(f"Pull request #{issue_number} not found")
            return False
        except Exception as e:
            log.error(f"Failed to check label on PR #{issue_number}: {e}")
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
            pr = self.repo.get_pull(pr_number)

            if pr.merged:
                log.warning(f"Pull request #{pr_number} is already merged")
                return True

            if pr.state != "open":
                log.error(f"Pull request #{pr_number} is not open (state: {pr.state})")
                return False

            if commit_message:
                result = pr.merge(commit_message=commit_message, merge_method=merge_method)
            else:
                result = pr.merge(merge_method=merge_method)

            if result.merged:
                log.info(f"Successfully merged pull request #{pr_number} into {pr.base.ref} using {merge_method}")
                return True
            else:
                log.error(f"Failed to merge pull request #{pr_number}: {result.message}")
                return False

        except Exception as e:
            log.error(f"Failed to merge pull request #{pr_number}: {e}")
            return False
