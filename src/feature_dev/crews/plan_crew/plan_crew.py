import os
from crewai import Agent, Crew, Process, Task, Memory
from crewai.project import CrewBase, agent, crew, task

from tools import DirectoryReadTool, FileReadTool
from crewai_tools import FileWriterTool

from ...types import PlanOutput


@CrewBase
class PlanCrew:
    """Plan Crew - Decompose task into user stories."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def planner(self) -> Agent:
        return Agent(
            config=self.agents_config["planner"],  # type: ignore
            tools=[FileReadTool(), DirectoryReadTool()],
            verbose=True,
        )

    @agent
    def setup(self) -> Agent:
        return Agent(
            config=self.agents_config["setup"],  # type: ignore
            verbose=True,
            tools=[],
        )

    @task
    def setup_task(self) -> Task:
        return Task(
            config=self.tasks_config["setup_task"],  # type: ignore
        )

    @task
    def plan_task(self) -> Task:
        return Task(
            config=self.tasks_config["plan_task"],  # type: ignore
            context=[self.setup_task()],  # type: ignore
            output_pydantic=PlanOutput,
        )  # type: ignore

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # type: ignore
            tasks=self.tasks,  # type: ignore
            process=Process.sequential,
            verbose=True,
        )
