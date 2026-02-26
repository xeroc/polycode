"""
Feature Development Crew - Implements features through user stories.

This crew handles the feature development workflow from antfarm:
- Planner: Decomposes tasks into ordered user stories
- Setup: Prepares environment and creates branch
- Developer: Implements each story with tests
- Verifier: Quick sanity check of developer work
- Tester: Integration and E2E testing
- Reviewer: Reviews PRs and provides feedback
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from typing import List


@CrewBase
class FeatureDevCrew:
    """Feature Development Crew - Implements features through user stories."""

    agents: List[Agent]
    tasks: List[Task]

    @agent
    def planner(self) -> Agent:
        """Decomposes tasks into ordered user stories."""
        return Agent(
            config=self.agents_config['planner'],
            verbose=True,
            tools=[],
            allow_delegation=False,
        )

    @agent
    def setup(self) -> Agent:
        """Prepares environment, creates branch, establishes baseline."""
        return Agent(
            config=self.agents_config['setup'],
            verbose=True,
            tools=[],
            allow_delegation=False,
        )

    @agent
    def developer(self) -> Agent:
        """Implements features, writes tests, creates PRs."""
        return Agent(
            config=self.agents_config['developer'],
            verbose=True,
            tools=[],
            allow_delegation=False,
        )

    @agent
    def verifier(self) -> Agent:
        """Quick sanity check - did developer actually do the work?"""
        return Agent(
            config=self.agents_config['verifier'],
            verbose=True,
            tools=[],
            allow_delegation=False,
        )

    @agent
    def tester(self) -> Agent:
        """Integration and E2E testing after all stories are implemented."""
        return Agent(
            config=self.agents_config['tester'],
            verbose=True,
            tools=[],
            allow_delegation=False,
        )

    @agent
    def reviewer(self) -> Agent:
        """Reviews PRs, requests changes or approves."""
        return Agent(
            config=self.agents_config['reviewer'],
            verbose=True,
            tools=[],
            allow_delegation=False,
        )

    @task
    def plan_task(self) -> Task:
        """Decompose the task into ordered user stories."""
        return Task(
            config=self.tasks_config['plan_task'],
        )

    @task
    def setup_task(self) -> Task:
        """Prepare the development environment."""
        return Task(
            config=self.tasks_config['setup_task'],
            context=[self.plan_task()],
        )

    @task
    def implement_task(self) -> Task:
        """Implement the first user story (simplified - would loop over all stories)."""
        return Task(
            config=self.tasks_config['implement_task'],
            context=[self.plan_task(), self.setup_task()],
        )

    @task
    def verify_task(self) -> Task:
        """Verify the developer's work."""
        return Task(
            config=self.tasks_config['verify_task'],
            context=[self.implement_task()],
        )

    @task
    def test_task(self) -> Task:
        """Integration and E2E testing."""
        return Task(
            config=self.tasks_config['test_task'],
            context=[self.verify_task()],
        )

    @task
    def pr_task(self) -> Task:
        """Create a pull request."""
        return Task(
            config=self.tasks_config['pr_task'],
            context=[self.test_task()],
        )

    @task
    def review_task(self) -> Task:
        """Review the pull request."""
        return Task(
            config=self.tasks_config['review_task'],
            context=[self.pr_task()],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Feature Development crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
