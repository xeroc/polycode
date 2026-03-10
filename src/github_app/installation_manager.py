"""GitHub App installation manager - manages installations and tokens."""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from github_app.auth import GitHubAppAuth
from github_app.models import GitHubAppInstallation, GitHubWebhookRegistration

logger = logging.getLogger(__name__)


class InstallationManager:
    """Manages GitHub App installations and their lifecycle."""

    def __init__(self, db_session: Session, github_auth: GitHubAppAuth):
        self.db_session = db_session
        self.github_auth = github_auth

    def register_installation(
        self, installation_data: Dict[str, Any]
    ) -> GitHubAppInstallation:
        """Register or update a GitHub App installation."""
        installation_id = installation_data["id"]

        existing = (
            self.db_session.query(GitHubAppInstallation)
            .filter(GitHubAppInstallation.installation_id == installation_id)
            .first()
        )

        if existing:
            result = self.update_installation(
                installation_id, installation_data
            )
            assert result is not None, (
                "Update should succeed for existing installation"
            )
            return result

        installation = GitHubAppInstallation(
            installation_id=installation_id,
            account_id=installation_data["account"]["id"],
            account_login=installation_data["account"]["login"],
            account_type=installation_data["account"]["type"],
            app_id=installation_data["app_id"],
            permissions=installation_data.get("permissions", {}),
            events=installation_data.get("events", []),
            repositories={},
        )

        self.db_session.add(installation)
        self.db_session.commit()

        logger.info(
            f"Registered installation {installation_id} "
            f"for {installation_data['account']['login']}"
        )

        return installation

    def update_installation(
        self,
        installation_id: int,
        installation_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[GitHubAppInstallation]:
        """Update an existing installation."""
        installation = (
            self.db_session.query(GitHubAppInstallation)
            .filter(GitHubAppInstallation.installation_id == installation_id)
            .first()
        )

        if not installation:
            return None

        if installation_data:
            installation.account_id = installation_data["account"]["id"]
            installation.account_login = installation_data["account"]["login"]
            installation.account_type = installation_data["account"]["type"]
            installation.permissions = installation_data.get("permissions", {})
            installation.events = installation_data.get("events", [])

        self.db_session.commit()
        logger.info(f"Updated installation {installation_id}")

        return installation

    def deactivate_installation(self, installation_id: int) -> bool:
        """Deactivate an installation (e.g., when uninstalled from GitHub)."""
        installation = (
            self.db_session.query(GitHubAppInstallation)
            .filter(GitHubAppInstallation.installation_id == installation_id)
            .first()
        )

        if not installation:
            return False

        installation.is_active = False
        self.db_session.commit()

        logger.info(f"Deactivated installation {installation_id}")
        return True

    def get_installation(
        self, installation_id: int
    ) -> Optional[GitHubAppInstallation]:
        """Get an active installation by ID."""
        return (
            self.db_session.query(GitHubAppInstallation)
            .filter(
                GitHubAppInstallation.installation_id == installation_id,
                GitHubAppInstallation.is_active.is_(True),
            )
            .first()
        )

    def list_installations(
        self, active_only: bool = True
    ) -> List[GitHubAppInstallation]:
        """List all installations."""
        query = self.db_session.query(GitHubAppInstallation)

        if active_only:
            query = query.filter(GitHubAppInstallation.is_active.is_(True))

        return query.all()

    def sync_repositories(self, installation_id: int) -> Optional[List[str]]:
        """Sync repository list from GitHub for this installation."""
        installation = self.get_installation(installation_id)
        if not installation:
            return None

        repos = self.github_auth.get_installation_repos(installation_id)
        if repos:
            installation.repositories = {"repos": repos}
            self.db_session.commit()
            logger.info(
                f"Synced {len(repos)} repos for installation {installation_id}"
            )

        return repos

    def get_installation_token(self, installation_id: int) -> Optional[str]:
        """Get an installation access token."""
        return self.github_auth.get_installation_token(installation_id)

    def register_webhook(
        self,
        installation_id: int,
        target_repo: str,
        events: List[str],
        secret: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> GitHubWebhookRegistration:
        """Register a webhook for a specific repository."""
        webhook = GitHubWebhookRegistration(
            installation_id=installation_id,
            target_repo=target_repo,
            events=events,
            secret=secret,
            webhook_url=webhook_url,
            is_active=True,
        )

        self.db_session.add(webhook)
        self.db_session.commit()

        logger.info(
            f"Registered webhook for {target_repo} (installation: {installation_id})"
        )

        return webhook

    def list_webhooks(
        self,
        installation_id: Optional[int] = None,
        target_repo: Optional[str] = None,
        active_only: bool = True,
    ) -> List[GitHubWebhookRegistration]:
        """List webhooks, optionally filtered."""
        query = self.db_session.query(GitHubWebhookRegistration)

        if installation_id:
            query = query.filter(
                GitHubWebhookRegistration.installation_id == installation_id
            )

        if target_repo:
            query = query.filter(
                GitHubWebhookRegistration.target_repo == target_repo
            )

        if active_only:
            query = query.filter(GitHubWebhookRegistration.is_active.is_(True))

        return query.all()

    def deactivate_webhook(self, webhook_id: int) -> bool:
        """Deactivate a webhook."""
        webhook = (
            self.db_session.query(GitHubWebhookRegistration)
            .filter(GitHubWebhookRegistration.id == webhook_id)
            .first()
        )

        if not webhook:
            return False

        webhook.is_active = False
        self.db_session.commit()

        logger.info(f"Deactivated webhook {webhook_id}")
        return True
