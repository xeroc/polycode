"""Worker commands for Polycode CLI."""

import sys

import typer
from rich.console import Console

from cli import print_error, print_info, print_success
from cli.utils import get_logger

log = get_logger(__name__)
console = Console()

worker_app = typer.Typer(help="Celery worker management commands")


@worker_app.command("start")
def worker_start(
    queues: str = typer.Option("celery,default", "--queues", "-q", help="Comma-separated queue names"),
    concurrency: int = typer.Option(0, "--concurrency", "-c", help="Number of worker processes (0 = auto)"),
    loglevel: str = typer.Option("info", "--loglevel", "-l", help="Log level"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Start Celery worker for processing async tasks.

    Worker handles flow execution, webhook processing, and periodic tasks.
    """
    if verbose:
        import cli.utils

        cli.utils.setup_logging("DEBUG")

    queues_list = [q.strip() for q in queues.split(",") if q.strip()]
    concurrency_str = str(concurrency) if concurrency > 0 else 10

    print_info("⚙️ Starting Celery worker")
    print_info(f"   Queues: {', '.join(queues_list)}")
    print_info(f"   Concurrency: {concurrency_str}")
    print_info(f"   Log level: {loglevel}")

    try:
        from bootstrap import bootstrap
        from celery_tasks import app as celery_app
        from celery_tasks import worker

        assert worker

        print_info("📦 Initializing modules...")
        bootstrap()

        registered = worker.register_module_tasks()
        if registered:
            print_info(f"   Module tasks: {len(registered)} registered")

        celery_app.worker_main(
            [
                "worker",
                f"--queues={','.join(queues_list)}",
                f"--concurrency={concurrency_str}",
                f"--loglevel={loglevel}",
                "-Ofair",
                "--task-events",
            ]
        )
    except KeyboardInterrupt:
        print_info("⏹ Worker stopped by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Failed to start worker: {e}")
        log.exception(f"Worker startup failed: {e}")
        sys.exit(1)


@worker_app.command("status")
def worker_status(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Check Celery worker status using inspect.

    Shows active workers, registered tasks, and queue statistics.
    """
    if verbose:
        import cli.utils

        cli.utils.setup_logging("DEBUG")

    print_info("🔍 Checking worker status...")

    try:
        from celery_tasks import app as celery_app

        inspect = celery_app.control.inspect()

        active = inspect.active()
        registered = inspect.registered()
        stats = inspect.stats()

        if active:
            for worker_name, tasks in active.items():
                console.print(f"\n[bold cyan]Worker: {worker_name}[/]")
                console.print(f"  Active tasks: {len(tasks)}")
        else:
            console.print("[yellow]⚠️ No active workers found[/]")

        if registered:
            console.print("\n[bold cyan]Registered tasks:[/]")
            for worker_name, tasks in registered.items():
                for task in tasks:
                    console.print(f"  • {task}")

        if stats:
            console.print("\n[bold cyan]Statistics:[/]")
            for worker_name, stat in stats.items():
                console.print(f"  {worker_name}:")
                for key, value in stat.items():
                    if key == "pool":
                        console.print(f"    Pool: {value.get('max-concurrency', 'N/A')} processes")

        print_success("Worker status check complete")

    except Exception as e:
        print_error(f"Failed to check worker status: {e}")
        log.exception(f"Worker status check failed: {e}")
        sys.exit(1)
