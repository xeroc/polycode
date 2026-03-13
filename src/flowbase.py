"""
Feature Development Flow module.
"""

import shutil

import json
import os
import re
import subprocess
import uuid
import logging
from pathlib import Path
from typing import Optional, TypeVar

import git
from crewai import Flow
from crewai.memory.unified_memory import Memory
from crewai.rag.embeddings.providers.ollama.types import (
    OllamaProviderConfig,
    OllamaProviderSpec,
)
from pydantic import BaseModel, Field

from glm import GLMJSONLLM
from persistence.postgres import (
    SessionLocal,
    ensure_request_exists,
    update_request_status,
)
from project_manager import GitHubProjectManager
from project_manager.git_utils import get_github_repo_from_local
from project_manager.types import ProjectConfig

T = TypeVar("T", bound="BaseFlowModel")
logger = logging.getLogger(__name__)


class KickoffRepo(BaseModel):
    owner: str = Field(description="repo owner")
    repository: str = Field(description="repository name")


class KickoffIssue(BaseModel):
    id: int = Field(description="Issue ID")
    flow_id: uuid.UUID = Field(
        default=uuid.uuid4(), description="UUID of the flow that will run"
    )
    title: str = Field(description="Issue title")
    body: str = Field(description="Issue description")
    memory_prefix: str = Field(description="prefix for memory")
    repository: KickoffRepo
    project_config: ProjectConfig


def sanitize_branch_name(name: str) -> str:
    """Convert string to valid git branch name."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9._/-]", "-", s)  # replace invalid chars with dash
    s = re.sub(r"-+", "-", s)  # collapse multiple dashes
    s = s.strip("-._/")  # strip leading/trailing junk
    s = re.sub(r"\.{2,}", ".", s)  # no consecutive dots
    s = re.sub(r"/+", "/", s)  # no consecutive slashes
    return s[:16] or "unnamed"


class BaseFlowModel(BaseModel):
    project_config: Optional[ProjectConfig] = Field(
        default=None, description="Description of the project to work on"
    )
    path: str = Field(default="", description="Path to repository")
    repo: str = Field(default="", description="Path to repository in a worktree")
    branch: str = Field(default="", description="Feature branch name")
    task: str = Field(default="", description="Feature development task")

    # FIXME: redundant because also part of project_config
    repo_owner: Optional[str] = Field(
        default=None, description="GitHub repository owner"
    )
    repo_name: Optional[str] = Field(default=None, description="GitHub repository name")

    pr_number: Optional[int] = Field(default=None, description="Pull request number")
    pr_url: Optional[str] = Field(default=None, description="Pull request URL")
    issue_id: int = Field(default=0, description="issue id on github")

    commit_title: Optional[str] = Field(
        default=None,
        description="Commit Message title including conventional commit prefix",
    )
    commit_message: Optional[str] = Field(
        default=None, description="The body of the commit message"
    )
    commit_footer: Optional[str] = Field(
        default=None, description="Commit message footer"
    )
    memory_prefix: str = Field(default="", description="prefix for memory")

    test_cmd: Optional[str] = Field(default=None, description="Test command")
    build_cmd: Optional[str] = Field(
        default=None, description="Build command from package.json"
    )


class FlowIssueManagement(Flow[T]):
    """Generic base class that passes type parameter to Flow"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.memory = Memory(
            llm=GLMJSONLLM(),
            embedder=OllamaProviderSpec(
                provider="ollama",
                config=OllamaProviderConfig(
                    model_name="all-minilm:22m",
                ),
            ),
        )
        logger.info("💾 Memory:")
        logger.info(self.memory.tree())

        self.agents_md_map: dict[str, str] = {}
        self.root_agents_md: str = ""

    @property
    def _project_manager(self) -> GitHubProjectManager:
        if not self.state.project_config:
            raise ValueError("projet_config not specified!")
        return GitHubProjectManager(self.state.project_config)

    @property
    def _git_repo(self) -> git.Repo:
        return git.Repo(self.state.path)

    def _setup(self):
        self._prepare_work_tree()
        if not self.state.project_config:
            raise ValueError("project_config required!")

        try:
            ensure_request_exists(SessionLocal, self.state.issue_id, self.state.task)
            logger.info(f"🏹 Ensured request exists for issue #{self.state.issue_id}")
        except Exception as e:
            logger.error(f"🚨 Failed to ensure request exists: {e}")

    def pickup_issue(self):
        try:
            update_request_status(SessionLocal, self.state.issue_id, "inprogress")
            logger.info(
                f"🏹 Set PostgreSQL request status to inprogress for issue #{self.state.issue_id}"
            )
        except Exception as e:
            logger.error(f"🚨 Failed to update PostgreSQL status to inprogress: {e}")

    def _list_git_tree(self):
        return self._git_repo.git.ls_files()

    def setup_develop_branch(self):
        # Fetch latest from remote
        self._git_repo.remotes.origin.fetch()

        # Get default branch from remote
        # This gets the HEAD reference which points to the default branch
        default_branch = self._git_repo.remotes.origin.refs.HEAD.reference

        # Check if remote develop branch exists
        remote_develop_exists = hasattr(self._git_repo.remotes.origin.refs, "develop")

        # Determine which branch to use
        branch_name = "develop"  # Still call it develop locally
        if remote_develop_exists:
            target_remote_branch = self._git_repo.remotes.origin.refs.develop
            logger.info(f"🏹 Remote develop branch found, using origin/develop")
        else:
            target_remote_branch = default_branch
            logger.info(
                f"🏹 No remote develop branch found, using default branch: {default_branch}"
            )

        # Check if local develop branch exists
        if "develop" in self._git_repo.heads:
            develop_branch = self._git_repo.heads.develop
        else:
            # Create local develop branch tracking the target remote branch
            develop_branch = self._git_repo.create_head("develop", target_remote_branch)

        # Checkout develop branch
        develop_branch.checkout()

        # Reset to target remote branch
        self._git_repo.git.reset("--hard", target_remote_branch)

        print(f"Successfully set up develop branch pointing to {target_remote_branch}")
        return develop_branch

    def _prepare_work_tree(self):
        if ".worktrees" in self.state.path:
            self.state.path = os.path.join(self.state.path, "..", "..")

        branch_name = self.state.branch
        root_repo = self.state.path

        logger.info("🏹 Preparing work tree ...")

        if os.path.exists(root_repo):
            return

        logger.info(f"🚨 Repository not found at {root_repo}, cloning...")
        parent_dir = os.path.dirname(root_repo)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        # TODO: this requires setting up a ssh alias!
        repo_url = f"github:{self.state.repo_owner}/{self.state.repo_name}"
        git.Repo.clone_from(repo_url, root_repo)
        logger.info(f"🏹 Cloned repository from {repo_url} to {root_repo}")

        # TODO: develop branch is required currently
        self._git_repo.git.fetch("origin")
        self._git_repo.git.reset("--hard", "origin/develop")

        if branch_name not in [b.name for b in self._git_repo.branches]:
            develop_branch = self._git_repo.branches["develop"]
            self._git_repo.create_head(branch_name, develop_branch.name)
            logger.info(f"🏹 Created branch: {branch_name}")

        worktrees_dir = os.path.join(root_repo, ".git", ".worktrees")
        try:
            os.makedirs(worktrees_dir, exist_ok=True)
        except Exception:
            logger.error(f"Failed to create directory: {worktrees_dir}")
        worktree_path = os.path.join(worktrees_dir, branch_name)

        # if os.path.exists(worktree_path):
        #     self._git_repo.git.worktree("remove", worktree_path, "--force")
        #     logger.info(f"🏹 Removed existing worktree at: {worktree_path}")

        self._git_repo.git.worktree("add", worktree_path, branch_name)
        logger.info(f"🏹 Created worktree at: {worktree_path}")

        dependencies = ["node_modules", ".venv", ".env"]
        for dep in dependencies:
            source = os.path.join(root_repo, dep)
            target = os.path.join(worktree_path, dep)
            if os.path.exists(source) and not os.path.exists(target):
                os.symlink(source, target)
                logger.info(f"🔗 Linked {dep} from main repo to worktree")

        # Update inputs
        self.state.repo = worktree_path

    def _commit_changes(self, title: str, body="", footer=""):
        logger.info("🏹 Commiting changes to repo")
        repo = git.Repo(self.state.repo)

        # Stage changes (all modified files)
        repo.git.add(A=True)  # -A stages all changes (including deletions)

        # merge_base = repo.merge_base("develop", self.state.branch)[0]
        # diff = repo.git.diff(merge_base, self.state.branch)
        # if not diff:
        #     logger.warn("No changes have been made to the repo!")
        #     # no changes made
        #     return
        #
        # # Ensure we are on branch self.state.branch
        # branch_name = repo.active_branch.name
        # if branch_name != self.state.branch:
        #     raise ValueError(
        #         f"Wrong branch in the working directory ({self.state.repo}). Current branch '{branch_name}'. Excected '{self.state.branch}'"
        #     )

        commit_message = f"{title}\n\n{body}\n\n{footer}"
        commit = repo.index.commit(commit_message)
        logger.info(
            f"🏹 Committed changes: {commit_message.split('\n')[0]} ... (#{commit.hexsha})"
        )

    def recall_as_markdown_list(self, name: str, **kwargs):
        if "scope" not in kwargs:
            kwargs.update(dict(scope=self.state.memory_prefix))
        conf_recall = self.recall(name, **kwargs)
        return "\n".join(f"- {m.record.content}" for m in conf_recall)

    def discover_agents_md_files(self):
        """Discover all AGENTS.md files in the repository."""
        repo_path = Path(self.state.repo)
        agents_md_files = {}

        for agents_file in repo_path.rglob("AGENTS.md"):
            try:
                relative_path = str(agents_file.relative_to(repo_path))
                if relative_path.startswith("."):
                    continue
                with open(agents_file, "r", encoding="utf-8") as f:
                    content = f.read()
                agents_md_files[relative_path] = content
                logger.info(f"📕 Discovered AGENTS.md: {relative_path}")
            except Exception as e:
                logger.error(f"🚨 Error reading {agents_file}: {e}")

        self.agents_md_map = agents_md_files

        # Extract root AGENTS.md if it exists
        if "AGENTS.md" in agents_md_files:
            self.root_agents_md = agents_md_files["AGENTS.md"]
        elif len(agents_md_files) > 0:
            # Use the first discovered file as root if no direct AGENTS.md
            first_path = next(iter(agents_md_files.keys()))
            self.root_agents_md = agents_md_files[first_path]
            logger.info(f"📕 Using {first_path} as root AGENTS.md")

        logger.info(f"📕 Total AGENTS.md files discovered: {len(agents_md_files)}")
        return agents_md_files

    def _push_repo(self):
        repo, *_ = get_github_repo_from_local(self.state.repo)
        logger.info("🏹 Pushing repo ...")

        origin = repo.remote(name="origin")
        origin.push()

    def _create_pr(self):
        """Step 6: Create pull request."""
        logger.info("🏹 Creating pull request")
        if self.state.pr_number:
            return

        _, github_repo, _ = get_github_repo_from_local(self.state.repo)

        # PR
        pr = github_repo.create_pull(
            title=self.state.commit_title or self.state.task,
            body=f"{self.state.commit_message or ''}\n\n{self.state.commit_footer or ''}",
            head=self.state.branch,
            base="develop",
        )

        # Get diff between two branches
        self.state.pr_url = pr.html_url
        self.state.pr_number = pr.number
        logger.info(f"🏹 PR {self.state.pr_number} created: {self.state.pr_url}")

        self._project_manager.add_comment(
            self.state.issue_id,
            f"## 🔍 Review Started\n\n"
            f"Pull request #{self.state.pr_number} is now under review.\n"
            f"[View PR]({self.state.pr_url})",
        )

    def _merge_branch(self):
        if self.state.pr_number:
            self._project_manager.merge_pull_request(self.state.pr_number)

    def _cleanup_worktree(self):
        try:
            self._project_manager.update_issue_status(self.state.issue_id, "Done")
        except Exception as e:
            logger.info(f"🚨 Failed to update project status to Done: {e}")

        try:
            update_request_status(SessionLocal, self.state.issue_id, "completed")
            logger.info(
                f"🏹 Updated PostgreSQL request status to completed for issue #{self.state.issue_id}"
            )
        except Exception as e:
            logger.error(f"🚨 Failed to update PostgreSQL status: {e}")

        self._git_repo.git.worktree("remove", self.state.repo)
        logger.info(f"🏹 Removed worktree: {self.state.repo}")

        parent_dir = os.path.dirname(self.state.repo)
        if os.path.exists(parent_dir):
            try:
                # os.rmdir(parent_dir)
                shutil.rmtree(parent_dir)
            except Exception:
                pass
        logger.info("🏹 Cleaned up worktree parent directory")

    def _discover_build_cmd(self):
        """Discover build command from package.json."""
        if not self.state.repo:
            return

        package_json = Path(self.state.repo) / "package.json"
        if package_json.exists():
            try:
                with open(package_json, "r") as f:
                    pkg = json.load(f)
                scripts = pkg.get("scripts", {})
                if "build" in scripts:
                    self.state.build_cmd = f"pnpm run -C {self.state.repo} build"
                    logger.info(f"📦 Build command: {self.state.build_cmd}")
                elif "typecheck" in scripts:
                    self.state.build_cmd = f"pnpm run-C {self.state.repo} typecheck"
                    logger.info(f"📦 Typecheck command: {self.state.build_cmd}")
            except Exception as e:
                logger.warn(f"⚠️ Could not read package.json: {e}")

    def _build(self):
        if not self.state.build_cmd:
            logger.warn("⚠️ No build command, skipping verification")
            return

        result = subprocess.run(
            self.state.build_cmd,
            shell=True,
            cwd=self.state.repo,
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
        logger.info(
            f"✅ Build verification passed\n{result.stdout[:200] if result.stdout else ''}..."
        )

    def _test(self):
        if not self.state.test_cmd:
            logger.warn("⚠️ No test command, skipping verification")
            return

        result = subprocess.run(
            self.state.test_cmd,
            shell=True,
            cwd=self.state.repo,
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
        logger.info(
            f"✅ Test verification passed\n{result.stdout[:200] if result.stdout else ''}..."
        )
