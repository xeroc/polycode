from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import FileWriterTool

from glm import GLMJSONLLM
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
            config=self.agents_config["developer"],  # type: ignore
            verbose=True,
            tools=[
                FileReadTool(),
                FileWriterTool(),
                DirectoryReadTool(),
                ExecTool(),
            ],
        )

    @agent
    def consolidator(self) -> Agent:
        return Agent(
            config=self.agents_config["consolidator"],  # type: ignore
            verbose=True,
            llm=GLMJSONLLM(),
        )

    @task
    def implement_task(self) -> Task:
        return Task(
            config=self.tasks_config["implement_task"],  # type: ignore
        )

    @task
    def generate_result(self) -> Task:
        return Task(
            config=self.tasks_config["generate_result"],  # type: ignore
            output_pydantic=ImplementOutput,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # type: ignore
            tasks=self.tasks,  # type: ignore
            process=Process.sequential,
            verbose=True,
            # memory=True,
        )
