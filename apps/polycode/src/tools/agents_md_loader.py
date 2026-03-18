from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class AgentsMDLoaderInput(BaseModel):
    relative_path: str = Field(
        ...,
        description="Relative path to the AGENTS.md file to load (e.g., 'src/crews/AGENTS.md')",
    )


class AgentsMDLoaderTool(BaseTool):
    name: str = "agents_md_loader"
    description: str = ""
    args_schema: Type[BaseModel] = AgentsMDLoaderInput

    agents_md_map: dict[str, str] = Field(default_factory=dict, exclude=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # We dynamically patch the relative folders of agetns.md into the
        # description
        self.description = (
            "Load AGENTS.md content from a specific subdirectory. "
            "Use this to access project-specific CrewAI patterns and guidelines "
            "from subdirectories when needed. Available AGENTS.md files: " + "\n - ".join(self.agents_md_map.keys())
        )

    def _run(self, relative_path: str) -> str:
        if relative_path in self.agents_md_map:
            return f"Content of {relative_path}:\n\n{self.agents_md_map[relative_path]}"
        available = "\n".join(f"  - {path}" for path in self.agents_md_map.keys())
        return f"AGENTS.md not found at '{relative_path}'.\nAvailable AGENTS.md files:\n{available}"
