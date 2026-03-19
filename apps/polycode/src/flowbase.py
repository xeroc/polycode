"""
Feature Development Flow module.

Generic flow orchestration that delegates project-specific operations (PR, merge, issue management)
to plugin hooks. This module has no knowledge of GitHub or any specific provider.
"""

import json
import logging
import subprocess
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Optional, TypeVar

import git
from crewai import Flow
from crewai.memory.unified_memory import Memory
from crewai.rag.embeddings.providers.ollama.types import (
    OllamaProviderConfig,
    OllamaProviderSpec,
)
from pydantic import BaseModel, Field

from gitcore import GitOperations
from glm import GLMJSONLLM
from modules.hooks import FlowPhase
from persistence.postgres import (
    SessionLocal,
    ensure_request_exists,
    update_request_status,
)
from project_manager.types import ProjectConfig

if TYPE_CHECKING:
    import pluggy

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


class BaseFlowModel(BaseModel):
    project_config: Optional[ProjectConfig] = Field(
        default=None, description="Description of the project to work on"
    )
    path: str = Field(default="", description="Original Path to repository")
    repo: str = Field(default="", description="Path to repository in a worktree")
    branch: str = Field(default="", description="Feature branch name")
    task: str = Field(default="", description="Feature development task")

    repo_owner: Optional[str] = Field(default=None, description="Repository owner")
    repo_name: Optional[str] = Field(default=None, description="Repository name")

    pr_number: Optional[int] = Field(default=None, description="Pull request number")
    pr_url: Optional[str] = Field(default=None, description="Pull request URL")
    issue_id: int = Field(default=0, description="issue id")

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
    """Generic base class that passes type parameter to Flow."""

    _pm: "pluggy.PluginManager | None" = None
    _agents_md_map: dict[str, str] = {}
    _root_agents_md: str = ""
    _git_ops: GitOperations | None = None

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

    @classmethod
    def configure_hooks(cls, pm: "pluggy.PluginManager") -> None:
        """Set the plugin manager for all flow instances."""
        cls._pm = pm

    def _emit(self, phase: FlowPhase, result: object | None = None) -> None:
        """Emit a hook event. Safe to call even if no pm configured."""
        if not self._pm:
            return
        try:
            self._pm.hook.on_flow_phase(
                phase=phase,
                flow_id=str(getattr(self.state, "flow_id", "")),
                state=self.state,
                result=result,
            )
        except Exception as e:
            logger.warning(f"⚠️ Hook error in {phase}: {e}")

    @property
    def _git_repo(self) -> git.Repo:
        return git.Repo(self.state.repo)

    @property
    def git_operations(self) -> GitOperations:
        """Get git operations instance for this flow."""
        return GitOperations.from_flow_state(self.state, self._pm)

    def _setup(self):
        self._emit(FlowPhase.PRE_SETUP)
        worktree_path = self.git_operations.prepare_worktree()
        self.state.repo = worktree_path
        if not self.state.project_config:
            raise ValueError("project_config required!")

        try:
            ensure_request_exists(SessionLocal, self.state.issue_id, self.state.task)
            logger.info(f"🏹 Ensured request exists for issue #{self.state.issue_id}")
        except Exception as e:
            logger.error(f"🚨 Failed to ensure request exists: {e}")
        self._emit(FlowPhase.POST_SETUP)

    def pickup_issue(self):
        try:
            update_request_status(SessionLocal, self.state.issue_id, "inprogress")
            logger.info(
                f"🏹 Set PostgreSQL request status to inprogress for issue #{self.state.issue_id}"
            )
        except Exception as e:
            logger.error(f"🚨 Failed to update PostgreSQL status to inprogress: {e}")

    def _commit_changes(self, title: str, body="", footer=""):
        self._emit(FlowPhase.PRE_COMMIT)

        commit = self.git_operations.commit(title, body, footer)

        self._emit(FlowPhase.POST_COMMIT, result=commit)
        return commit

    def _get_commit_url(self, commit_sha: str) -> str:
        """Get the URL for a commit."""
        return self.git_operations.get_commit_url(commit_sha)

    def _push_repo(self):
        self._emit(FlowPhase.PRE_PUSH)
        self.git_operations.push()
        self._emit(FlowPhase.POST_PUSH)

    def _post_planning_checklist(self, stories: list, issue_id: int) -> int | None:
        """Post planning checklist to issue.

        Delegates to project_manager module via hooks.
        Emits PRE_PLANNING_COMMENT/POST_PLANNING_COMMENT with stories as result.
        """
        self._emit(FlowPhase.PRE_PLANNING_COMMENT, result=stories)
        self._emit(FlowPhase.POST_PLANNING_COMMENT, result=stories)
        return getattr(self.state, "planning_comment_id", None)

    def _update_planning_checklist(
        self,
        stories: list,
        completed_story_ids: list[int],
        issue_id: int,
        pr_url: str | None = None,
        merged: bool = False,
    ):
        """Update the planning checklist with progress.

        Delegates to project_manager module via hooks.
        Emits PRE_UPDATE_CHECKLIST/POST_UPDATE_CHECKLIST with checklist data as result.
        """
        data = {
            "stories": stories,
            "completed_ids": completed_story_ids,
            "pr_url": pr_url,
            "merged": merged,
        }
        self._emit(FlowPhase.PRE_UPDATE_CHECKLIST, result=data)
        self._emit(FlowPhase.POST_UPDATE_CHECKLIST, result=data)

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

        self._agents_md_map = agents_md_files

        if "AGENTS.md" in agents_md_files:
            self._root_agents_md = agents_md_files["AGENTS.md"]
        elif len(agents_md_files) > 0:
            first_path = next(iter(agents_md_files.keys()))
            self._root_agents_md = agents_md_files[first_path]
            logger.info(f"📕 Using {first_path} as root AGENTS.md")

        logger.info(f"📕 Total AGENTS.md files discovered: {len(agents_md_files)}")
        return agents_md_files

    def _create_pr(self):
        """Create pull request.

        Delegates to project_manager module via hooks.
        Emits PRE_PR/POST_PR hooks - project_manager handles PR creation.
        """
        self._emit(FlowPhase.PRE_PR)
        logger.info("🏹 Creating pull request (via hook)")
        self._emit(FlowPhase.POST_PR)

    def _merge_branch(self):
        """Merge the pull request.

        Delegates to project_manager module via hooks.
        Emits PRE_MERGE/POST_MERGE hooks - project_manager handles merge logic.
        """
        self._emit(FlowPhase.PRE_MERGE)
        logger.info("🏹 Processing merge (via hook)")
        self._emit(FlowPhase.POST_MERGE)

    def _cleanup_worktree(self):
        """Cleanup worktree and update issue status.

        Delegates issue status update to project_manager via POST_CLEANUP hook.
        """
        self._emit(FlowPhase.PRE_CLEANUP)

        try:
            update_request_status(SessionLocal, self.state.issue_id, "completed")
            logger.info(
                f"🏹 Updated PostgreSQL request status to completed for issue #{self.state.issue_id}"
            )
        except Exception as e:
            logger.error(f"🚨 Failed to update PostgreSQL status: {e}")

        self.git_operations.cleanup()

        self._emit(FlowPhase.POST_CLEANUP)

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
