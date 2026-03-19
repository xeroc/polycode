"""
Feature Development Flow module.
"""

import json
import logging
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

from channels.dispatcher import ChannelDispatcher
from channels.types import ChannelConfig, ChannelType, Notification, NotificationLevel
from gitcore import GitOperations
from glm import GLMJSONLLM
from modules.hooks import FlowPhase
from persistence.postgres import (
    SessionLocal,
    ensure_request_exists,
    update_request_status,
)
from project_manager import GitHubProjectManager
from project_manager.config import settings as project_settings
from project_manager.git_utils import get_github_repo_from_local
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
    flow_id: uuid.UUID = Field(default=uuid.uuid4(), description="UUID of the flow that will run")
    title: str = Field(description="Issue title")
    body: str = Field(description="Issue description")
    memory_prefix: str = Field(description="prefix for memory")
    repository: KickoffRepo
    project_config: ProjectConfig


class BaseFlowModel(BaseModel):
    project_config: Optional[ProjectConfig] = Field(default=None, description="Description of the project to work on")
    path: str = Field(default="", description="Original Path to repository")
    repo: str = Field(default="", description="Path to repository in a worktree")
    branch: str = Field(default="", description="Feature branch name")
    task: str = Field(default="", description="Feature development task")

    repo_owner: Optional[str] = Field(default=None, description="GitHub repository owner")
    repo_name: Optional[str] = Field(default=None, description="GitHub repository name")

    pr_number: Optional[int] = Field(default=None, description="Pull request number")
    pr_url: Optional[str] = Field(default=None, description="Pull request URL")
    issue_id: int = Field(default=0, description="issue id on github")

    planning_comment_id: Optional[int] = Field(default=None, description="ID of the planning progress comment")
    commit_urls: dict[int, str] = Field(default_factory=dict, description="Story ID to commit URL mapping")

    commit_title: Optional[str] = Field(
        default=None,
        description="Commit Message title including conventional commit prefix",
    )
    commit_message: Optional[str] = Field(default=None, description="The body of the commit message")
    commit_footer: Optional[str] = Field(default=None, description="Commit message footer")
    memory_prefix: str = Field(default="", description="prefix for memory")

    test_cmd: Optional[str] = Field(default=None, description="Test command")
    build_cmd: Optional[str] = Field(default=None, description="Build command from package.json")


class FlowIssueManagement(Flow[T]):
    """Generic base class that passes type parameter to Flow"""

    _pm: "pluggy.PluginManager | None" = None

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
        self._git_ops: GitOperations | None = None

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

    def _should_skip(self, phase: FlowPhase) -> bool:
        """Check if any module wants to skip this phase."""
        if not self._pm:
            return False
        return bool(
            self._pm.hook.should_skip_phase(
                phase=phase,
                flow_id=str(getattr(self.state, "flow_id", "")),
                state=self.state,
            )
        )

    @property
    def _project_manager(self) -> GitHubProjectManager:
        """Get GitHub project manager (for backwards compatibility)."""
        if not self.state.project_config:
            raise ValueError("projet_config not specified!")
        return GitHubProjectManager(self.state.project_config)

    @property
    def _channels(self) -> ChannelDispatcher | None:
        """Get channel dispatcher for sending notifications."""
        if not self.state.project_config:
            return None

        extra = self.state.project_config.extra or {}
        channel_configs_data = extra.get("channels", [])

        if not channel_configs_data:
            return None

        configs = [
            ChannelConfig(
                channel_type=ChannelType(c["channel_type"]),
                enabled=c.get("enabled", True),
                extra=c.get("extra", {}),
            )
            for c in channel_configs_data
        ]

        return ChannelDispatcher(configs, self.state.project_config)

    async def _notify(
        self,
        content: str,
        level: NotificationLevel = NotificationLevel.INFO,
        context: dict | None = None,
    ) -> None:
        """Send a notification through configured channels."""
        if not self._channels:
            logger.debug("No channels configured, skipping notification")
            return

        notification = Notification(
            content=content,
            level=level,
            context=context or {},
            metadata={"flow_id": str(getattr(self.state, "flow_id", "unknown"))},
        )

        results = await self._channels.dispatch(notification)

        for result in results:
            if result.success:
                logger.info(f"Notification sent via {result.channel_type.value}")
            else:
                logger.warning(f"Failed to send notification via {result.channel_type.value}: {result.error}")

    @property
    def _git_repo(self) -> git.Repo:
        return git.Repo(self.state.repo)

    @property
    def git_operations(self) -> GitOperations:
        """Get git operations instance for this flow."""
        if self._git_ops is None:
            self._git_ops = GitOperations.from_flow_state(self.state, self._pm)
        return self._git_ops

    def _setup(self):
        self._emit(FlowPhase.PRE_SETUP)
        self._prepare_work_tree()
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
            logger.info(f"🏹 Set PostgreSQL request status to inprogress for issue #{self.state.issue_id}")
        except Exception as e:
            logger.error(f"🚨 Failed to update PostgreSQL status to inprogress: {e}")

    def _list_git_tree(self):
        return self.git_operations.list_tree()

    def _prepare_work_tree(self):
        if self._should_skip(FlowPhase.PRE_SETUP):
            logger.info("Skipping worktree preparation (hook)")
            return

        worktree_path = self.git_operations.prepare_worktree()
        self.state.repo = worktree_path

    def _commit_changes(self, title: str, body="", footer=""):
        self._emit(FlowPhase.PRE_COMMIT)

        commit = self.git_operations.commit(title, body, footer)

        self._emit(FlowPhase.POST_COMMIT, result=commit)
        return commit

    def _get_commit_url(self, commit_sha: str) -> str:
        """Get the GitHub URL for a commit."""
        return self.git_operations.get_commit_url(commit_sha)

    def _push_repo(self):
        self._emit(FlowPhase.PRE_PUSH)
        self.git_operations.push()
        self._emit(FlowPhase.POST_PUSH)

    def _post_planning_checklist(self, stories: list, issue_id: int) -> int | None:
        """Post planning checklist to issue and return comment ID."""
        checklist_items = "\n".join(f"- [ ] {story.description}" for story in stories)
        comment = (
            f"## 📋 Implementation Plan\n\n{checklist_items}\n\n_Progress will be updated as stories are implemented._"
        )
        self._project_manager.add_comment(issue_id, comment)

        comment_id = self._project_manager.get_last_comment_by_user(issue_id, self._project_manager.bot_username)
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
                    checklist_lines.append(f"- [x] {story.description} ([commit]({commit_url}))")
                else:
                    checklist_lines.append(f"- [x] {story.description}")
            else:
                checklist_lines.append(f"- [ ] {story.description}")

        body = "## 📋 Implementation Plan\n\n" + "\n".join(checklist_lines)

        if pr_url:
            if merged:
                body += f"\n\n---\n\n✅ **Merged** - [PR #{self.state.pr_number}]({pr_url})"
            else:
                body += f"\n\n---\n\n🔍 **Review in progress** - [PR #{self.state.pr_number}]({pr_url})"
        else:
            body += "\n\n_Progress will be updated as stories are implemented._"

        self._project_manager.update_comment(issue_id, self.state.planning_comment_id, body)
        logger.info(f"🏹 Updated planning checklist for issue #{issue_id}")

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

        if "AGENTS.md" in agents_md_files:
            self.root_agents_md = agents_md_files["AGENTS.md"]
        elif len(agents_md_files) > 0:
            first_path = next(iter(agents_md_files.keys()))
            self.root_agents_md = agents_md_files[first_path]
            logger.info(f"📕 Using {first_path} as root AGENTS.md")

        logger.info(f"📕 Total AGENTS.md files discovered: {len(agents_md_files)}")
        return agents_md_files

    def _create_pr(self):
        """Step 6: Create pull request."""
        self._emit(FlowPhase.PRE_PR)
        logger.info("🏹 Creating pull request")
        if self.state.pr_number:
            self._emit(FlowPhase.POST_PR)
            return

        _, github_repo, _ = get_github_repo_from_local(self.state.repo)

        pr = github_repo.create_pull(
            title=self.state.commit_title or self.state.task,
            body=f"{self.state.commit_message or ''}\n\n{self.state.commit_footer or ''}",
            head=self.state.branch,
            base="develop",
        )

        self.state.pr_url = pr.html_url
        self.state.pr_number = pr.number
        logger.info(f"🏹 PR {self.state.pr_number} created: {self.state.pr_url}")

        self._project_manager.add_comment(
            self.state.issue_id,
            f"## 🔍 Review Started\n\n"
            f"Pull request #{self.state.pr_number} is now under review.\n"
            f"[View PR]({self.state.pr_url})",
        )

        self._emit(FlowPhase.POST_PR, result=pr)

    def _merge_branch(self):
        """Merge the pull request only if the required label is present."""
        self._emit(FlowPhase.PRE_MERGE)

        if not self.state.pr_number:
            logger.warning("⚠️ No PR number set, skipping merge")
            self._emit(FlowPhase.POST_MERGE)
            return

        if not self._project_manager.has_label(self.state.issue_id, project_settings.MERGE_REQUIRED_LABEL):
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
            self._emit(FlowPhase.POST_MERGE)
            return

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

        self._emit(FlowPhase.POST_MERGE)

    def _cleanup_worktree(self):
        self._emit(FlowPhase.PRE_CLEANUP)

        try:
            self._project_manager.update_issue_status(self.state.issue_id, "Done")
        except Exception as e:
            logger.info(f"🚨 Failed to update project status to Done: {e}")

        try:
            update_request_status(SessionLocal, self.state.issue_id, "completed")
            logger.info(f"🏹 Updated PostgreSQL request status to completed for issue #{self.state.issue_id}")
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

        import subprocess

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

        import subprocess

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
