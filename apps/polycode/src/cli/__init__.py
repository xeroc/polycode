"""Central CLI tool for Polycode.

Entry point: `polycode` command.

Usage:
    polycode server webhook       # Start webhook server
    polycode server socketio      # Start Socket.IO server
    polycode server flower        # Start Flower monitoring
    polycode worker start         # Start Celery worker
    polycode flow run ralph     # Run a flow manually
    polycode project sync         # Sync issues to project
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

__version__ = "0.1.0"


def print_banner():
    """Print pretty CLI banner."""
    banner = Text.assemble(
        ("🚀 ", "bold cyan"),
        ("polycode", "bold white"),
        (f" v{__version__}", "dim"),
    )
    console.print(Panel(banner, border_style="cyan"))


def print_error(message: str) -> None:
    """Print error message in red."""
    console.print(f"[bold red]❌ {message}[/]")


def print_success(message: str) -> None:
    """Print success message in green."""
    console.print(f"[bold green]✓ {message}[/]")


def print_warning(message: str) -> None:
    """Print warning message in yellow."""
    console.print(f"[bold yellow]⚠️ {message}[/]")


def print_info(message: str) -> None:
    """Print info message in blue."""
    console.print(f"[bold blue]ℹ️ {message}[/]")


__all__ = ["print_error", "print_success", "print_warning", "print_info", "console"]
