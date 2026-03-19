"""Individual agent execution Celery tasks."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from celery import current_task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bootstrap import init_plugins
from flowbase import KickoffIssue, KickoffRepo
from persistence.celery_tasks import CeleryTask, CeleryTaskTracker
from persistence.postgres import Base
from project_manager import StatusMapping
from project_manager.config import settings as project_settings
from project_manager.github import GitHubProjectManager
from project_manager.types import Issue, ProjectConfig
from ralph import kickoff as kickoff_ralph

from . import app, calculate_timeout, get_flow_id
from .celery_config import settings

log = logging.getLogger(__name__)

# Initialize plugin system at module level (runs once when worker starts)
init_plugins()

_persistence_tracker = None


def get_persistence_tracker():
    """Get or create persistence tracker instance."""
    global _persistence_tracker

    if _persistence_tracker is None:
        connection_string = settings.DATABASE_URL
        engine = create_engine(
            connection_string,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        session = sessionmaker(bind=engine)
        _persistence_tracker = CeleryTaskTracker(session)
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
def kickoff_task(self, project_config_dict: dict, issue_number: int) -> dict[str, Any]:
    """Kickoff flow development flow for an issue.

    This task orchestrates the entire development process:
    1. Get issue details from GitHub
    2. Initialize flow
    3. Process through planning, implementation, testing, and review

    Args:
        issue_number: GitHub issue number

    Returns:
        Dict with flow results

    Raises:
        Exception: If kickoff fails
    """
    config = ProjectConfig(**project_config_dict)
    task_id = current_task.request.id  # type: ignore
    flow_id = get_flow_id()

    log.info(f"Starting flow for issue #{issue_number}, task_id: {task_id}, flow_id: {flow_id}")

    try:
        update_task_started(task_id)
        update_status_task(
            project_config_dict,
            issue_number,
            settings.GITHUB_PROJECT_STATUS_MAPPING["in_progress"],
        )

        manager = GitHubProjectManager(config)
        issue = manager.get_issue(issue_number)
        repo_name = config.repo_name
        repo_owner = config.repo_owner

        project_item = manager.find_project_item(issue_number)
        if not project_item:
            log.warning(f"Issue #{issue_number} not found in project")
            update_status_task(project_config_dict, issue_number, "Ready")
            return {
                "status": "error",
                "message": f"Issue #{issue_number} not found in project",
            }

        flow_identifier = f"{repo_owner}/{repo_name}/{issue_number}"
        kickoff_issue = KickoffIssue(
            id=issue_number,
            flow_id=uuid.uuid5(uuid.NAMESPACE_DNS, flow_identifier),
            title=issue.title,
            body=issue.body or "",
            memory_prefix=f"{repo_owner}/{repo_name}",
            repository=KickoffRepo(
                owner=manager.config.repo_owner,
                repository=manager.config.repo_name,
            ),
            project_config=config,
        )

        log.info(f"Kicking off flow for: {kickoff_issue.title}")

        kickoff_ralph(kickoff_issue)

        log.info(f"Flow completed for issue #{issue_number}")
        update_status_task(project_config_dict, issue_number, "In review")
        update_task_completed(project_config_dict, task_id, "Development completed")

        return {
            "status": "success",
            "issue_number": issue_number,
            "flow_id": flow_id,
            "message": "Development completed successfully",
        }

    except Exception as e:
        log.error(
            f"Flow failed for issue #{issue_number}: {e}",
            exc_info=True,
        )
        update_task_failed(project_config_dict, task_id, str(e))
        update_status_task(project_config_dict, issue_number, "Ready")

        retry_count = self.request.retries
        if retry_count < self.max_retries:
            timeout = calculate_timeout(retry_count)
            log.info(f"Retrying issue #{issue_number}, attempt {retry_count + 1}/{self.max_retries}")
            raise self.retry(exc=e, countdown=timeout)

        return {
            "status": "failed",
            "issue_number": issue_number,
            "flow_id": flow_id,
            "message": f"Development failed: {str(e)}",
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
def update_task_completed(_project_config_dict: dict, task_id: str, result: str | None = None) -> None:
    """Mark task as completed in database.

    Args:
        task_id: Celery task ID
        result: Optional result data
    """
    tracker = get_persistence_tracker()
    tracker.update_task_completed(task_id, result)


@app.task()
def update_task_failed(_project_config_dict: dict, task_id: str, error_message: str) -> None:
    """Mark task as failed in database.

    Args:
        task_id: Celery task ID
        error_message: Error message
    """
    tracker = get_persistence_tracker()
    tracker.update_task_failed(task_id, error_message)


@app.task()
def update_status_task(project_config_dict: dict, issue_number: int, status: str) -> bool:
    """Update GitHub issue status in project board.

    Args:
        issue_number: GitHub issue number
        status: New status value

    Returns:
        True if successful, False otherwise
    """
    try:
        config = ProjectConfig(**project_config_dict)
        manager = GitHubProjectManager(config)
        success = manager.update_issue_status(issue_number, status)

        if success:
            log.info(f"Updated issue #{issue_number} to '{status}'")
        else:
            log.warning(f"Failed to update issue #{issue_number} to '{status}'")

        return success

    except Exception as e:
        log.error(f"Failed to update status for issue #{issue_number}: {e}")
        return False


def add_issue_to_project_task(project_config_dict: dict, issue: Any) -> bool:
    """Add issue to project board (synchronous helper).

    Args:
        issue: Issue object

    Returns:
        True if successful, False otherwise
    """
    config = ProjectConfig(**project_config_dict)
    try:
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
    get_persistence_tracker()
    log.info("Running flow heartbeat check")

    try:
        running_tasks = []
        timed_out_tasks = []

        connection_string = settings.DATABASE_URL
        engine = create_engine(connection_string)
        session = sessionmaker(bind=engine)

        with session() as session:
            running_tasks_data = session.query(CeleryTask).filter(CeleryTask.status == "running").all()

            for task in running_tasks_data:
                running_tasks.append(task.task_id)

                if task.started_at:
                    now = datetime.now(timezone.utc)
                    age = (now - task.started_at).total_seconds()

                    if age > 7200:
                        log.warning(f"Task {task.task_id} appears stuck, age: {age} seconds")
                        timed_out_tasks.append(task.task_id)

        log.info(f"Heartbeat: {len(running_tasks)} running tasks, {len(timed_out_tasks)} potential timeouts")

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
    repo_name = repository.get("name", "")
    owner = repository.get("owner", {}).get("login", "")

    config = ProjectConfig(
        provider="github",
        repo_owner=owner,
        repo_name=repo_name,
        # FIXME: only works with first project so far! (might want to use `repository.has_projects` and disable projects)
        project_identifier=None,
        status_mapping=StatusMapping(),
    )

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

            if label_name == project_settings.WORK_FLOW_START_LABEL:
                log.info(f"Label '{project_settings.WORK_FLOW_START_LABEL}' added to issue #{issue_number}")

                add_issue_to_project_task(config.model_dump(), issue_obj)
                updated = update_status_task(config.model_dump(), issue_number, "Ready")

                if updated:
                    log.info(f"Updated issue #{issue_number} to Ready status")
                else:
                    log.warning(f"Failed to update issue #{issue_number} to Ready")

                kickoff_task.delay(config.model_dump(), issue_number)  # type: ignore
                log.info(f"Triggered flow for issue #{issue_number}")

                update_task_completed(task_id, "Issue labeled and flow triggered")

                return {
                    "status": "triggered",
                    "issue_number": issue_number,
                    "action": action,
                    "label": label_name,
                    "message": f"Issue #{issue_number} moved to Ready and flow triggered",
                }

        else:
            log.info(f"Unhandled event for issue #{issue_number}: {action}")

        update_task_completed(task_id, "Webhook processed")

        return {
            "status": "success",
            "issue_number": issue_number,
            "action": action,
            "message": f"Issue #{issue_number} added to project",
        }

    except Exception as e:
        log.error(f"Webhook processing failed: {e}", exc_info=True)

        update_task_failed(config.model_dump(), task_id, str(e))

        retry_count = self.request.retries
        if retry_count < self.max_retries:
            timeout = 60 * (retry_count + 1)
            log.info(f"Retrying webhook processing, attempt {retry_count + 1}/{self.max_retries}")
            raise self.retry(exc=e, countdown=timeout)

        return {
            "status": "failed",
            "issue_number": issue_number,
            "action": action,
            "message": f"Webhook processing failed: {str(e)}",
        }
