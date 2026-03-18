"""
Feature Development Flow module.
"""

import uuid

import git
from crewai import CrewOutput
from crewai.flow.flow import listen, start
from crewai.flow.persistence import persist
from crewai.flow.persistence.sqlite import SQLiteFlowPersistence

from crews import (
    ImplementCrew,
    PlanCrew,
    ReviewCrew,
    TestCrew,
    VerifyCrew,
)
from crews.implement_crew.types import ImplementOutput
from crews.plan_crew.types import PlanOutput, Story
from crews.review_crew.types import ReviewOutput
from crews.test_crew.types import TestOutput
from crews.verify_crew.types import VerifyOutput
from flowbase import FlowIssueManagement, KickoffIssue, sanitize_branch_name
from persistence import PostgresFlowPersistence
from project_manager import StatusMapping
from project_manager.config import settings as project_settings
from project_manager.types import ProjectConfig

from .types import FeatureDevState

DATABASE_URL = project_settings.DATABASE_URL
if DATABASE_URL and DATABASE_URL.startswith("postgres"):
    print("📊 Connecting persistence with postgres")
    persistence = PostgresFlowPersistence(connection_string=DATABASE_URL)
else:
    persistence = SQLiteFlowPersistence()


@persist(persistence=persistence, verbose=False)
class FeatureDevFlow(FlowIssueManagement[FeatureDevState]):
    """
    Feature development workflow with consecutive flows.
    """

    @start()
    def setup(self):
        """Step 1: Plan - decompose task into user stories."""
        print("📑 Planning feature into user stories")

        # Discover AGENTS.md files
        self.discover_agents_md_files()
        self._setup()

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
                self.remember(getattr(output, key), scope=f"{scope}/key")
            print(f"🔖 Stored project details to memory at scope: {scope}")

        print(f"🔖 Planned {len(output.stories)} stories")
        for current_story in output.stories:
            print(f"  |- 🔖 {current_story.description}")

        self.state.planning_comment_id = self._post_planning_checklist(output.stories, self.state.issue_id)
        return output

    @listen(setup)
    def implement_story(self):
        """Step 3: Implement - implement user story."""
        print("🏭 Implementing user story")
        for current_story in self.state.stories or []:
            print(f"  |- 🔖 {current_story.description}")

        print("Completed Stories:")
        for current_story in self.state.completed_stories or []:
            print(f"  |- ✅ {current_story.description}")

        if len(self.state.completed_stories or []) == len(self.state.stories or []):
            return

        def implement_single_story(current_story: Story):
            print(f"   |-⏳ user story:  {current_story.description}")

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
                        completed_stories="\n- ".join([x.description for x in self.state.completed_stories or []]),
                        current_story_id=current_story.id,
                        current_story_title=current_story.title,
                        architecture=self.recall_as_markdown_list("architecture"),
                        configuration=self.recall_as_markdown_list("configuration"),
                        tech_stack=self.recall_as_markdown_list("tech_stack"),
                        agents_md=self.root_agents_md,
                    )
                )
            )

            implement_result: ImplementOutput = output.pydantic  # type: ignore  # or cast

            commit_title = implement_result.title
            commit_message = implement_result.message
            commit_footer = implement_result.footer
            commit = self._commit_changes(commit_title, commit_message, commit_footer)

            if commit:
                commit_url = self._get_commit_url(commit.hexsha)
                self.state.commit_urls[current_story.id] = commit_url

            return implement_result

        completed_ids = [x.id for x in self.state.completed_stories or []]
        missing_stories = [x for x in self.state.stories or [] if x.id not in completed_ids]

        self.state.completed_stories = []
        self.state.changes = []
        self.state.tests = []

        for story in missing_stories or []:
            print(f"  |- Title: {story.title}")
            print(f"  |- Description: {story.description}")
            result = implement_single_story(story)
            self.state.completed_stories.append(story)
            self.state.changes.append(result.changes)
            self.state.tests.append(result.tests)

            self._push_repo()

            completed_ids = [x.id for x in self.state.completed_stories or []]
            self._update_planning_checklist(
                self.state.stories or [],
                completed_ids,
                self.state.issue_id,
            )

    @listen(implement_story)
    def create_pr(self):
        self._create_pr()
        completed_ids = [x.id for x in self.state.completed_stories or []]
        self._update_planning_checklist(
            self.state.stories or [],
            completed_ids,
            self.state.issue_id,
            pr_url=self.state.pr_url,
        )

    @listen(implement_story)
    def test_integration(self):
        """Step 5: Test - integration and E2E testing."""
        print("🏃 Running integration tests")

        # dsiable for now
        return

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
            print(f"🚨 Test failures: {test_result.failures}")
        else:
            print(f"✅ Tests passed: {test_result.results}")

        return test_result

    @listen(test_integration)
    def verify(self):
        """Step 4: Verify - quick sanity check of implementation."""
        print("🏁 Verifying implementation")

        # dsiable for now
        return

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
                    completed_stories=[x.description for x in self.state.completed_stories or []],
                )
            )
        )

        verify_result: VerifyOutput = output.tasks_output[0].pydantic  # type: ignore  # or cast
        self.state.verified = verify_result.status == "done"

        if verify_result.issues:
            print(f"🚨 Verification issues found: {verify_result.issues}")
        else:
            print(f"✅ Verification passed: {verify_result.verified}")

        return verify_result

    @listen(create_pr)
    def review(self):
        """Step 7: Review - review the pull request."""
        print("🔍 Reviewing pull request")
        if self.state.review_status:
            return

        repo = git.Repo(self.state.repo)
        merge_base = repo.merge_base("develop", self.state.branch)[0]
        self.state.diff = repo.git.diff(merge_base, self.state.branch)

        try:
            self._project_manager.update_issue_status(self.state.issue_id, "In review")
        except Exception as e:
            print(f"🚨 Failed to update project status: {e}")

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
            print(f"🫡 Review feedback: {review_result.feedback}")
        else:
            print(f"✅ Review decision: {review_result.decision}")

        return review_result

    @listen(review)
    def finish(self):
        """Step 8: Update project status and cleanup worktree."""
        self._merge_branch()
        if self.state.pr_url:
            completed_ids = [x.id for x in self.state.completed_stories or []]
            self._update_planning_checklist(
                self.state.stories or [],
                completed_ids,
                self.state.issue_id,
                pr_url=self.state.pr_url,
                merged=True,
            )
        self._cleanup_worktree()


############################
# Global variables
############################


def kickoff(issue: KickoffIssue):
    """
    Run the flow.
    """
    feature_dev_flow = FeatureDevFlow()
    feature_dev_flow.kickoff(
        inputs=dict(
            id=str(issue.flow_id),
            issue_id=issue.id,
            task=f"{issue.title}\n\n{issue.body}",
            path=f"{project_settings.DATA_PATH}/{issue.repository.owner}/{issue.repository.repository}",
            branch=f"{issue.id}-{sanitize_branch_name(issue.title)}",
            memory_prefix=f"{issue.repository.owner}/{issue.repository.repository}",
            repo_owner=issue.repository.owner,
            repo_name=issue.repository.repository,
            project_config=ProjectConfig(
                provider="github",
                repo_owner=issue.repository.owner,
                repo_name=issue.repository.repository,
                project_identifier="1",
                status_mapping=StatusMapping(),
            ),
        )
    )


def plot():
    """
    Plot the flow.
    """
    feature_dev_flow = FeatureDevFlow()
    feature_dev_flow.plot()


def example():
    repo_owner = "chainsquad"
    repo_name = "chaoscraft"
    issue_id = 14
    task = "Add some extra margin to the first headline. Replace headline by 'Welcome to ChaosCraft'."
    path = f"/home/xeroc/projects/{repo_owner}/{repo_name}"
    branch = "welcome"
    flow_identifier = f"{repo_owner}/{repo_name}/{issue_id}"
    id = uuid.uuid5(uuid.NAMESPACE_DNS, flow_identifier)
    # id = "888a8fb6-e86d-457a-a2ea-a8e858b1d3f2"
    feature_dev_flow = FeatureDevFlow()
    feature_dev_flow.kickoff(
        inputs=dict(
            id=str(id),
            issue_id=issue_id,
            task=task,
            path=path,
            branch=branch,
            repo_owner=repo_owner,
            repo_name=repo_name,
        )
    )


if __name__ == "__main__":
    print("🚨 Cannot run manually, requires issue data!")
