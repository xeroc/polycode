"""Flow execution commands for Polycode CLI."""

import json
import sys
from typing import Any
from uuid import NAMESPACE_DNS, uuid5

import typer
from alive_progress import alive_bar
from rich import box
from rich.console import Console
from rich.table import Table

from bootstrap import init_plugins
from cli import print_error, print_info, print_success
from cli.utils import get_logger
from flows.base import KickoffIssue, KickoffRepo
from project_manager.github import GitHubProjectManager
from project_manager.types import ProjectConfig, StatusMapping

log = get_logger(__name__)
console = Console()
flow_app = typer.Typer(help="Flow execution commands")


@flow_app.command("list")
def flow_list(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """List all available flows from registered modules."""
    if verbose:
        import cli.utils

        cli.utils.setup_logging("DEBUG")

    from flows.registry import get_flow_registry

    from flows.specify import SpecifyModule
    from flows.ralph import RalphModule
    from modules.registry import ModuleRegistry

    from bootstrap import init_plugins

    module_registry = ModuleRegistry()
    module_registry.discover()

    module_registry.register_builtin(RalphModule)
    module_registry.register_builtin(SpecifyModule)

    registry = get_flow_registry()
    registry.collect_from_modules(module_registry.modules)

    init_plugins()

    flow_names = registry.list_flows()

    table = Table(title="Available Flows", box=box.ROUNDED)
    table.add_column("Name", style="cyan", header_style="bold")
    table.add_column("Description", style="white")
    table.add_column("Labels", style="yellow")
    table.add_column("Priority", style="dim", justify="right")

    for name in sorted(flow_names):
        flow_def = registry.get_flow(name)
        if flow_def:
            labels = ", ".join(flow_def.supported_labels) if flow_def.supported_labels else "-"
            table.add_row(
                name,
                flow_def.description or "-",
                labels,
                str(flow_def.priority),
            )

    console.print(table)
    print_success(f"Found {len(flow_names)} flow(s)")


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

        flow_identifier = f"{flow_name}/{manager.config.repo_owner}/{manager.config.repo_name}/{issue_number}"

        comments = manager.get_comments(issue_number)

        kickoff_issue = KickoffIssue(
            id=issue_number,
            flow_id=uuid5(NAMESPACE_DNS, flow_identifier),
            title=issue.title,
            body=issue.body or "",
            comments=[
                {
                    "id": c.id,
                    "user": c.user.login if c.user else None,
                    "body": c.body,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in comments
            ],
            memory_prefix=f"{manager.config.repo_owner}/{manager.config.repo_name}",
            repository=KickoffRepo(
                owner=manager.config.repo_owner,
                repository=manager.config.repo_name,
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
            bar.text = f"Processing issue #{issue_number}: {issue.title}"

            from flows.ralph import ralph_kickoff

            ralph_kickoff(kickoff_issue)

            bar()

        print_success(f"Flow '{flow_name}' completed for issue #{issue_number}")

    except Exception as e:
        print_error(f"Flow execution failed: {e}")
        log.exception(f"Flow execution failed: {e}")
        sys.exit(1)
