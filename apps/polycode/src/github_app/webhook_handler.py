"""GitHub App webhook handler - integrates with FlowRunner and existing system."""

from project_manager.config import settings

import hashlib
import hmac
import json
import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request

from github_app.auth import GitHubAppAuth
from github_app.installation_manager import InstallationManager
from github_app.label_mapper import LabelFlowMapper
from project_manager.flow_runner import FlowRunner
from project_manager.github import GitHubProjectManager
from project_manager.types import ProjectConfig, StatusMapping

logger = logging.getLogger(__name__)


class GitHubAppWebhookHandler:
    """Handles GitHub webhooks for GitHub App installations.

    Integrates with existing system:
    - Uses FlowRunner for concurrent flow management
    - Delegates to existing Celery tasks (kickoff_task)
    - Triggers CrewAI flows (ralph, etc.)
    - Works with existing GitHubProjectManager
    """

    def __init__(
        self,
        github_auth: GitHubAppAuth,
        installation_manager: InstallationManager,
        label_mapper: LabelFlowMapper,
        webhook_secret: Optional[str] = None,
    ):
        self.github_auth = github_auth
        self.installation_manager = installation_manager
        self.label_mapper = label_mapper
        self.webhook_secret = webhook_secret

    def validate_signature(self, payload: bytes, signature: str) -> bool:
        """Validate GitHub webhook signature (from project_manager/webhook.py)."""
        if not self.webhook_secret:
            logger.warning("No webhook secret configured, skipping signature validation")
            return True

        if not signature.startswith("sha256="):
            logger.error("Invalid signature format")
            return False

        expected_signature = signature[7:]

        mac = hmac.new(self.webhook_secret.encode(), msg=payload, digestmod=hashlib.sha256)
        computed_signature = mac.hexdigest()

        return hmac.compare_digest(computed_signature, expected_signature)

    async def handle_webhook(self, request: Request) -> Dict[str, Any]:
        """Main webhook entry point."""
        payload_bytes = await request.body()
        payload_str = payload_bytes.decode("utf-8")
        payload = json.loads(payload_str)

        event_type = request.headers.get("X-GitHub-Event")
        signature = request.headers.get("X-Hub-Signature-256", "")
        delivery_id = request.headers.get("X-GitHub-Delivery", "")

        logger.info(f"Received webhook: {event_type} (delivery: {delivery_id})")

        if event_type == "ping":
            return self._handle_ping(payload)

        installation_id = self._extract_installation_id(payload)
        if not installation_id:
            raise HTTPException(status_code=400, detail="Missing installation ID")

        if self.webhook_secret and signature:
            if not self.validate_signature(payload_bytes, signature):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

        if event_type == "installation":
            return await self._handle_installation_event(payload)
        elif event_type == "issues":
            return await self._handle_issue_event(installation_id, payload)
        else:
            logger.info(f"Unhandled event type: {event_type}")
            return {"status": "ignored", "event": event_type}

    def _extract_installation_id(self, payload: Dict[str, Any]) -> Optional[int]:
        """Extract installation ID from payload."""
        if "installation" in payload:
            return payload["installation"].get("id")
        return None

    def _handle_ping(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping event (from project_manager/webhook.py)."""
        logger.info("Received ping from GitHub")
        logger.info(f"  Zen: {payload.get('zen')}")

        hook = payload.get("hook", {})
        if hook:
            events = hook.get("events", [])
            logger.info(f"  Events: {events}")
            logger.info(f"  URL: {hook.get('config', {}).get('url')}")

        return {
            "status": "pong",
            "zen": payload.get("zen"),
            "hook_id": payload.get("hook_id"),
            "events": hook.get("events", []) if hook else [],
        }

    async def _handle_installation_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle installation lifecycle events."""
        action = payload.get("action")
        installation = payload.get("installation", {})

        if action == "created":
            self.installation_manager.register_installation(installation)
            logger.info(f"Installation created: {installation.get('id')}")
        elif action == "deleted":
            installation_id = installation.get("id")
            if installation_id:
                self.installation_manager.deactivate_installation(installation_id)
                logger.info(f"Installation deleted: {installation_id}")

        return {"status": "processed", "action": action}

    def _resolve_flow_name(self, installation_id: int, labels: list[dict], repo_slug: str) -> str | None:
        """Resolve flow_name from issue labels using LabelFlowMapper.

        Checks each label against the label_flow_mappings table for the
        installation, ordered by priority. Returns the first match.

        Args:
            installation_id: GitHub App installation ID
            labels: List of label dicts from the issue payload
            repo_slug: Full repo slug (owner/repo) for pattern matching

        Returns:
            flow_name if a mapping is found, None otherwise
        """
        for label in labels:
            label_name = label.get("name", "")
            mapping = self.label_mapper.get_flow_for_label(installation_id, label_name, repo_slug)
            if mapping:
                logger.info(
                    f"Resolved label '{label_name}' -> flow '{mapping.flow_name}' "
                    f"for {repo_slug} (installation: {installation_id})"
                )
                return mapping.flow_name

        logger.warning(
            f"No label->flow mapping found for {repo_slug} "
            f"(installation: {installation_id}, labels: {[lbl.get('name') for lbl in labels]})"
        )
        label_names = [lbl.get("name") for lbl in labels]

        # FIXME: default labels should be dealt with differently
        if f"{settings.FLOW_LABEL_PREFIX}specify".lower() in label_names:
            return "specify"
        if f"{settings.FLOW_LABEL_PREFIX}implement".lower() in label_names:
            return "ralph"
        return None

    async def _handle_issue_event(self, installation_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle issue events - uses FlowRunner for concurrent flow management.

        This method:
        1. Gets installation token and creates per-repo GitHubProjectManager
        2. Resolves flow_name from issue labels via LabelFlowMapper
        3. Creates FlowRunner to check if flow is already running
        4. Delegates to kickoff_task with the resolved flow_name
        """
        action = payload.get("action")
        issue = payload.get("issue", {})
        repo = payload.get("repository", {})
        repo_slug = repo.get("full_name")
        issue_number = issue.get("number")
        labels = issue.get("labels", [])

        logger.info(f"Processing issue event: {action} on {repo_slug}#{issue_number} (installation: {installation_id})")

        if action not in ["opened", "reopened", "labeled"]:
            return {
                "status": "ignored",
                "reason": f"action '{action}' not handled",
                "issue": issue_number,
            }

        flow_name = self._resolve_flow_name(installation_id, labels, repo_slug)

        # Get installation token
        token = self.installation_manager.get_installation_token(installation_id)
        if not token:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get installation token for {installation_id}",
            )

        # Create per-repo project manager and flow runner
        try:
            owner, name = repo_slug.split("/", 1)

            config = ProjectConfig(
                provider="github",
                repo_owner=owner,
                repo_name=name,
                project_identifier=None,
                token=token,
                status_mapping=StatusMapping(),
            )

            manager = GitHubProjectManager(config)
            flow_runner = FlowRunner(manager=manager)
            task_id = flow_runner.trigger_flow(issue_number, flow_name=flow_name)

            return {
                "status": "queued",
                "task_id": task_id,
                "installation_id": installation_id,
            }

        except Exception as e:
            logger.error(f"Failed to create project manager for {repo_slug}: {e}")

            return {
                "status": "failed",
                "task_id": None,
                "installation_id": installation_id,
            }
