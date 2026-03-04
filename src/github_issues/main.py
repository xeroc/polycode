"""Daemon that manages GitHub issues using webhook-driven flow."""

import logging
import os
from typing import Callable

import click

from feature_dev import kickoff as feature_dev_kickoff
from feature_dev.types import KickoffIssue, KickoffRepo

from project_manager import GitHubProjectManager
from project_manager.types import ProjectConfig, ProjectItem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)


def create_kickoff_callback(
    manager: GitHubProjectManager,
) -> Callable[[ProjectItem], None] | None:
    """Create a callback to kickoff feature development.

    Returns:
        Callback function or None if feature_dev not available
    """

    def on_issue_ready(item: ProjectItem) -> None:
        """Callback when an issue is ready to process."""
        log.info(f"Starting feature development for issue #{item.issue_number}")
        log.info(f"Title: {item.title}")
        log.info(f"Description: {item.body or '(no description)'}")

        kickoff_issue = KickoffIssue(
            id=item.issue_number,
            title=item.title,
            body=item.body or "",
            repository=KickoffRepo(
                owner=manager.config.repo_owner,
                repository=manager.config.repo_name,
            ),
            memory_prefix=f"{manager.config.repo_owner}/{manager.config.repo_name}",
        )
        feature_dev_kickoff(kickoff_issue)

    return on_issue_ready


@click.command()
@click.argument("repo", type=str)
@click.option("--once", is_flag=True, help="Run one cycle and exit")
@click.option("--interval", default=300, help="Polling interval in seconds")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(repo: str, once: bool, interval: int, verbose: bool) -> None:
    """Watch repository for issues to process (polling mode).

    REPO should be in the format: owner/name (e.g., xeroc/demo)

    For webhook mode, use: python -m project_manager.cli webhook
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        repo_owner, repo_name = repo.split("/")
    except ValueError:
        raise click.BadParameter("REPO must be in format: owner/name")

    project_identifier = os.environ.get("PROJECT_IDENTIFIER", "1")

    config = ProjectConfig(
        provider="github",
        repo_owner=repo_owner,
        repo_name=repo_name,
        project_identifier=project_identifier,
    )

    manager = GitHubProjectManager(config)
    callback = create_kickoff_callback(manager)

    from project_manager import RepoWatcher

    watcher = RepoWatcher(
        manager=manager,
        poll_interval=interval,
        on_issue_ready=callback,
    )

    watcher.start(run_once=once)


if __name__ == "__main__":
    main()
