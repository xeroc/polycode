import os
from pathlib import Path
from typing import List

import yaml
from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from crewai.tools import BaseTool
from crewai_tools import FileWriterTool, MCPServerAdapter
from mcp import StdioServerParameters

from crews.base import PolycodeCrewMixin
from glm import GLMJSONLLM
from tools import AgentsMDLoaderTool, DirectoryReadTool, ExecTool, FileReadTool

from .types import ImplementOutput, TaskTemplate


@CrewBase
class ImplementCrew(PolycodeCrewMixin):
    """Flexible Implement Crew that accepts custom task configurations."""

    crew_label = "implement"
    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    agents_md_map: dict[str, str] | None = None
    _custom_tasks: dict[str, TaskTemplate] | None = None
    _base_tasks_config: dict | None = None
    _loaded_agents_config: dict | None = None
    _project_root: str | None = None

    _contextplus_server_params: StdioServerParameters | None = None
    _contextplus_enabled: bool = False
    _contextplus_tools: list = []

    def _setup_contextplus(self, project_root: str | None) -> None:
        """Initialize Context+ MCP if project_root is available."""
        if not project_root:
            return

        self._contextplus_enabled = True
        self._contextplus_server_params = StdioServerParameters(
            command="bunx",
            args=["contextplus", project_root],
            env={
                "OLLAMA_HOST": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                "OLLAMA_EMBED_MODEL": os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
                "OLLAMA_CHAT_MODEL": os.getenv("OLLAMA_CHAT_MODEL", "gemma2:27b"),
                **os.environ,
            },
        )

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
                config["context"] = template.context  # pyright:ignore # ty:ignore
            return config

        if self._base_tasks_config and task_name in self._base_tasks_config:
            return self._base_tasks_config[task_name]

        return self.tasks_config[task_name]  # pyright:ignore # ty:ignore

    def _get_agent_config(self, agent_name: str) -> dict:
        """Get agent config."""
        if self._loaded_agents_config and agent_name in self._loaded_agents_config:
            return self._loaded_agents_config[agent_name]
        return self.agents_config[agent_name]  # pyright:ignore # ty:ignore

    @agent
    def developer(self) -> Agent:
        tools: list[BaseTool] = [
            FileReadTool(),
            FileWriterTool(),
            DirectoryReadTool(),
            ExecTool(),
        ]

        if self.agents_md_map:
            tools.append(AgentsMDLoaderTool(agents_md_map=self.agents_md_map))

        if self._contextplus_enabled and self._contextplus_tools:
            tools.extend(self._contextplus_tools)

        return Agent(  # ty:ignore
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

        return Agent(  # ty:ignore
            config=self._get_agent_config("consolidator"),
            verbose=False,
            llm=GLMJSONLLM(),
            tools=tools,
        )

    @task
    def implement_task(self) -> Task:
        config = self._get_task_config("implement_task")
        return Task(  # ty:ignore # pyright:ignore
            config=config,
        )

    @task
    def retrospective(self) -> Task:
        config = self._get_task_config("retrospective")
        return Task(  # ty:ignore # pyright:ignore
            config=config,
        )

    @task
    def generate_result(self) -> Task:
        config = self._get_task_config("generate_result")
        return Task(  # pyright:ignore # ty:ignore
            config=config,
            output_pydantic=ImplementOutput,
        )

    @crew
    def crew(
        self,
        agents_md_map: dict[str, str] | None = None,
        custom_tasks: dict[str, TaskTemplate] | None = None,
        project_root: str | None = None,
    ) -> Crew:
        self.agents_md_map = agents_md_map or {}
        if custom_tasks:
            self._custom_tasks = custom_tasks
        if project_root:
            self._project_root = project_root
            self._setup_contextplus(project_root)

        if self._contextplus_enabled and self._contextplus_server_params:
            with MCPServerAdapter(self._contextplus_server_params) as mcp_tools:
                contextplus_tool_names = [
                    "semantic_code_search",
                    "get_blast_radius",
                    "get_context_tree",
                    "semantic_navigate",
                ]
                self._contextplus_tools = [t for t in mcp_tools if t.name in contextplus_tool_names]

                return Crew(
                    agents=self.agents,
                    tasks=self.tasks,
                    process=Process.sequential,
                    verbose=False,
                )
        else:
            return Crew(
                agents=self.agents,
                tasks=self.tasks,
                process=Process.sequential,
                verbose=False,
            )
