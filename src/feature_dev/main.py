#!/usr/bin/env python
import asyncio
import os
import uuid
from typing import List

from crewai.project import after_kickoff, before_kickoff
import git
from crewai.flow.flow import Flow, listen, start
from git.exc import InvalidGitRepositoryError, NoSuchPathError

from .crews.implement_crew.implement_crew import ImplementCrew
from .crews.plan_crew.plan_crew import PlanCrew
from .crews.review_crew.review_crew import ReviewCrew
from .crews.setup_crew.setup_crew import SetupCrew
from .crews.test_crew.test_crew import TestCrew
from .crews.verify_crew.verify_crew import VerifyCrew
from crewai.flow.persistence import persist
from .types import (
    CommitMessageOutput,
    FeatureDevState,
    ImplementOutput,
    PlanOutput,
    ReviewOutput,
    SetupOutput,
    Story,
    TestOutput,
    VerifyOutput,
)
from .utils import get_github_repo_from_local


@persist(verbose=True)
class FeatureDevFlow(Flow[FeatureDevState]):
    """
    Feature development workflow with consecutive flows.
    """

    @start()
    def prepare_work_tree(self):
        branch_name = self.state.branch
        root_repo = self.state.path
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

    @start()
    def setup(self):
        print("Setting up development environment")

        if self.state.findings and self.state.baseline:
            return

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
        return output

    @listen(setup)
    def plan_task(self):
        """Step 1: Plan - decompose task into user stories."""
        print("Planning feature into user stories")

        if self.state.stories:
            return

        result = (
            PlanCrew()
            .crew()
            .kickoff(
                inputs=dict(
                    task=self.state.task,
                    repo=self.state.repo,
                    branch=self.state.branch,
                    baseline=self.state.baseline,
                    findings=self.state.findings,
                )
            )
        )
        output: PlanOutput = result.pydantic

        self.state.stories = output.stories

        print(f"Planned {len(output.stories)} stories")
        return output

    @listen(setup)
    def implement_story(self):
        """Step 3: Implement - implement user story."""
        print("Implementing user story")
        tasks = []

        if len(self.state.completed_stories) == len(self.state.stories):
            return

        def implement_single_story(current_story: Story):
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

        # FIXME: need a more robust way of comparing completed with missing!
        missing_stories = [
            x
            for x in self.state.stories or []
            if self.state.completed_stories and x not in self.state.completed_stories
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
    def test_integration(self):
        """Step 5: Test - integration and E2E testing."""
        print("Running integration tests")
        if self.state.tested:
            return

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
        if self.state.verified:
            return

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
                    "completed_stories": [
                        x.description for x in self.state.completed_stories or []
                    ],
                }
            )
        )

        print(output)
        print(output.tasks_output)
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
        print(f"Commit title: {self.state.commit_title}")
        print(f"Commit message: {self.state.commit_message}")
        print(f"Commit footer: {self.state.commit_footer}")

        return verify_result

    @listen(verify)
    def commit_changes(self):
        print("Commiting changes to repo")

        if self.state.diff:
            return

        repo = git.Repo(self.state.repo)

        # Ensure we are on branch self.state.branch
        branch_name = repo.active_branch.name
        if branch_name != self.state.branch:
            raise ValueError(
                f"Wrong branch in the working directory ({self.state.repo}). Current branch '{branch_name}'. Excected '{self.state.branch}'"
            )

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
        if self.state.pr_number:
            return

        repo, github_repo, _ = get_github_repo_from_local(self.state.repo)

        # Push
        repo.git.push("origin", self.state.branch)

        # PR
        pr = github_repo.create_pull(
            title=self.state.commit_title or self.state.task,
            body=f"{self.state.commit_message}\n\n{self.state.commit_footer}",
            head=self.state.branch,
            base="develop",
        )

        # Get diff between two branches
        self.state.pr_url = pr.html_url
        self.state.pr_number = pr.number
        print(f"PR {self.state.pr_number} created: {self.state.pr_url}")

    @listen(commit_changes)
    def review(self):
        """Step 7: Review - review the pull request."""
        print("Reviewing pull request")
        if self.state.review_status:
            return

        if not self.state.diff:
            print("No diff to review")
            return None

        output = (
            ReviewCrew()
            .crew()
            .kickoff(
                inputs={
                    "task": self.state.task,
                    "diff": str(self.state.diff),
                    "changes": str(self.state.changes),
                }
            )
        )
        print("Output: ")
        print(output)
        print("=" * 80)
        review_result: ReviewOutput = output.pydantic
        self.state.review_status = review_result.decision

        if review_result.feedback:
            print(f"Review feedback: {review_result.feedback}")
        else:
            print(f"Review decision: {review_result.decision}")

        return review_result

    @listen(review)
    def delete_repo(self):
        git_repo = git.Repo(self.state.repo)
        git_repo.git.worktree("remove", self.state.repo)
        print(f"Removed worktree: {self.state.repo}")

        parent_dir = os.path.dirname(self.state.repo)
        if os.path.exists(parent_dir):
            os.rmdir(parent_dir)
        print(f"Cleaned up worktree parent directory")


def kickoff():
    """
    Run the flow.
    """
    feature_dev_flow = FeatureDevFlow()
    issue_id = 4
    feature_dev_flow.kickoff(
        inputs=dict(
            id=str(uuid.UUID("f7491704-26da-4735-9073-3fd7ad3c2807")),
            issue_id=issue_id,
            task="create a simple html based website with tailwinds (from CDN) that says hello world",
            path="/home/xeroc/projects/chaoscraft/demo",
            branch=f"{issue_id}-feature-branch",
        )
    )


def plot():
    """
    Plot the flow.
    """
    feature_dev_flow = FeatureDevFlow()
    feature_dev_flow.plot()


if __name__ == "__main__":
    kickoff()
