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

    @abstractmethod
    def get_open_issues(self) -> list[Issue]:
        """Get all open issues from the repository.

        Returns:
            List of open issues
        """
        pass

    @abstractmethod
    def get_project_items(self) -> list[ProjectItem]:
        """Get all items in the project.

        Returns:
            List of project items
        """
        pass

    @abstractmethod
    def add_issue_to_project(self, issue: Issue) -> str | None:
        """Add an issue to the project.

        Args:
            issue: Issue to add

        Returns:
            Project item ID if successful, None otherwise
        """
        pass

    @abstractmethod
    def update_issue_status(self, issue_number: int, status: str) -> bool:
        """Update the status of an issue in the project.

        Args:
            issue_number: Issue number
            status: New status value

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def add_comment(self, issue_number: int, comment: str) -> bool:
        """Add a comment to an issue.

        Args:
            issue_number: Issue number
            comment: Comment text

        Returns:
            True if successful, False otherwise
        """
        pass

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
