"""FastAPI webhook endpoint for GitHub."""

import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
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

    def handle_issue_event(self, payload: GitHubWebhookPayload) -> dict[str, Any]:
        """Handle GitHub issue event.

        Args:
            payload: Webhook payload

        Returns:
            Response dict with status
        """
        if not payload.issue:
            return {"status": "ignored", "reason": "no issue in payload"}

        if not payload.action:
            return {"status": "ignored", "reason": "no action in payload"}

        if payload.action not in ["opened", "reopened", "labeled"]:
            return {
                "status": "ignored",
                "reason": f"action '{payload.action}' not handled",
            }

        issue_data = payload.issue
        issue_number = issue_data.get("number")

        log.info(f"Received issue #{issue_number} - {payload.action}")
        log.info(f"Title: {issue_data.get('title')}")
        log.info(f"Repository: {payload.repository.get('full_name')}")

        if not issue_number:
            return {"status": "error", "reason": "no issue number in payload"}

        issue = Issue(
            id=issue_number,
            number=issue_number,
            title=issue_data.get("title", ""),
            body=issue_data.get("body"),
            node_id=issue_data.get("node_id"),
            url=issue_data.get("html_url"),
            labels=[label.get("name", "") for label in issue_data.get("labels", [])],
        )

        if payload.action == "labeled":
            label_name = payload.label.get("name") if payload.label else None
            if label_name == MOVE_TO_READY_STATE_LABEL:
                log.info(
                    f"Label '{ MOVE_TO_READY_STATE_LABEL }' added to issue #{issue_number}"
                )
                updated = self.flow_runner.manager.update_issue_status(
                    issue_number, "Ready"
                )
                if updated:
                    log.info(f"Updated issue #{issue_number} to Ready status")
                    return {
                        "status": "updated",
                        "issue_number": issue_number,
                        "message": f"Moved issue #{issue_number} to Ready",
                    }
                else:
                    log.warning(f"Failed to update issue #{issue_number} to Ready")
                    return {
                        "status": "error",
                        "issue_number": issue_number,
                        "message": f"Failed to update issue #{issue_number} to Ready",
                    }

        added = self.flow_runner.manager.add_issue_to_project(issue)
        if added:
            log.info(f"Added issue #{issue_number} to project")
        else:
            log.info(f"Issue #{issue_number} already in project or failed to add")

        triggered = self.flow_runner.trigger_flow()
        if triggered:
            return {
                "status": "triggered",
                "issue_number": issue_number,
                "message": f"Started processing issue #{issue_number}",
            }
        else:
            running = self.flow_runner.get_running_flow()
            if running:
                return {
                    "status": "queued",
                    "issue_number": issue_number,
                    "message": f"Flow already running for issue #{running.issue_number}, queued for later",
                }
            else:
                return {
                    "status": "queued",
                    "issue_number": issue_number,
                    "message": f"Issue #{issue_number} added to project, not in ready state",
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
        background_tasks: BackgroundTasks,
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

            def process_event():
                try:
                    result = handler.handle_issue_event(payload)
                    log.info(f"Event processed: {result}")
                except Exception as e:
                    log.error(f"Error processing event: {e}", exc_info=True)

            background_tasks.add_task(process_event)

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
        background_tasks: BackgroundTasks,
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

        def trigger():
            try:
                flow_runner.trigger_flow(issue_number)
            except Exception as e:
                log.error(f"Error triggering flow: {e}", exc_info=True)

        background_tasks.add_task(trigger)

        return {
            "status": "triggered",
            "message": (
                f"Flow triggered for issue #{issue_number}"
                if issue_number
                else "Flow triggered for next ready issue"
            ),
        }

    return app
