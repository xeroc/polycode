"""Database management commands for Polycode CLI."""

import sys

import typer
from sqlalchemy import create_engine

from cli import print_error, print_info, print_success, print_warning
from cli.utils import get_logger
from persistence.postgres import Base

log = get_logger(__name__)
db_app = typer.Typer(help="Database management commands")


@db_app.command("init")
def db_init(
    drop: bool = typer.Option(False, "--drop", help="Drop existing tables first"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Initialize database tables.

    Creates all tables defined in the persistence layer.
    """
    if verbose:
        import cli.utils

        cli.utils.setup_logging("DEBUG")

    print_info("🔧 Initializing database...")

    try:
        from project_manager.config import settings

        connection_string = settings.DATABASE_URL
        engine = create_engine(connection_string)

        if drop:
            print_info("🗑 Dropping existing tables...")
            Base.metadata.drop_all(engine)
            print_success("Existing tables dropped")

        print_info("📊 Creating tables...")
        Base.metadata.create_all(engine)
        print_success("Database initialized successfully")

    except Exception as e:
        print_error(f"Database initialization failed: {e}")
        log.exception(f"Database init failed: {e}")
        sys.exit(1)


@db_app.command("migrate")
def db_migrate(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Run database migrations.

    Note: Migration support not yet implemented.
    """
    if verbose:
        import cli.utils

        cli.utils.setup_logging("DEBUG")

    print_warning("⚠️ Migration support not yet implemented")
    print_info("Use 'polycode db init --drop' to recreate tables")
