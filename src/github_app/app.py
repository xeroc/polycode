"""GitHub App FastAPI webhook server - unified webhook endpoint.

Merges functionality from:
- src/github_app/webhook_handler.py (GitHub App webhooks)
- src/project_manager/webhook.py (signature validation, ping handling)

This replaces the separate FastAPI instance in project_manager.
"""

import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from redis import Redis

from github_app.auth import GitHubAppAuth
from github_app.config import settings
from github_app.installation_manager import InstallationManager
from github_app.label_mapper import LabelFlowMapper
from github_app.webhook_handler import GitHubAppWebhookHandler
from persistence.postgres import SessionLocal

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.GITHUB_APP_NAME,
    description="GitHub App for multi-repo CrewAI flow automation",
    version="2.0.0",
)

redis_client = Redis(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB
)

github_auth = GitHubAppAuth(
    app_id=settings.GITHUB_APP_ID,
    private_key=settings.GITHUB_APP_PRIVATE_KEY,
    redis_client=redis_client,
)


def get_db_session():
    """Get database session from postgres.py."""
    return SessionLocal()


def get_webhook_handler(db_session) -> GitHubAppWebhookHandler:
    """Create webhook handler with dependencies."""
    installation_manager = InstallationManager(db_session, github_auth)
    label_mapper = LabelFlowMapper(db_session)

    return GitHubAppWebhookHandler(
        github_auth=github_auth,
        installation_manager=installation_manager,
        label_mapper=label_mapper,
        webhook_secret=settings.GITHUB_APP_WEBHOOK_SECRET,
    )


# ============================================================================
# Health & Status Endpoints (from project_manager/webhook.py)
# ============================================================================


@app.get("/")
async def root():
    return {
        "name": settings.GITHUB_APP_NAME,
        "version": "2.0.0",
        "status": "running",
        "mode": "github_app",
    }


@app.get("/health")
async def health():
    """Health check endpoint (from project_manager/webhook.py)."""
    return {
        "status": "healthy",
        "redis": "connected",  # TODO: Check actual Redis connection
        "database": "connected",  # TODO: Check actual DB connection
    }


# ============================================================================
# Main Webhook Endpoint (unified)
# ============================================================================


@app.post("/webhook/github")
async def github_webhook(request: Request):
    """Handle GitHub webhook events.

    Unified endpoint for:
    - GitHub App webhooks (multi-repo, installation-based)
    - Legacy webhooks (single repo, from project_manager/webhook.py)

    Supported events:
    - ping: Webhook verification
    - installation: GitHub App installation lifecycle
    - issues: Issue events (delegates to process_github_webhook_task)
    """
    db_session = get_db_session()

    try:
        handler = get_webhook_handler(db_session)
        result = await handler.handle_webhook(request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db_session.close()


# ============================================================================
# Manual Trigger Endpoint (from project_manager/webhook.py)
# ============================================================================


@app.post("/trigger")
async def manual_trigger(
    issue_number: Optional[int] = None,
    repo_owner: Optional[str] = None,
    repo_name: Optional[str] = None,
    installation_id: Optional[int] = None,
):
    """Manually trigger a flow.

    Args:
        issue_number: Specific issue to process
        repo_owner: Repository owner (required if not using installation)
        repo_name: Repository name (required if not using installation)
        installation_id: GitHub App installation ID (for multi-repo)
    """
    from celery_tasks.tasks import kickoff_task
    from project_manager.flow_runner import FlowRunner
    from project_manager.github import GitHubProjectManager
    from project_manager.types import ProjectConfig, StatusMapping

    # Use environment variables as fallback
    repo_owner = repo_owner or os.environ.get("GITHUB_REPO_OWNER")
    repo_name = repo_name or os.environ.get("GITHUB_REPO_NAME")

    if not repo_owner or not repo_name:
        raise HTTPException(
            status_code=400,
            detail="repo_owner and repo_name required (or set env vars)",
        )

    # Get token (either from GitHub App or environment)
    if installation_id:
        token = github_auth.get_installation_token(installation_id)
        if not token:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get token for installation {installation_id}",
            )
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise HTTPException(status_code=500, detail="GITHUB_TOKEN not set")

    # Create project manager and flow runner
    config = ProjectConfig(
        provider="github",
        repo_owner=repo_owner,
        repo_name=repo_name,
        project_identifier=os.environ.get("GITHUB_PROJECT_ID", "1"),
        token=token,
        status_mapping=StatusMapping(),
    )

    manager = GitHubProjectManager(config)
    flow_runner = FlowRunner(manager=manager)

    # Check if flow is already running
    if flow_runner.is_flow_running():
        current = flow_runner.get_running_flow()
        return {
            "status": "already_running",
            "message": (
                f"Flow already running for issue #{current.issue_number}"
                if current
                else "Flow already running"
            ),
            "repo": f"{repo_owner}/{repo_name}",
        }

    # Trigger flow
    if issue_number:
        task_result = kickoff_task.delay(issue_number)  # type: ignore
        return {
            "status": "triggered",
            "message": f"Flow triggered for issue #{issue_number}",
            "repo": f"{repo_owner}/{repo_name}",
            "task_id": task_result.id,
        }
    else:
        # Trigger next ready issue
        triggered = flow_runner.trigger_flow()
        if triggered:
            return {
                "status": "triggered",
                "message": "Flow triggered for next ready issue",
                "repo": f"{repo_owner}/{repo_name}",
                "task_id": triggered if isinstance(triggered, str) else None,
            }
        else:
            return {
                "status": "no_ready_issues",
                "message": "No ready issues to process",
                "repo": f"{repo_owner}/{repo_name}",
            }


# ============================================================================
# Installation Management API
# ============================================================================


@app.post("/installations/{installation_id}/sync")
async def sync_installation(installation_id: int):
    """Sync repositories for an installation."""
    db_session = get_db_session()

    try:
        installation_manager = InstallationManager(db_session, github_auth)
        repos = installation_manager.sync_repositories(installation_id)

        if repos is None:
            raise HTTPException(
                status_code=404, detail="Installation not found"
            )

        return {
            "installation_id": installation_id,
            "repositories": repos,
            "count": len(repos or []),
        }
    finally:
        db_session.close()


@app.get("/installations")
async def list_installations():
    """List all active installations."""
    db_session = get_db_session()

    try:
        installation_manager = InstallationManager(db_session, github_auth)
        installations = installation_manager.list_installations()

        return {
            "installations": [
                {
                    "id": inst.installation_id,
                    "account": inst.account_login,
                    "active": inst.is_active,
                    "repos_count": len(
                        inst.repositories.get("repos", [])
                        if inst.repositories
                        else []
                    ),
                }
                for inst in installations
            ]
        }
    finally:
        db_session.close()


# ============================================================================
# Label Mapping API
# ============================================================================


@app.post("/mappings")
async def create_label_mapping(
    installation_id: int,
    label_name: str,
    flow_name: str,
    repo_pattern: Optional[str] = None,
    priority: int = 0,
):
    """Create a label-to-flow mapping."""
    db_session = get_db_session()
    label_mapper = LabelFlowMapper(db_session)

    try:
        mapping = label_mapper.create_mapping(
            installation_id=installation_id,
            label_name=label_name,
            flow_name=flow_name,
            repo_pattern=repo_pattern,
            priority=priority,
        )

        return {
            "id": mapping.id,
            "label": mapping.label_name,
            "flow": mapping.flow_name,
            "pattern": mapping.repo_pattern,
            "priority": mapping.priority,
        }
    finally:
        db_session.close()


@app.get("/mappings")
async def list_label_mappings(installation_id: Optional[int] = None):
    """List label-to-flow mappings."""
    db_session = get_db_session()
    label_mapper = LabelFlowMapper(db_session)

    try:
        mappings = label_mapper.list_mappings(installation_id=installation_id)

        return {
            "mappings": [
                {
                    "id": m.id,
                    "label": m.label_name,
                    "flow": m.flow_name,
                    "pattern": m.repo_pattern,
                    "priority": m.priority,
                    "active": m.is_active,
                }
                for m in mappings
            ]
        }
    finally:
        db_session.close()


# ============================================================================
# Error Handlers
# ============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500, content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=settings.WEBHOOK_HOST,
        port=settings.WEBHOOK_PORT,
        reload=True,
    )
