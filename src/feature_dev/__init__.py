"""
Feature Development Flow module.
"""

import os
import uuid
from pathlib import Path

from crewai import CrewOutput
from crewai.memory.unified_memory import Memory
from crewai.rag.embeddings.providers.ollama.types import (
    OllamaProviderConfig,
    OllamaProviderSpec,
)
import git
from crewai.flow.flow import Flow, listen, start

from glm import GLMJSONLLM

from .crews.implement_crew.implement_crew import ImplementCrew
from .crews.plan_crew.plan_crew import PlanCrew
from .crews.review_crew.review_crew import ReviewCrew
from .crews.test_crew.test_crew import TestCrew
from .crews.verify_crew.verify_crew import VerifyCrew
from crewai.flow.persistence import persist
from crewai.flow.persistence.sqlite import SQLiteFlowPersistence
from .types import (
    FeatureDevState,
    ImplementOutput,
    KickoffIssue,
    PlanOutput,
    ReviewOutput,
    Story,
    TestOutput,
    VerifyOutput,
)
from .github_status import ProjectStatusManager
from .utils import get_github_repo_from_local, sanitize_branch_name
from persistence import PostgresFlowPersistence

DATA_PATH = os.environ.get("DATA_PATH", "/data")
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres:"):
    persistence = PostgresFlowPersistence(
        connection_string="postgresql://user:pass@localhost/dbname"
    )
else:
    persistence = SQLiteFlowPersistence()


@persist(verbose=True)
class FeatureDevFlow(Flow[FeatureDevState]):
    """
    Feature development workflow with consecutive flows.
    """

    status_manager: ProjectStatusManager

    def _commit_changes(self, title: str, body="", footer=""):
        print("Commiting changes to repo")
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
        print(f"Committed changes: {commit_message}")

    def recall_as_markdown_list(self, name: str):
        conf_recall = self.recall(name)
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
                print(f"Error reading {agents_file}: {e}")

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

    @start()
    def prepare_work_tree(self):
        branch_name = self.state.branch
        root_repo = self.state.path

        if not os.path.exists(root_repo):
            print(f"Repository not found at {root_repo}, cloning...")
            parent_dir = os.path.dirname(root_repo)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            repo_url = f"https://github.com/{self.state.repo_owner}/{self.state.repo_name}"
            git.Repo.clone_from(repo_url, root_repo)
            print(f"Cloned repository from {repo_url} to {root_repo}")

        git_repo = git.Repo(root_repo)

        if branch_name not in [b.name for b in git_repo.branches]:
            develop_branch = git_repo.branches["develop"]
            git_repo.create_head(branch_name, develop_branch.name)
            print(f"Created branch: {branch_name}")

        worktrees_dir = os.path.join(root_repo, ".git", ".worktrees")
        os.makedirs(worktrees_dir, exist_ok=True)
        worktree_path = os.path.join(worktrees_dir, branch_name)

        if os.path.exists(worktree_path):
            git_repo.git.worktree("remove", worktree_path, "--force")
            print(f"Removed existing worktree at: {worktree_path}")

        git_repo.git.worktree("add", worktree_path, branch_name)
        print(f"Created worktree at: {worktree_path}")

        dependencies = ["node_modules", ".venv", ".env"]
        for dep in dependencies:
            source = os.path.join(root_repo, dep)
            target = os.path.join(worktree_path, dep)
            if os.path.exists(source) and not os.path.exists(target):
                os.symlink(source, target)
                print(f"Linked {dep} from main repo to worktree")

        # Update inputs
        self.state.repo = worktree_path
        self.state.path = worktree_path

    @start()
    def setup(self):
        """Step 1: Plan - decompose task into user stories."""
        print("Planning feature into user stories")

        # Discover AGENTS.md files
        self.discover_agents_md_files()

        self.status_manager = ProjectStatusManager()

        if self.state.stories:
            return

        result = (
            PlanCrew()
            .crew(agents_md_map=self.agents_md_map)
            .kickoff(
                inputs=dict(
                    task=self.state.task,
                    repo=self.state.repo,
                    branch=self.state.branch,
                    agents_md=self.root_agents_md,
                )
            )
        )

        output: PlanOutput = result.pydantic  # type: ignore
        self.state.stories = output.stories

        # output: SetupOutput = result.tasks_output[0].pydantic  # type: ignore
        self.state.build_cmd = output.build_cmd
        self.state.test_cmd = output.test_cmd
        self.state.baseline = output.baseline
        self.state.findings = output.findings

        scope = self.state.memory_prefix
        for key in (
            "findings",
            "baseline",
            "purpose",
            "tech_stack",
            "architecture",
            "entry_points",
            "configuration",
            "documentation",
            "build_cmd",
            "test_cmd",
        ):
            self.remember(getattr(output, key), scope=f"{scope}/key")
        print(f"Stored project details to memory at scope: {scope}")

        print(f"Planned {len(output.stories)} stories")
        for current_story in output.stories:
            print(f"   🔖 user story:  {current_story.description}")

        self.status_manager.add_comment(
            self.state.issue_id,
            f"## 📋 Planning completed\n\n"
            "Tasks that need implementing:"
            "\n - [ ] ".join([x.description for x in output.stories]),
        )
        return output

    @listen(setup)
    def implement_story(self):
        """Step 3: Implement - implement user story."""
        print("Implementing user story")

        print("Stories:")
        for current_story in self.state.stories or []:
            print(f"   🔖 {current_story.description}")

        print("Completed Stories:")
        for current_story in self.state.completed_stories or []:
            print(f"   ✅ {current_story.description}")

        if len(self.state.completed_stories or []) == len(
            self.state.stories or []
        ):
            return

        def implement_single_story(current_story: Story):
            print(f"   🔖 user story:  {current_story.description}")

            output = (
                ImplementCrew()
                .crew(agents_md_map=self.agents_md_map)
                .kickoff(
                    inputs=dict(
                        task=self.state.task,
                        repo=self.state.repo,
                        branch=self.state.branch,
                        build_cmd=self.state.build_cmd,
                        test_cmd=self.state.test_cmd,
                        current_story=current_story.model_dump_json(),
                        completed_stories="\n- ".join(
                            [
                                x.description
                                for x in self.state.completed_stories or []
                            ]
                        ),
                        current_story_id=current_story.id,
                        current_story_title=current_story.title,
                        architecture=self.recall_as_markdown_list(
                            "architecture"
                        ),
                        configuration=self.recall_as_markdown_list(
                            "configuration"
                        ),
                        tech_stack=self.recall_as_markdown_list("tech_stack"),
                        agents_md=self.root_agents_md,
                    )
                )
            )

            implement_result: ImplementOutput = output.pydantic  # type: ignore  # or cast

            commit_title = implement_result.title
            commit_message = implement_result.message
            commit_footer = implement_result.footer
            self._commit_changes(commit_title, commit_message, commit_footer)

            return implement_result

        # TODO:
        completed_ids = [x.id for x in self.state.completed_stories or []]
        missing_stories = [
            x for x in self.state.stories or [] if x.id not in completed_ids
        ]

        self.state.completed_stories = []
        self.state.changes = []
        self.state.tests = []

        for story in missing_stories or []:
            print(f"Title: {story.title}")
            print(f"Description: {story.description}")
            # Schedule each chapter writing task
            result = implement_single_story(story)
            self.state.completed_stories.append(story)
            self.state.changes.append(result.changes)
            self.state.tests.append(result.tests)

    @listen(implement_story)
    def push_repo(self):
        repo, *_ = get_github_repo_from_local(self.state.repo)
        print("Pushing repo ...")
        repo.git.push("origin", self.state.branch)

    @listen(push_repo)
    def create_pr(self):
        """Step 6: Create pull request."""
        print("Creating pull request")
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
        print(f"PR {self.state.pr_number} created: {self.state.pr_url}")

        self.status_manager.add_comment(
            self.state.issue_id,
            f"## 🔍 Review Started\n\n"
            f"Pull request #{self.state.pr_number} is now under review.\n"
            f"[View PR]({self.state.pr_url})",
        )

    @listen(implement_story)
    def test_integration(self):
        """Step 5: Test - integration and E2E testing."""
        print("Running integration tests")
        if self.state.tested:
            return

        output = (
            TestCrew()
            .crew()
            .kickoff(
                inputs=dict(
                    task=self.state.task,
                    repo=self.state.repo,
                    branch=self.state.branch,
                    changes=self.state.changes,
                    build_cmd=self.state.build_cmd,
                    test_cmd=self.state.test_cmd,
                )
            )
        )

        test_result: TestOutput = output.pydantic  # type: ignore  # or cast
        self.state.tested = test_result.status == "done"

        if test_result.failures:
            print(f"Test failures: {test_result.failures}")
        else:
            print(f"Tests passed: {test_result.results}")

        return test_result

    @listen(test_integration)
    def verify(self):
        """Step 4: Verify - quick sanity check of implementation."""
        print("Verifying implementation")
        if self.state.verified:
            return

        output = (
            VerifyCrew()
            .crew()
            .kickoff(
                inputs=dict(
                    task=self.state.task,
                    repo=self.state.repo,
                    branch=self.state.branch,
                    changes=self.state.changes,
                    test_cmd=self.state.test_cmd,
                    current_story=self.state.current_story,
                    completed_stories=[
                        x.description
                        for x in self.state.completed_stories or []
                    ],
                )
            )
        )

        verify_result: VerifyOutput = output.tasks_output[0].pydantic  # type: ignore  # or cast
        self.state.verified = verify_result.status == "done"

        if verify_result.issues:
            print(f"Verification issues found: {verify_result.issues}")
        else:
            print(f"Verification passed: {verify_result.verified}")

        return verify_result

    @listen(create_pr)
    def review(self):
        """Step 7: Review - review the pull request."""
        print("Reviewing pull request")
        if self.state.review_status:
            return

        repo = git.Repo(self.state.repo)
        merge_base = repo.merge_base("develop", self.state.branch)[0]
        self.state.diff = repo.git.diff(merge_base, self.state.branch)

        try:
            self.status_manager.update_status(self.state.issue_id, "Reviewing")
        except Exception as e:
            print(f"Failed to update project status: {e}")

        output = (
            ReviewCrew()
            .crew()
            .kickoff(
                inputs=dict(
                    task=self.state.task,
                    diff=str(self.state.diff),
                    changes=str(self.state.changes),
                )
            )
        )
        if not isinstance(output, CrewOutput):
            raise ValueError()

        review_result: ReviewOutput = output.pydantic  # type: ignore  # or cast
        self.state.review_status = review_result.decision

        if review_result.feedback:
            print(f"Review feedback: {review_result.feedback}")
        else:
            print(f"Review decision: {review_result.decision}")

        return review_result

    @listen(review)
    def finish(self):
        """Step 8: Update project status and cleanup worktree."""

        try:
            self.status_manager.update_status(self.state.issue_id, "Done")
        except Exception as e:
            print(f"Failed to update project status to Done: {e}")

        git_repo = git.Repo(self.state.repo)
        git_repo.git.worktree("remove", self.state.repo)
        print(f"Removed worktree: {self.state.repo}")

        parent_dir = os.path.dirname(self.state.repo)
        if os.path.exists(parent_dir):
            os.rmdir(parent_dir)
        print(f"Cleaned up worktree parent directory")

        if self.state.pr_number:
            self.status_manager.merge_pull_request(self.state.pr_number)


############################
# Global variables
############################


def kickoff(issue: KickoffIssue):
    """
    Run the flow.
    """
    feature_dev_flow = FeatureDevFlow()

    id = uuid.uuid4()
    id = uuid.UUID("9c572241-c66e-4323-a812-ac916b9d8508")
    feature_dev_flow.kickoff(
        inputs=dict(
            id=str(id),
            issue_id=issue.id,
            task=f"{issue.title}\n\n{issue.body}",
            path=f"{DATA_PATH}/{issue.repository.owner}/{issue.repository.repository}",
            branch=f"{issue.id}-{sanitize_branch_name(issue.title)}",
            memory_prefix="xeroc/demo",
            repo_owner=issue.repository.owner,
            repo_name=issue.repository.repository,
        )
    )


def plot():
    """
    Plot the flow.
    """
    feature_dev_flow = FeatureDevFlow()
    feature_dev_flow.plot()


def example():
    id = uuid.uuid4()
    # id = "d5e1b205-ebb5-4742-9ac7-2aab0fa29301"
    feature_dev_flow = FeatureDevFlow()
    feature_dev_flow.kickoff(
        inputs=dict(
            id=str(id),
            issue_id=12,
            task="Add an about section below the headline that explains what the project is about.",
            path="/home/xeroc/projects/chaoscraft/demo",
            branch="background",
            repo_owner="xeroc",
            repo_name="demo",
        )
    )


if __name__ == "__main__":
    print("Cannot run manually, requires issue data!")
