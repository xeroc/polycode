"""Git-notes operations for storing structured data on commits.

Provides a generic wrapper around git-notes for attaching arbitrary
Pydantic-serializable data to commits. Used by retro and other modules
that need commit-attached metadata.
"""

import logging
import subprocess
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from gitcore.types import GitContext, GitNotesError

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_NOTES_REF = "refs/notes/commits"


class GitNotes:
    """Wrapper for git-notes operations.

    Stores Pydantic model instances as JSON notes on commits using
    a configurable notes ref.
    """

    def __init__(
        self,
        context: GitContext,
        notes_ref: str = DEFAULT_NOTES_REF,
    ):
        """Initialize git-notes wrapper.

        Args:
            context: GitContext providing repo path
            notes_ref: Custom ref for notes (defaults to refs/notes/commits)

        Raises:
            GitNotesError: If the repository path is invalid
        """
        self.repo_path = Path(context.repo_path).resolve()
        self.notes_ref = notes_ref

        if not self.repo_path.exists():
            raise GitNotesError(f"Repository not found: {self.repo_path}")

        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            raise GitNotesError(f"Not a git repository: {self.repo_path}")

    def _git(self, *args: str, check: bool = True) -> str:
        """Run git command and return output."""
        cmd = ["git", "-C", str(self.repo_path), *args]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            log.error(f"🚨 Git command failed: {' '.join(cmd)}")
            log.error(f" stderr: {e.stderr}")
            raise GitNotesError(f"Git command failed: {e.stderr}") from e

    def _get_current_sha(self) -> str:
        """Get current HEAD commit SHA."""
        sha = self._git("rev-parse", "HEAD").strip()
        log.info(f"🔖 Current commit: {sha}")
        return sha

    def add(
        self,
        model: BaseModel,
        commit_sha: str | None = None,
        force: bool = False,
    ) -> None:
        """Add a note to a commit.

        Args:
            model: Pydantic model instance to store as JSON
            commit_sha: Target commit (defaults to HEAD)
            force: Overwrite existing note if True
        """
        target = commit_sha or self._get_current_sha()
        note_json = model.model_dump_json(indent=2)

        args = ["notes", "--ref", self.notes_ref, "add"]
        if force:
            args.append("-f")
        args.extend(["-m", note_json, target])

        try:
            self._git(*args, check=True)
            log.info(f"📝 Note stored for commit {target[:8]} (ref: {self.notes_ref})")
        except GitNotesError:
            if not force:
                log.warning("⚠️ Note exists, use force=True to overwrite")

    def show(
        self,
        model_type: type[T],
        commit_sha: str | None = None,
    ) -> T | None:
        """Show note for a commit, deserialized as the given model type.

        Args:
            model_type: Pydantic model class to deserialize into
            commit_sha: Target commit (defaults to HEAD)

        Returns:
            Deserialized model instance or None if no note exists
        """
        target = commit_sha or self._get_current_sha()
        try:
            note_content = self._git("notes", "--ref", self.notes_ref, "show", target)
            try:
                instance = model_type.model_validate_json(note_content)
                log.info(f"📖 Retrieved note for {target[:8]}")
                return instance
            except ValidationError as e:
                log.error(f"🚨 Failed to parse note: {e}")
                return None
        except subprocess.CalledProcessError as e:
            if "no note found" in e.stderr.lower():
                log.debug(f"No note for {target[:8]}")
                return None
            raise GitNotesError(f"Failed to show note: {e.stderr}") from e

    def list_all(self) -> list[str]:
        """List all commit SHAs with notes.

        Returns:
            List of commit SHAs that have notes
        """
        try:
            output = self._git("notes", "--ref", self.notes_ref, "list")
            if not output.strip():
                log.info("📭 No notes found")
                return []

            shas = []
            for line in output.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 2:
                    shas.append(parts[-1])

            log.info(f"📚 Found {len(shas)} notes")
            return shas
        except subprocess.CalledProcessError as e:
            raise GitNotesError(f"Failed to list notes: {e.stderr}") from e

    def remove(self, commit_sha: str) -> None:
        """Remove note from a commit.

        Args:
            commit_sha: Commit SHA to remove note from
        """
        try:
            self._git("notes", "--ref", self.notes_ref, "remove", commit_sha, check=True)
            log.info(f"🗑️ Removed note for {commit_sha[:8]}")
        except GitNotesError:
            log.warning(f"No note to remove for {commit_sha[:8]}")

    def push(self, remote: str = "origin") -> None:
        """Push notes to remote.

        Args:
            remote: Git remote name (default: origin)
        """
        try:
            self._git("push", remote, self.notes_ref, check=True)
            log.info(f"📤 Pushed notes to {remote}/{self.notes_ref}")
        except GitNotesError as e:
            log.error(f"🚨 Failed to push notes: {e}")

    def pull(self, remote: str = "origin") -> None:
        """Pull notes from remote.

        Args:
            remote: Git remote name (default: origin)
        """
        try:
            self._git("fetch", remote, f"{self.notes_ref}:{self.notes_ref}", check=True)
            log.info(f"📥 Pulled notes from {remote}/{self.notes_ref}")
        except GitNotesError as e:
            log.error(f"🚨 Failed to pull notes: {e}")
