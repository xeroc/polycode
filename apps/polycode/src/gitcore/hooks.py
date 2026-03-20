"""Git operations hooks for flow lifecycle events."""

import logging

from gitcore.operations import GitOperations
from modules.hooks import FlowEvent, hookimpl

logger = logging.getLogger(__name__)


class GitcoreHooks:
    """Hook implementations for git operations.

    Handles:
    - STORY_COMPLETED: Commit and push changes
    - FLOW_FINISHED: Cleanup worktree
    """

    @hookimpl
    def on_flow_event(self, event, flow_id, state, result=None, label=""):
        """Handle git-related flow events."""
        logger.info(f"🎣 Hook called in {__name__}")
        if event in [FlowEvent.FLOW_STARTED, FlowEvent.SETUP]:
            self._handle_setup(flow_id, state)
        elif event == FlowEvent.STORY_COMPLETED:
            self._handle_story_completed(flow_id, state, result)
        elif event == FlowEvent.FLOW_FINISHED:
            self._handle_flow_finished(flow_id, state)
        elif event == FlowEvent.CLEANUP:
            self._handle_cleanup(flow_id, state)

    def _handle_setup(self, flow_id, state):
        """Initialite the the worktree"""
        git_op = GitOperations.from_flow_state(state)
        worktree_path = git_op.prepare_worktree()
        state.repo = worktree_path

    def _handle_story_completed(self, flow_id, state, story):
        """Commit and push changes for a completed story.

        Args:
            flow_id: Flow identifier
            state: Flow state with commit_title, commit_message, commit_footer
            story: Completed story object
        """
        from gitcore import GitOperations

        logger.info(f"💾 Committing story: {story.title if hasattr(story, 'title') else 'unknown'}")

        git_ops = GitOperations.from_flow_state(state)

        # Get commit details from state
        title = getattr(state, "commit_title", None) or f"feat: {story.title if hasattr(story, 'title') else 'Story'}"
        body = getattr(state, "commit_message", "") or (story.description if hasattr(story, "description") else "")
        footer = getattr(state, "commit_footer", "") or ""

        # Commit changes
        commit = git_ops.commit(title, body, footer)

        if commit:
            commit_url = git_ops.get_commit_url(commit.hexsha)
            logger.info(f"✅ Committed: {commit_url}")

            # Store commit URL in state
            if hasattr(state, "commit_urls") and hasattr(story, "id"):
                state.commit_urls[story.id] = commit_url

        # Push changes
        logger.info("📤 Pushing changes...")
        git_ops.push()
        logger.info("✅ Pushed successfully")

    def _handle_flow_finished(self, flow_id, state):
        """One final push to ensure remote is in sync even when restarting the
        flow"""
        logger.info("📤 Pushing changes...")
        git_ops = GitOperations.from_flow_state(state)
        git_ops.push()

    def _handle_cleanup(self, flow_id, state):
        """Cleanup worktree after flow completes.

        Args:
            flow_id: Flow identifier
            state: Flow state
        """
        from gitcore import GitOperations

        logger.info("🧹 Cleaning up worktree...")

        git_ops = GitOperations.from_flow_state(state)
        git_ops.cleanup()

        logger.info("✅ Worktree cleaned up")
