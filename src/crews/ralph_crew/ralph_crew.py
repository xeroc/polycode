from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from crewai.tools import BaseTool
from crewai_tools import FileWriterTool

from tools import AgentsMDLoaderTool, DirectoryReadTool, ExecTool, FileReadTool

from .types import RalphOutput


@CrewBase
class RalphCrew:
    """Ralph implementation crew - minimal loop for fast changes."""

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
        return Agent(
            config=self.agents_config["implementer"],  # type: ignore[index]
            verbose=False,
            tools=tools,
            allow_code_execution=False,
        )

    @agent
    def summarizer(self) -> Agent:
        return Agent(
            config=self.agents_config["summarizer"],  # type: ignore[index]
            verbose=False,
        )

    @task
    def implement_task(self) -> Task:
        return Task(
            config=self.tasks_config["implement_task"],  # type: ignore[index]
        )

    @task
    def commit_message_task(self) -> Task:
        return Task(
            config=self.tasks_config["commit_message_task"],  # type: ignore[index]
            output_pydantic=RalphOutput,
            context=[self.implement_task()],  # pyright:ignore
        )

    @crew
    def crew(self, agents_md_map: dict[str, str] | None = None) -> Crew:
        self.agents_md_map = agents_md_map or {}
        return Crew(
            agents=self.agents,  # type: ignore[arg-type]
            tasks=self.tasks,  # type: ignore[arg-type]
            process=Process.sequential,
            verbose=False,
        )
