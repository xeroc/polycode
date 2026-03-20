from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from crewai.tools import BaseTool
from crewai_tools import FileWriterTool

from crews.base import PolycodeCrewMixin
from glm import GLMJSONLLM
from tools import AgentsMDLoaderTool, DirectoryReadTool, FileReadTool

from .types import PlanOutput


@CrewBase
class PlanCrew(PolycodeCrewMixin):
    """Plan Crew - Decompose task into user stories."""

    crew_label = "plan"
    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    agents_md_map: dict[str, str] | None = None

    @agent
    def setup(self) -> Agent:
        tools: List[BaseTool] = [FileReadTool(), DirectoryReadTool(), FileWriterTool()]

        if self.agents_md_map:
            tools.append(AgentsMDLoaderTool(agents_md_map=self.agents_md_map))

        return Agent(  # ty:ignore
            config=self.agents_config["setup"],  # type: ignore
            verbose=False,
            llm=GLMJSONLLM(),
            # llm=self._streaming_llm,
            tools=tools,
            allow_code_execution=False,
        )

    @agent
    def planner(self) -> Agent:
        tools: List[BaseTool] = []

        if self.agents_md_map:
            tools.append(AgentsMDLoaderTool(agents_md_map=self.agents_md_map))

        return Agent(  # ty:ignore
            config=self.agents_config["planner"],  # type: ignore
            llm=GLMJSONLLM(),
            verbose=False,
            tools=tools,
        )

    @task
    def setup_task(self) -> Task:
        return Task(  # ty:ignore
            config=self.tasks_config["setup_task"],  # type: ignore
        )

    @task
    def plan_task(self) -> Task:
        return Task(  # ty:ignore
            config=self.tasks_config["plan_task"],  # type: ignore
            output_pydantic=PlanOutput,
        )

    @crew
    def crew(self, agents_md_map: dict[str, str] | None = None) -> Crew:
        self.agents_md_map = agents_md_map or {}

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
        )
