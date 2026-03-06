"""
Feature Development Flow module.
"""

import os
from typing import TypeVar
from pathlib import Path

from crewai import Flow
from crewai.memory.unified_memory import Memory
from crewai.rag.embeddings.providers.ollama.types import (
    OllamaProviderConfig,
    OllamaProviderSpec,
)
import git
from pydantic import BaseModel

from glm import GLMJSONLLM

from github_issues.github_status import ProjectStatusManager
from github_issues.utils import get_github_repo_from_local
from typing import Optional

from pydantic import Field

from persistence.postgres import (
    ensure_request_exists,
    update_request_status,
    SessionLocal,
)

T = TypeVar("T", bound="BaseFlowModel")


class BaseFlowModel(BaseModel):
    path: str = Field(default="", description="Path to repository")
    repo: str = Field(
        default="", description="Path to repository in a worktree"
    )
    branch: str = Field(default="", description="Feature branch name")
    task: str = Field(default="", description="Feature development task")

    repo_owner: Optional[str] = Field(
        default=None, description="GitHub repository owner"
    )
    repo_name: Optional[str] = Field(
        default=None, description="GitHub repository name"
    )

    pr_number: Optional[int] = Field(
        default=None, description="Pull request number"
    )
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


class FlowIssueManagement(Flow[T]):
    """Generic base class that passes type parameter to Flow"""

    status_manager: ProjectStatusManager

    def _setup(self):
        self.status_manager = ProjectStatusManager(
            self.state.repo_owner, self.state.repo_name
        )

        try:
            ensure_request_exists(
                SessionLocal, self.state.issue_id, self.state.task
            )
            print(
                f"🏹 Ensured request exists for issue #{self.state.issue_id}"
            )
        except Exception as e:
            print(f"🚨 Failed to ensure request exists: {e}")

        try:
            update_request_status(
                SessionLocal, self.state.issue_id, "inprogress"
            )
            print(
                f"🏹 Set PostgreSQL request status to inprogress for issue #{self.state.issue_id}"
            )
        except Exception as e:
            print(f"🚨 Failed to update PostgreSQL status to inprogress: {e}")

    def _prepare_work_tree(self):
        branch_name = self.state.branch
        root_repo = self.state.path

        print("🏹 Preparing work tree ...")

        if not os.path.exists(root_repo):
            print(f"🚨 Repository not found at {root_repo}, cloning...")
            parent_dir = os.path.dirname(root_repo)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            # TODO: this requires setting up a ssh alias!
            repo_url = f"github:{self.state.repo_owner}/{self.state.repo_name}"
            git.Repo.clone_from(repo_url, root_repo)
            print(f"🏹 Cloned repository from {repo_url} to {root_repo}")

        # TODO: develop branch is required currently
        git_repo = git.Repo(root_repo)
        git_repo.git.fetch("origin")
        git_repo.git.checkout("develop")
        git_repo.git.reset("--hard", "origin/develop")

        if branch_name not in [b.name for b in git_repo.branches]:
            develop_branch = git_repo.branches["develop"]
            git_repo.create_head(branch_name, develop_branch.name)
            print(f"🏹 Created branch: {branch_name}")

        worktrees_dir = os.path.join(root_repo, ".git", ".worktrees")
        os.makedirs(worktrees_dir, exist_ok=True)
        worktree_path = os.path.join(worktrees_dir, branch_name)

        if os.path.exists(worktree_path):
            git_repo.git.worktree("remove", worktree_path, "--force")
            print(f"🏹 Removed existing worktree at: {worktree_path}")

        git_repo.git.worktree("add", worktree_path, branch_name)
        print(f"🏹 Created worktree at: {worktree_path}")

        dependencies = ["node_modules", ".venv", ".env"]
        for dep in dependencies:
            source = os.path.join(root_repo, dep)
            target = os.path.join(worktree_path, dep)
            if os.path.exists(source) and not os.path.exists(target):
                os.symlink(source, target)
                print(f"🔗 Linked {dep} from main repo to worktree")

        # Update inputs
        self.state.repo = worktree_path
        self.state.path = worktree_path

    def _commit_changes(self, title: str, body="", footer=""):
        print("🏹 Commiting changes to repo")
        repo = git.Repo(self.state.repo)

        # Ensure we are on branch self.state.branch
        branch_name = repo.active_branch.name
        if branch_name != self.state.branch:
            raise ValueError(
                f"Wrong branch in the working directory ({self.state.repo}). Current branch '{branch_name}'. Excected '{self.state.branch}'"
            )

        # commit all changes to the repo
        repo.git.add("-A")
        commit_message = f"{title}\n\n{body}\n\n{footer}"
        repo.index.commit(commit_message)
        print(f"🏹 Committed changes: {commit_message.split('\n')[0]} ...")

    def recall_as_markdown_list(self, name: str, **kwargs):
        if "scope" not in kwargs:
            kwargs.update(dict(scope=self.state.memory_prefix))
        conf_recall = self.recall(name, **kwargs)
        return "\n".join(f"- {m.record.content}" for m in conf_recall)

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
        print("💾 Memory:")
        print(self.memory.tree())

        self.agents_md_map: dict[str, str] = {}
        self.root_agents_md: str = ""

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
                print(f"📕 Discovered AGENTS.md: {relative_path}")
            except Exception as e:
                print(f"🚨 Error reading {agents_file}: {e}")

        self.agents_md_map = agents_md_files

        # Extract root AGENTS.md if it exists
        if "AGENTS.md" in agents_md_files:
            self.root_agents_md = agents_md_files["AGENTS.md"]
        elif len(agents_md_files) > 0:
            # Use the first discovered file as root if no direct AGENTS.md
            first_path = next(iter(agents_md_files.keys()))
            self.root_agents_md = agents_md_files[first_path]
            print(f"📕 Using {first_path} as root AGENTS.md")

        print(f"📕 Total AGENTS.md files discovered: {len(agents_md_files)}")
        return agents_md_files

    def _push_repo(self):
        repo, *_ = get_github_repo_from_local(self.state.repo)
        print("🏹 Pushing repo ...")
        repo.git.push("origin", self.state.branch)

    def _create_pr(self):
        """Step 6: Create pull request."""
        print("🏹 Creating pull request")
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
        print(f"🏹 PR {self.state.pr_number} created: {self.state.pr_url}")

        self.status_manager.add_comment(
            self.state.issue_id,
            f"## 🔍 Review Started\n\n"
            f"Pull request #{self.state.pr_number} is now under review.\n"
            f"[View PR]({self.state.pr_url})",
        )

    def _merge_branch(self):
        if self.state.pr_number:
            self.status_manager.merge_pull_request(self.state.pr_number)

    def _cleanup_worktree(self):
        try:
            self.status_manager.update_status(self.state.issue_id, "Done")
        except Exception as e:
            print(f"🚨 Failed to update project status to Done: {e}")

        try:
            update_request_status(
                SessionLocal, self.state.issue_id, "completed"
            )
            print(
                f"🏹 Updated PostgreSQL request status to completed for issue #{self.state.issue_id}"
            )
        except Exception as e:
            print(f"🚨 Failed to update PostgreSQL status: {e}")

        git_repo = git.Repo(self.state.repo)
        git_repo.git.worktree("remove", self.state.repo)
        print(f"🏹 Removed worktree: {self.state.repo}")

        parent_dir = os.path.dirname(self.state.repo)
        if os.path.exists(parent_dir):
            os.rmdir(parent_dir)
        print(f"🏹 Cleaned up worktree parent directory")
