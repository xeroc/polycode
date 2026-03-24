"""GitHub App authentication using PyGithub's native GitHub App support."""

import hashlib
import hmac
import logging

import github
from github import Auth, Github, GithubIntegration
from github.Installation import Installation

logger = logging.getLogger(__name__)


class GitHubAppAuth:
    """GitHub App authentication using PyGithub's GithubIntegration.

    Wraps PyGithub's native GitHub App support with:
    - Webhook signature verification
    - Convenient access to Github client instances
    """

    def __init__(
        self,
        app_id: str | int,
        private_key: str,
    ):
        self.app_id = str(app_id)
        self.private_key = private_key

        # Create PyGithub GithubIntegration
        self._auth = Auth.AppAuth(app_id=self.app_id, private_key=private_key)
        self._integration = GithubIntegration(auth=self._auth)

        # Cache for Github clients per installation
        self._clients: dict[int, Github] = {}

    @property
    def integration(self) -> GithubIntegration:
        """Get the GithubIntegration instance."""
        return self._integration

    def get_installation_token(self, installation_id: int) -> str | None:
        """Get an installation access token.

        Args:
            installation_id: GitHub App installation ID

        Returns:
            Installation token or None if failed
        """
        # Get fresh token
        try:
            # Fallback: create token directly via API
            return self._create_installation_token(installation_id)
        except github.GithubException as e:
            logger.error(f"Failed to get installation token: {e}")
            return None

    def _create_installation_token(self, installation_id: int) -> str | None:
        """Create installation token via GitHub API (fallback method)."""
        return self._integration.get_access_token(installation_id=installation_id).token

    def get_installation(self, installation_id: int) -> Installation | None:
        """Get installation by ID using PyGithub.

        Args:
            installation_id: GitHub App installation ID

        Returns:
            Installation object or None
        """
        try:
            return self._integration.get_app_installation(installation_id)
        except github.GithubException as e:
            logger.error(f"Failed to get installation {installation_id}: {e}")
            return None

    def get_repo_installation(self, owner: str, repo: str) -> Installation | None:
        """Get installation for a specific repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Installation object or None
        """
        try:
            return self._integration.get_repo_installation(owner, repo)
        except github.GithubException as e:
            logger.error(f"Failed to get installation for {owner}/{repo}: {e}")
            return None

    def get_org_installation(self, org: str) -> Installation | None:
        """Get installation for an organization.

        Args:
            org: Organization name

        Returns:
            Installation object or None
        """
        try:
            return self._integration.get_org_installation(org)
        except github.GithubException as e:
            logger.error(f"Failed to get installation for org {org}: {e}")
            return None

    def list_installations(self) -> list[Installation]:
        """List all installations for this GitHub App.

        Returns:
            List of Installation objects
        """
        try:
            return list(self._integration.get_installations())
        except github.GithubException as e:
            logger.error(f"Failed to list installations: {e}")
            return []

    def verify_webhook_payload(self, payload: str | bytes, signature: str, secret: str) -> bool:
        """Verify GitHub webhook signature.

        Args:
            payload: Raw webhook payload (string or bytes)
            signature: X-Hub-Signature-256 header value
            secret: Webhook secret

        Returns:
            True if signature is valid
        """
        if isinstance(payload, str):
            payload = payload.encode()

        expected_signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        return hmac.compare_digest(f"sha256={expected_signature}", signature)
