"""Individual agent execution Celery tasks."""

import logging
import uuid
from typing import Any

from celery import current_task
from bootstrap import bootstrap, get_module_registry
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from flows.base import KickoffIssue, KickoffRepo
from persistence.postgres import Base
from persistence.tasks import CeleryTaskTracker
from project_manager.github import GitHubProjectManager
from project_manager.types import ProjectConfig

from . import app, get_flow_id
from .config import settings

log = logging.getLogger(__name__)

bootstrap()

_persistence_tracker = None


def get_persistence_tracker():
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
def kickoff_task(
    self,
    project_config_dict: dict,
    issue_number: int,
    flow_name: str | None,
) -> dict[str, Any]:
    """Kickoff flow development flow for an issue.


    This task orchestrates the entire development process:
    1. Get issue details from GitHub
    2. Initialize flow
    3. Process through planning, implementation, testing, and review

    Args:
        issue_number: GitHub issue number
        flow_name: Optional flow name to override. If None, defaults to "ralph".

    Returns:
        Dict with flow results

    Raises:
        Exception: If kickoff fails
    """
    config = ProjectConfig(**project_config_dict)
    task_id = current_task.request.id  # type: ignore
    flow_id = get_flow_id()
    flow_name = flow_name or "ralph"

    log.info(f"Starting flow '{flow_name}' for issue #{issue_number}, task_id={task_id}, flow_id={flow_id}")

    try:
        tracker = get_persistence_tracker()
        tracker.update_task_started(task_id)

        manager = GitHubProjectManager(config)
        issue = manager.get_issue(issue_number)

        project_item = manager.find_project_item(issue_number)
        if not project_item:
            log.warning(f"Issue #{issue_number} not found in project")
            return {
                "status": "error",
                "message": f"Issue #{issue_number} not found in project",
            }

        flow_identifier = f"{flow_name}/{manager.config.repo_owner}/{manager.config.repo_name}/{issue_number}"
        flow_id = uuid.uuid5(uuid.NAMESPACE_DNS, flow_identifier)

        comments = manager.get_comments(issue_number)

        kickoff_issue = KickoffIssue(
            id=issue_number,
            flow_id=flow_id,
            title=issue.title,
            body=issue.body or "",
            comments=[
                {
                    "id": c.id,
                    "user": c.user.login if c.user else None,
                    "body": c.body,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in comments
            ],
            memory_prefix=f"{manager.config.repo_owner}/{manager.config.repo_name}",
            repository=KickoffRepo(
                owner=manager.config.repo_owner,
                repository=manager.config.repo_name,
            ),
            project_config=config,
        )
        log.info(f"Kicking off flow '{flow_name}' for issue #{issue_number}")

        flow_def = get_module_registry().flow_registry.get_flow(flow_name)

        if flow_def:
            flow_def.kickoff_func(kickoff_issue)
            log.info("🏁 Flow finished - emitting FLOW_FINISHED event")
        else:
            log.warning(f"⚠️ Flow '{flow_name}' not found and default 'ralph' also not found")
            return {
                "status": "error",
                "message": f"Flow '{flow_name}' not found",
            }

    except Exception as e:
        log.error(f"Failed to complete flow '{flow_name}': {e}")
        return {
            "status": "error",
            "message": f"Flow '{flow_name}' failed: {str(e)}",
        }

    return {"status": "success"}


@app.task(bind=True)
def process_github_webhook_task(self, payload: dict) -> dict:
    """Process GitHub webhook events.

    Args:
        payload: GitHub webhook payload

    Returns:
        Dict with status
    """
    log.info(f"Processing webhook: {payload.get('event_type', 'unknown')}")
    return {"status": "processed"}
