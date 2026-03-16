from pathlib import Path

import yaml
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import FileWriterTool

from glm import GLMJSONLLM
from solcraft.types import ImplementOutput, TaskTemplate
from tools import AgentsMDLoaderTool, DirectoryReadTool, ExecTool, FileReadTool


@CrewBase
class SolcraftImplementCrew:
    """Flexible Implement Crew that accepts custom task configurations."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    agents_md_map: dict[str, str] | None = None
    _custom_tasks: dict[str, TaskTemplate] | None = None
    _base_tasks_config: dict | None = None
    _loaded_agents_config: dict | None = None

    def __init__(
        self,
        custom_tasks: dict[str, TaskTemplate] | None = None,
    ):
        self._custom_tasks = custom_tasks or {}
        self._load_base_configs()

    def _load_base_configs(self):
        config_path = Path(__file__).parent / "config" / "tasks.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self._base_tasks_config = yaml.safe_load(f)
        else:
            self._base_tasks_config = {}

        agents_path = Path(__file__).parent / "config" / "agents.yaml"
        if agents_path.exists():
            with open(agents_path, "r", encoding="utf-8") as f:
                self._loaded_agents_config = yaml.safe_load(f)
        else:
            self._loaded_agents_config = {}

    def _get_task_config(self, task_name: str) -> dict:
        """Get task config, merging custom templates with base configs."""
        if self._custom_tasks and task_name in self._custom_tasks:
            template = self._custom_tasks[task_name]
            config = {
                "description": template.description,
                "expected_output": template.expected_output,
                "agent": template.agent,
            }
            if template.context:
                config["context"] = template.context
            return config

        if self._base_tasks_config and task_name in self._base_tasks_config:
            return self._base_tasks_config[task_name]

        return {}

    def _get_agent_config(self, agent_name: str) -> dict:
        """Get agent config."""
        if (
            self._loaded_agents_config
            and agent_name in self._loaded_agents_config
        ):
            return self._loaded_agents_config[agent_name]
        return {}

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
            config=self._get_agent_config("developer"),
            verbose=False,
            tools=tools,
            allow_code_execution=False,
        )

    @agent
    def consolidator(self) -> Agent:
        tools = []

        if self.agents_md_map:
            tools.append(AgentsMDLoaderTool(agents_md_map=self.agents_md_map))

        return Agent(
            config=self._get_agent_config("consolidator"),
            verbose=False,
            llm=GLMJSONLLM(),
            tools=tools,
        )

    @task
    def implement_task(self) -> Task:
        config = self._get_task_config("implement_task")
        return Task(
            config=config,
        )

    @task
    def retrospective(self) -> Task:
        config = self._get_task_config("retrospective")
        return Task(
            config=config,
        )

    @task
    def generate_result(self) -> Task:
        config = self._get_task_config("generate_result")
        return Task(
            config=config,
            output_pydantic=ImplementOutput,
        )

    @crew
    def crew(
        self,
        agents_md_map: dict[str, str] | None = None,
        custom_tasks: dict[str, TaskTemplate] | None = None,
    ) -> Crew:
        self.agents_md_map = agents_md_map or {}
        if custom_tasks:
            self._custom_tasks = custom_tasks

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
        )
