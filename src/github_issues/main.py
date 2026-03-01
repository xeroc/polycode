"""Daemon that manages GitHub issues and project status for xeroc/demo."""

import logging
import os
import time

from github import Github
from pydantic import BaseModel

from .github_project import GitHubProjectsClient, ProjectItem

try:
    from feature_dev.main import kickoff as feature_dev_kickoff
    from feature_dev.types import KickoffIssue
except ImportError:
    KickoffIssue = None
    feature_dev_kickoff = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_OWNER = "xeroc"
REPO_NAME = "demo"
PROJECT_NUMBER = 1
INTERVAL_SECONDS = 300  # 5 minutes


class IssueData(BaseModel):
    """Data structure for a GitHub issue."""

    number: int
    node_id: str
    title: str
    body: str | None


def in_progress_issue(issue: ProjectItem) -> None:
    """Start feature development for an issue.

    Args:
        issue: The project item to start working on.
    """
    if not feature_dev_kickoff or not KickoffIssue:
        log.warning("feature_dev module not available, skipping kickoff")
        return

    issue_data = {
        "issue_number": issue.issue_number,
        "title": issue.title,
        "body": issue.body,
    }

    log.info(f"Starting feature development for issue #{issue.issue_number}")
    log.info(f"Title: {issue.title}")
    log.info(f"Description: {issue.body or '(no description)'}")

    kickoff_issue = KickoffIssue(**issue_data, id=issue.issue_number)
    feature_dev_kickoff(kickoff_issue)


def get_all_issues(github_client: Github) -> list[IssueData]:
    """Get all open issues from the repository.

    Args:
        github_client: GitHub API client.

    Returns:
        List of issue data dictionaries.
    """
    repo = github_client.get_repo(f"{REPO_OWNER}/{REPO_NAME}")
    issues: list[IssueData] = []

    for issue in repo.get_issues(state="open"):
        issues.append(
            IssueData(
                number=issue.number,
                node_id=issue.node_id,
                title=issue.title,
                body=issue.body,
            )
        )

    return issues


def run_cycle() -> None:
    """Run one cycle of the daemon.

    This function:
    1. Fetches all open issues from the repository.
    2. Adds any missing issues to project #1.
    3. Finds items in "Ready" status.
    4. If no items are "In progress", moves the top "Ready" item to "In progress".
    """
    if not GITHUB_TOKEN:
        log.error("GITHUB_TOKEN environment variable not set")
        return

    github_client = Github(GITHUB_TOKEN)
    projects_client = GitHubProjectsClient(GITHUB_TOKEN, REPO_NAME)

    log.info("Starting cycle")

    # Get project ID
    project_id = projects_client.get_project_id(REPO_OWNER, PROJECT_NUMBER)
    log.info(f"Project ID: {project_id}")

    # Get all issues from repo
    all_issues = get_all_issues(github_client)
    log.info(f"Found {len(all_issues)} open issues in repository")

    # Get current project items
    project_items = projects_client.get_project_items(project_id)
    project_issue_numbers = {item.issue_number for item in project_items}
    log.info(f"Found {len(project_items)} items in project")

    # Add missing issues to project
    issues_added = 0
    for issue in all_issues:
        if issue.number not in project_issue_numbers:
            log.info(f"Adding issue #{issue.number} to project")
            try:
                projects_client.add_issue_to_project(project_id, issue.node_id)
                issues_added += 1
            except Exception as e:
                log.error(f"Failed to add issue #{issue.number}: {e}")

    if issues_added > 0:
        log.info(f"Added {issues_added} new issues to project")
        # Refresh project items after adding
        project_items = projects_client.get_project_items(project_id)

    # Get status field info
    status_field_id, status_options = projects_client.get_status_field_id(
        project_id
    )
    log.info(f"Status options: {list(status_options.keys())}")

    # Find items by status
    ready_items = [item for item in project_items if item.status == "Ready"]
    in_progress_items = [
        item for item in project_items if item.status == "In progress"
    ]

    log.info(
        f"Ready: {len(ready_items)}, In progress: {len(in_progress_items)}"
    )

    # If no in progress, move top ready to in progress
    if not in_progress_items and ready_items:
        top_item = ready_items[0]

        log.info(f"Moving '{top_item.title}' to In progress")
        log.info(f"Title: {top_item.title}")
        log.info(f"Description: {top_item.body or '(no description)'}")

        if "In progress" in status_options:
            projects_client.update_item_status(
                project_id,
                top_item.project_item_id,
                status_field_id,
                status_options["In progress"],
            )
            log.info("Successfully moved to In progress")

            in_progress_issue(top_item)

        else:
            log.warning("'In progress' status option not found in project")
    elif in_progress_items:
        log.info(f"Already have {len(in_progress_items)} item(s) in progress")
    else:
        log.info("No ready items to process")

    log.info("Cycle complete")


def main() -> None:
    """Main daemon loop.

    Runs the daemon cycle immediately on startup, then repeats every
    INTERVAL_SECONDS (5 minutes).
    """
    log.info("Starting GitHub Issues Daemon")
    log.info(f"Repository: {REPO_OWNER}/{REPO_NAME}")
    log.info(f"Project: {PROJECT_NUMBER}")
    log.info(f"Interval: {INTERVAL_SECONDS} seconds")

    # Run immediately on startup
    try:
        run_cycle()
    except Exception as e:
        log.error(f"Error in initial cycle: {e}")

    # Then run every INTERVAL_SECONDS
    while True:
        time.sleep(INTERVAL_SECONDS)
        try:
            run_cycle()
        except Exception as e:
            log.error(f"Error in cycle: {e}")


if __name__ == "__main__":
    main()
