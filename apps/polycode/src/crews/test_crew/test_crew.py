from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from crews.base import PolycodeCrewMixin
from glm import GLMJSONLLM
from tools import DirectoryReadTool, ExecTool, FileReadTool

from .types import TestOutput


@CrewBase
class TestCrew(PolycodeCrewMixin):
    """Test Crew - Integration and E2E testing."""

    crew_label = "test"
    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def tester(self) -> Agent:
        return Agent(  # ty:ignore
            config=self.agents_config["tester"],  # type: ignore
            tools=[ExecTool(), DirectoryReadTool(), FileReadTool()],
            verbose=False,
            llm=GLMJSONLLM(),
            allow_code_execution=False,
        )

    @task
    def test_task(self) -> Task:
        return Task(  # ty:ignore
            config=self.tasks_config["test_task"],  # type: ignore
            output_pydantic=TestOutput,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
        )
