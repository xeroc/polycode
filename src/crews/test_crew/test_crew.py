from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from glm import GLMJSONLLM
from tools import DirectoryReadTool, ExecTool, FileReadTool

from .types import TestOutput


@CrewBase
class TestCrew:
    """Test Crew - Integration and E2E testing."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def tester(self) -> Agent:
        return Agent(
            config=self.agents_config["tester"],  # type: ignore
            tools=[ExecTool(), DirectoryReadTool(), FileReadTool()],
            verbose=False,
            llm=GLMJSONLLM(),
            allow_code_execution=False,
        )

    @task
    def test_task(self) -> Task:
        return Task(
            config=self.tasks_config["test_task"],  # pyright:ignore
            output_pydantic=TestOutput,  # type: ignore
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # type: ignore
            tasks=self.tasks,  # type: ignore
            process=Process.sequential,
            verbose=False,
        )
