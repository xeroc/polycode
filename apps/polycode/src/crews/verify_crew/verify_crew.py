from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import agent, crew, task

from crews.base import PolycodeCrewMixin
from glm import GLMJSONLLM
from tools import DirectoryReadTool, ExecTool, FileReadTool

from .types import VerifyOutput


class VerifyCrew(PolycodeCrewMixin):
    """Verify Crew - Verify implementation."""

    crew_label = "verify"
    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def verifier(self) -> Agent:
        return Agent(
            config=self.agents_config["verifier"],  # type: ignore
            tools=[ExecTool(), DirectoryReadTool(), FileReadTool()],
            verbose=False,
            llm=GLMJSONLLM(),
            allow_code_execution=False,
        )

    @task
    def verify_task(self) -> Task:
        return Task(
            config=self.tasks_config["verify_task"],  # type: ignore
            output_pydantic=VerifyOutput,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # type: ignore
            tasks=self.tasks,  # type: ignore
            process=Process.sequential,
            verbose=False,
        )
