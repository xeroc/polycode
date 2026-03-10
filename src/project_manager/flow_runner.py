"""Flow runner for managing issue processing."""

import logging
from typing import Callable

from .base import ProjectManager
from .types import IssueStatus, ProjectItem

log = logging.getLogger(__name__)


class FlowRunner:
    """Manages flow execution using project manager as source of truth."""

    def __init__(
        self,
        manager: ProjectManager,
        on_issue_ready: Callable[[ProjectItem], None] | None = None,
    ) -> None:
        """Initialize flow runner.

        Args:
            manager: Project manager instance
            on_issue_ready: Callback when an issue is ready to process
        """
        self.manager = manager
        self.on_issue_ready = on_issue_ready

    def is_flow_running(self) -> bool:
        """Check if a flow is currently running.

        Uses project manager as single source of truth - checks if any
        item has "In progress" status.

        Returns:
            True if a flow is running, False otherwise
        """
        items = self.manager.get_project_items()
        in_progress_status = self.manager.config.status_mapping.to_provider_status(
            IssueStatus.IN_PROGRESS
        )

        in_progress_items = [
            item for item in items if item.status == in_progress_status
        ]
        return len(in_progress_items) > 0

    def get_running_flow(self) -> ProjectItem | None:
        """Get the currently running flow.

        Returns:
            ProjectItem if a flow is running, None otherwise
        """
        items = self.manager.get_project_items()
        in_progress_status = self.manager.config.status_mapping.to_provider_status(
            IssueStatus.IN_PROGRESS
        )

        for item in items:
            if item.status == in_progress_status:
                return item
        return None

    def trigger_flow(self, issue_number: int | None = None) -> bool | str:
        """Trigger a flow for an issue.

        If issue_number is provided, processes that specific issue.
        Otherwise, finds the next ready issue.

        When Celery is available, returns task ID for async processing.
        When Celery is not available, returns bool for sync processing.

        Args:
            issue_number: Optional specific issue to process

        Returns:
            True/task_id if flow was triggered, False if already running or no issue found
        """
        if self.is_flow_running():
            current = self.get_running_flow()
            if current:
                log.info(f"Flow already running for issue #{current.issue_number}")
            return False

        if issue_number:
            return self._process_specific_issue(issue_number)
        else:
            return self._process_next_ready_issue()

    def _process_specific_issue(self, issue_number: int) -> bool | str:
        """Process a specific issue.

        Args:
            issue_number: Issue number to process

        Returns:
            True/task_id if flow was triggered, False otherwise
        """
        item = self.manager.find_project_item(issue_number)
        if not item:
            log.warning(f"Issue #{issue_number} not found in project")
            return False

        ready_status = self.manager.config.status_mapping.to_provider_status(
            IssueStatus.READY
        )
        in_progress_status = self.manager.config.status_mapping.to_provider_status(
            IssueStatus.IN_PROGRESS
        )

        if item.status != ready_status:
            log.info(
                f"Issue #{issue_number} not ready (status: {item.status}), skipping"
            )
            return False

        success = self.manager.update_issue_status(issue_number, in_progress_status)
        if not success:
            log.error(f"Failed to move issue #{issue_number} to {in_progress_status}")
            return False

        log.info(f"Started flow for issue #{issue_number}: {item.title}")

        try:
            from celery_tasks.tasks import kickoff_task

            task_result = kickoff_task.apply_async(args=[self.manager.config.model_dump(), issue_number])  # type: ignore
            log.info(f"Queued Celery task for issue #{issue_number}: {task_result.id}")
            return task_result.id
        except Exception as e:
            log.error(f"Failed to queue Celery task: {e}")
            log.warning("Falling back to synchronous processing")

        if self.on_issue_ready:
            try:
                self.on_issue_ready(item)
            except Exception as e:
                log.error(f"Error processing issue #{issue_number}: {e}")
                raise
        else:
            log.info(f"No callback configured for issue #{issue_number}")

        return True

    def _process_next_ready_issue(self) -> bool:
        """Process the next ready issue.

        Returns:
            True if flow was triggered, False if no ready issues
        """
        items = self.manager.get_project_items()
        ready_status = self.manager.config.status_mapping.to_provider_status(
            IssueStatus.READY
        )

        ready_items = [item for item in items if item.status == ready_status]
        if not ready_items:
            log.info("No ready items to process")
            return False

        top_item = ready_items[0]
        return bool(self._process_specific_issue(top_item.issue_number))
