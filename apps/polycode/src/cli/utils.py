"""Shared utilities for CLI commands."""

import logging
from typing import Any

from rich.console import Console
from rich.logging import RichHandler

console = Console()

NOISY_LOGGERS = [
    "urllib3.connectionpool",
    "httpcore.connection",
    "httpcore",
    "openai._base_client",
]


def setup_logging(level: int | str = logging.INFO) -> None:
    """Configure Rich logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) as int or str
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(name)s - %(message)s",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
            )
        ],
    )

    for logger_name in NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"polycode.{name}")


def load_bootstrap() -> Any:
    """Load bootstrap system for full runtime initialization.

    Returns:
        ModuleContext with engine, hook manager, and config
    """
    from bootstrap import bootstrap

    log = get_logger("cli.utils")
    log.debug("🔧 Loading bootstrap system...")

    context = bootstrap()

    log.debug(f"✅ Bootstrap loaded: {len(context.config)} modules configured")

    return context
