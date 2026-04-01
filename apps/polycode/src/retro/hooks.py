"""Hook implementations for retro module.

Uses trylast=True to guarantee retro runs AFTER gitcore commit+push.
"""

import logging
import subprocess

from modules.hooks import FlowEvent, hookimpl

log = logging.getLogger(__name__)

RETRO_NOTES_REF = "refs/notes/retros"


class RetroHooks:
    """Lifecycle hooks for retrospective generation."""

    @hookimpl(trylast=True)
    def on_flow_event(self, event, flow_id, state, result, label):
        if event == FlowEvent.STORY_COMPLETED:
            self._retro_on_commit(flow_id, state, result)

        if event == FlowEvent.FLOW_ERROR:
            self._retro_on_failure(flow_id, state, result)

    def _retro_on_commit(self, flow_id, state, story):
        from gitcore import GitNotes
        from gitcore.types import GitContext
        from retro.types import RetroEntry

        commit_sha = self._get_head_sha(state.repo)
        retro = RetroEntry(
            commit_sha=commit_sha,
            flow_id=flow_id,
            story_id=getattr(story, "id", None),
            story_title=getattr(story, "title", None),
            repo_owner=state.repo_owner or "",
            repo_name=state.repo_name or "",
            retro_type="success",
            what_worked=self._extract_successes(story),
            what_failed=getattr(story, "errors", []),
            root_causes=[],
            actionable_improvements=[],
            retry_count=len(getattr(story, "errors", [])),
        )

        notes = GitNotes(
            GitContext(repo_path=state.repo),
            notes_ref=RETRO_NOTES_REF,
        )
        notes.add(model=retro, force=True)
        log.info(f"📝 Retro attached to commit {commit_sha[:8]}")

    def _retro_on_failure(self, flow_id, state, error):
        from gitcore import GitNotes
        from gitcore.types import GitContext
        from retro.types import RetroEntry

        commit_sha = self._get_head_sha(state.repo)
        retro = RetroEntry(
            commit_sha=commit_sha,
            flow_id=flow_id,
            repo_owner=state.repo_owner or "",
            repo_name=state.repo_name or "",
            retro_type="failure",
            what_worked=[],
            what_failed=[str(error)[:200]],
            root_causes=[],
            actionable_improvements=[],
        )

        notes = GitNotes(
            GitContext(repo_path=state.repo),
            notes_ref=RETRO_NOTES_REF,
        )
        notes.add(model=retro, force=True)
        log.info(f"📝 Failure retro attached to commit {commit_sha[:8]}")

    @staticmethod
    def _get_head_sha(repo_path: str) -> str:
        result = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    @staticmethod
    def _extract_successes(story) -> list[str]:
        if not hasattr(story, "errors") or not story.errors:
            return ["All tests passed"]
        return []
