from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from tools import DirectoryReadTool, FileReadTool

from ...types import PlanOutput


@CrewBase
class PlanCrew:
    """Plan Crew - Decompose task into user stories."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def planner(self) -> Agent:
        return Agent(
            config=self.agents_config["planner"],
            tools=[FileReadTool(), DirectoryReadTool()],
            verbose=True,
        )

    @task
    def plan_task(self) -> Task:
        return Task(config=self.tasks_config["plan_task"], output_pydantic=PlanOutput)

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
