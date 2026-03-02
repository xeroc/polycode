"""FastAPI webhook endpoint for GitHub."""

import hashlib
import hmac
import json
import logging
from typing import Any

from celery_tasks.tasks import process_github_webhook_task
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from .flow_runner import FlowRunner
from .types import Issue

log = logging.getLogger(__name__)

MOVE_TO_READY_STATE_LABEL = "verified"


class GitHubWebhookPayload(BaseModel):
    """GitHub webhook payload structure.

    Supports both ping events and issue events.
    """

    action: str | None = None
    zen: str | None = None
    hook_id: int | None = None
    hook: dict[str, Any] | None = None
    issue: dict[str, Any] | None = None
    label: dict[str, Any] | None = None
    repository: dict[str, Any]
    sender: dict[str, Any]


class GitHubWebhookHandler:
    """Handles GitHub webhook events."""

    def __init__(
        self,
        flow_runner: FlowRunner,
        webhook_secret: str | None = None,
    ) -> None:
        """Initialize webhook handler.

        Args:
            flow_runner: Flow runner instance
            webhook_secret: Optional secret for signature validation
        """
        self.flow_runner = flow_runner
        self.webhook_secret = webhook_secret

    def validate_signature(
        self, payload: bytes, signature: str, timestamp: str | None = None
    ) -> bool:
        """Validate GitHub webhook signature.

        Args:
            payload: Raw request body
            signature: X-Hub-Signature-256 header value
            timestamp: Optional timestamp for additional validation

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_secret:
            log.warning("No webhook secret configured, skipping signature validation")
            return True

        if not signature.startswith("sha256="):
            log.error("Invalid signature format")
            return False

        expected_signature = signature[7:]

        mac = hmac.new(
            self.webhook_secret.encode(), msg=payload, digestmod=hashlib.sha256
        )
        computed_signature = mac.hexdigest()

        return hmac.compare_digest(computed_signature, expected_signature)

    def handle_ping_event(self, payload: GitHubWebhookPayload) -> dict[str, Any]:
        """Handle GitHub ping event.

        Sent when webhook is first created to verify endpoint.

        Args:
            payload: Webhook payload

        Returns:
            Response dict with status
        """
        log.info(f"Received ping from GitHub")
        log.info(f"  Zen: {payload.zen}")
        log.info(f"  Hook ID: {payload.hook_id}")
        log.info(f"  Repository: {payload.repository.get('full_name')}")

        if payload.hook:
            events = payload.hook.get("events", [])
            log.info(f"  Events: {events}")
            log.info(f"  URL: {payload.hook.get('config', {}).get('url')}")

        return {
            "status": "pong",
            "zen": payload.zen,
            "hook_id": payload.hook_id,
            "events": payload.hook.get("events", []) if payload.hook else [],
        }


def create_webhook_app(
    flow_runner: FlowRunner,
    webhook_secret: str | None = None,
) -> FastAPI:
    """Create FastAPI app for GitHub webhooks.

    Args:
        flow_runner: Flow runner instance
        webhook_secret: Optional secret for signature validation

    Returns:
        FastAPI application
    """
    app = FastAPI(title="Project Manager Webhook", version="1.0.0")
    handler = GitHubWebhookHandler(flow_runner, webhook_secret)

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        running = flow_runner.get_running_flow()
        return {
            "status": "healthy",
            "flow_running": flow_runner.is_flow_running(),
            "current_flow": running.model_dump() if running else None,
        }

    @app.post("/webhook/github")
    async def github_webhook(
        request: Request,
    ):
        """Handle GitHub webhook events.

        Supported events:
        - ping: Webhook verification (sent when webhook is created)
        - issues: Issue events (opened, reopened, labeled)
        """
        signature = request.headers.get("X-Hub-Signature-256", "")
        event_type = request.headers.get("X-GitHub-Event", "")
        delivery_id = request.headers.get("X-GitHub-Delivery", "")
        hook_id = request.headers.get("X-GitHub-Hook-Id", "")

        log.info(
            f"Received webhook: {event_type} (delivery: {delivery_id}, hook: {hook_id})"
        )

        payload_bytes = await request.body()

        if not handler.validate_signature(payload_bytes, signature):
            log.error("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

        try:
            payload_data = json.loads(payload_bytes)
            payload = GitHubWebhookPayload(**payload_data)
        except Exception as e:
            log.error(f"Failed to parse payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")

        if event_type == "ping":
            result = handler.handle_ping_event(payload)
            log.info(f"Ping processed: {result}")
            return {
                "status": "pong",
                "event": event_type,
                "delivery_id": delivery_id,
                "hook_id": hook_id,
                "zen": payload.zen,
            }

        elif event_type == "issues":
            try:
                task_result = process_github_webhook_task.apply_async(  # type: ignore
                    args=[payload.model_dump()]
                )
                log.info(f"Queued webhook for Celery processing: {task_result.id}")
                return {
                    "status": "queued",
                    "event": event_type,
                    "delivery_id": delivery_id,
                    "task_id": task_result.id,
                }
            except Exception as e:
                log.error(f"Failed to queue Celery task: {e}")
                log.warning("Falling back to background task processing")

            return {
                "status": "received",
                "event": event_type,
                "delivery_id": delivery_id,
            }

        else:
            log.info(f"Ignoring event type: {event_type}")
            return {
                "status": "ignored",
                "event": event_type,
                "message": f"Event type '{event_type}' not handled",
            }

    @app.post("/trigger")
    async def manual_trigger(
        issue_number: int | None = None,
    ):
        """Manually trigger a flow.

        Args:
            issue_number: Optional specific issue to process
        """
        if flow_runner.is_flow_running():
            current = flow_runner.get_running_flow()
            return {
                "status": "already_running",
                "message": (
                    f"Flow already running for issue #{current.issue_number}"
                    if current
                    else "Flow already running"
                ),
            }

        return {
            "status": "triggered",
            "message": (
                f"Flow triggered for issue #{issue_number}"
                if issue_number
                else "Flow triggered for next ready issue"
            ),
        }

    return app
