#!/usr/bin/env python
import asyncio
import os
import uuid
import git
import github

from typing import List
from crewai.flow.flow import Flow, listen, start
from git.exc import InvalidGitRepositoryError, NoSuchPathError

from .utils import get_github_repo_from_local
from .types import (
    CommitMessageOutput,
    FeatureDevState,
    PlanOutput,
    SetupOutput,
    ImplementOutput,
    Story,
    VerifyOutput,
    TestOutput,
    ReviewOutput,
)
from .crews.plan_crew.plan_crew import PlanCrew
from .crews.setup_crew.setup_crew import SetupCrew
from .crews.implement_crew.implement_crew import ImplementCrew
from .crews.verify_crew.verify_crew import VerifyCrew
from .crews.test_crew.test_crew import TestCrew
from .crews.review_crew.review_crew import ReviewCrew
from .db import init_db
from .persistence import save_state_snapshot
from .webhooks import trigger_webhooks


class FeatureDevFlow(Flow[FeatureDevState]):
    """
    Feature development workflow with consecutive flows.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        init_db()
        self._flow_id = str(uuid.uuid4())[:8]

    def _persist_and_notify(self, phase: str):
        state_json = self.state.model_dump_json()
        save_state_snapshot(self._flow_id, phase, state_json)
        trigger_webhooks(phase, self.state.model_dump())

    @start()
    def setup(self):
        print("Setting up development environment")
        self.state.issue_id = 1
        self.state.task = "create a simple html based website with tailwinds (from CDN) that says hello world"
        self.state.repo = "/home/xeroc/projects/chaoscraft/demo"
        self.state.branch = f"{self.state.issue_id}-feature-branch"

        result = (
            SetupCrew()
            .crew()
            .kickoff(
                inputs=dict(
                    task=self.state.task,
                    repo=self.state.repo,
                    branch=self.state.branch,
                )
            )
        )

        output: SetupOutput = result.pydantic

        self.state.build_cmd = output.build_cmd
        self.state.test_cmd = output.test_cmd
        self.state.ci_notes = output.ci_notes
        self.state.baseline = output.baseline
        self.state.findings = output.findings

        print(f"Build cmd: {output.build_cmd}")
        print(f"Test cmd: {output.test_cmd}")
        self._persist_and_notify("setup")
        return output

    @listen(setup)
    def plan_task(self):
        """Step 1: Plan - decompose task into user stories."""
        print("Planning feature into user stories")

        result = (
            PlanCrew()
            .crew()
            .kickoff(
                inputs=dict(
                    task=self.state.task,
                    repo=self.state.repo,
                    branch=self.state.branch,
                )
            )
        )
        output: PlanOutput = result.pydantic

        self.state.stories = output.stories

        print(f"Planned {len(output.stories)} stories")
        return output

    @listen(plan_task)
    def create_branch(self):
        branch_name = self.state.branch
        repo = self.state.repo
        try:
            git_repo = git.Repo(repo)
            git_repo.create_head(branch_name, git_repo.branches["develop"]).checkout()
            print(f"Created and checked out branch: {branch_name}")
        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            raise e

    @listen(setup)
    async def implement_story(self):
        """Step 3: Implement - implement user story."""
        print("Implementing user story")
        tasks = []

        async def implement_single_story(self, current_story: Story):

            output = (
                ImplementCrew()
                .crew()
                .kickoff(
                    inputs={
                        "task": self.state.task,
                        "repo": self.state.repo,
                        "branch": self.state.branch,
                        "build_cmd": self.state.build_cmd,
                        "test_cmd": self.state.test_cmd,
                        "current_story": current_story.model_dump_json(),
                        "completed_stories": self.state.completed_stories,
                        "current_story_id": current_story.id,
                        "current_story_title": current_story.title,
                    }
                )
            )

            implement_result: ImplementOutput = output.pydantic
            return implement_result

        tasks = []
        for story in self.state.stories or []:
            print(f"Title: {story.title}")
            print(f"Description: {story.description}")
            # Schedule each chapter writing task
            task = asyncio.create_task(implement_single_story(self, story))
            tasks.append(task)

        # Await all chapter writing tasks concurrently
        results: List[ImplementOutput] = await asyncio.gather(*tasks)
        self.state.completed_stories = self.state.stories
        self.state.changes = [x.changes for x in results]
        self.state.tests = [x.tests for x in results]
        return results

    @listen(implement_story)
    def test_integration(self):
        """Step 5: Test - integration and E2E testing."""
        print("Running integration tests")
        output = (
            TestCrew()
            .crew()
            .kickoff(
                inputs={
                    "task": self.state.task,
                    "repo": self.state.repo,
                    "branch": self.state.branch,
                    "changes": self.state.changes,
                    "build_cmd": self.state.build_cmd,
                    "test_cmd": self.state.test_cmd,
                }
            )
        )

        test_result: TestOutput = output.pydantic
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
        output = (
            VerifyCrew()
            .crew()
            .kickoff(
                inputs={
                    "task": self.state.task,
                    "repo": self.state.repo,
                    "branch": self.state.branch,
                    "changes": self.state.changes,
                    "test_cmd": self.state.test_cmd,
                    "current_story": self.state.current_story,
                }
            )
        )

        verify_result: VerifyOutput = output.tasks_output[0].pydantic
        self.state.verified = verify_result.status == "done"

        if verify_result.issues:
            print(f"Verification issues found: {verify_result.issues}")
        else:
            print(f"Verification passed: {verify_result.verified}")

        commit_message_result: CommitMessageOutput = output.tasks_output[1].pydantic
        self.state.commit_title = commit_message_result.title
        self.state.commit_message = commit_message_result.message
        self.state.commit_footer = commit_message_result.footer

        return verify_result

    @listen(test_integration)
    def commit_changes(self):
        print("Commiting changes to repo")

        branch_name = self.state.branch_name
        repo = git.Repo(self.state.repo)

        # Ensure we are on branch self.state.branch
        if branch_name in repo.heads:
            branch = repo.heads[branch_name]
        else:
            branch = repo.create_head(branch_name, repo.heads["develop"].commit)  # creates from current HEAD
        branch.checkout()

        # commit all changes to the repo
        repo.git.add("-A")
        commit_message = f"{self.state.commit_title}\n\n{self.state.commit_message}\n\n{self.state.commit_footer}"
        repo.index.commit(commit_message)
        print(f"Committed changes: {commit_message}")

        merge_base = repo.merge_base("develop", self.state.branch)[0]
        self.state.diff = repo.git.diff(merge_base, self.state.branch)

    @listen(commit_changes)
    def create_pr(self):
        """Step 6: Create pull request."""
        print("Creating pull request")

        repo, g = get_github_repo_from_local(self.state.repo)
        pr = g.create_pull(
            title=self.state.commit_title or self.state.task,
            body=f"{self.state.commit_message}\n\n{self.state.commit_footer}",
            head=self.state.branch,
            base="develop",
        )
        # Get diff between two branches
        self.state.diff = repo.git.diff("develop", self.state.branch, patch=True)
        self.state.pr_url = pr.html_url
        self.state.pr_number = pr.number
        print(f"PR {self.state.pr_number} created: {self.state.pr_url}")

        repo = git.Repo(self.state.repo)
        merge_base = repo.merge_base("develop", self.state.branch)[0]
        self.state.diff = repo.git.diff(merge_base, self.state.branch)

    @listen(commit_changes)
    def review(self):
        """Step 7: Review - review the pull request."""
        print("Reviewing pull request")

        if not self.state.diff:
            print("No diff to review")
            return None

        output = (
            ReviewCrew()
            .crew()
            .kickoff(
                inputs={
                    "diff": self.state.diff,
                    "task": self.state.task,
                    "changes": self.state.changes,
                }
            )
        )
        review_result: ReviewOutput = output.pydantic
        self.state.review_status = review_result.decision

        if review_result.feedback:
            print(f"Review feedback: {review_result.feedback}")
        else:
            print(f"Review decision: {review_result.decision}")

        return review_result


def kickoff():
    """
    Run the flow.
    """
    feature_dev_flow = FeatureDevFlow()
    feature_dev_flow.kickoff()


def plot():
    """
    Plot the flow.
    """
    feature_dev_flow = FeatureDevFlow()
    feature_dev_flow.plot()


if __name__ == "__main__":
    kickoff()
