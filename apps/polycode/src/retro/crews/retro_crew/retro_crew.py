"""Retro Crew - CrewAI crew for generating structured retrospectives."""

import logging
from typing import TYPE_CHECKING

from crewai import Agent, Crew, Process, Task
from crewai.project import agent, crew, task

from crews import PolycodeCrewMixin
from retro.types import RetroEntry

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


class RetroCrew(PolycodeCrewMixin):
    """CrewAI crew for retrospective analysis and generation."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def retro_analyst(self) -> Agent:
        """Retro analyst agent."""
        return Agent(  # ty:ignore
            config=self.agents_config["retro_analyst"],  # pyright:ignore # ty:ignore
            verbose=False,
        )

    @task
    def analyze_execution(self) -> Task:
        """Analyze flow execution data."""
        config = self.tasks_config["analyze_execution"]  # pyright:ignore # ty:ignore
        return Task(  # pyright:ignore # ty:ignore
            config=config,
        )

    @task
    def generate_improvements(self) -> Task:
        """Generate actionable improvements."""
        config = self.tasks_config["generate_improvements"]  # pyright:ignore # ty:ignore
        return Task(  # ty:ignore
            config=config,
            context=[self.analyze_execution()],  # pyright:ignore
        )

    @task
    def finalize_retro(self) -> Task:
        """Finalize structured retro."""
        config = self.tasks_config["finalize_retro"]  # pyright:ignore # ty:ignore
        return Task(  # ty:ignore # pyright:ignore
            config=config,
            context=[self.generate_improvements()],  # pyright:ignore
            output_pydantic=RetroEntry,
        )

    @crew
    def crew(self) -> Crew:
        """Creates Retrospective Crew."""
        return Crew(  # pyright:ignore
            agents=self.agents,  # pyright:ignore # ty:ignore
            tasks=self.tasks,  # pyright:ignore # ty:ignore
            process=Process.sequential,
            verbose=False,
        )
