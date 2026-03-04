from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from feature_dev.types import VerifyOutput
from glm import GLMJSONLLM
from tools import DirectoryReadTool, ExecTool, FileReadTool


@CrewBase
class VerifyCrew:
    """Verify Crew - Verify implementation."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def verifier(self) -> Agent:
        return Agent(
            config=self.agents_config["verifier"],  # type: ignore
            tools=[ExecTool(), DirectoryReadTool(), FileReadTool()],
            verbose=False,
            llm=GLMJSONLLM(),
            allow_code_execution=True,
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
