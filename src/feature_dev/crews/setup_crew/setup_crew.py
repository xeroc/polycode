from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from feature_dev.types import SetupOutput
from crewai_tools import FileWriterTool


@CrewBase
class SetupCrew:
    """Setup Crew - Prepare development environment."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def setup(self) -> Agent:
        return Agent(
            config=self.agents_config["setup"], verbose=True, tools=[FileWriterTool()]
        )

    @agent
    def consolidator(self) -> Agent:
        return Agent(config=self.agents_config["consolidator"], verbose=False)

    @task
    def setup_task(self) -> Task:
        return Task(
            config=self.tasks_config["setup_task"],
        )

    @task
    def generate_result(self) -> Task:
        return Task(
            config=self.tasks_config["generate_result"], output_pydantic=SetupOutput
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
