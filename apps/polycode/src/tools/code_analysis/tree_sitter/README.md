"""Tree-sitter tool README.md."""

# Tree-sitter Tools

Fast, local code analysis using tree-sitter for structural analysis, symbol extraction, and usage tracking.

## Tools

### FileSkeletonTool

Extract function/class signatures and type definitions with line ranges - no implementation bodies.

### SymbolsTool

List all symbols (functions, classes, variables) with positions

### ImportsTool

Get all import/requires statements with resolved paths

### ASTQueryTool

Run tree-sitter queries (e.g., find all `async def`)

### BlastRadiusTool

Find every file/line where a symbol is used across the project

## Installation

```bash
cd apps/polycode
uv sync  # Install dependencies
```

## Usage

```python
from pathlib import Path

from tools.code_analysis.tree_sitter import FileSkeletonTool, SymbolsTool, ImportsTool, ASTQueryTool, BlastRadiusTool

from tools.code_analysis import CodeContext

# Get file skeleton
skeleton_tool = FileSkeletonTool(project_root="/path/to/project")
symbols_tool = SymbolsTool(project_root="/path/to/project")
imports_tool = ImportsTool(project_root="/path/to/project")
query_tool = ASTQueryTool(project_root="/path/to/project")
blast_radius_tool = BlastRadiusTool(project_root="/path/to/project")

# Example usage
skeleton = skeleton_tool.run(file_path="src/main.py")
print(skeleton)
```

## Dependencies

```
tree-sitter>=0.23.0
tree-sitter-python>=0.23.0
tree-sitter-javascript>=0.23.0
tree-sitter-typescript>=0.23.0
tree-sitter-rust>=0.23.0
tree-sitter-go>=0.23.0
```
