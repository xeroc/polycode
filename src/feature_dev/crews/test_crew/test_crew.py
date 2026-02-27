from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from feature_dev.types import TestOutput
from tools import ExecTool, DirectoryReadTool, FileReadTool


@CrewBase
class TestCrew:
    """Test Crew - Integration and E2E testing."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def tester(self) -> Agent:
        return Agent(
            config=self.agents_config["tester"],
            tools=[ExecTool(), DirectoryReadTool(), FileReadTool()],
            verbose=True,
        )

    @task
    def test_task(self) -> Task:
        return Task(config=self.tasks_config["test_task"], output_pydantic=TestOutput)

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
