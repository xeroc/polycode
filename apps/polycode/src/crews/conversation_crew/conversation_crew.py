from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from crewai.tools import BaseTool
from crewai_tools import FileWriterTool

from crews.base import PolycodeCrewMixin
from tools import AgentsMDLoaderTool, FileReadTool

from .types import SpecOutput


@CrewBase
class ConversationCrew(PolycodeCrewMixin):
    """Conversation-driven specification crew."""

    crew_label = "conversation"
    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    agents_md_map: dict[str, str] | None = None

    @agent
    def spec_elicitor(self) -> Agent:
        tools: List[BaseTool] = [FileReadTool(), FileWriterTool()]
        if self.agents_md_map:
            tools.append(AgentsMDLoaderTool(agents_md_map=self.agents_md_map))
        return Agent(  # ty:ignore
            config=self.agents_config["spec_elicitor"],  # type: ignore[index]
            verbose=False,
        )

    @task
    def spec_elicitation_task(self) -> Task:
        return Task(  # ty:ignore
            config=self.tasks_config["spec_elicitation_task"],  # type: ignore[index]
            output_pydantic=SpecOutput,
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
