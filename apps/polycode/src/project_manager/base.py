"""Abstract base class for project managers."""

from abc import ABC, abstractmethod

from .types import Issue, ProjectConfig, ProjectItem


class ProjectManager(ABC):
    """Abstract base class for project management providers."""

    def __init__(self, config: ProjectConfig) -> None:
        """Initialize project manager with configuration.

        Args:
            config: Project configuration
        """
        self.config = config

    @property
    @abstractmethod
    def has_project(self) -> bool:
        """Is a project configured that can be used for management, e.g.
        Kanban?
        """

    @abstractmethod
    def get_comments(self, issue_number: int) -> list:
        """Get all comments for an issue.

        Args:
            issue_number: Issue number

        Returns:
            List of comments
        """

    @abstractmethod
    def get_last_comment_by_user(self, issue_number: int, username: str) -> int | None:
        """Get the last comment ID by a specific user.

        Args:
            issue_number: Issue number
            username: GitHub username

        Returns:
            Comment ID if found, None otherwise
        """

    @abstractmethod
    def update_comment(self, issue_number: int, comment_id: int, body: str) -> bool:
        """Update an existing comment.

        Args:
            issue_number: Issue number
            comment_id: Comment ID to update
            body: New comment body

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    def get_open_issues(self) -> list[Issue]:
        """Get all open issues from the repository.

        Returns:
            List of open issues
        """

    @abstractmethod
    def get_issue(self, issue_number: int) -> Issue:
        """Get a specific issue by number.

        Args:
            issue_number: Issue number

        Returns:
            Issue object
        """

    @abstractmethod
    def get_project_items(self) -> list[ProjectItem]:
        """Get all items in the project.

        Returns:
            List of project items
        """

    @abstractmethod
    def add_issue_to_project(self, issue: Issue) -> str | None:
        """Add an issue to the project.

        Args:
            issue: Issue to add

        Returns:
            Project item ID if successful, None otherwise
        """

    @abstractmethod
    def update_issue_status(self, issue_number: int, status: str) -> bool:
        """Update the status of an issue in the project.

        Args:
            issue_number: Issue number
            status: New status value

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    def add_comment(self, issue_number: int, comment: str) -> bool:
        """Add a comment to an issue.

        Args:
            issue_number: Issue number
            comment: Comment text

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    def has_label(self, issue_number: int, label_name: str) -> bool:
        """Check if an issue/PR has a specific label.

        Args:
            issue_number: Issue or PR number
            label_name: Name of the label to check for

        Returns:
            True if label is present
        """

    @abstractmethod
    def add_labels(self, issue_number: int, labels: list[str]) -> bool:
        """Add labels to an issue/PR.

        Args:
            issue_number: Issue or PR number
            labels: List of label names to add

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "develop",
    ) -> tuple[int, str] | None:
        """Create a pull request.

        Args:
            title: PR title
            body: PR body/description
            head: Source branch name
            base: Target branch name (default: "develop")

        Returns:
            Tuple of (pr_number, pr_url) if successful, None otherwise
        """

    @abstractmethod
    def merge_pull_request(
        self,
        pr_number: int,
        commit_message: str | None = None,
        merge_method: str = "merge",
    ) -> bool:
        """Merge a pull request.

        Args:
            pr_number: Pull request number
            commit_message: Optional custom commit message for the merge
            merge_method: Merge method - "merge", "squash", or "rebase"

        Returns:
            True if successful
        """

    @property
    @abstractmethod
    def bot_username(self) -> str:
        """Get the authenticated bot username."""
        ...

    @abstractmethod
    def close_issue(self, issue_number: int) -> bool:
        """Close an issue.

        Args:
            issue_number: Issue number

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    def assign_issue(self, issue_number: int, username: str) -> bool:
        """Assign an issue to a user.

        Args:
            issue_number: Issue number
            username: Username to assign to

        Returns:
            True if successful, False otherwise
        """

    @abstractmethod
    def get_labels(self) -> list[str]:
        """Get all repository labels.

        Returns:
            List of label names
        """

    @abstractmethod
    def remove_label(self, issue_number: int, label_name: str) -> bool:
        """Remove a label from an issue/PR.

        Args:
            issue_number: Issue or PR number
            label_name: Name of the label to remove

        Returns:
            True if successful, False otherwise
        """

    def find_project_item(self, issue_number: int) -> ProjectItem | None:
        """Find a project item by issue number.

        Args:
            issue_number: Issue number

        Returns:
            Project item if found, None otherwise
        """
        items = self.get_project_items()
        for item in items:
            if item.issue_number == issue_number:
                return item
        return None

    def sync_issues_to_project(self) -> int:
        """Sync all open issues to the project.

        Adds any issues that aren't already in the project.

        Returns:
            Number of issues added
        """
        issues = self.get_open_issues()
        items = self.get_project_items()
        existing_numbers = {item.issue_number for item in items}

        added = 0
        for issue in issues:
            if issue.number not in existing_numbers:
                if self.add_issue_to_project(issue):
                    added += 1

        return added
