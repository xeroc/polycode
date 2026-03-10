"""

Ralph Loop - Ralph Loop pattern using CrewAI @router for control flow.

Flow: Setup → Plan → Ralph Loop (router-controlled) → Verify → Commit

Ralph Loop mechanism:
  1. Completion Promise: Agent outputs `<promise>COMPLETE</promise>` when objective
     criteria are met (tests passing, build succeeding, linter clean, etc.)
  2. Stop Hook: Router scans agent output for exact completion promise string
  3. Router Routes: Based on presence/absence of completion promise
     - "retry" → implement again (continue Ralph loop, max 3 iterations)
     - "done" → verify_build (completion criteria met or max iterations)
  4. Emergency Brake: Max iterations (3) prevents runaway processes
  5. Agent receives previous_errors context for smarter retries
"""

import os
import subprocess
import uuid
from typing import cast

from crewai.flow.flow import listen, router, start
from crewai.flow.persistence import SQLiteFlowPersistence, persist

from flowbase import FlowIssueManagement, KickoffIssue, sanitize_branch_name
from persistence.postgres import PostgresFlowPersistence

from .crews.plan_crew.plan_crew import PlanCrew
from .crews.ralph_crew.ralph_crew import RalphCrew
from .types import PlanOutput, RalphLoopState, RalphOutput, Story

MAX_ITERATIONS = 3
DATA_PATH = os.environ.get("DATA_PATH", "/data")
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres"):
    print("📊 Connecting persistence with postgres")
    persistence = PostgresFlowPersistence(connection_string=DATABASE_URL)
else:
    persistence = SQLiteFlowPersistence()


@persist(persistence=persistence, verbose=True)
class RalphLoopFlow(FlowIssueManagement[RalphLoopState]):
    """
    Ralph Loop Flow - externally verified completion with completion promise.

    Ralph Loop mechanism:
    - Agent outputs completion promise when objective criteria are met
    - Stop hook scans output for exact string match (case-sensitive)
    - Router routes based on completion promise presence
    - Max iterations safety brake prevents runaway processes
    - Agent receives previous_errors for smarter iteration
    - Runs per-story with individual iteration tracking
    """

    agents_md_map: dict[str, str] = {}
    root_agents_md: str = ""

    def _current_story(self) -> Story | None:
        """Get the current story being processed."""
        if not self.state.stories or self.state.current_story_index >= len(
            self.state.stories
        ):
            return None
        return self.state.stories[self.state.current_story_index]

    def _has_more_stories(self) -> bool:
        """Check if there are more stories after the current one."""
        return (
            self.state.stories is not None
            and self.state.current_story_index + 1 < len(self.state.stories)
        )

    @start()
    def setup(self):
        """Prepare worktree, discover build command and AGENTS.md files."""
        print("🚀 Ralph Loop starting...")
        self._prepare_work_tree()

    @listen(setup)
    def plan(self):
        """Create a single story from the 120-char prompt."""

        self.discover_agents_md_files()
        self._setup()
        self._discover_build_cmd()

        if self.state.stories:
            return

        print("📝 Planning story from prompt...")

        result = (
            PlanCrew()
            .crew(agents_md_map=self.agents_md_map)
            .kickoff(
                inputs=dict(
                    task=self.state.task[:120],
                    repo=self.state.repo,
                    branch=self.state.branch,
                    agents_md=self.root_agents_md,
                )
            )
        )

        output: PlanOutput = result.pydantic  # type: ignore
        self.state.stories = output.stories
        self.state.build_cmd = output.build_cmd
        self.state.test_cmd = output.test_cmd

        print(f"🔖 Planned {len(output.stories)} stories")
        for current_story in output.stories:
            print(f"  |- 🔖 {current_story.description}")

    @listen(plan)
    def start_ralph_loop(self):
        """
        Ralph Loop entry - log start info.
        """
        num_stories = len(self.state.stories) if self.state.stories else 0
        print(
            f"\n🔨 Starting Ralph Loop for {num_stories} stories (max {MAX_ITERATIONS} iterations each)"
        )

    @listen(start_ralph_loop)
    def implement(self):
        """
        Single iteration of Ralph Loop for current story.

        Agent is instructed to output completion promise ONLY when:
        - All objective criteria are met (tests pass, build succeeds, etc.)
        - Not based on subjective judgment
        """
        story = self._current_story()
        if not story:
            return

        story.iteration += 1
        print(
            f"\n📖 Story {self.state.current_story_index + 1}/{len(self.state.stories or [])}: {story.title}"
        )
        print(f"🔨 Iteration {story.iteration}/{MAX_ITERATIONS}")

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
                    iteration=story.iteration,
                    max_iterations=MAX_ITERATIONS,
                    previous_errors=error_context,
                )
            )
        )

        output = cast(RalphOutput, result.pydantic)  # type: ignore
        self.state.agent_output = output.changes
        self.state.commit_title = output.title
        self.state.commit_message = output.message
        self.state.commit_footer = output.footer

        return output.status

    @router(implement)
    def check_completion_promise(self, status):
        """
        Ralph Loop Router: determines next action based on completion promise.

        Routes:
        - "retry" → implement (continue Ralph loop for current story)
        - "next_story" → implement (move to next story, current passed)
        - "done" → verify_build (all stories complete or max iterations)
        """
        story = self._current_story()
        if not story:
            return "done"

        try:
            self._test()
        except Exception as e:
            story.errors.append(str(e))
            return "retry"

        agent_output = self.state.agent_output or ""

        if status == "done":
            print("✅ Completion")
            print(
                f"Story '{story.title}' complete - objective criteria verified"
            )
            story.completed = True
            story.errors = []

            if self._has_more_stories():
                self.state.current_story_index += 1
                print("➡️ Moving to next story...")
                return "next_story"

            return status

        if story.iteration >= MAX_ITERATIONS:
            print(
                f"⚠️ Max iterations ({MAX_ITERATIONS}) reached for story '{story.title}'"
            )
            story.completed = True
            print("Proceeding with current state (safety brake engaged)")

            if self._has_more_stories():
                self.state.current_story_index += 1
                print("➡️ Moving to next story...")
                return "next_story"
            return "done"

        print("Completion promise not found, retrying...")
        story.errors.append(
            f"Iteration {story.iteration}: {agent_output[:200]}..."
        )
        print(f"🔄 Routing to: implement (iteration {story.iteration + 1})")
        return "retry"

    @listen("retry")
    def implement_retry(self):
        """Retry implementation - called by router for "retry" route."""
        return self.implement()  # pyright:ignore

    @listen("next_story")
    def implement_next_story(self):
        """Start implementing next story."""
        return self.implement()  # pyright:ignore

    @listen("done")
    def verify_build(self):
        """Final verification that build passes."""
        print(f"\n🔍 Final build verification: {self.state.build_cmd}")
        self.state.build_success = True
        try:
            self._build()
        except subprocess.TimeoutExpired:
            print("⏱️ Build timed out after 180 seconds")
            self.state.build_success = False
        except subprocess.CalledProcessError as e:
            print(f"❌ Build verification failed:\n{e.stderr}")
            self.state.build_success = False

        self.state.test_success = True
        try:
            self._test()
        except subprocess.TimeoutExpired:
            print("⏱️ Test timed out after 180 seconds")
            self.state.test_success = False
        except subprocess.CalledProcessError as e:
            print(f"❌ Test verification failed:\n{e.stderr}")
            self.state.test_success = False

    @listen(verify_build)
    def commit(self):
        """Commit changes with conventional commit message from agent."""
        print("\n💾 Committing changes...")

        self._commit_changes(
            title=self.state.commit_title or "chore: ralph loop changes",
            body=self.state.commit_message or "",
            footer=self.state.commit_footer or "",
        )

        print(f"✅ Committed: {self.state.commit_title}")

    @listen(commit)
    def push_repo(self):
        self._push_repo()

    @listen(push_repo)
    def create_pr(self):
        self._create_pr()

    @listen(create_pr)
    def finish(self):
        """Step 8: Update project status and cleanup worktree."""
        self._merge_branch()
        self._cleanup_worktree()


def kickoff(issue: KickoffIssue):
    """
    Run Ralph Loop with externally verified completion criteria.

    Args:
        task: Max 120 character prompt describing the change
        repo: Path to the repository
        branch: Branch name (default: ralph-loop)

    Ralph Loop mechanism:
        - Completion promise: Agent outputs `<promise>COMPLETE</promise>` when done
        - Stop hook: Router scans output for exact string match (case-sensitive)
        - Objective verification: Agent only outputs promise when criteria are met
          (tests passing, build succeeding, linter clean, etc.)
        - Emergency brake: Max iterations (3) prevents runaway processes
        - Router: "retry" → continue loop, "done" → verify and commit
    """
    flow = RalphLoopFlow()
    flow.kickoff(
        inputs=dict(
            id=str(issue.flow_id),
            issue_id=issue.id,
            task=f"{issue.title}\n\n{issue.body}",
            path=f"{DATA_PATH}/{issue.repository.owner}/{issue.repository.repository}",
            branch=f"{issue.id}-{sanitize_branch_name(issue.title)}",
            memory_prefix=f"{issue.repository.owner}/{issue.repository.repository}",
            repo_owner=issue.repository.owner,
            repo_name=issue.repository.repository,
            max_iterations=MAX_ITERATIONS,
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
        )
    )


if __name__ == "__main__":
    example()
