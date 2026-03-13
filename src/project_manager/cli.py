"""CLI tools for project management."""

import logging
import os

import click
from sqlalchemy import create_engine
import uvicorn

from celery_tasks.tasks import kickoff_task
from persistence.postgres import Base
from github_app import (
    models,
)  # side-effect: required to be loaded for createion  # pyright:ignore #ty:ignore

from .github import GitHubProjectManager  # noqa: E402
from .types import IssueStatus, ProjectConfig, StatusMapping  # noqa: E402
from .config import settings

log = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def create_manager_from_env() -> GitHubProjectManager:
    """Create project manager from environment variables.

    Required environment variables:
        PROJECT_PROVIDER: Provider type (e.g., "github")
        REPO_OWNER: Repository owner
        REPO_NAME: Repository name
        PROJECT_IDENTIFIER: Project number/ID
        GITHUB_TOKEN: GitHub access token (for GitHub provider)

    Optional environment variables:
        STATUS_TODO: Custom "Todo" status name
        STATUS_READY: Custom "Ready" status name
        STATUS_IN_PROGRESS: Custom "In progress" status name
        STATUS_REVIEWING: Custom "In review" status name
        STATUS_DONE: Custom "Done" status name
        STATUS_BLOCKED: Custom "Blocked" status name

    Returns:
        Configured project manager
    """
    from .config import settings

    provider = settings.PROJECT_PROVIDER or "github"
    repo_owner = settings.REPO_OWNER
    repo_name = settings.REPO_NAME
    project_identifier = settings.PROJECT_IDENTIFIER

    if not repo_owner or not repo_name or not project_identifier:
        raise ValueError(
            "Missing required environment variables: REPO_OWNER, REPO_NAME, PROJECT_IDENTIFIER"
        )

    status_mapping = StatusMapping(
        todo=os.environ.get("STATUS_TODO", "Todo"),
        ready=os.environ.get("STATUS_READY", "Ready"),
        in_progress=os.environ.get("STATUS_IN_PROGRESS", "In progress"),
        reviewing=os.environ.get("STATUS_REVIEWING", "In review"),
        done=os.environ.get("STATUS_DONE", "Done"),
        blocked=os.environ.get("STATUS_BLOCKED", "Blocked"),
    )

    config = ProjectConfig(
        provider=provider,
        repo_owner=repo_owner,
        repo_name=repo_name,
        project_identifier=project_identifier,
        status_mapping=status_mapping,
    )

    if provider == "github":
        return GitHubProjectManager(config)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


@click.group()
def cli() -> None:
    """Project management CLI tools."""


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def sync(verbose: bool) -> None:
    """Sync all open issues to the project."""
    setup_logging(verbose)

    manager = create_manager_from_env()
    added = manager.sync_issues_to_project()

    if added > 0:
        click.echo(f"Added {added} issues to project")
    else:
        click.echo("All issues already in project")


@cli.command("list")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def list_items(verbose: bool) -> None:
    """List all project items."""
    setup_logging(verbose)

    manager = create_manager_from_env()
    items = manager.get_project_items()

    for item in items:
        status = item.status or "No status"
        click.echo(f"#{item.issue_number:4d} [{status:12s}] {item.title}")


@cli.command()
@click.option("--host", default="0.0.0.0", help="Webhook server host")
@click.option("--port", default=8000, help="Webhook server port")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def webhook(host: str, port: int, verbose: bool) -> None:
    """Start webhook server for GitHub events.

    Uses the unified GitHub App webhook server.
    For GitHub App webhooks (multi-repo), set GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY.
    For legacy webhooks (single repo), set GITHUB_TOKEN and repo env vars.
    """
    setup_logging(verbose)

    log.info("Creating tables ...")
    connection_string = settings.DATABASE_URL
    engine = create_engine(connection_string)
    Base.metadata.create_all(engine)

    click.echo(f"Starting unified webhook server on {host}:{port}")

    if settings.GITHUB_APP_ID:
        click.echo("Mode: GitHub App (multi-repo)")
        click.echo(f"Webhook endpoint: http://{host}:{port}/webhook/github")
        click.echo(f"Health check: http://{host}:{port}/health")
        click.echo(f"Manual trigger: POST http://{host}:{port}/trigger")
    else:
        manager = create_manager_from_env()
        click.echo("Mode: Legacy (single repo)")
        click.echo(
            f"Repository: {manager.config.repo_owner}/{manager.config.repo_name}"
        )
        click.echo(f"Project: {manager.config.project_identifier}")
        click.echo(f"Webhook endpoint: http://{host}:{port}/webhook/github")

    from github_app.app import app

    uvicorn.run(app, host=host, port=port, log_level="info" if verbose else "warning")


@cli.command("github-issue")
@click.argument("issue_number", type=int)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def github_issue_cmd(issue_number: int, verbose: bool) -> None:
    """Process a specific GitHub issue by number.

    Fetches the issue and moves it to 'In progress' status.
    """
    setup_logging(verbose)

    manager = create_manager_from_env()
    click.echo(f"Processing issue #{issue_number}...")

    in_progress_status = manager.config.status_mapping.to_provider_status(
        IssueStatus.IN_PROGRESS
    )

    success = manager.update_issue_status(issue_number, in_progress_status)

    if success:
        click.echo(f"Issue #{issue_number} moved to '{in_progress_status}'")
        kickoff_task(manager.config.model_dump(), issue_number)  # pyright:ignore
    else:
        click.echo(f"Failed to update issue #{issue_number}", err=True)
        raise SystemExit(1)


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def status(verbose: bool) -> None:
    """Show current flow status from GitHub Project."""
    setup_logging(verbose)

    manager = create_manager_from_env()

    items = manager.get_project_items()
    ready_status = manager.config.status_mapping.to_provider_status(IssueStatus.READY)
    in_progress_status = manager.config.status_mapping.to_provider_status(
        IssueStatus.IN_PROGRESS
    )

    ready = [item for item in items if item.status == ready_status]
    in_progress = [item for item in items if item.status == in_progress_status]

    if in_progress:
        item = in_progress[0]
        click.echo(f"✓ Flow running: Issue #{item.issue_number}")
        click.echo(f"  Title: {item.title}")
        click.echo(f"  Status: {item.status}")
    else:
        click.echo("✗ No flow currently running")

    click.echo(f"\nReady: {len(ready)}, In progress: {len(in_progress)}")

    if ready:
        click.echo("\nNext ready issues:")
        for item in ready[:5]:
            click.echo(f"  #{item.issue_number}: {item.title}")


if __name__ == "__main__":
    cli()
