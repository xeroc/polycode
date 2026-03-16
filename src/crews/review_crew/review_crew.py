from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from glm import GLMJSONLLM

from .types import ReviewOutput


@CrewBase
class ReviewCrew:
    """Review Crew - Review pull requests."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["reviewer"],  # type: ignore
            verbose=False,
            llm=GLMJSONLLM(),
        )

    @task
    def review_task(self) -> Task:
        return Task(
            config=self.tasks_config["review_task"],  # pyright:ignore
            output_pydantic=ReviewOutput,  # type: ignore
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # type: ignore
            tasks=self.tasks,  # type: ignore
            process=Process.sequential,
            verbose=False,
        )
