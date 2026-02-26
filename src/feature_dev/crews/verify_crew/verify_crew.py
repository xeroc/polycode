from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


@CrewBase
class VerifyCrew:
    """Verify Crew - Verify implementation."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def verifier(self) -> Agent:
        return Agent(
            config=self.agents_config["verifier"],
            verbose=True,
        )

    @task
    def verify_task(self) -> Task:
        return Task(
            config=self.tasks_config["verify_task"],
        )

    @task
    def generate_result(self) -> Task:
        return Task(config=self.tasks_config["generate_result"], output_pydantic=VerifyOutput)

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
