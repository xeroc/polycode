"""
Solcraft Flow - Customizable implementation flow with pluggable task templates.

Flow: Setup → Plan → Implement (with custom tasks) → Push → PR → Finish
"""

import logging
import uuid

from crewai.flow.flow import listen, start
from crewai.flow.persistence import SQLiteFlowPersistence, persist

from flowbase import FlowIssueManagement, KickoffIssue
from gitcore import sanitize_branch_name
from persistence.postgres import PostgresFlowPersistence
from project_manager import StatusMapping
from project_manager.config import settings as project_settings
from project_manager.types import ProjectConfig

from .task_loader import load_task_templates
from .types import ImplementOutput, PlanOutput, SolcraftState, TaskTemplate

logger = logging.getLogger(__name__)

DATABASE_URL = project_settings.DATABASE_URL
if DATABASE_URL and DATABASE_URL.startswith("postgres"):
    logger.info("📊 Connecting persistence with postgres")
    persistence = PostgresFlowPersistence(connection_string=DATABASE_URL)
else:
    persistence = SQLiteFlowPersistence()


@persist(persistence=persistence, verbose=False)
class SolcraftFlow(FlowIssueManagement[SolcraftState]):
    """
    Solcraft Flow with customizable task templates.

    Features:
    - Uses existing PlanCrew for task decomposition
    - Supports custom task templates loaded from markdown files
    - Flexible implementation crew that accepts runtime task configurations

    Task Templates:
    - Load from markdown files with YAML frontmatter
    - Override default implement_crew tasks at runtime
    - Support for multiple task templates per flow
    """

    task_templates: dict[str, TaskTemplate] = {}

    @start()
    def setup(self):
        logger.info("🚀 Solcraft Flow starting...")
        self._setup()
        self.pickup_issue()

        if self.state.task_templates:
            self.task_templates = load_task_templates(self.state.task_templates)
            logger.info(f"📄 Loaded {len(self.task_templates)} task templates")

    @listen(setup)
    def plan(self):
        """Decompose task into user stories using PlanCrew."""
        from crews.plan_crew.plan_crew import PlanCrew

        self.discover_agents_md_files()
        self._discover_build_cmd()

        if self.state.stories:
            return

        logger.info("📝 Planning feature into user stories...")

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

        output: PlanOutput = result.pydantic  # ty:ignore # pyright:ignore
        self.state.stories = output.stories
        self.state.build_cmd = output.build_cmd
        self.state.test_cmd = output.test_cmd
        self.state.baseline = output.baseline
        self.state.findings = output.findings

        if not self.recall_as_markdown_list("architecture"):
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
                self.remember(getattr(output, key), scope=f"{scope}/key")  # ty:ignore
            logger.info(f"🔖 Stored project details to memory at scope: {scope}")

        logger.info(f"🔖 Planned {len(output.stories)} stories")
        for story in output.stories:
            logger.info(f"  |- 🔖 {story.description}")

        # Planning comment is now handled via hooks (PRE/POST_PLANNING_COMMENT)
        self._post_planning_checklist(output.stories, self.state.issue_id)
        return output

    @listen(plan)
    def implement_story(self):
        """Implement user stories with custom task templates."""
        logger.info("🏭 Implementing user stories...")

        for story in self.state.stories or []:
            logger.info(f"  |- 🔖 {story.description}")

        logger.info("Completed Stories:")
        for story in self.state.completed_stories or []:
            logger.info(f"  |- ✅ {story.description}")

        if len(self.state.completed_stories or []) == len(self.state.stories or []):
            return

        completed_ids = [x.id for x in self.state.completed_stories or []]
        missing_stories = [x for x in self.state.stories or [] if x.id not in completed_ids]

        self.state.completed_stories = []
        self.state.changes = []
        self.state.tests = []

        for story in missing_stories or []:
            logger.info(f"  |- Title: {story.title}")
            logger.info(f"  |- Description: {story.description}")

            result = self._implement_single_story(story)

            self.state.completed_stories.append(story)
            self.state.changes.append(result.changes)
            self.state.tests.append(result.tests)

    def _implement_single_story(self, story) -> ImplementOutput:
        """Implement a single story with the configured task templates."""
        from crews.implement_crew.implement_crew import ImplementCrew

        logger.info(f"   |-⏳ user story:  {story.description}")

        output = (
            ImplementCrew()
            .crew(
                agents_md_map=self.agents_md_map,
                custom_tasks=self.task_templates,
            )
            .kickoff(
                inputs=dict(
                    task=self.state.task,
                    repo=self.state.repo,
                    branch=self.state.branch,
                    build_cmd=self.state.build_cmd,
                    test_cmd=self.state.test_cmd,
                    current_story=story.model_dump_json(),
                    completed_stories="\n- ".join([x.description for x in self.state.completed_stories or []]),
                    current_story_id=story.id,
                    current_story_title=story.title,
                    architecture=self.recall_as_markdown_list("architecture"),
                    configuration=self.recall_as_markdown_list("configuration"),
                    tech_stack=self.recall_as_markdown_list("tech_stack"),
                    agents_md=self.root_agents_md,
                )
            )
        )

        implement_result: ImplementOutput = (  # ty:ignore
            output.pydantic  # pyright:ignore
        )

        commit_title = implement_result.title
        commit_message = implement_result.message
        commit_footer = implement_result.footer
        self._commit_changes(commit_title, commit_message, commit_footer)

        return implement_result

    @listen(implement_story)
    def push_repo(self):
        self._push_repo()

    @listen(push_repo)
    def create_pr(self):
        self._create_pr()

    @listen(create_pr)
    def finish(self):
        self._merge_branch()
        self._cleanup_worktree()


def kickoff(
    issue: KickoffIssue,
    task_templates: list[str] | None = None,
):
    """
    Run the Solcraft Flow.

    Args:
        issue: The issue to process
        task_templates: Optional list of paths to task template markdown files.
                       These templates override the default implement_crew tasks.
    """
    flow = SolcraftFlow()
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
            task_templates=task_templates,
        )
    )


def example():
    """Example usage of SolcraftFlow with custom task templates."""
    repo_owner = "chainsquad"
    repo_name = "chaoscraft"
    issue_id = 14
    task = "Add some extra margin to the first headline."
    path = f"/home/xeroc/projects/{repo_owner}/{repo_name}"
    branch = "solcraft-test"
    flow_identifier = f"{repo_owner}/{repo_name}/{issue_id}"
    id = uuid.uuid5(uuid.NAMESPACE_DNS, flow_identifier)

    task_templates = [
        "task_templates/custom_implement.md",
    ]

    flow = SolcraftFlow()
    flow.kickoff(
        inputs=dict(
            id=str(id),
            issue_id=issue_id,
            task=task,
            path=path,
            branch=branch,
            repo_owner=repo_owner,
            repo_name=repo_name,
            project_config=ProjectConfig(
                provider="github",
                repo_owner=repo_owner,
                repo_name=repo_name,
                project_identifier="1",
                status_mapping=StatusMapping(),
            ),
            task_templates=task_templates,
        )
    )


def plot():
    """Plot the flow."""
    flow = SolcraftFlow()
    flow.plot()


if __name__ == "__main__":
    example()
