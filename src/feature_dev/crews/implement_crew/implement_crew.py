from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import FileWriterTool

from glm import GLMJSONLLM
from tools import DirectoryReadTool, ExecTool, FileReadTool, AgentsMDLoaderTool

from ...types import ImplementOutput


@CrewBase
class ImplementCrew:
    """Implement Crew - Implement features."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    agents_md_map: dict[str, str] | None = None

    @agent
    def developer(self) -> Agent:
        tools = [
            FileReadTool(),
            FileWriterTool(),
            DirectoryReadTool(),
            ExecTool(),
        ]

        if self.agents_md_map:
            tools.append(AgentsMDLoaderTool(agents_md_map=self.agents_md_map))

        return Agent(
            config=self.agents_config["developer"],  # type: ignore
            verbose=False,
            tools=tools,
            allow_code_execution=True,
        )

    @agent
    def consolidator(self) -> Agent:
        tools = []

        if self.agents_md_map:
            tools.append(AgentsMDLoaderTool(agents_md_map=self.agents_md_map))

        return Agent(
            config=self.agents_config["consolidator"],  # type: ignore
            verbose=False,
            llm=GLMJSONLLM(),
            tools=tools,
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

    @task
    def retrospective(self) -> Task:
        return Task(
            config=self.tasks_config["retrospective"],  # type: ignore
        )

    @crew
    def crew(self, agents_md_map: dict[str, str] | None = None) -> Crew:
        self.agents_md_map = agents_md_map or {}

        return Crew(
            agents=self.agents,  # type: ignore
            tasks=self.tasks,  # type: ignore
            process=Process.sequential,
            verbose=False,
            # memory=True,
        )
