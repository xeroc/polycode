"""
Bug Fix Crew - Triages, investigates, and fixes bugs.

This crew handles the bug fix workflow from antfarm:
- Triager: Analyzes bug reports and classifies severity
- Investigator: Traces root cause
- Setup: Creates bugfix branch and establishes baseline
- Fixer: Implements the fix with regression tests
- Verifier: Confirms correctness
- PR Creator: Creates pull request
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from typing import List


@CrewBase
class BugFixCrew:
    """Bug Fix Crew - Triages, investigates, and fixes bugs."""

    agents: List[Agent]
    tasks: List[Task]

    @agent
    def triager(self) -> Agent:
        """Analyzes bug reports, reproduces issues, classifies severity."""
        return Agent(
            config=self.agents_config["triager"],
            verbose=True,
            tools=[],
            allow_delegation=False,
        )

    @agent
    def investigator(self) -> Agent:
        """Traces bugs to root cause and proposes fix approach."""
        return Agent(
            config=self.agents_config["investigator"],
            verbose=True,
            tools=[],
            allow_delegation=False,
        )

    @agent
    def setup(self) -> Agent:
        """Creates bugfix branch and establishes baseline."""
        return Agent(
            config=self.agents_config["setup"],
            verbose=True,
            tools=[],
            allow_delegation=False,
        )

    @agent
    def fixer(self) -> Agent:
        """Implements the fix and writes regression tests."""
        return Agent(
            config=self.agents_config["fixer"],
            verbose=True,
            tools=[],
            allow_delegation=False,
        )

    @agent
    def verifier(self) -> Agent:
        """Verifies the fix and regression test correctness."""
        return Agent(
            config=self.agents_config["verifier"],
            verbose=True,
            tools=[],
            allow_delegation=False,
        )

    @agent
    def pr_creator(self) -> Agent:
        """Creates a pull request with bug fix details."""
        return Agent(
            config=self.agents_config["pr_creator"],
            verbose=True,
            tools=[],
            allow_delegation=False,
        )

    @task
    def triage_task(self) -> Task:
        """Triage the bug report - analyze, reproduce, classify severity."""
        return Task(
            config=self.tasks_config["triage_task"],
        )

    @task
    def investigate_task(self) -> Task:
        """Investigate the root cause of the bug."""
        return Task(
            config=self.tasks_config["investigate_task"],
            context=[self.triage_task()],
        )

    @task
    def setup_task(self) -> Task:
        """Prepare environment and create bugfix branch."""
        return Task(
            config=self.tasks_config["setup_task"],
            context=[self.triage_task()],
        )

    @task
    def fix_task(self) -> Task:
        """Implement the bug fix with regression test."""
        return Task(
            config=self.tasks_config["fix_task"],
            context=[self.investigate_task(), self.setup_task()],
        )

    @task
    def verify_task(self) -> Task:
        """Verify the fix is correct and complete."""
        return Task(
            config=self.tasks_config["verify_task"],
            context=[self.fix_task()],
        )

    @task
    def pr_task(self) -> Task:
        """Create a pull request for the bug fix."""
        return Task(
            config=self.tasks_config["pr_task"],
            context=[self.verify_task()],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Bug Fix crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
