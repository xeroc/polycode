from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import FileWriterTool

from tools import DirectoryReadTool, ExecTool, FileReadTool

from ...types import ImplementOutput


@CrewBase
class ImplementCrew:
    """Implement Crew - Implement features."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def developer(self) -> Agent:
        return Agent(
            config=self.agents_config["developer"],
            verbose=True,
            tools=[FileReadTool(), FileWriterTool(), DirectoryReadTool(), ExecTool()],
        )

    @agent
    def consolidator(self) -> Agent:
        return Agent(
            config=self.agents_config["consolidator"],
            verbose=True,
        )

    @task
    def implement_task(self) -> Task:
        return Task(
            config=self.tasks_config["implement_task"],
        )

    @task
    def generate_result(self) -> Task:
        return Task(
            config=self.tasks_config["generate_result"], output_pydantic=ImplementOutput
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
