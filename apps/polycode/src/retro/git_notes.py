"""Git-notes integration for retrospectives."""

import logging
import subprocess
from pathlib import Path

from pydantic import ValidationError

from .types import RetroEntry

log = logging.getLogger(__name__)


class GitNotesError(Exception):
    """Exception raised for git-notes operations."""


class GitNotes:
    """Wrapper for git-notes operations with retro notes ref."""

    def __init__(self, repo_path: str, notes_ref: str = "refs/notes/retros"):
        """Initialize git-notes wrapper.

        Args:
            repo_path: Path to git repository
            notes_ref: Custom ref for retros (defaults to refs/notes/retros)
        """
        self.repo_path = Path(repo_path).resolve()
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

    def add(self, retro: RetroEntry, force: bool = False) -> None:
        """Add retro note to commit.

        Args:
            retro: RetroEntry to store
            force: Overwrite existing note if True
        """
        if not retro.commit_sha:
            retro.commit_sha = self._get_current_sha()

        note_json = retro.model_dump_json(indent=2)

        args = ["notes", "add"]
        if force:
            args.append("-f")
        args.extend(["-m", note_json, retro.commit_sha])

        try:
            self._git(*args, check=True)
            log.info(f"📝 Retro stored for commit {retro.commit_sha[:8]} (ref: {self.notes_ref})")
        except GitNotesError:
            if not force:
                log.warning("⚠️ Note exists, use force=True to overwrite")

    def show(self, commit_sha: str | None = None) -> RetroEntry | None:
        """Show retro note for commit.

        Args:
            commit_sha: Commit SHA (defaults to HEAD)

        Returns:
            RetroEntry or None if no note exists
        """
        target = commit_sha or self._get_current_sha()
        try:
            note_content = self._git("notes", "show", target)
            try:
                retro = RetroEntry.model_validate_json(note_content)
                log.info(f"📖 Retrieved retro for {target[:8]}")
                return retro
            except ValidationError as e:
                log.error(f"🚨 Failed to parse retro: {e}")
                return None
        except subprocess.CalledProcessError as e:
            if "no note found" in e.stderr.lower():
                log.debug(f"No retro for {target[:8]}")
                return None
            raise GitNotesError(f"Failed to show note: {e.stderr}") from e

    def list_all(self) -> list[str]:
        """List all commit SHAs with retro notes.

        Returns:
            List of commit SHAs
        """
        try:
            output = self._git("notes", "--ref", self.notes_ref, "list")
            if not output.strip():
                log.info("📭 No retros found")
                return []

            shas = []
            for line in output.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 2:
                    shas.append(parts[-1])

            log.info(f"📚 Found {len(shas)} retros")
            return shas
        except subprocess.CalledProcessError as e:
            raise GitNotesError(f"Failed to list notes: {e.stderr}") from e

    def remove(self, commit_sha: str) -> None:
        """Remove retro note from commit.

        Args:
            commit_sha: Commit SHA to remove note from
        """
        try:
            self._git("notes", "remove", commit_sha, check=True)
            log.info(f"🗑️ Removed retro for {commit_sha[:8]}")
        except GitNotesError:
            log.warning(f"No retro to remove for {commit_sha[:8]}")

    def push(self, remote: str = "origin") -> None:
        """Push retro notes to remote.

        Args:
            remote: Git remote name (default: origin)
        """
        try:
            self._git("push", remote, self.notes_ref, check=True)
            log.info(f"📤 Pushed retros to {remote}/{self.notes_ref}")
        except GitNotesError as e:
            log.error(f"🚨 Failed to push retros: {e}")

    def pull(self, remote: str = "origin") -> None:
        """Pull retro notes from remote.

        Args:
            remote: Git remote name (default: origin)
        """
        try:
            self._git("fetch", remote, self.notes_ref, check=True)
            self._git("notes", "merge", f"{remote}/{self.notes_ref}", check=True)
            log.info(f"📥 Pulled retros from {remote}/{self.notes_ref}")
        except GitNotesError as e:
            log.error(f"🚨 Failed to pull retros: {e}")
