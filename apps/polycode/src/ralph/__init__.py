"""Ralph Loop - Ralph Loop pattern using CrewAI @router for control flow.

Flow: Setup → Plan → Ralph Loop (router-controlled) → Verify → Push → PR

Ralph Loop mechanism:
  1. Completion Promise: Agent outputs `<promise>COMPLETE</promise>` when objective
     criteria are met (tests passing, build succeeding, linter clean, etc.)
  2. Stop Hook: Router scans agent output for exact completion promise string
  3. Per-Story Commits: Each story is committed immediately upon completion
  4. Agent receives previous_errors context for smarter retries
"""

import logging
import subprocess
import uuid
from typing import cast

from crewai.flow.flow import listen, start
from crewai.flow.persistence import SQLiteFlowPersistence, persist

from crews import PlanCrew, RalphCrew
from crews.plan_crew.types import PlanOutput
from crews.plan_crew.types import Story as Story
from crews.ralph_crew.types import RalphOutput
from flowbase import FlowIssueManagement, KickoffIssue, sanitize_branch_name
from persistence.postgres import PostgresFlowPersistence
from project_manager import StatusMapping
from project_manager.config import settings as project_settings
from project_manager.types import ProjectConfig

from .types import RalphLoopState

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DATABASE_URL = project_settings.DATABASE_URL
if DATABASE_URL and DATABASE_URL.startswith("postgres"):
    logger.info("📊 Connecting persistence with postgres")
    persistence = PostgresFlowPersistence(connection_string=DATABASE_URL)
else:
    persistence = SQLiteFlowPersistence()


@persist(persistence=persistence, verbose=False)
class RalphLoopFlow(FlowIssueManagement[RalphLoopState]):
    """
    Ralph Loop Flow - externally verified completion with per-story commits.

    Ralph Loop mechanism:
    - Agent outputs completion promise when objective criteria are met
    - Stop hook scans output for exact string match (case-sensitive)
    - Router routes based on completion promise presence
    - Agent receives previous_errors for smarter iteration
    - Each story is committed immediately upon completion
    - Runs per-story with individual iteration tracking
    """

    agents_md_map: dict[str, str] = {}
    root_agents_md: str = ""

    @start()
    def setup(self):
        logger.info("🚀 Ralph Loop starting...")
        self._setup()
        # self._prepare_work_tree()
        self.pickup_issue()

    @listen(setup)
    def plan(self):
        """Create a single story from the 120-char prompt."""

        self.discover_agents_md_files()
        self._discover_build_cmd()

        if self.state.stories:
            return

        logger.info("📝 Planning story from prompt...")

        result = (
            PlanCrew()
            .crew(agents_md_map=self.agents_md_map)
            .kickoff(
                inputs=dict(
                    task=self.state.task[:120],
                    repo=self.state.repo,
                    branch=self.state.branch,
                    agents_md=self.root_agents_md,
                    file_in_repos=self._list_git_tree(),
                )
            )
        )

        output: PlanOutput = result.pydantic  # type: ignore
        self.state.stories = output.stories
        self.state.build_cmd = output.build_cmd
        self.state.test_cmd = output.test_cmd

        logger.info(f"🔖 Planned {len(output.stories)} stories")
        for current_story in output.stories:
            logger.info(f"  |- 🔖 {current_story.description}")

        self.state.planning_comment_id = self._post_planning_checklist(
            output.stories, self.state.issue_id
        )

        num_stories = len(self.state.stories) if self.state.stories else 0
        logger.info(f"\n🔨 Starting Ralph Loop for {num_stories} stories")

    @listen(plan)
    def implement(self):
        """
        Single iteration of Ralph Loop for current story per story

        Agent is instructed to output completion promise ONLY when:
        - All objective criteria are met (tests pass, build succeeds, etc.)
        - Not based on subjective judgment
        """

        unfinished_stories = list(
            filter(lambda story: not story.completed, self.state.stories or [])
        )

        logger.info(f"Unfinished stories: {len(unfinished_stories)}")
        for story in unfinished_stories:
            logger.info(f"\n📖 Story: {story.title}")

            error_context = (
                "\n\n## Previous Errors:\n"
                + "\n".join(f"- {err}" for err in story.errors)
                if story.errors
                else "No previous errors"
            )

            result = (
                RalphCrew()
                .crew(agents_md_map=self.agents_md_map)
                .kickoff(
                    inputs=dict(
                        task=self.state.task[:120],
                        story=story.model_dump_json(),
                        repo=self.state.repo,
                        branch=self.state.branch,
                        test_cmd=self.state.test_cmd,
                        build_cmd=self.state.build_cmd,
                        agents_md=self.root_agents_md,
                        previous_errors=error_context,
                    )
                )
            )

            output = cast(RalphOutput, result.pydantic)  # pyright:ignore
            self.state.agent_output = output.changes
            self.state.commit_title = output.title
            self.state.commit_message = output.message
            self.state.commit_footer = output.footer

            try:
                self._test()
            except Exception as e:
                logger.warning("❌ Tests failed")
                story.errors.append(str(e))
                continue

            logger.warning("✅ Tests succeeded")

            logger.info(f"\n💾 Committing story: {story.title}")
            commit = self._commit_changes(
                title=self.state.commit_title or f"feat: {story.title}",
                body=self.state.commit_message or story.description,
                footer=self.state.commit_footer or "",
            )

            if commit:
                commit_url = self._get_commit_url(commit.hexsha)
                self.state.commit_urls[story.id] = commit_url

            logger.info("✅ Completion")
            logger.info(f"Story '{story.title}' complete - objective criteria verified")
            story.completed = True
            story.errors = []

        self._push_repo()

        completed_ids = [x.id for x in self.state.stories or [] if x.completed]
        self._update_planning_checklist(
            self.state.stories or [],
            completed_ids,
            self.state.issue_id,
        )

    @listen(implement)
    def verify_build(self):
        """Final verification that build passes."""
        logger.info(f"\n🔍 Final build verification: {self.state.build_cmd}")
        self.state.build_success = True
        try:
            self._build()
        except subprocess.TimeoutExpired:
            logger.info("⏱ Build timed out after 180 seconds")
            self.state.build_success = False
        except subprocess.CalledProcessError as e:
            logger.info(f"❌ Build verification failed:\n{e.stderr}")
            self.state.build_success = False

        self.state.test_success = True
        try:
            self._test()
        except subprocess.TimeoutExpired:
            logger.info("⏱ Test timed out after 180 seconds")
            self.state.test_success = False
        except subprocess.CalledProcessError as e:
            logger.info(f"❌ Test verification failed:\n{e.stderr}")
            self.state.test_success = False

    @listen(verify_build)
    def create_pr(self):
        self._create_pr()

        completed_ids = [x.id for x in self.state.stories or [] if x.completed]
        self._update_planning_checklist(
            self.state.stories or [],
            completed_ids,
            self.state.issue_id,
            pr_url=self.state.pr_url,
        )

    @listen(create_pr)
    def finish(self):
        """Step 8: Update project status and cleanup worktree."""
        self._merge_branch()
        if self.state.pr_url:
            completed_ids = [x.id for x in self.state.stories or [] if x.completed]
            self._update_planning_checklist(
                self.state.stories or [],
                completed_ids,
                self.state.issue_id,
                pr_url=self.state.pr_url,
                merged=True,
            )
        self._cleanup_worktree()


def kickoff(issue: KickoffIssue):
    """
    Run Ralph Loop with externally verified completion criteria.

    Args:
        task: Max 120 character prompt describing the change
        repo: Path to the repository
        branch: Branch name (default: ralph-loop)

    Ralph Loop mechanism:
        - Completion promise: Agent outputs `<promise>COMPLETE</promise>` when completed
        - Stop hook: Router scans output for exact string match (case-sensitive)
        - Objective verification: Agent only outputs promise when criteria are met
          (tests passing, build succeeding, linter clean, etc.)
        - Per-story commits: Each story is committed immediately upon completion
    """
    flow = RalphLoopFlow()
    flow.kickoff(
        inputs=dict(
            id=str(issue.flow_id),
            issue_id=issue.id,
            task=f"{issue.title}\n\n{issue.body}",
            path=f"{project_settings.DATA_PATH}/{issue.repository.owner}/{issue.repository.repository}",
            branch=f"{issue.id}-{sanitize_branch_name(issue.title)}",
            memory_prefix=f"{issue.repository.owner}/{issue.repository.repository}",
            repo_owner=issue.repository.owner,
            repo_name=issue.repository.repository,
            project_config=issue.project_config,
        )
    )


def example():
    repo_owner = "chainsquad"
    repo_name = "chaoscraft"
    issue_id = 17
    task = "Make the dancing robot smaller on desktop screens."
    path = f"/home/xeroc/projects/{repo_owner}/{repo_name}"
    branch = "smaller-robot"
    flow_identifier = f"{repo_owner}/{repo_name}/{issue_id}"
    id = uuid.uuid5(uuid.NAMESPACE_DNS, flow_identifier)
    project_config = ProjectConfig(
        provider="github",
        repo_owner=repo_owner,
        repo_name=repo_name,
        project_identifier="1",
        status_mapping=StatusMapping(),
    )
    # id = "888a8fb6-e86d-457a-a2ea-a8e858b1d3f2"
    flow = RalphLoopFlow()
    flow.kickoff(
        inputs=dict(
            id=str(id),
            issue_id=issue_id,
            task=task,
            path=path,
            branch=branch,
            repo_owner=repo_owner,
            repo_name=repo_name,
            project_config=project_config,
        )
    )


def plot():
    """
    Plot the flow.
    """
    flow = RalphLoopFlow()
    flow.plot()


if __name__ == "__main__":
    example()
