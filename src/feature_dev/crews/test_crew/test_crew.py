from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from feature_dev.types import TestOutput
from glm import GLMJSONLLM
from tools import DirectoryReadTool, ExecTool, FileReadTool


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
            config=self.tasks_config["test_task"], output_pydantic=TestOutput  # type: ignore
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # type: ignore
            tasks=self.tasks,  # type: ignore
            process=Process.sequential,
            verbose=False,
        )
