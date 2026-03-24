import logging
import subprocess
import uuid
from typing import cast

from crewai.flow.flow import listen, start
from crewai.flow.persistence import persist

from crews import PlanCrew, RalphCrew
from crews.plan_crew.types import PlanOutput
from crews.ralph_crew.types import RalphOutput
from flows.base import FlowIssueManagement, KickoffIssue
from gitcore import sanitize_branch_name
from modules.hooks import FlowEvent
from persistence.postgres import persistence
from project_manager import StatusMapping
from project_manager.config import settings as project_settings
from project_manager.types import ProjectConfig

from .types import RalphLoopState

logger = logging.getLogger(__name__)


@persist(persistence=persistence, verbose=False)
class RalphLoopFlow(FlowIssueManagement[RalphLoopState]):
    """Ralph Loop Flow - simplified event-driven architecture.

    Delegates git operations, PR management, and checklist updates to plugin hooks.
    Flow focuses on orchestration and crew execution.
    """

    @start()
    def setup(self):
        """Initialize flow and emit FLOW_STARTED event."""
        logger.info("🚀 Ralph Loop starting...")
        self._emit(FlowEvent.FLOW_STARTED, label="ralph")
        self._setup()

    @listen(setup)
    def plan(self):
        """Create stories from the prompt.

        PlanCrew emits CREW_FINISHED event via PolycodeCrewMixin @after_kickoff.
        """
        if self.state.stories:
            return

        logger.info("📝 Planning stories from prompt...")

        result = (
            PlanCrew()
            .crew(agents_md_map=self._agents_md_map)
            .kickoff(
                inputs=dict(
                    task=self.state.task[:120],
                    repo=self.state.repo,
                    branch=self.state.branch,
                    agents_md=self._root_agents_md,
                    file_in_repos=self.git_operations.list_tree(),
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

        num_stories = len(self.state.stories) if self.state.stories else 0

        self._emit(FlowEvent.STORIES_PLANNED)
        logger.info(f"\n🔨 Starting implementation for {num_stories} stories")

    @listen(plan)
    def implement(self):
        """Implement each story and emit STORY_COMPLETED events.

        RalphCrew emits CREW_FINISHED event via PolycodeCrewMixin @after_kickoff.
        STORY_COMPLETED event triggers:
          - gitcore hook: commit + push
          - project_manager hook: update checklist item
        """
        unfinished_stories = list(filter(lambda story: not story.completed, self.state.stories or []))

        logger.info(f"Unfinished stories: {len(unfinished_stories)}")
        for story in unfinished_stories:
            logger.info(f"\n📖 Story: {story.title}")

            error_context = (
                "\n\n## Previous Errors:\n" + "\n".join(f"- {err}" for err in story.errors)
                if story.errors
                else "No previous errors"
            )

            result = (
                RalphCrew()
                .crew(agents_md_map=self._agents_md_map)
                .kickoff(
                    inputs=dict(
                        task=self.state.task[:120],
                        story=story.model_dump_json(),
                        repo=self.state.repo,
                        branch=self.state.branch,
                        test_cmd=self.state.test_cmd,
                        build_cmd=self.state.build_cmd,
                        agents_md=self._root_agents_md,
                        previous_errors=error_context,
                    )
                )
            )

            output = cast(RalphOutput, result.pydantic)  # type: ignore
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

            logger.info(f"✅ Story '{story.title}' complete")
            story.completed = True
            story.errors = []

            self._emit(FlowEvent.STORY_COMPLETED, result=story, label=str(story.id))

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

        logger.info("🏁 Flow finished - emitting FLOW_FINISHED event")
        self._emit(FlowEvent.FLOW_FINISHED, label="ralph")
        self._emit(FlowEvent.CLEANUP)


def kickoff(issue: KickoffIssue):
    """Run Ralph Loop with event-driven architecture.

    Args:
        issue: Issue details including title, body, repository info

    Events emitted:
        - FLOW_STARTED: At flow start
        - CREW_FINISHED: After each crew (plan, implement)
        - STORY_COMPLETED: After each story implementation
        - FLOW_FINISHED: After final verification
    """
    flow = RalphLoopFlow()
    inputs = dict(
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
    flow.kickoff(inputs=inputs)


def example():
    from cli.utils import setup_logging

    setup_logging("INFO")

    repo_owner = "chainsquad"
    repo_name = "chaoscraft"
    issue_id = 19
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
    """Plot the flow."""
    flow = RalphLoopFlow()
    flow.plot()
