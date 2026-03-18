# Code Analysis Tools

Semantic code intelligence tools for CrewAI agents using tree-sitter and LSP.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Code Analysis Tools                      │
├─────────────────────────────────────────────────────────────┤
│  tree_sitter/          │ LSP (Semantic/Deep)       │ Context Manager   │
│  ├─ base.py           │  ├─ base.py            │  ├─ context_manager.py  │
│  ├─ skeleton_tool.py  │  ├─ hover_tool.py        │  ├─ language_support.py  │
│  ├─ symbols_tool.py  │  ├─ definition_tool.py   │                            │
│  ├─ imports_tool.py  │  ├─ references_tool.py  │                            │
│  ├─ query_tool.py   │  ├─ diagnostics_tool.py │                            │
│  └─ blast_radius.py  │  └─ completions_tool.py  │                            │
└─────────────────────────────────────────────────────────────┘
```

## Tree-sitter Tools (Fast/Local)

| Tool | Purpose |
|------|---------|
| `FileSkeletonTool` | Extract function signatures, class methods, type defs with line ranges |
| `SymbolsTool` | List all symbols (functions, classes, variables) with positions |
| `ImportsTool` | Get all imports/requires with resolved paths |
| `ASTQueryTool` | Run tree-sitter queries (e.g., find all `async def`) |
| `BlastRadiusTool` | Find every file/line where a symbol is used |

## LSP Tools (Semantic/Deep)

| Tool | Purpose |
|------|---------|
| `HoverTool` | Get type info, docs at cursor position |
| `DefinitionTool` | Jump to definition (file:line:col) |
| `ReferencesTool` | Find all usages across project |
| `DiagnosticsTool` | Get type errors, lint warnings |
| `CompletionsTool` | Get completions (optional) |

## Supported Languages

- Python (`.py`)
- TypeScript (`.ts`, `.tsx`)
- JavaScript (`.js`, `.jsx`)
- Go (`.go`)
- Rust (`.rs`)

## Dependencies

```
tree-sitter>=0.23.0
tree-sitter-python>=0.23.0
tree-sitter-javascript>=0.23.0
tree-sitter-typescript>=0.23.0
tree-sitter-rust>=0.23.0
tree-sitter-go>=0.23.0
```

## Usage

```python
from tools.code_analysis import FileSkeletonTool, SymbolsTool, BlastRadiusTool

# Initialize with project root
skeleton_tool = FileSkeletonTool(project_root="/path/to/project")
symbols_tool = SymbolsTool(project_root="/path/to/project")

# Get file skeleton (signatures only, no bodies)
skeleton = skeleton_tool.run(file_path="src/main.py")

# Get all symbols in a file
symbols = symbols_tool.run(file_path="src/main.py")

# Find where a symbol is used
usage = blast_radius_tool.run(symbol_name="calculate_total", file_path="src/utils.py")
```

## Installation

```bash
cd apps/polycode
uv sync  # Install new dependencies
```
