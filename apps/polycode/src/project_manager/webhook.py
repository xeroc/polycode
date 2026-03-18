"""DEPRECATED: Webhook functionality moved to github_app.

This module is deprecated and will be removed in a future version.

Use github_app.app instead, which provides:
- GitHub App webhooks (multi-repo, installation-based)
- Legacy webhooks (single repo, token-based)
- FlowRunner integration for concurrent flow management

Migration guide:
- OLD: from project_manager.webhook import create_webhook_app
- NEW: from github_app.app import app

The unified webhook server is at src/github_app/app.py
"""

import warnings

warnings.warn(
    "project_manager.webhook is deprecated. Use github_app.app instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility (will be removed)
from github_app.app import app as webhook_app

__all__ = ["webhook_app"]
