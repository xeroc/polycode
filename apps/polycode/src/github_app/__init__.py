"""GitHub App module for multi-repo CrewAI flow automation."""

from github_app.auth import GitHubAppAuth
from github_app.installation_manager import InstallationManager
from github_app.label_mapper import LabelFlowMapper
from github_app.webhook_handler import GitHubAppWebhookHandler

__all__ = [
    "GitHubAppAuth",
    "InstallationManager",
    "LabelFlowMapper",
    "GitHubAppWebhookHandler",
]
