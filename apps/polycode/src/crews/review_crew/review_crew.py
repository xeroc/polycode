import logging

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from crews.base import PolycodeCrewMixin
from glm import GLMJSONLLM

from .types import ReviewOutput

log = logging.getLogger(__name__)


@CrewBase
class ReviewCrew(PolycodeCrewMixin):
    """Review Crew - Multi-persona code review with Night Shift patterns.

    Uses CrewAI hierarchical process with 6 specialized reviewer personas
    coordinated by a manager agent. Each reviewer owns a documentation domain
    and suggests improvements when they spot gaps.

    Night Shift pattern: every failure makes the system better via
    postmortem-first failure handling (apply_doc_improvements).
    """

    crew_label = "review"
    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def review_manager(self) -> Agent:
        return Agent(  # ty:ignore
            config=self.agents_config["review_manager"],  # type: ignore[index]
            verbose=False,
            llm=GLMJSONLLM(),
            allow_delegation=True,
        )

    @agent
    def design_reviewer(self) -> Agent:
        return Agent(  # ty:ignore
            config=self.agents_config["design_reviewer"],  # type: ignore[index]
            verbose=False,
            llm=GLMJSONLLM(),
        )

    @agent
    def architect_reviewer(self) -> Agent:
        return Agent(  # ty:ignore
            config=self.agents_config["architect_reviewer"],  # type: ignore[index]
            verbose=False,
            llm=GLMJSONLLM(),
        )

    @agent
    def domain_expert_reviewer(self) -> Agent:
        return Agent(  # ty:ignore
            config=self.agents_config["domain_expert_reviewer"],  # type: ignore[index]
            verbose=False,
            llm=GLMJSONLLM(),
        )

    @agent
    def code_expert_reviewer(self) -> Agent:
        return Agent(  # ty:ignore
            config=self.agents_config["code_expert_reviewer"],  # type: ignore[index]
            verbose=False,
            llm=GLMJSONLLM(),
        )

    @agent
    def performance_expert_reviewer(self) -> Agent:
        return Agent(  # ty:ignore
            config=self.agents_config["performance_expert_reviewer"],  # type: ignore[index]
            verbose=False,
            llm=GLMJSONLLM(),
        )

    @agent
    def human_advocate_reviewer(self) -> Agent:
        return Agent(  # ty:ignore
            config=self.agents_config["human_advocate_reviewer"],  # type: ignore[index]
            verbose=False,
            llm=GLMJSONLLM(),
        )

    @task
    def review_coordination(self) -> Task:
        return Task(  # ty:ignore
            config=self.tasks_config["review_coordination"],  # type: ignore[index]
            output_pydantic=ReviewOutput,
        )

    @task
    def design_review(self) -> Task:
        return Task(  # ty:ignore
            config=self.tasks_config["design_review"],  # type: ignore[index]
        )

    @task
    def architecture_review(self) -> Task:
        return Task(  # ty:ignore
            config=self.tasks_config["architecture_review"],  # type: ignore[index]
        )

    @task
    def domain_review(self) -> Task:
        return Task(  # ty:ignore
            config=self.tasks_config["domain_review"],  # type: ignore[index]
        )

    @task
    def code_review(self) -> Task:
        return Task(  # ty:ignore
            config=self.tasks_config["code_review"],  # type: ignore[index]
        )

    @task
    def performance_review(self) -> Task:
        return Task(  # ty:ignore
            config=self.tasks_config["performance_review"],  # type: ignore[index]
        )

    @task
    def human_advocacy_review(self) -> Task:
        return Task(  # ty:ignore
            config=self.tasks_config["human_advocacy_review"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.hierarchical,
            manager_agent=self.review_manager(),  # type: ignore[union-attr]
            verbose=False,
        )

    def apply_doc_improvements(
        self,
        error_context: str,
        flow_id: str,
        label: str,
    ) -> list[str]:
        """Analyze failure and suggest doc/workflow improvements.

        When agent fails, fix docs/workflow FIRST, then fix code. This method
        analyzes the failure context and returns structured suggestions for doc
        improvements.

        Args:
            error_context: The error message and surrounding context.
            flow_id: ID of the failed flow.
            label: Flow label (e.g., "ralph").

        Returns:
            List of suggested doc improvements.
        """
        agent = Agent(
            role="Documentation Improvement Analyst",
            goal=("Analyze failures and identify documentation or workflow gaps that led to the failure"),
            backstory=(
                "You're a postmortem specialist. When an AI agent fails, "
                "you don't just look at the code — you look at what docs, "
                "skills, or workflow instructions could have prevented the "
                "failure. You suggest concrete improvements to documentation "
                "that will prevent similar failures."
            ),
            llm=GLMJSONLLM(),
            verbose=False,
        )
        result = agent.kickoff(
            f"Analyze this failure and suggest doc improvements:\n\n"
            f"Flow: {label}\nFlow ID: {flow_id}\n\n"
            f"Error context:\n{error_context}\n\n"
            f"Return a list of specific, actionable doc improvements that "
            f"would prevent this failure in the future."
        )
        improvements = [line.strip() for line in result.raw.split("\n") if line.strip()]  # type: ignore[union-attr]
        log.info(f"📋 Doc improvements suggested: {len(improvements)}")
        return improvements
