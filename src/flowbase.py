"""
Feature Development Flow module.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import uuid
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
from project_manager.config import settings as project_settings
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
    path: str = Field(default="", description="Original Path to repository")
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

    planning_comment_id: Optional[int] = Field(
        default=None, description="ID of the planning progress comment"
    )
    commit_urls: dict[int, str] = Field(
        default_factory=dict, description="Story ID to commit URL mapping"
    )

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
        return git.Repo(self.state.repo)

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

    def _setup_develop_branch(self):
        git_repo = git.Repo(self.state.path)

        # Fetch latest from remote
        git_repo.remotes.origin.fetch()

        # Get default branch from remote
        # This gets the HEAD reference which points to the default branch
        default_branch = git_repo.remotes.origin.refs.HEAD.reference

        # Check if remote develop branch exists
        remote_develop_exists = hasattr(git_repo.remotes.origin.refs, "develop")

        # Determine which branch to use
        if remote_develop_exists:
            target_remote_branch = git_repo.remotes.origin.refs.develop
            logger.info("🏹 Remote develop branch found, using origin/develop")
        else:
            target_remote_branch = default_branch
            logger.info(
                f"🏹 No remote develop branch found, using default branch: {default_branch}"
            )

        # Check if local develop branch exists
        if "develop" in git_repo.heads:
            develop_branch = git_repo.heads.develop
        else:
            # Create local develop branch tracking the target remote branch
            develop_branch = git_repo.create_head("develop", target_remote_branch)

        # Checkout develop branch
        develop_branch.checkout()

        # Ensure develop branch is tracking the correct remote (origin)
        if "origin" in git_repo.remotes:
            origin = git_repo.remotes.origin
            if "develop" in origin.refs:
                # Ensure develop branch tracks origin/develop
                develop_branch.set_tracking_branch(origin.refs.develop)

            # Reset to target remote branch
            git_repo.git.reset("--hard", target_remote_branch)

            print(
                f"Successfully set up develop branch pointing to {target_remote_branch}"
            )
        return develop_branch

    def _prepare_work_tree(self):
        if ".worktrees" in self.state.path:
            self.state.path = os.path.join(self.state.path, "..", "..")

        branch_name = self.state.branch
        self.state.path = self.state.path
        worktrees_dir = os.path.join(self.state.path, ".git", ".worktrees")
        worktree_path = os.path.join(worktrees_dir, branch_name)
        self.state.repo = worktree_path

        logger.warning(f"Repo dir: {self.state.repo}")
        if os.path.exists(worktree_path):
            return

        logger.info("🏹 Preparing work tree ...")
        if not os.path.exists(self.state.path):
            logger.info(f"🚨 Repository not found at {self.state.path}, cloning...")
            parent_dir = os.path.dirname(self.state.path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            # TODO: this requires setting up a ssh alias!
            repo_url = f"github:{self.state.repo_owner}/{self.state.repo_name}"
            git.Repo.clone_from(repo_url, self.state.path)
            logger.info(f"🏹 Cloned repository from {repo_url} to {self.state.path}")

        self._setup_develop_branch()
        self._create_worktree(branch_name)
        self._symblink_packages(worktree_path)

    def _symblink_packages(self, worktree_path: str):
        # symlink some dependencies from root, if exists
        dependencies = ["node_modules", ".venv", ".env"]
        for dep in dependencies:
            source = os.path.join(self.state.path, dep)
            target = os.path.join(worktree_path, dep)
            if os.path.exists(source) and not os.path.exists(target):
                os.symlink(source, target)
                logger.info(f"🔗 Linked {dep} from main repo to worktree")

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
            f"🏹 Committed changes: {commit_message.split(chr(10))[0]} ... (#{commit.hexsha})"
        )
        return commit

    def _get_commit_url(self, commit_sha: str) -> str:
        """Get the GitHub URL for a commit."""
        return (
            f"https://github.com/{self.state.repo_owner}/{self.state.repo_name}"
            f"/commit/{commit_sha}"
        )

    def _push_repo(self):
        repo, *_ = get_github_repo_from_local(self.state.repo)
        logger.info("🏹 Pushing repo ...")

        origin = repo.remote(name="origin")
        origin.push()

    def _post_planning_checklist(self, stories: list, issue_id: int) -> int | None:
        """Post planning checklist to issue and return comment ID."""
        checklist_items = "\n".join(f"- [ ] {story.description}" for story in stories)
        comment = (
            f"## 📋 Implementation Plan\n\n"
            f"{checklist_items}\n\n"
            f"_Progress will be updated as stories are implemented._"
        )
        self._project_manager.add_comment(issue_id, comment)

        comment_id = self._project_manager.get_last_comment_by_user(
            issue_id, self._project_manager.bot_username
        )
        if comment_id:
            logger.info(f"🏹 Posted planning checklist, comment ID: {comment_id}")
        return comment_id

    def _update_planning_checklist(
        self,
        stories: list,
        completed_story_ids: list[int],
        issue_id: int,
        pr_url: str | None = None,
        merged: bool = False,
    ):
        """Update the planning checklist with progress."""
        if not self.state.planning_comment_id:
            logger.warning("No planning comment ID, cannot update checklist")
            return

        checklist_lines = []
        for story in stories:
            if story.id in completed_story_ids:
                commit_url = self.state.commit_urls.get(story.id)
                if commit_url:
                    checklist_lines.append(
                        f"- [x] {story.description} ([commit]({commit_url}))"
                    )
                else:
                    checklist_lines.append(f"- [x] {story.description}")
            else:
                checklist_lines.append(f"- [ ] {story.description}")

        body = "## 📋 Implementation Plan\n\n" + "\n".join(checklist_lines)

        if pr_url:
            if merged:
                body += (
                    f"\n\n---\n\n✅ **Merged** - [PR #{self.state.pr_number}]({pr_url})"
                )
            else:
                body += f"\n\n---\n\n🔍 **Review in progress** - [PR #{self.state.pr_number}]({pr_url})"
        else:
            body += "\n\n_Progress will be updated as stories are implemented._"

        self._project_manager.update_comment(
            issue_id, self.state.planning_comment_id, body
        )
        logger.info(f"🏹 Updated planning checklist for issue #{issue_id}")

    def recall_as_markdown_list(self, name: str, **kwargs):
        if "scope" not in kwargs:
            kwargs.update(dict(scope=self.state.memory_prefix))
        conf_recall = self.recall(name, **kwargs)  # ty:ignore
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
        """Merge the pull request only if the required label is present."""
        if not self.state.pr_number:
            logger.warning("⚠️ No PR number set, skipping merge")
            return

        # Check if the required label is present
        if not self._project_manager.has_label(
            self.state.issue_id, project_settings.MERGE_REQUIRED_LABEL
        ):
            logger.warning(
                f"⚠️ Issue #{self.state.issue_id} does not have the required label "
                f"'{project_settings.MERGE_REQUIRED_LABEL}'. Merge aborted."
            )
            self._project_manager.add_comment(
                self.state.issue_id,
                f"## ⚠️ Merge Blocked\n\n"
                f"Pull request #{self.state.pr_number} cannot be merged because. The issue {self.state.issue_id} does not have "
                f"the required label: `{project_settings.MERGE_REQUIRED_LABEL}`.\n\n"
                f"Please add the label and try again.",
            )
            return

        # Label is present, proceed with merge
        logger.info(
            f"✅ Pull request #{self.state.pr_number} has required label '{project_settings.MERGE_REQUIRED_LABEL}', proceeding with merge"
        )
        success = self._project_manager.merge_pull_request(self.state.pr_number)

        if success:
            self._project_manager.add_comment(
                self.state.issue_id,
                f"## ✅ Task Completed\n\n"
                f"Pull request #{self.state.pr_number} has been merged.\n"
                f"[View merged PR]({self.state.pr_url})",
            )

    def _create_worktree(self, branch_name: str):
        root_git_repo = git.Repo(self.state.path)
        worktrees_dir = os.path.join(self.state.path, ".git", ".worktrees")
        worktree_path = os.path.join(worktrees_dir, branch_name)
        if branch_name not in [b.name for b in root_git_repo.branches]:
            develop_branch = root_git_repo.branches["develop"]
            root_git_repo.create_head(branch_name, develop_branch.name)
            logger.info(f"🏹 Created branch: {branch_name}")
        try:
            os.makedirs(worktrees_dir, exist_ok=True)
        except Exception:
            logger.error(f"Failed to create directory: {worktrees_dir}")

        root_git_repo.git.worktree("add", worktree_path, branch_name)
        logger.info(f"🏹 Created worktree at: {worktree_path}")

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
                logger.warning(f"⚠️ Could not read package.json: {e}")

    def _build(self):
        if not self.state.build_cmd:
            logger.warning("⚠️ No build command, skipping verification")
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
            logger.warning("⚠️ No test command, skipping verification")
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
