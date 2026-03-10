"""Repository watcher with polling support."""

import logging
import time
from typing import Callable

from .base import ProjectManager
from .types import IssueStatus, ProjectItem

log = logging.getLogger(__name__)


class RepoWatcher:
    """Watches a repository for issues to process."""

    def __init__(
        self,
        manager: ProjectManager,
        poll_interval: int = 300,
        on_issue_ready: Callable[[ProjectItem], None] | None = None,
    ) -> None:
        """Initialize the repository watcher.

        Args:
            manager: Project manager instance
            poll_interval: Polling interval in seconds (default: 5 minutes)
            on_issue_ready: Callback when an issue is ready to process
        """
        self.manager = manager
        self.poll_interval = poll_interval
        self.on_issue_ready = on_issue_ready
        self._running = False

    def process_cycle(self) -> None:
        """Run one processing cycle.

        1. Syncs all open issues to the project
        2. Finds items in "Ready" status
        3. If no items are "In progress", processes the top "Ready" item
        """
        log.info("Starting processing cycle")

        added = self.manager.sync_issues_to_project()
        if added > 0:
            log.info(f"Added {added} new issues to project")

        items = self.manager.get_project_items()
        ready_status = self.manager.config.status_mapping.to_provider_status(
            IssueStatus.READY
        )
        in_progress_status = (
            self.manager.config.status_mapping.to_provider_status(
                IssueStatus.IN_PROGRESS
            )
        )

        ready_items = [item for item in items if item.status == ready_status]
        in_progress_items = [
            item for item in items if item.status == in_progress_status
        ]

        log.info(
            f"Ready: {len(ready_items)}, In progress: {len(in_progress_items)}"
        )

        if not in_progress_items and ready_items:
            top_item = ready_items[0]

            log.info(f"Processing '{top_item.title}'")
            log.info(f"  Issue #{top_item.issue_number}")
            log.info(f"  Description: {top_item.body or '(no description)'}")

            success = self.manager.update_issue_status(
                top_item.issue_number, in_progress_status
            )

            if success:
                log.info(
                    f"Moved issue #{top_item.issue_number} to {in_progress_status}"
                )

                if self.on_issue_ready:
                    try:
                        self.on_issue_ready(top_item)
                    except Exception as e:
                        log.error(
                            f"Error processing issue #{top_item.issue_number}: {e}"
                        )
            else:
                log.error(
                    f"Failed to move issue #{top_item.issue_number} to {in_progress_status}"
                )

        elif in_progress_items:
            log.info(
                f"Already have {len(in_progress_items)} item(s) in progress"
            )
        else:
            log.info("No ready items to process")

        log.info("Processing cycle complete")

    def start(self, run_once: bool = False) -> None:
        """Start watching the repository.

        Args:
            run_once: If True, run one cycle and exit
        """
        self._running = True

        log.info("Starting repository watcher")
        log.info(
            f"Repository: {self.manager.config.repo_owner}/{self.manager.config.repo_name}"
        )
        log.info(f"Project: {self.manager.config.project_identifier}")
        log.info(f"Poll interval: {self.poll_interval} seconds")

        try:
            self.process_cycle()
        except Exception as e:
            log.error(f"Error in initial cycle: {e}")
            if run_once:
                raise

        if run_once:
            return

        while self._running:
            time.sleep(self.poll_interval)
            try:
                self.process_cycle()
            except Exception as e:
                log.error(f"Error in cycle: {e}")

    def stop(self) -> None:
        """Stop watching the repository."""
        self._running = False
