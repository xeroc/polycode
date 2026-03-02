from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import FileWriterTool

from feature_dev.types import SetupOutput


@CrewBase
class SetupCrew:
    """Setup Crew - Prepare development environment."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def setup(self) -> Agent:
        return Agent(
            config=self.agents_config["setup"],  # type: ignore
            verbose=True,
            tools=[FileWriterTool()],
        )

    @agent
    def consolidator(self) -> Agent:
        return Agent(config=self.agents_config["consolidator"], verbose=True)  # type: ignore

    @task
    def setup_task(self) -> Task:
        return Task(
            config=self.tasks_config["setup_task"],  # type: ignore
        )

    @task
    def generate_result(self) -> Task:
        return Task(
            config=self.tasks_config["generate_result"],  # type: ignore
            output_pydantic=SetupOutput,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # type: ignore
            tasks=self.tasks,  # type: ignore
            process=Process.sequential,
            verbose=True,
        )
