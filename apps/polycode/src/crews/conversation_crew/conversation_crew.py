from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import agent, crew, task

from crews.base import PolycodeCrew

from .types import SpecOutput


class ConversationCrew(PolycodeCrew):
    """Conversation-driven specification crew."""

    crew_label = "conversation"
    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def spec_elicitor(self) -> Agent:
        return Agent(
            config=self.agents_config["spec_elicitor"],  # type: ignore[index]
            verbose=False,
        )

    @agent
    def story_planner(self) -> Agent:
        return Agent(
            config=self.agents_config["story_planner"],  # type: ignore[index]
            verbose=False,
        )

    @agent
    def ralph_initializer(self) -> Agent:
        return Agent(
            config=self.agents_config["ralph_initializer"],  # type: ignore[index]
            verbose=False,
        )

    @task
    def spec_elicitation_task(self) -> Task:
        return Task(
            config=self.tasks_config["spec_elicitation_task"],  # type: ignore[index]
            output_pydantic=SpecOutput,
        )

    @task
    def story_breakdown_task(self) -> Task:
        return Task(
            config=self.tasks_config["story_breakdown_task"],  # type: ignore[index]
            output_pydantic=List[SpecOutput],
            context=[self.spec_elicitation_task()],  # pyright: ignore
        )

    @task
    def ralph_init_task(self) -> Task:
        return Task(
            config=self.tasks_config["ralph_init_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Conversation Crew."""
        return Crew(
            agents=self.agents,  # type: ignore[arg-type]
            tasks=self.tasks,  # type: ignore[arg-type]
            process=Process.sequential,
            verbose=False,
        )
