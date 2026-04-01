"""AgentsMD built-in module for the Polycode plugin system."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flows.protocol import FlowDef

log = logging.getLogger(__name__)


def _collect_agents_md(state: Any) -> dict[str, Any]:
    """Discover AGENTS.md files and return context dict."""
    repo_path = Path(state.repo) if hasattr(state, "repo") else None
    if not repo_path or not repo_path.exists():
        return {"agents_md": "", "agents_md_map": {}}

    agents_md_map: dict[str, str] = {}
    for agents_file in repo_path.rglob("AGENTS.md"):
        try:
            relative = str(agents_file.relative_to(repo_path))
            if relative.startswith("."):
                continue
            agents_md_map[relative] = agents_file.read_text(encoding="utf-8")
            log.info(f"📕 Discovered AGENTS.md: {relative}")
        except Exception as e:
            log.error(f"Error reading {agents_file}: {e}")

    root_agents_md = agents_md_map.get("AGENTS.md", "")
    if not root_agents_md and agents_md_map:
        first_path = next(iter(agents_md_map.keys()))
        root_agents_md = agents_md_map[first_path]
        log.info(f"📕 Using {first_path} as root AGENTS.md")

    log.info(f"📕 Total AGENTS.md files discovered: {len(agents_md_map)}")
    return {
        "agents_md": root_agents_md,
        "agents_md_map": agents_md_map,
    }


class AgentsMDPolycodeModule:
    """AgentsMD module: discovers and injects AGENTS.md content."""

    name = "agentsmd"
    version = "0.1.0"
    dependencies: list[str] = []

    @classmethod
    def on_load(cls, context: Any) -> None:
        pass

    @classmethod
    def register_hooks(cls, hook_manager: Any) -> None:
        pass

    @classmethod
    def get_models(cls) -> list[type]:
        return []

    @classmethod
    def get_flows(cls) -> list["FlowDef"]:
        return []

    @classmethod
    def get_context_collectors(cls) -> list[tuple[str, Any]]:
        return [("agents_md", _collect_agents_md)]
