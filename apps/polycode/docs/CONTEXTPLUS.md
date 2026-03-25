# Context+ Integration Plan

## Overview

Context+ provides semantic code intelligence via MCP. Integration enables:

- Semantic code search (find by meaning, not exact text)
- Blast radius analysis (impact before changes)
- AST-based structural navigation
- Feature hub mapping (Obsidian-style wikilinks)

## Environment Variables

Add to `.env`:

```bash
OLLAMA_HOST=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_CHAT_MODEL=gemma2:27b
```

## Implementation Steps

### Step 1: Add MCP Server Parameters

File: `src/crews/implement_crew/implement_crew.py`

Add class attributes and configure MCP:

```python
from crewai.mcp import StdioServerParameters

@CrewBase
class ImplementCrew(PolycodeCrewMixin):
    # ... existing attributes ...

    # Context+ MCP Configuration
    mcp_server_params: list[StdioServerParameters] = []
    mcp_connect_timeout: int = 60
    _contextplus_enabled: bool = False

    def _setup_contextplus(self, project_root: str | None) -> None:
        """Initialize Context+ MCP if project_root is available."""
        if not project_root:
            return

        import os

        self._contextplus_enabled = True
        self.mcp_server_params = [
            StdioServerParameters(
                command="bunx",
                args=["contextplus", project_root],
                env={
                    "OLLAMA_HOST": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                    "OLLAMA_EMBED_MODEL": os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
                    "OLLAMA_CHAT_MODEL": os.getenv("OLLAMA_CHAT_MODEL", "gemma2:27b"),
                },
            )
        ]
```

### Step 2: Update Developer Agent

Modify `@agent def developer(self)` to include Context+ tools:

```python
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

    if self._project_root:
        from tools.code_analysis import (
            DefinitionTool,
            DiagnosticsTool,
            HoverTool,
            ReferencesTool,
        )

        tools.extend(
            [
                DiagnosticsTool(),
                HoverTool(),
                DefinitionTool(),
                ReferencesTool(),
            ]
        )

    # Add Context+ MCP tools if enabled
    if self._contextplus_enabled:
        contextplus_tools = self.get_mcp_tools(
            "semantic_code_search",
            "get_blast_radius",
            "get_context_tree",
            "semantic_navigate",
        )
        tools.extend(contextplus_tools)

    return Agent(
        config=self._get_agent_config("developer"),
        verbose=False,
        tools=tools,
        allow_code_execution=False,
    )
```

### Step 3: Update Crew Method

```python
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

    return Crew(
        agents=self.agents,
        tasks=self.tasks,
        process=Process.sequential,
        verbose=False,
    )
```

### Step 4: Update Task Description

File: `src/crews/implement_crew/config/tasks.yaml`

Add Context+ tools to the TOOLS section:

```yaml
    TOOLS:
      * FileReadTool
      * FileWriterTool
      * DirectoryReadTool
      * ExecTool
      * AgentsMDLoaderTool: Load AGENTS.md files from subdirectories
      * semantic_code_search: Search codebase by meaning (Context+)
      * get_blast_radius: Find all usages of a symbol before changes (Context+)
      * get_context_tree: View project structure with symbols (Context+)
      * semantic_navigate: Browse related code clusters (Context+)
```

## Context+ Tool Reference

| Tool                   | Use Case                   | When to Call                          |
| ---------------------- | -------------------------- | ------------------------------------- |
| `semantic_code_search` | Find code by description   | Before implementing, to find patterns |
| `get_blast_radius`     | Impact analysis            | Before modifying functions/classes    |
| `get_context_tree`     | Project structure overview | Starting new feature work             |
| `semantic_navigate`    | Discover related code      | Understanding unfamiliar areas        |

## Verification

1. Start Ollama: `ollama serve`
2. Pull models: `ollama pull nomic-embed-text && ollama pull gemma2:27b`
3. Test MCP: `bunx contextplus skeleton .`
4. Run crew with project_root set

## Notes

- Context+ creates `.mcp_data/` cache directory in project root
- First run builds embeddings (slow), subsequent runs are fast
- Only enable when `project_root` is provided (avoid in CI without repo)
- Read-only tools first; `propose_commit` integration later if needed
