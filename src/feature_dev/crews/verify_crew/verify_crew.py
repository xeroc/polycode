from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from feature_dev.types import CommitMessageOutput, VerifyOutput
from tools import DirectoryReadTool, ExecTool, FileReadTool


@CrewBase
class VerifyCrew:
    """Verify Crew - Verify implementation."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def verifier(self) -> Agent:
        return Agent(
            config=self.agents_config["verifier"],
            tools=[ExecTool(), DirectoryReadTool(), FileReadTool()],
            verbose=True,
        )

    @agent
    def commit_message_preparer(self) -> Agent:
        return Agent(
            config=self.agents_config["commit_message_preparer"],
            verbose=True,
        )

    @task
    def verify_task(self) -> Task:
        return Task(
            config=self.tasks_config["verify_task"],
            output_pydantic=VerifyOutput,
        )

    @task
    def produce_commit_message(self) -> Task:
        return Task(
            config=self.tasks_config["produce_commit_message"],
            output_pydantic=CommitMessageOutput,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
