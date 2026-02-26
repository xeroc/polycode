#!/usr/bin/env python
import asyncio
from typing import Any, Dict, List

from crewai.flow.flow import Flow, listen, start

from .types import FeatureDevState, PlanOutput, SetupOutput, ImplementOutput, Story, VerifyOutput, TestOutput, ReviewOutput
from .crews.plan_crew.plan_crew import PlanCrew
from .crews.setup_crew.setup_crew import SetupCrew
from .crews.implement_crew.implement_crew import ImplementCrew
from .crews.verify_crew.verify_crew import VerifyCrew
from .crews.test_crew.test_crew import TestCrew
from .crews.review_crew.review_crew import ReviewCrew


class FeatureDevFlow(Flow[FeatureDevState]):
    """
    Feature development workflow with consecutive flows.
    """

    # model = "gpt-4o-mini"

    @start()
    def plan_task(self):
        """Step 1: Plan - decompose task into user stories."""
        print("Planning feature into user stories")

        inputs = dict(
            task="create a simple html based website with tailwinds (from CDN) that says hello world",
            repo="/home/xeroc/projects/chaoscraft/demo",
            branch="feature/website",
        )
        for k, v in inputs.items():
            setattr(self.state, k, v)

        result = PlanCrew().crew().kickoff(inputs=inputs)
        output: PlanOutput = result.pydantic

        self.state.stories = output.stories

        print(f"Planned {len(output.stories)} stories")
        return output

    @listen(plan_task)
    def setup(self):
        """Step 2: Setup - prepare development environment."""
        print("Setting up development environment")
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

        print(f"Build cmd: {output.build_cmd}")
        print(f"Test cmd: {output.test_cmd}")
        return output

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
        for story in self.state.stories:
            print(f"Title: {story.title}")
            print(f"Description: {story.description}")
            # Schedule each chapter writing task
            task = asyncio.create_task(implement_single_story(self, story))
            tasks.append(task)

        # Await all chapter writing tasks concurrently
        results : List[ImplementOutput] = await asyncio.gather(*tasks)
        self.state.completed_stories.extend(self.state.stories)  # TODO: worthless waiting for them all
        self.state.changes = [x.changes for x in results]
        self.state.tests = [x.tests for x in results]
        return results 

    # @listen(implement_story)
    # def verify(self, implement_result: ImplementOutput):
    #     """Step 4: Verify - quick sanity check of implementation."""
    #     print("Verifying implementation")
    #     output = (
    #         VerifyCrew()
    #         .crew()
    #         .kickoff(
    #             inputs={
    #                 "task": self.state.task,
    #                 "repo": self.state.repo,
    #                 "branch": self.state.branch,
    #                 "changes": self.state.changes,
    #                 "test_cmd": self.state.test_cmd,
    #                 "current_story": self.state.current_story,
    #             }
    #         )
    #     )
    #
    #     verify_result: VerifyOutput = output["pydantic"]
    #     self.state.verified = verify_result.status == "done"
    #
    #     if verify_result.issues:
    #         print(f"Verification issues found: {verify_result.issues}")
    #     else:
    #         print(f"Verification passed: {verify_result.verified}")
    #
    #     return verify_result
    #
    # @listen(verify)
    # def test_integration(self, verify_result: VerifyOutput):
    #     """Step 5: Test - integration and E2E testing."""
    #     print("Running integration tests")
    #     output = (
    #         TestCrew()
    #         .crew()
    #         .kickoff(
    #             inputs={
    #                 "task": self.state.task,
    #                 "repo": self.state.repo,
    #                 "branch": self.state.branch,
    #                 "changes": self.state.changes,
    #                 "build_cmd": self.state.build_cmd,
    #                 "test_cmd": self.state.test_cmd,
    #             }
    #         )
    #     )
    #
    #     test_result: TestOutput = output["pydantic"]
    #     self.state.tested = test_result.status == "done"
    #
    #     if test_result.failures:
    #         print(f"Test failures: {test_result.failures}")
    #     else:
    #         print(f"Tests passed: {test_result.results}")
    #
    #     return test_result
    #
    # @listen(test_integration)
    # def create_pr(self, test_result: TestOutput):
    #     """Step 6: Create pull request."""
    #     print("Creating pull request")
    #
    #     if not self.state.tested or test_result.failures:
    #         print("Skipping PR creation - tests did not pass")
    #         return None
    #
    #     output = (
    #         ImplementCrew()
    #         .crew()
    #         .kickoff(
    #             inputs={
    #                 "task": self.state.task,
    #                 "repo": self.state.repo,
    #                 "branch": self.state.branch,
    #                 "changes": self.state.changes,
    #                 "results": test_result.results,
    #             }
    #         )
    #     )
    #
    #     self.state.pr_url = output.get("pr")
    #     print(f"PR created: {self.state.pr_url}")
    #     return output
    #
    # @listen(create_pr)
    # def review(self, pr_result: Any):
    #     """Step 7: Review - review the pull request."""
    #     print("Reviewing pull request")
    #
    #     if not self.state.pr_url:
    #         print("No PR to review")
    #         return None
    #
    #     output = (
    #         ReviewCrew()
    #         .crew()
    #         .kickoff(
    #             inputs={
    #                 "pr": self.state.pr_url,
    #                 "task": self.state.task,
    #                 "changes": self.state.changes,
    #             }
    #         )
    #     )
    #
    #     review_result: ReviewOutput = output["pydantic"]
    #     self.state.review_status = review_result.decision
    #
    #     if review_result.feedback:
    #         print(f"Review feedback: {review_result.feedback}")
    #     else:
    #         print(f"Review decision: {review_result.decision}")
    #
    #     return review_result


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
