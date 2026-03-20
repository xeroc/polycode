from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from crews.base import PolycodeCrewMixin
from glm import GLMJSONLLM

from .types import ReviewOutput


@CrewBase
class ReviewCrew(PolycodeCrewMixin):
    """Review Crew - Review pull requests."""

    crew_label = "review"
    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def reviewer(self) -> Agent:
        return Agent(  # ty:ignore
            config=self.agents_config["reviewer"],  # type: ignore
            verbose=False,
            llm=GLMJSONLLM(),
        )

    @task
    def review_task(self) -> Task:
        return Task(  # ty:ignore
            config=self.tasks_config["review_task"],  # type: ignore
            output_pydantic=ReviewOutput,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
        )
