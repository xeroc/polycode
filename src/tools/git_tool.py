"""Git management tool for CrewAI."""

from pathlib import Path
from typing import Any, Optional

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing_extensions import Self


class AddSchema(BaseModel):
    """Schema for git add operation."""

    paths: str = Field(
        default=".",
        description="File paths to stage (space-separated). Use '.' for all changes.",
    )


class CommitSchema(BaseModel):
    """Schema for git commit operation."""

    message: str = Field(
        ...,
        description="Commit message describing the changes.",
    )
    allow_empty: bool = Field(
        default=False,
        description="Allow empty commit (no staged changes).",
    )


class FetchSchema(BaseModel):
    """Schema for git fetch operation."""

    remote: str = Field(
        default="origin",
        description="Remote repository name.",
    )
    branch: Optional[str] = Field(
        default=None,
        description="Branch to fetch. If None, fetches all branches.",
    )


class MergeSchema(BaseModel):
    """Schema for git merge operation."""

    branch: str = Field(
        ...,
        description="Branch or commit to merge into current branch.",
    )
    message: Optional[str] = Field(
        default=None,
        description="Custom merge message. If None, uses default.",
    )


class CheckoutSchema(BaseModel):
    """Schema for git checkout operation."""

    branch: str = Field(
        ...,
        description="Branch or commit to checkout.",
    )
    create_new: bool = Field(
        default=False,
        description="Create and checkout a new branch.",
    )
    force: bool = Field(
        default=False,
        description="Force checkout, discarding local changes.",
    )


class GitTool(BaseTool):
    """Tool for managing local git repositories using GitPython.

    Supports: add, commit, fetch, merge, checkout operations.
    """

    name: str = "Git Tool"
    description: str = """
    Manage local git repositories. Provides operations:
    - add: Stage files for commit
    - commit: Commit staged changes
    - fetch: Fetch updates from remote
    - merge: Merge branches/commits
    - checkout: Switch branches or create new ones
    """
    repo_path: str = Field(
        default=".",
        description="Path to the git repository. Defaults to current directory.",
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._ensure_gitpython()

    def _ensure_gitpython(self) -> None:
        """Ensure GitPython is available."""
        try:
            import git  # noqa: F401
        except ImportError:
            raise ImportError("GitPython is required. Install with: pip install GitPython")

    @property
    def repo(self) -> Any:
        """Get git.Repo instance."""
        import git

        path = Path(self.repo_path).expanduser().resolve()
        if not path.exists():
            raise ValueError(f"Path does not exist: {self.repo_path}")
        return git.Repo(path)

    def add(self, paths: str = ".") -> str:
        """Stage files for commit.

        Args:
            paths: Space-separated file paths. Use '.' for all changes.

        Returns:
            Success message with staged files.
        """
        repo = self.repo
        expanded_paths = [Path(p).expanduser().resolve() for p in paths.split()]

        staged = []
        for path in expanded_paths:
            try:
                repo.index.add([str(path)])
                staged.append(str(path))
            except Exception as e:
                return f"Error adding {path}: {e}"

        return f"Staged {len(staged)} item(s): {', '.join(staged) if staged else 'None'}"

    def commit(self, message: str, allow_empty: bool = False) -> str:
        """Commit staged changes.

        Args:
            message: Commit message.
            allow_empty: Allow empty commit.

        Returns:
            Commit hash and message.
        """
        repo = self.repo

        try:
            commit = repo.index.commit(
                message,
                allow_empty=allow_empty,
            )
            return f"Commit created: {commit.hexsha[:7]} - {message}"
        except Exception as e:
            return f"Commit failed: {e}"

    def fetch(self, remote: str = "origin", branch: Optional[str] = None) -> str:
        """Fetch updates from remote.

        Args:
            remote: Remote repository name.
            branch: Branch to fetch. If None, fetches all.

        Returns:
            Fetch results summary.
        """
        repo = self.repo

        try:
            if branch:
                fetch_info = repo.remotes[remote].fetch(branch)
            else:
                fetch_info = repo.remotes[remote].fetch()

            details = [f"{info.name} -> {info.flags}" for info in fetch_info]
            return f"Fetched {len(fetch_info)} ref(s):\n" + "\n".join(details)
        except IndexError:
            return f"Remote '{remote}' not found"
        except Exception as e:
            return f"Fetch failed: {e}"

    def merge(self, branch: str, message: Optional[str] = None) -> str:
        """Merge branch or commit into current branch.

        Args:
            branch: Branch or commit to merge.
            message: Custom merge message.

        Returns:
            Merge result with commit hash.
        """
        repo = self.repo

        try:
            if message:
                commit = repo.merge(branch, message=message)
            else:
                commit = repo.merge(branch)
            return f"Merged {branch} -> {commit.hexsha[:7]}"
        except Exception as e:
            return f"Merge failed: {e}"

    def checkout(
        self,
        branch: str,
        create_new: bool = False,
        force: bool = False,
    ) -> str:
        """Checkout branch or create new branch.

        Args:
            branch: Branch or commit to checkout.
            create_new: Create and checkout new branch.
            force: Force checkout, discarding changes.

        Returns:
            Checkout result with current branch.
        """
        repo = self.repo

        try:
            if create_new:
                new_branch = repo.create_head(branch)
                new_branch.checkout()
                return f"Created and checked out new branch: {branch}"
            else:
                repo.git.checkout(branch, force=force)
                return f"Checked out: {branch}"
        except Exception as e:
            return f"Checkout failed: {e}"

    def push(self, remote: str = "origin", branch: Optional[str] = None) -> str:
        """Push local commits to remote.

        Args:
            remote: Remote repository name.
            branch: Branch to push. If None, pushes current branch.

        Returns:
            Push result summary.
        """
        repo = self.repo

        try:
            if branch:
                push_info = repo.remotes[remote].push(branch)
            else:
                push_info = repo.remotes[remote].push()

            details = [f"{info.local_ref} -> {info.remote_ref}" for info in push_info]
            return f"Pushed {len(push_info)} ref(s):\n" + "\n".join(details)
        except IndexError:
            return f"Remote '{remote}' not found"
        except Exception as e:
            return f"Push failed: {e}"

    def status(self) -> str:
        """Get repository status.

        Returns:
            Status summary with staged, unstaged, and untracked files.
        """
        repo = self.repo

        staged = [item.a_path for item in repo.index.diff(repo.head.commit)]
        unstaged = [item.a_path for item in repo.index.diff(None)]
        untracked = repo.untracked_files

        lines = [f"Branch: {repo.active_branch.name}"]

        if staged:
            lines.append(f"\nStaged ({len(staged)}):")
            lines.extend(f"  + {f}" for f in staged)

        if unstaged:
            lines.append(f"\nModified ({len(unstaged)}):")
            lines.extend(f"  ~ {f}" for f in unstaged)

        if untracked:
            lines.append(f"\nUntracked ({len(untracked)}):")
            lines.extend(f"  ? {f}" for f in untracked[:10])
            if len(untracked) > 10:
                lines.append(f"  ... and {len(untracked) - 10} more")

        if not (staged or unstaged or untracked):
            lines.append("\nWorking tree clean")

        return "\n".join(lines)

    def branches(self, remote: bool = False) -> str:
        """List branches.

        Args:
            remote: List remote branches instead of local.

        Returns:
            Branch list with current branch marked.
        """
        repo = self.repo

        if remote:
            branches_list = [ref.name for ref in repo.refs if ref.is_remote]
            return "Remote branches:\n" + "\n".join(f"  {b}" for b in branches_list)

        current = repo.active_branch.name
        local_branches = [b.name for b in repo.heads]

        lines = ["Local branches:"]
        for b in local_branches:
            marker = "* " if b == current else "  "
            lines.append(f"{marker}{b}")

        return "\n".join(lines)

    def _run(self, *args: Any, **kwargs: Any) -> str:
        """Run the tool (not used directly - operations are called as methods)."""
        raise NotImplementedError("Call specific methods: add, commit, fetch, merge, checkout, push, status, branches")

    @classmethod
    def from_directory(cls, repo_path: str) -> Self:
        """Create GitTool for specific repository directory.

        Args:
            repo_path: Path to git repository.

        Returns:
            Configured GitTool instance.
        """
        return cls(repo_path=repo_path)
