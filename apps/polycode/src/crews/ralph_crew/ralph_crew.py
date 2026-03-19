from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import agent, crew, task
from crewai.tools import BaseTool
from crewai_tools import FileWriterTool

from crews.base import PolycodeCrewMixin
from glm import GLMJSONLLM
from tools import AgentsMDLoaderTool, DirectoryReadTool, ExecTool, FileReadTool

from .types import RalphOutput


class RalphCrew(PolycodeCrewMixin):
    """Ralph implementation crew - minimal loop for fast changes."""

    crew_label = "implement"
    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    agents_md_map: dict[str, str] | None = None

    @agent
    def implementer(self) -> Agent:
        tools: List[BaseTool] = [
            FileReadTool(),
            FileWriterTool(),
            DirectoryReadTool(),
            ExecTool(),
        ]
        if self.agents_md_map:
            tools.append(AgentsMDLoaderTool(agents_md_map=self.agents_md_map))

        return Agent(  # ty:ignore
            config=self.agents_config["implementer"],  # type: ignore
            verbose=False,
            llm=GLMJSONLLM(),
            tools=tools,
            allow_code_execution=False,
        )

    @agent
    def summarizer(self) -> Agent:
        return Agent(  # ty:ignore
            config=self.agents_config["summarizer"],  # type: ignore
            verbose=False,
            llm=GLMJSONLLM(),
        )

    @task
    def implement_task(self) -> Task:
        return Task(  # ty:ignore
            config=self.tasks_config["implement_task"],  # type: ignore
        )

    @task
    def commit_message_task(self) -> Task:
        return Task(  # ty:ignore
            config=self.tasks_config["commit_message_task"],  # type: ignore
            output_pydantic=RalphOutput,
            context=[self.implement_task()],  # pyright:ignore
        )

    @crew
    def crew(self, agents_md_map: dict[str, str] | None = None) -> Crew:
        self.agents_md_map = agents_md_map
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
        )
