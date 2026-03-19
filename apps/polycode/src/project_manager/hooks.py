"""Hook implementations for project management operations.

This module contains hook implementations that handle GitHub-specific
operations like PR creation, merging, and issue management.
"""

import logging
from typing import TYPE_CHECKING, Any, Callable

from modules.hooks import FlowEvent, hookimpl

if TYPE_CHECKING:
    from project_manager.base import ProjectManager
    from project_manager.types import ProjectConfig

log = logging.getLogger(__name__)


class ProjectManagerHooks:
    """Hook implementations for GitHub project management.

    This class handles all GitHub-specific operations triggered by flow orchestration events.
    It creates PRs, handles merges, posts comments, and updates issue status.
    """

    def __init__(
        self,
        project_manager_factory: Callable[["ProjectConfig"], "ProjectManager"],
    ):
        """Initialize hooks with a factory function.

        Args:
            project_manager_factory: Callable that creates a ProjectManager from ProjectConfig
        """
        self._pm_factory = project_manager_factory

    def _get_pm(self, config: "ProjectConfig") -> "ProjectManager":
        """Get project manager instance for the given config."""
        return self._pm_factory(config)

    @hookimpl
    def on_flow_event(
        self,
        event: FlowEvent,
        flow_id: str,
        state: Any,
        result: Any | None = None,
        label: str = "",
    ) -> None:
        """Handle flow orchestration events for project management operations.

        This is the main hook that dispatches to specific handlers based on event type.

        Args:
            event: Current flow event
            flow_id: Unique flow identifier
            state: Flow state model (mutable)
            result: Event-specific result (e.g., commit sha, pr url)
            label: Context label (e.g., "plan", "implement", "review")
        """
        if not hasattr(state, "project_config") or not state.project_config:
            log.debug("No project_config in state, skipping project manager hooks")
            return

        pm = self._get_pm(state.project_config)

        if event == FlowEvent.FLOW_STARTED:
            self._handle_flow_started(state, pm)
        elif event == FlowEvent.STORY_COMPLETED:
            self._handle_story_completed(state, pm, result)
        elif event == FlowEvent.FLOW_FINISHED:
            self._handle_flow_finished(state, pm)

    def _handle_review_start(self, state: Any, pm: "ProjectManager") -> None:
        """Update issue status to 'In review' when review phase starts.

        Args:
            state: Flow state
            pm: Project manager instance
        """
        issue_id = getattr(state, "issue_id", 0)
        if not issue_id:
            return

        try:
            pm.update_issue_status(issue_id, "In review")
            log.info(f"🏹 Updated issue #{issue_id} status to In review")
        except Exception as e:
            log.warning(f"🚨 Failed to update project status to In review: {e}")

    def _handle_create_pr(self, state: Any, pm: "ProjectManager") -> None:
        """Create pull request.

        Args:
            state: Flow state (mutated with pr_number, pr_url)
            pm: Project manager instance
        """
        if getattr(state, "pr_number", None):
            log.info("PR already exists, skipping creation")
            return

        from project_manager.git_utils import get_github_repo_from_local

        repo_path = getattr(state, "repo", "")
        if not repo_path:
            log.warning("No repo path in state, cannot create PR")
            return

        _, github_repo, _ = get_github_repo_from_local(repo_path)

        title = getattr(state, "commit_title", None) or getattr(state, "task", "")
        body = f"{getattr(state, 'commit_message', '') or ''}\n\n{getattr(state, 'commit_footer', '') or ''}"
        branch = getattr(state, "branch", "")
        base_branch = "develop"

        pr = github_repo.create_pull(
            title=title,
            body=body.strip(),
            head=branch,
            base=base_branch,
        )

        state.pr_url = pr.html_url
        state.pr_number = pr.number

        log.info(f"🏹 PR {state.pr_number} created: {state.pr_url}")

        issue_id = getattr(state, "issue_id", 0)
        if issue_id:
            pm.add_comment(
                issue_id,
                f"## 🔍 Review Started\n\n"
                f"Pull request #{state.pr_number} is now under review.\n"
                f"[View PR]({state.pr_url})",
            )

    def _handle_merge(self, state: Any, pm: "ProjectManager") -> None:
        """Handle PR merge with label check.

        Args:
            state: Flow state
            pm: Project manager instance
        """
        from project_manager.config import settings as project_settings

        pr_number = getattr(state, "pr_number", None)
        issue_id = getattr(state, "issue_id", 0)

        if not pr_number:
            log.warning("No PR number set, skipping merge")
            return

        required_label = project_settings.MERGE_REQUIRED_LABEL

        if not pm.has_label(issue_id, required_label):
            log.warning(f"⚠️ Issue #{issue_id} does not have required label '{required_label}'. Merge aborted.")
            pm.add_comment(
                issue_id,
                f"## ⚠️ Merge Blocked\n\n"
                f"Pull request #{pr_number} cannot be merged. "
                f"Issue {issue_id} does not have the required label: `{required_label}`.\n\n"
                f"Please add the label and try again.",
            )
            return

        log.info(f"✅ PR #{pr_number} has required label '{required_label}', proceeding with merge")

        success = pm.merge_pull_request(pr_number)

        if success:
            pr_url = getattr(state, "pr_url", "")
            pm.add_comment(
                issue_id,
                f"## ✅ Task Completed\n\nPull request #{pr_number} has been merged.\n[View merged PR]({pr_url})",
            )

    def _handle_cleanup(self, state: Any, pm: "ProjectManager") -> None:
        """Update issue status after cleanup.

        Args:
            state: Flow state
            pm: Project manager instance
        """
        issue_id = getattr(state, "issue_id", 0)
        if not issue_id:
            return

        try:
            pm.update_issue_status(issue_id, "Done")
            log.info(f"🏹 Updated issue #{issue_id} status to Done")
        except Exception as e:
            log.info(f"🚨 Failed to update project status to Done: {e}")

    def _handle_planning_comment(self, state: Any, pm: "ProjectManager", stories: Any | None) -> None:
        """Post planning checklist to issue.

        Args:
            state: Flow state (mutated with planning_comment_id)
            pm: Project manager instance
            stories: List of stories from planning phase
        """
        if not stories:
            log.debug("No stories to post in planning checklist")
            return

        issue_id = getattr(state, "issue_id", 0)
        if not issue_id:
            return

        checklist_items = "\n".join(f"- [ ] {getattr(story, 'description', str(story))}" for story in stories)
        comment = (
            f"## 📋 Implementation Plan\n\n{checklist_items}\n\n_Progress will be updated as stories are implemented._"
        )
        pm.add_comment(issue_id, comment)

        comment_id = pm.get_last_comment_by_user(issue_id, pm.bot_username)
        if comment_id:
            state.planning_comment_id = comment_id
            log.info(f"🏹 Posted planning checklist, comment ID: {comment_id}")

    def _handle_update_checklist(self, state: Any, pm: "ProjectManager", data: Any | None) -> None:
        """Update planning checklist with progress.

        Args:
            state: Flow state
            pm: Project manager instance
            data: Tuple of (stories, completed_story_ids, pr_url, merged) or dict
        """
        planning_comment_id = getattr(state, "planning_comment_id", None)
        if not planning_comment_id:
            log.warning("No planning comment ID, cannot update checklist")
            return

        issue_id = getattr(state, "issue_id", 0)
        if not issue_id:
            return

        if data is None:
            return

        if isinstance(data, dict):
            stories = data.get("stories", [])
            completed_ids = data.get("completed_ids", [])
            pr_url = data.get("pr_url")
            merged = data.get("merged", False)
        elif isinstance(data, tuple) and len(data) >= 2:
            stories, completed_ids = data[0], data[1]
            pr_url = data[2] if len(data) > 2 else None
            merged = data[3] if len(data) > 3 else False
        else:
            return

        commit_urls = getattr(state, "commit_urls", {})
        pr_number = getattr(state, "pr_number")

        checklist_lines = []
        for story in stories:
            story_id = getattr(story, "id", None)
            story_desc = getattr(story, "description", str(story))

            if story_id in completed_ids:
                commit_url = commit_urls.get(story_id)
                if commit_url:
                    checklist_lines.append(f"- [x] {story_desc} ([commit]({commit_url}))")
                else:
                    checklist_lines.append(f"- [x] {story_desc}")
            else:
                checklist_lines.append(f"- [ ] {story_desc}")

        body = "## 📋 Implementation Plan\n\n" + "\n".join(checklist_lines)

        if pr_url:
            if merged:
                body += f"\n\n---\n\n✅ **Merged** - [PR #{pr_number}]({pr_url})"
            else:
                body += f"\n\n---\n\n🔍 **Review in progress** - [PR #{pr_number}]({pr_url})"
        else:
            body += "\n\n_Progress will be updated as stories are implemented._"

        pm.update_comment(issue_id, planning_comment_id, body)
        log.info(f"🏹 Updated planning checklist for issue #{issue_id}")

    def _handle_flow_started(self, state: Any, pm: "ProjectManager") -> None:
        """Handle flow start - post initial planning checklist.

        Args:
            state: Flow state
            pm: Project manager instance
        """
        issue_id = getattr(state, "issue_id", 0)
        if not issue_id:
            return

        log.info(f"🚀 Flow started for issue #{issue_id}")

    def _handle_story_completed(self, state: Any, pm: "ProjectManager", story: Any) -> None:
        """Handle story completion - update checklist item.

        Args:
            state: Flow state
            pm: Project manager instance
            story: Completed story object
        """
        issue_id = getattr(state, "issue_id", 0)
        planning_comment_id = getattr(state, "planning_comment_id", None)

        if not issue_id or not planning_comment_id:
            return

        stories = getattr(state, "stories", [])
        completed_ids = [s.id for s in stories if s.completed]

        # Update checklist
        self._handle_update_checklist(
            state,
            pm,
            {
                "stories": stories,
                "completed_ids": completed_ids,
                "pr_url": None,
                "merged": False,
            },
        )

        log.info(f"✅ Updated checklist for story: {story.title if hasattr(story, 'title') else 'unknown'}")

    def _handle_flow_finished(self, state: Any, pm: "ProjectManager") -> None:
        """Handle flow finish - create PR, merge, update final checklist, cleanup.

        Args:
            state: Flow state
            pm: Project manager instance
        """
        issue_id = getattr(state, "issue_id", 0)
        if not issue_id:
            return

        # Create PR
        self._handle_create_pr(state, pm)

        # Merge PR (if approved)
        self._handle_merge(state, pm)

        # Final checklist update with PR link
        stories = getattr(state, "stories", [])
        completed_ids = [s.id for s in stories if s.completed]
        pr_url = getattr(state, "pr_url", None)

        if pr_url:
            self._handle_update_checklist(
                state,
                pm,
                {
                    "stories": stories,
                    "completed_ids": completed_ids,
                    "pr_url": pr_url,
                    "merged": True,
                },
            )

        # Update issue status to Done
        self._handle_cleanup(state, pm)

        log.info(f"🏁 Flow finished for issue #{issue_id}")
