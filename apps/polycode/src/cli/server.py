"""Server commands for Polycode CLI."""

import sys

import typer
import uvicorn
from rich.console import Console

from cli import print_error, print_info
from cli.utils import get_logger
from github_app.app import app as github_app

log = get_logger(__name__)
console = Console()

server_app = typer.Typer(help="Server management commands")


@server_app.command("webhook")
def webhook_server(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Webhook server host"),
    port: int = typer.Option(8000, "--port", "-p", help="Webhook server port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload (development)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Start webhook server for GitHub events.

    Uses GitHub App webhook server.
    Set GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY for GitHub App authentication.
    """
    if verbose:
        import cli.utils

        cli.utils.setup_logging("DEBUG")

    print_info(f"🚀 Starting webhook server on {host}:{port}")

    if reload:
        print_info("🔁 Auto-reload enabled")

    try:
        uvicorn.run(
            github_app,
            host=host,
            port=port,
            reload=reload,
            log_level="debug" if verbose else "warning",
        )
    except KeyboardInterrupt:
        print_info("⏹ Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Failed to start server: {e}")
        log.exception(f"Server startup failed: {e}")
        sys.exit(1)


@server_app.command("socketio")
def socketio_server(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Socket.IO server host"),
    port: int = typer.Option(8001, "--port", "-p", help="Socket.IO server port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload (development)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Start Socket.IO streaming server.

    Bridges Redis pub/sub to Socket.IO clients for real-time flow updates.
    """
    if verbose:
        import cli.utils

        cli.utils.setup_logging("DEBUG")

    print_info(f"🔌 Starting Socket.IO server on {host}:{port}")

    if reload:
        print_info("🔁 Auto-reload enabled")

    try:
        uvicorn.run(
            "channels.stream.server_app:asgi_app",
            host=host,
            port=port,
            reload=reload,
            log_level="debug" if verbose else "warning",
        )
    except KeyboardInterrupt:
        print_info("⏹ Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Failed to start Socket.IO server: {e}")
        log.exception(f"Socket.IO server startup failed: {e}")
        sys.exit(1)


@server_app.command("flower")
def flower_server(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Flower server host"),
    port: int = typer.Option(5555, "--port", "-p", help="Flower server port"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Start Flower monitoring UI for Celery workers.

    Flower provides real-time monitoring of Celery tasks and workers.
    """
    if verbose:
        import cli.utils

        cli.utils.setup_logging("DEBUG")

    print_info(f"🌸 Starting Flower monitoring on {host}:{port}")

    try:
        uvicorn.run(
            "flower:app",
            host=host,
            port=port,
            log_level="debug" if verbose else "warning",
        )
    except KeyboardInterrupt:
        print_info("⏹ Flower stopped by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Failed to start Flower: {e}")
        log.exception(f"Flower startup failed: {e}")
        sys.exit(1)
