"""Feature Development Flow module.

Generic flow orchestration that delegates project-specific operations (PR, merge, issue management)
to plugin hooks. This module has no knowledge of GitHub or any specific provider.
"""

import json
import logging
import subprocess
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Optional, TypeVar

from crewai import Flow
from crewai.events.utils.console_formatter import set_suppress_console_output
from crewai.memory.unified_memory import Memory
from crewai.rag.embeddings.providers.ollama.types import (
    OllamaProviderConfig,
    OllamaProviderSpec,
)
from pydantic import BaseModel, Field

from gitcore import GitOperations
from glm import GLMJSONLLM
from modules.hooks import FlowEvent
from persistence.postgres import (
    SessionLocal,
    ensure_request_exists,
    update_request_status,
)
from project_manager.base import ProjectManager
from project_manager.factory import ProjectManagerFactory
from project_manager.types import IssueComment, ProjectConfig

if TYPE_CHECKING:
    import pluggy

T = TypeVar("T", bound="BaseFlowModel")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class KickoffRepo(BaseModel):
    owner: str = Field(description="repo owner")
    repository: str = Field(description="repository name")


class KickoffIssue(BaseModel):
    id: int = Field(description="Issue ID")
    flow_id: uuid.UUID = Field(default=uuid.uuid4(), description="UUID of flow that will run")
    title: str = Field(description="Issue title")
    body: str = Field(description="Issue description")
    comments: list[IssueComment] = Field(default_factory=list, description="Issue comments")
    memory_prefix: str = Field(description="prefix for memory")
    repository: KickoffRepo
    project_config: ProjectConfig


class BaseFlowModel(BaseModel):
    project_config: Optional[ProjectConfig] = Field(default=None, description="Description of project to work on")
    path: str = Field(default="", description="Original Path to repository")
    repo: str = Field(default="", description="Path to repository in a worktree")
    branch: str = Field(default="", description="Feature branch name")
    task: str = Field(default="", description="Feature development task")

    repo_owner: Optional[str] = Field(default=None, description="Repository owner")
    repo_name: Optional[str] = Field(default=None, description="Repository name")

    pr_number: Optional[int] = Field(default=None, description="Pull request number")
    pr_url: Optional[str] = Field(default=None, description="Pull request URL")
    issue_id: int = Field(default=0, description="issue id")
    planning_comment_id: Optional[int] = Field(default=None, description="ID of planning progress comment")
    commit_title: Optional[str] = Field(
        default=None,
        description="Commit Message title including conventional commit prefix",
    )
    commit_message: Optional[str] = Field(default=None, description="The body of commit message")
    commit_footer: Optional[str] = Field(default=None, description="Commit message footer")
    memory_prefix: str = Field(default="", description="prefix for memory")
    test_cmd: Optional[str] = Field(default=None, description="Test command")
    build_cmd: Optional[str] = Field(default=None, description="Build command from package.json")


set_suppress_console_output(True)


class FlowIssueManagement(Flow[T]):
    """Generic base class that passes type parameter to Flow."""

    _pm: "pluggy.PluginManager | None" = None
    _agents_md_map: dict[str, str] = {}
    _root_agents_md: str = ""
    _git_ops: GitOperations | None = None
    _project_manager: ProjectManager | None = None

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

    def get_project_manager(self) -> ProjectManager:
        """Get project manager instance for this flow."""
        if not self._project_manager:
            if not self.state.project_config:
                raise Exception("Project config not provided, cannot use project manager!")
            self._project_manager = ProjectManagerFactory.create(self.state.project_config)
        return self._project_manager

    @classmethod
    def use_plugin_manager(cls, pm: "pluggy.PluginManager") -> None:
        """Inject plugin manager for all flow instances."""
        cls._pm = pm

    def _emit(
        self,
        event: FlowEvent,
        result: object | None = None,
        label: str = "",
    ) -> None:
        """Emit a hook event. Safe to call even if no pm configured."""
        if not self._pm:
            logger.warning("PluginManager not available in base flow!")
            return
        try:
            logger.info(f"🪝 Received an emit, calling hooks for {event}")
            self._pm.hook.on_flow_event(
                event=event,
                flow_id=str(getattr(self.state, "id", "")),
                state=self.state,
                result=result,
                label=label,
            )
        except Exception as e:
            logger.warning(f"⚠️ Hook error in {event}: {e}")

    @property
    def git_operations(self) -> GitOperations:
        """Get git operations instance for this flow."""
        return GitOperations.from_flow_state(self.state)

    def _setup(self):
        """Initialize flow - prepare worktree and discover project structure."""
        self.state.repo = self.git_operations.worktree_path
        if not self.state.project_config:
            raise ValueError("project_config required!")

        try:
            ensure_request_exists(SessionLocal, self.state.issue_id, self.state.task)
            logger.info(f"🏹 Ensured request exists for issue #{self.state.issue_id}")
        except Exception as e:
            logger.error(f"🚨 Failed to ensure request exists: {e}")

        try:
            update_request_status(SessionLocal, self.state.issue_id, "inprogress")
            logger.info(f"🏹 Set request status to inprogress for issue #{self.state.issue_id}")
        except Exception as e:
            logger.error(f"🚨 Failed to update status to inprogress: {e}")

        self.discover_agents_md_files()
        self._discover_build_cmd()

    def recall_as_markdown_list(self, name: str, **kwargs):
        if "scope" not in kwargs:
            kwargs.update(dict(scope=self.state.memory_prefix))
        conf_recall = self.recall(name, **kwargs)
        return "\n".join(f"- {m.record.content}" for m in conf_recall)

    def discover_agents_md_files(self):
        """Discover all AGENTS.md files in repository."""
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
                    self.state.build_cmd = f"pnpm run -C {self.state.repo} typecheck"
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
        logger.info(f"✅ Build verification passed\n{result.stdout[:200] if result.stdout else ''}...")

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
        logger.info(f"✅ Test verification passed\n{result.stdout[:200] if result.stdout else ''}...")
