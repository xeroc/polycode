from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


@CrewBase
class TestCrew:
    """Test Crew - Integration and E2E testing."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def tester(self) -> Agent:
        return Agent(
            config=self.agents_config["tester"],
            verbose=True,
        )

    @task
    def test_task(self) -> Task:
        return Task(
            config=self.tasks_config["test_task"],
        )

    @task
    def generate_result(self) -> Task:
        return Task(config=self.tasks_config["generate_result"], output_pydantic=TestOutput)

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
