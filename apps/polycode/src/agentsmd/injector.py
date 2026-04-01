"""Context injector for AGENTS.md file discovery."""

import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class AgentsMDInjector:
    """Injects AGENTS.md content into crew task templates.

    Scans the repository for AGENTS.md files and provides:
    - agents_md: root AGENTS.md content (string)
    - agents_md_map: all AGENTS.md files as {relative_path: content}
    """

    name = "agents_md"
    keys = ["agents_md", "agents_md_map"]

    def collect(self, state: Any) -> dict[str, Any]:
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
