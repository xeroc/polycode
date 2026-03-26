"""Core git operations for Polycode flows.

Extracted from flowbase.py to provide reusable git functionality
that integrates with the plugin system via lifecycle hooks.
"""

import logging
import os
import re
import shutil
from typing import TYPE_CHECKING, Any

import git

from gitcore.types import GitContext, WorktreeConfig

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


def sanitize_branch_name(name: str) -> str:
    """Convert string to valid git branch name."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9._/-]", "-", s)
    s = re.sub(r"-+", "-", s)
    s = s.strip("-._/")
    s = re.sub(r"\.{2,}", ".", s)
    s = re.sub(r"/+", "/", s)
    return s[:16] or "unnamed"


def clone_repository(
    repo_owner: str,
    repo_name: str,
    target_path: str,
    installation_token: str | None = None,
) -> git.Repo:
    """Clone a repository from GitHub.

    Args:
        repo_owner: GitHub repository owner
        repo_name: Repository name
        target_path: Local path to clone to
        installation_token: GitHub App installation token (optional)

    Returns:
        git.Repo object for the cloned repository
    """
    parent_dir = os.path.dirname(target_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    if installation_token:
        repo_url = f"https://x-access-token:{installation_token}@github.com/{repo_owner}/{repo_name}.git"
        safe_url = f"https://x-access-token:***@github.com/{repo_owner}/{repo_name}.git"
    else:
        repo_url = f"github:{repo_owner}/{repo_name}"
        safe_url = repo_url

    repo = git.Repo.clone_from(repo_url, target_path)
    log.info(f"🏹 Cloned repository from {safe_url} to {target_path}")
    return repo


def setup_develop_branch(repo: git.Repo) -> git.Head:
    """Set up the develop branch for feature work.

    Creates or updates local develop branch to track remote develop/main.
    """
    repo.remotes.origin.fetch()

    default_branch = repo.remotes.origin.refs.HEAD.reference
    remote_develop_exists = hasattr(repo.remotes.origin.refs, "develop")

    if remote_develop_exists:
        target_remote_branch = repo.remotes.origin.refs.develop
        log.info("🏹 Remote develop branch found, using origin/develop")
    else:
        target_remote_branch = default_branch
        log.info(f"🏹 No remote develop branch found, using default: {default_branch}")

    if "develop" in repo.heads:
        develop_branch = repo.heads.develop
    else:
        develop_branch = repo.create_head("develop", target_remote_branch)

    develop_branch.checkout()

    if "origin" in repo.remotes:
        origin = repo.remotes.origin
        if "develop" in origin.refs:
            develop_branch.set_tracking_branch(origin.refs.develop)

        repo.git.reset("--hard", target_remote_branch)

        log.info(f"Successfully set up develop branch pointing to {target_remote_branch}")

    return develop_branch


def create_worktree(
    repo: git.Repo,
    config: WorktreeConfig,
) -> str:
    """Create a git worktree for isolated development.

    Args:
        repo: The root git repository
        config: Worktree configuration

    Returns:
        Path to the created worktree
    """
    worktrees_dir = config.worktrees_dir or os.path.join(repo.git_dir, ".worktrees")
    worktree_path = os.path.join(worktrees_dir, config.branch_name)

    if config.branch_name not in [b.name for b in repo.branches]:
        base_branch = repo.branches[config.base_branch]
        repo.create_head(config.branch_name, base_branch.name)
        log.info(f"🏹 Created branch: {config.branch_name}")

    try:
        os.makedirs(worktrees_dir, exist_ok=True)
    except Exception as e:
        log.error(f"Failed to create directory: {worktrees_dir}: {e}")
        raise

    repo.git.worktree("add", worktree_path, config.branch_name)
    log.info(f"🏹 Created worktree at: {worktree_path}")

    return worktree_path


def symlink_packages(
    source_path: str,
    target_path: str,
    deps: list[str] | None = None,
) -> None:
    """Symlink dependencies from source to target directory.

    Args:
        source_path: Path containing the dependencies
        target_path: Path to symlink into
        deps: List of dependency names to symlink
    """
    dependencies = deps or ["node_modules", ".venv", ".env"]
    for dep in dependencies:
        source = os.path.join(source_path, dep)
        target = os.path.join(target_path, dep)
        if os.path.exists(source) and not os.path.exists(target):
            os.symlink(source, target)
            log.info(f"🔗 Linked {dep} from main repo to worktree")


def commit_changes(
    repo: git.Repo,
    title: str,
    body: str = "",
    footer: str = "",
) -> git.Commit:
    """Commit changes to the repository.

    Args:
        repo: git.Repo object
        title: Commit message title
        body: Commit message body
        footer: Commit message footer

    Returns:
        The created commit object
    """
    log.info("🏹 Commiting changes to repo")

    repo.git.add(A=True)

    commit_message = f"{title}\n\n{body}\n\n{footer}"
    commit = repo.index.commit(commit_message)
    log.info(f"🏹 Committed changes: {commit_message.split(chr(10))[0]} ... (#{commit.hexsha})")

    return commit


def push_repo(repo: git.Repo) -> None:
    """Push the current branch to remote origin.

    Args:
        repo: git.Repo object
    """
    log.info("🏹 Pushing repo ...")

    branch = repo.active_branch.name
    repo.git.push("--set-upstream", "origin", branch)


def cleanup_worktree(
    repo: git.Repo,
    worktree_path: str,
) -> None:
    """Remove a worktree and its parent directory if empty.

    Args:
        repo: The root git repository
        worktree_path: Path to the worktree to remove
    """
    try:
        repo.git.worktree("remove", worktree_path)
        log.info(f"🏹 Removed worktree: {worktree_path}")
    except Exception as e:
        log.warning(f"⚠️ Failed to remove worktree: {e}")

    parent_dir = os.path.dirname(worktree_path)
    if os.path.exists(parent_dir):
        try:
            shutil.rmtree(parent_dir)
        except Exception:
            pass
    log.info("🏹 Cleaned up worktree parent directory")


def list_git_tree(repo: git.Repo) -> str:
    """List all files tracked by git.

    Args:
        repo: git.Repo object

    Returns:
        Output of git ls-files
    """
    return repo.git.ls_files()


def get_commit_url(repo_owner: str, repo_name: str, commit_sha: str) -> str:
    """Get the GitHub URL for a commit.

    Args:
        repo_owner: Repository owner
        repo_name: Repository name
        commit_sha: Commit SHA hash

    Returns:
        Full GitHub URL for the commit
    """
    return f"https://github.com/{repo_owner}/{repo_name}/commit/{commit_sha}"


class GitOperations:
    """High-level git operations for flow execution.

    This class provides a convenient interface for git operations
    within a flow, managing context and emitting lifecycle hooks.
    """

    def __init__(
        self,
        context: GitContext,
    ):
        self.context = context

    @classmethod
    def from_flow_state(
        cls,
        state: Any,
    ) -> "GitOperations":
        context = GitContext.from_flow_state(state)
        return cls(context)

    @property
    def worktree_path(self):
        ctx = self.context
        repo_path = ctx.repo_path
        worktrees_dir = os.path.join(repo_path, ".git", ".worktrees")
        return os.path.join(worktrees_dir, ctx.branch_name)

    def prepare_worktree(self) -> str:
        """Prepare a worktree for development.

        This method:
        1. Normalizes the repo path
        2. Clones the repo if needed
        3. Sets up the develop branch
        4. Creates the worktree
        5. Symlinks dependencies

        Returns:
            Path to the worktree
        """
        ctx = self.context
        repo_path = ctx.repo_path

        if ".worktrees" in repo_path:
            repo_path = os.path.join(repo_path, "..", "..")
            ctx.repo_path = repo_path

        worktrees_dir = os.path.join(repo_path, ".git", ".worktrees")
        worktree_path = os.path.join(worktrees_dir, ctx.branch_name)
        ctx.worktree_path = worktree_path

        log.info(f"📁 Repo dir: {worktree_path}")

        if os.path.exists(worktree_path):
            return worktree_path

        log.info("🏹 Preparing work tree ...")

        if not os.path.exists(repo_path):
            log.info(f"🚨 Repository not found at {repo_path}, cloning...")
            clone_repository(
                ctx.repo_owner,
                ctx.repo_name,
                repo_path,
                installation_token=ctx.installation_token,
            )

        setup_develop_branch(ctx.root_repo)

        config = WorktreeConfig(
            branch_name=ctx.branch_name,
            base_branch="develop",
            worktrees_dir=worktrees_dir,
        )
        create_worktree(ctx.root_repo, config)
        symlink_packages(repo_path, worktree_path)

        return worktree_path

    def commit(self, title: str, body: str = "", footer: str = "") -> git.Commit:
        """Commit changes to the worktree."""
        return commit_changes(self.context.repo, title, body, footer)

    def push(self) -> None:
        """Push the current branch to remote."""
        push_repo(self.context.repo)

    def cleanup(self) -> None:
        """Remove the worktree."""
        cleanup_worktree(self.context.root_repo, self.context.worktree_path)

    def get_commit_url(self, commit_sha: str) -> str:
        """Get GitHub URL for a commit."""
        return self.context.get_commit_url(commit_sha)

    def list_tree(self) -> str:
        """List all tracked files."""
        return list_git_tree(self.context.repo)
