"""Individual agent execution Celery tasks."""

import logging
import os
from typing import Any

from celery import current_task
from datetime import datetime, timezone
from feature_dev import FeatureDevFlow
from feature_dev import KickoffIssue
from persistence import PostgresFlowPersistence
from persistence.celery_tasks import CeleryTask
from persistence.celery_tasks import CeleryTaskTracker
from persistence.postgres import Base
from project_manager.github import GitHubProjectManager
from project_manager.types import Issue
from project_manager.types import ProjectConfig, StatusMapping
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from . import app, get_flow_id, calculate_timeout

log = logging.getLogger(__name__)

_persistence_tracker = None


GITHUB_LABEL_FOR_WORKFLOW_START = "verified"
GITHUB_PROJECT_STATUS_MAPPING = dict(
    todo="Backlog",
    ready="Ready",
    in_progress="In progress",
    reviewing="In review",
    done="Done",
)


def get_persistence_tracker():
    """Get or create persistence tracker instance."""
    global _persistence_tracker

    if _persistence_tracker is None:
        connection_string = os.environ.get("DATABASE_URL", "sqlite:///flow_state.db")
        engine = create_engine(connection_string)
        Session = sessionmaker(bind=engine)
        _persistence_tracker = CeleryTaskTracker(Session)
        log.info("Creating tables ...")
        Base.metadata.create_all(engine)

    return _persistence_tracker


get_persistence_tracker()


@app.task(
    bind=True,
    max_retries=3,
    soft_time_limit=7200,
    time_limit=7380,
)
def kickoff_feature_dev_task(self, issue_number: int) -> dict[str, Any]:
    """Kickoff feature development flow for an issue.

    This task orchestrates the entire feature development process:
    1. Get issue details from GitHub
    2. Initialize feature dev flow
    3. Process through planning, implementation, testing, and review

    Args:
        issue_number: GitHub issue number

    Returns:
        Dict with flow results

    Raises:
        Exception: If kickoff fails
    """
    task_id = current_task.request.id  # type: ignore
    flow_id = get_flow_id()

    log.info(
        f"Starting feature dev flow for issue #{issue_number}, "
        f"task_id: {task_id}, flow_id: {flow_id}"
    )

    try:
        update_task_started(task_id)
        update_status_task(issue_number, GITHUB_PROJECT_STATUS_MAPPING["in_progress"])

        repo_name = os.environ.get("GITHUB_REPO_NAME", "demo")
        repo_owner = os.environ.get("GITHUB_REPO_OWNER", "xeroc")
        project_id = os.environ.get("GITHUB_PROJECT_ID", "1")
        token = os.environ.get("GITHUB_TOKEN")

        config = ProjectConfig(
            provider="github",
            repo_name=repo_name,
            repo_owner=repo_owner,
            project_identifier=project_id,
            token=token,
            status_mapping=StatusMapping(**GITHUB_PROJECT_STATUS_MAPPING),
        )

        manager = GitHubProjectManager(config)
        project_item = manager.find_project_item(issue_number)

        if not project_item:
            log.warning(f"Issue #{issue_number} not found in project")
            update_status_task(issue_number, "Ready")
            return {
                "status": "error",
                "message": f"Issue #{issue_number} not found in project",
            }

        kickoff_issue = KickoffIssue(
            id=issue_number,
            title=project_item.title,
            body=project_item.body or "",
        )

        log.info(f"Kicking off feature dev for: {kickoff_issue.title}")

        connection_string = os.environ.get("DATABASE_URL", "sqlite:///flow_state.db")
        persistence = PostgresFlowPersistence(connection_string)

        feature_flow = FeatureDevFlow(kickoff_issue, persistence=persistence)
        feature_flow.kickoff()

        log.info(f"Feature dev flow completed for issue #{issue_number}")
        update_status_task(issue_number, "Reviewing")
        update_task_completed(task_id, "Feature development completed")

        return {
            "status": "success",
            "issue_number": issue_number,
            "flow_id": flow_id,
            "message": "Feature development completed successfully",
        }

    except Exception as e:
        log.error(
            f"Feature dev flow failed for issue #{issue_number}: {e}",
            exc_info=True,
        )
        update_task_failed(task_id, str(e))
        update_status_task(issue_number, "Ready")

        retry_count = self.request.retries
        if retry_count < self.max_retries:
            timeout = calculate_timeout(retry_count)
            log.info(
                f"Retrying feature dev for issue #{issue_number}, "
                f"attempt {retry_count + 1}/{self.max_retries}"
            )
            raise self.retry(exc=e, countdown=timeout)

        return {
            "status": "failed",
            "issue_number": issue_number,
            "flow_id": flow_id,
            "message": f"Feature development failed: {str(e)}",
        }


@app.task()
def create_task(
    task_id: str,
    flow_id: str,
    task_type: str,
    issue_number: int | None = None,
) -> None:
    """Create a new task record in database.

    Args:
        task_id: Celery task ID
        flow_id: Flow ID this task belongs to
        task_type: Type of task
        issue_number: Optional issue number
    """
    tracker = get_persistence_tracker()
    tracker.create_task(task_id, flow_id, task_type, issue_number)


@app.task()
def update_task_started(task_id: str) -> None:
    """Mark task as started in database.

    Args:
        task_id: Celery task ID
    """
    tracker = get_persistence_tracker()
    tracker.update_task_started(task_id)


@app.task()
def update_task_completed(task_id: str, result: str | None = None) -> None:
    """Mark task as completed in database.

    Args:
        task_id: Celery task ID
        result: Optional result data
    """
    tracker = get_persistence_tracker()
    tracker.update_task_completed(task_id, result)


@app.task()
def update_task_failed(task_id: str, error_message: str) -> None:
    """Mark task as failed in database.

    Args:
        task_id: Celery task ID
        error_message: Error message
    """
    tracker = get_persistence_tracker()
    tracker.update_task_failed(task_id, error_message)


@app.task()
def update_status_task(issue_number: int, status: str) -> bool:
    """Update GitHub issue status in project board.

    Args:
        issue_number: GitHub issue number
        status: New status value

    Returns:
        True if successful, False otherwise
    """
    try:
        repo_name = os.environ.get("GITHUB_REPO_NAME", "demo")
        repo_owner = os.environ.get("GITHUB_REPO_OWNER", "xeroc")
        project_id = os.environ.get("GITHUB_PROJECT_ID", "1")
        token = os.environ.get("GITHUB_TOKEN")

        config = ProjectConfig(
            provider="github",
            repo_name=repo_name,
            repo_owner=repo_owner,
            project_identifier=project_id,
            token=token,
            status_mapping=StatusMapping(**GITHUB_PROJECT_STATUS_MAPPING),
        )

        manager = GitHubProjectManager(config)
        success = manager.update_issue_status(issue_number, status)

        if success:
            log.info(f"Updated issue #{issue_number} to '{status}'")
        else:
            log.warning(f"Failed to update issue #{issue_number} to '{status}'")

        return success

    except Exception as e:
        import traceback

        traceback.print_exc()
        log.error(f"Failed to update status for issue #{issue_number}: {e}")
        return False


def add_issue_to_project_task(issue: Any) -> bool:
    """Add issue to project board (synchronous helper).

    Args:
        issue: Issue object

    Returns:
        True if successful, False otherwise
    """
    try:
        repo_name = os.environ.get("GITHUB_REPO_NAME", "demo")
        repo_owner = os.environ.get("GITHUB_REPO_OWNER", "xeroc")
        project_id = os.environ.get("GITHUB_PROJECT_ID", "1")
        token = os.environ.get("GITHUB_TOKEN")

        config = ProjectConfig(
            provider="github",
            repo_name=repo_name,
            repo_owner=repo_owner,
            project_identifier=project_id,
            token=token,
            status_mapping=StatusMapping(**GITHUB_PROJECT_STATUS_MAPPING),
        )

        manager = GitHubProjectManager(config)
        added = manager.add_issue_to_project(issue)

        if added:
            log.info(f"Added issue #{issue.number} to project")
        else:
            log.info(f"Issue #{issue.number} already in project")

        return bool(added)

    except Exception as e:
        log.error(f"Failed to add issue #{issue.number} to project: {e}")
        return False


@app.task()
def flow_heartbeat_task() -> dict[str, Any]:
    """Monitor running flows and check for timeouts.

    This task runs periodically to ensure flows are healthy.

    Returns:
        Dict with heartbeat results
    """
    tracker = get_persistence_tracker()
    log.info("Running flow heartbeat check")

    try:
        running_tasks = []
        timed_out_tasks = []

        connection_string = os.environ.get("DATABASE_URL", "sqlite:///flow_state.db")
        engine = create_engine(connection_string)
        Session = sessionmaker(bind=engine)

        with Session() as session:
            running_tasks_data = (
                session.query(CeleryTask).filter(CeleryTask.status == "running").all()
            )

            for task in running_tasks_data:
                running_tasks.append(task.task_id)

                if task.started_at:
                    now = datetime.now(timezone.utc)
                    age = (now - task.started_at).total_seconds()

                    if age > 7200:
                        log.warning(
                            f"Task {task.task_id} appears stuck, " f"age: {age} seconds"
                        )
                        timed_out_tasks.append(task.task_id)

        log.info(
            f"Heartbeat: {len(running_tasks)} running tasks, "
            f"{len(timed_out_tasks)} potential timeouts"
        )

        return {
            "status": "success",
            "running_tasks": len(running_tasks),
            "timed_out_tasks": timed_out_tasks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        log.error(f"Heartbeat check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
        }


@app.task()
def cleanup_completed_tasks(days_old: int = 7) -> dict[str, Any]:
    """Delete completed/failed tasks older than specified days.

    Args:
        days_old: Number of days to keep completed tasks

    Returns:
        Dict with cleanup results
    """
    tracker = get_persistence_tracker()
    log.info(f"Cleaning up tasks older than {days_old} days")

    try:
        deleted = tracker.cleanup_completed_tasks(days_old)
        log.info(f"Cleaned up {deleted} completed tasks")

        return {
            "status": "success",
            "deleted_count": deleted,
            "days_old": days_old,
        }

    except Exception as e:
        log.error(f"Cleanup task failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
        }


@app.on_after_configure.connect  # type: ignore
def setup_periodic_tasks(sender, **kwargs):
    """Configure periodic Celery tasks."""
    sender.add_periodic_task(
        300.0,
        flow_heartbeat_task.s(),  # type: ignore
        name="flow-heartbeat-every-5-minutes",
    )

    sender.add_periodic_task(
        86400.0,
        cleanup_completed_tasks.s(days_old=7),  # type: ignore
        name="cleanup-completed-tasks-daily",
    )


@app.task(bind=True, max_retries=3, soft_time_limit=300, time_limit=330)
def process_github_webhook_task(self, payload: dict[str, Any]) -> dict[str, Any]:
    """Process GitHub webhook event asynchronously.

    Migrated from webhook.py handle_issue_event:
    - Validates action is handled (opened, reopened, labeled)
    - For 'labeled' with 'verified': updates status to Ready, triggers flow
    - For all handled actions: adds issue to project

    Args:
        payload: Webhook payload data

    Returns:
        Dict with processing results

    Raises:
        Exception: If webhook processing fails
    """
    task_id = current_task.request.id  # type: ignore
    action = payload.get("action")
    issue = payload.get("issue", {})
    issue_number = issue.get("number")
    repository = payload.get("repository", {})

    log.info(
        f"Processing webhook: issue #{issue_number}, action: {action}, "
        f"repo: {repository.get('full_name')}, task_id: {task_id}"
    )

    if not issue_number:
        log.warning("No issue number in webhook payload")
        return {"status": "ignored", "reason": "no issue number"}

    if not action:
        return {"status": "ignored", "reason": "no action in payload"}

    if action not in ["opened", "reopened", "labeled"]:
        log.info(f"Action '{action}' not handled, skipping")
        return {
            "status": "ignored",
            "issue_number": issue_number,
            "action": action,
            "reason": f"action '{action}' not handled",
        }

    try:
        update_task_started(task_id)

        issue_obj = Issue(
            id=issue_number,
            number=issue_number,
            title=issue.get("title", ""),
            body=issue.get("body"),
            node_id=issue.get("node_id"),
            url=issue.get("html_url"),
            labels=[label.get("name", "") for label in issue.get("labels", [])],
        )

        if action == "labeled":
            label = payload.get("label", {})
            label_name = label.get("name") if label else None

            if label_name == GITHUB_LABEL_FOR_WORKFLOW_START:
                log.info(
                    f"Label '{GITHUB_LABEL_FOR_WORKFLOW_START}' added to issue #{issue_number}"
                )

                added = add_issue_to_project_task(issue_obj)
                if added:
                    log.info(f"Added issue #{issue_number} to project")

                updated = update_status_task(issue_number, "Ready")
                if updated:
                    log.info(f"Updated issue #{issue_number} to Ready status")
                else:
                    log.warning(f"Failed to update issue #{issue_number} to Ready")

                kickoff_feature_dev_task.delay(issue_number)  # type: ignore
                log.info(f"Triggered feature dev flow for issue #{issue_number}")

                update_task_completed(task_id, "Issue labeled and flow triggered")

                return {
                    "status": "triggered",
                    "issue_number": issue_number,
                    "action": action,
                    "label": label_name,
                    "message": f"Issue #{issue_number} moved to Ready and flow triggered",
                }
            else:
                added = add_issue_to_project_task(issue_obj)
                if added:
                    log.info(f"Added issue #{issue_number} to project")
                else:
                    log.info(
                        f"Issue #{issue_number} already in project or failed to add"
                    )

                update_task_completed(task_id, "Issue added to project")
                return {
                    "status": "success",
                    "issue_number": issue_number,
                    "action": action,
                    "label": label_name,
                    "message": f"Issue #{issue_number} added to project",
                }

        added = add_issue_to_project_task(issue_obj)
        if added:
            log.info(f"Added issue #{issue_number} to project")
        else:
            log.info(f"Issue #{issue_number} already in project or failed to add")

        update_task_completed(task_id, "Webhook processed")

        return {
            "status": "success",
            "issue_number": issue_number,
            "action": action,
            "message": f"Issue #{issue_number} added to project",
        }

    except Exception as e:
        log.error(f"Webhook processing failed: {e}", exc_info=True)

        update_task_failed(task_id, str(e))

        retry_count = self.request.retries
        if retry_count < self.max_retries:
            timeout = 60 * (retry_count + 1)
            log.info(
                f"Retrying webhook processing, "
                f"attempt {retry_count + 1}/{self.max_retries}"
            )
            raise self.retry(exc=e, countdown=timeout)

        return {
            "status": "failed",
            "issue_number": issue_number,
            "action": action,
            "message": f"Webhook processing failed: {str(e)}",
        }
