"""Main CLI entry point using Typer."""

import typer

from . import console, db, flow, print_banner, project, server, worker
from .utils import setup_logging

app = typer.Typer(
    name="polycode",
    help="🚀 Polycode: Multi-agent software development automation",
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

app.add_typer(server.server_app, name="server", help="Server management commands")
app.add_typer(worker.worker_app, name="worker", help="Celery worker management commands")
app.add_typer(flow.flow_app, name="flow", help="Flow execution commands")
app.add_typer(project.project_app, name="project", help="GitHub project management commands")
app.add_typer(db.db_app, name="db", help="Database management commands")


@app.callback()
def main(
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        "-l",
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose (DEBUG) logging"),
) -> None:
    """Polycode CLI - Multi-agent software development automation."""
    level = "DEBUG" if verbose else log_level
    setup_logging(level)

    if verbose or level.upper() == "DEBUG":
        console.print("[dim]🔍 Verbose mode enabled[/]")

    print_banner()


if __name__ == "__main__":
    app()
