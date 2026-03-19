"""GitHub App FastAPI webhook server - unified webhook endpoint.

Merges functionality from:
- src/github_app/webhook_handler.py (GitHub App webhooks)
- src/project_manager/webhook.py (signature validation, ping handling)

This replaces the separate FastAPI instance in project_manager.
"""

import logging
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

redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)

github_auth = GitHubAppAuth(
    app_id=settings.GITHUB_APP_ID,
    private_key=settings.GITHUB_APP_PRIVATE_KEY.replace("\\n", "\n"),
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
    - issues: Issue events
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
            raise HTTPException(status_code=404, detail="Installation not found")

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
                    "repos_count": len(inst.repositories.get("repos", []) if inst.repositories else []),
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
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=settings.WEBHOOK_HOST,
        port=settings.WEBHOOK_PORT,
        reload=True,
    )
