"""Project management commands for Polycode CLI."""

import sys

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from cli import print_error, print_info, print_success
from cli.utils import get_logger

log = get_logger(__name__)
console = Console()

project_app = typer.Typer(help="GitHub project management commands")


def create_manager_from_env():
    """Create project manager from environment variables.

    Uses GitHub App authentication via installation_id when available.

    Returns:
        Configured project manager
    """
    import os

    from project_manager.config import settings
    from project_manager.types import ProjectConfig, StatusMapping

    provider = settings.PROJECT_PROVIDER or "github"
    repo_owner = settings.REPO_OWNER or os.getenv("REPO_OWNER")
    repo_name = settings.REPO_NAME or os.getenv("REPO_NAME")
    project_identifier = settings.PROJECT_IDENTIFIER or os.getenv("PROJECT_IDENTIFIER")
    installation_id = os.getenv("INSTALLATION_ID")

    status_mapping = StatusMapping(
        todo=os.getenv("STATUS_TODO", "Todo"),
        ready=os.getenv("STATUS_READY", "Ready"),
        in_progress=os.getenv("STATUS_IN_PROGRESS", "In progress"),
        reviewing=os.getenv("STATUS_REVIEWING", "In review"),
        done=os.getenv("STATUS_DONE", "Done"),
        blocked=os.getenv("STATUS_BLOCKED", "Blocked"),
    )

    config = ProjectConfig(
        provider=provider,
        repo_owner=repo_owner or "",
        repo_name=repo_name or "",
        project_identifier=project_identifier,
        installation_id=int(installation_id) if installation_id else None,
        status_mapping=status_mapping,
    )

    if provider == "github":
        from project_manager.github import GitHubProjectManager

        return GitHubProjectManager(config)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


@project_app.command("sync")
def project_sync(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Sync all open issues to project."""
    if verbose:
        import cli.utils

        cli.utils.setup_logging("DEBUG")

    print_info("🔄 Syncing issues to project...")

    try:
        manager = create_manager_from_env()
        added = manager.sync_issues_to_project()

        if added > 0:
            print_success(f"Added {added} issues to project")
        else:
            print_info("All issues already in project")

    except Exception as e:
        print_error(f"Sync failed: {e}")
        log.exception(f"Sync failed: {e}")
        sys.exit(1)


@project_app.command("list")
def project_list(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """List all project items."""
    if verbose:
        import cli.utils

        cli.utils.setup_logging("DEBUG")

    print_info("📋 Listing project items...")

    try:
        manager = create_manager_from_env()
        items = manager.get_project_items()

        table = Table(title="Project Items", box=box.ROUNDED)
        table.add_column("#", style="cyan", header_style="bold")
        table.add_column("Status", style="green")
        table.add_column("Title", style="white")

        for item in items:
            status = item.status or "No status"
            table.add_row(f"#{item.issue_number}", f"[{status}]", item.title)

        console.print(table)
        print_success(f"Found {len(items)} item(s)")

    except Exception as e:
        print_error(f"List failed: {e}")
        log.exception(f"List failed: {e}")
        sys.exit(1)


@project_app.command("status")
def project_status(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Show current flow status from GitHub Project."""
    if verbose:
        import cli.utils

        cli.utils.setup_logging("DEBUG")

    print_info("🔍 Checking flow status...")

    try:
        manager = create_manager_from_env()

        items = manager.get_project_items()

        from project_manager.types import IssueStatus

        ready_status = manager.config.status_mapping.to_provider_status(IssueStatus.READY)
        in_progress_status = manager.config.status_mapping.to_provider_status(IssueStatus.IN_PROGRESS)

        ready = [item for item in items if item.status == ready_status]
        in_progress = [item for item in items if item.status == in_progress_status]

        if in_progress:
            item = in_progress[0]
            console.print(f"[bold green]✓ Flow running:[/] Issue #{item.issue_number}")
            console.print(f"  Title: {item.title}")
            console.print(f"  Status: {item.status}")
        else:
            console.print("[yellow]✗ No flow currently running[/]")

        console.print(f"\n[bold]Ready:[/] {len(ready)}, [bold]In progress:[/] {len(in_progress)}")

        if ready:
            console.print("\n[cyan]Next ready issues:[/]")
            for item in ready[:5]:
                console.print(f"  #{item.issue_number}: {item.title}")

        print_success("Status check complete")

    except Exception as e:
        print_error(f"Status check failed: {e}")
        log.exception(f"Status check failed: {e}")
        sys.exit(1)
