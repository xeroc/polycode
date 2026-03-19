"""Flow execution commands for Polycode CLI."""

import json
import sys
from typing import Any

import typer
from alive_progress import alive_bar
from rich import box
from rich.console import Console
from rich.table import Table

from bootstrap import init_plugins
from cli import print_error, print_info, print_success
from cli.utils import get_logger
from flowbase import KickoffIssue, KickoffRepo
from project_manager.github import GitHubProjectManager
from project_manager.types import ProjectConfig, StatusMapping

log = get_logger(__name__)
console = Console()
flow_app = typer.Typer(help="Flow execution commands")


@flow_app.command("list")
def flow_list(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """List all available flows."""
    if verbose:
        import cli.utils

        cli.utils.setup_logging("DEBUG")

    print_info("📋 Available flows:")

    flows: dict[str, str] = {
        "ralph": "Ralph - Feature development orchestrator with per-story commits",
        "feature_dev": "Feature development flow (legacy)",
    }

    table = Table(title="Available Flows", box=box.ROUNDED)
    table.add_column("Name", style="cyan", header_style="bold")
    table.add_column("Description", style="white")

    for name, description in flows.items():
        table.add_row(name, description)

    console.print(table)
    print_success(f"Found {len(flows)} flow(s)")


@flow_app.command("run")
def flow_run(
    flow_name: str = typer.Argument(..., help="Flow name to execute"),
    repo_owner: str = typer.Option(None, "--repo-owner", "-o", help="Repository owner (required)"),
    repo_name: str = typer.Option(None, "--repo-name", "-r", help="Repository name (required)"),
    issue_number: int = typer.Option(None, "--issue-number", "-i", help="Issue number to process (required)"),
    project_id: str | None = typer.Option(None, "--project-id", "-p", help="GitHub project ID/number"),
    provider: str = typer.Option("github", "--provider", help="Provider type (default: github)"),
    token: str | None = typer.Option(None, "--token", "-t", help="GitHub token (or use GITHUB_TOKEN env var)"),
    status_mapping: str | None = typer.Option(None, "--status-mapping", help="Custom status mapping as JSON"),
    plugins: list[str] = typer.Option([], "--plugin", help="Load additional plugins (repeatable)"),
    extra: str | None = typer.Option(None, "--extra", help="Extra configuration as JSON (for communications, etc.)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Run a flow manually against a repository.

    Requires full project configuration including provider, repository details,
    and optional extras for custom behavior.
    """
    if verbose:
        import cli.utils

        cli.utils.setup_logging("DEBUG")

    if not repo_owner:
        print_error("--repo-owner is required when specifying repo configuration")
        sys.exit(1)

    if not repo_name:
        print_error("--repo-name is required when specifying repo configuration")
        sys.exit(1)

    if not issue_number:
        print_error("--issue-number is required")
        sys.exit(1)

    print_info(f"🚀 Running flow '{flow_name}'")
    print_info(f"   Repository: {repo_owner}/{repo_name}")
    print_info(f"   Issue: #{issue_number}")

    try:
        init_plugins()

        if status_mapping:
            try:
                mapping_data = json.loads(status_mapping)
                status_map = StatusMapping.from_dict(mapping_data)
            except json.JSONDecodeError as e:
                print_error(f"Invalid status mapping JSON: {e}")
                sys.exit(1)
        else:
            status_map = StatusMapping()

        extra_data: dict[str, Any] = {}
        if extra:
            try:
                extra_data = json.loads(extra)
            except json.JSONDecodeError as e:
                print_error(f"Invalid extra JSON: {e}")
                sys.exit(1)

        if plugins:
            print_info(f"   Plugins: {', '.join(plugins)}")

        config = ProjectConfig(
            provider=provider,
            repo_owner=repo_owner,
            repo_name=repo_name,
            project_identifier=project_id,
            token=token,
            status_mapping=status_map,
            extra=extra_data,
        )

        manager = GitHubProjectManager(config)
        issue = manager.get_issue(issue_number)

        if not issue:
            print_error(f"Issue #{issue_number} not found")
            sys.exit(1)

        print_info(f"   Title: {issue.title}")

        from bootstrap import bootstrap

        bootstrap(config={"modules": {p: {} for p in plugins}})

        from uuid import NAMESPACE_DNS, uuid5

        flow_identifier = f"{repo_owner}/{repo_name}/{issue_number}"
        kickoff_issue = KickoffIssue(
            id=issue_number,
            flow_id=uuid5(NAMESPACE_DNS, flow_identifier),
            title=issue.title,
            body=issue.body or "",
            memory_prefix=f"{repo_owner}/{repo_name}",
            repository=KickoffRepo(
                owner=repo_owner,
                repository=repo_name,
            ),
            project_config=config,
        )
        with alive_bar(
            0,
            title=f"Running {flow_name}",
            spinner="squares",
            force_tty=True,
            enrich_print=False,
            enrich_offset=0,
            monitor=False,
        ) as bar:
            bar.text = (f"Processing issue #{issue_number}: {issue.title}",)

            from ralph import kickoff as kickoff_ralph

            kickoff_ralph(kickoff_issue)

            bar()

        print_success(f"Flow '{flow_name}' completed for issue #{issue_number}")

    except Exception as e:
        print_error(f"Flow execution failed: {e}")
        log.exception(f"Flow execution failed: {e}")
        sys.exit(1)
