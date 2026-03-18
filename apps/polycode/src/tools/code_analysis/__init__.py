"""Code analysis tools for Polycode agents.

Provides tree-sitter (structural) and LSP (semantic) analysis capabilities.
"""

from pathlib import Path

# Context management
from tools.code_analysis.context_manager import CodeContext

# Language support
from tools.code_analysis.language_support import (
    EXTENSION_MAP,
    LANGUAGE_MAP,
    LanguageSupport,
    get_language_support,
)

# LSP tools
from tools.code_analysis.lsp.base import BaseLSPTool, LSPToolInput, PositionInput
from tools.code_analysis.lsp.client_pool import (
    LSP_SERVERS,
    LSPClient,
    LSPClientPool,
    LSPServerConfig,
    close_client_pool,
    get_client_pool,
)
from tools.code_analysis.lsp.definition_tool import DefinitionTool
from tools.code_analysis.lsp.diagnostics_tool import DiagnosticsTool
from tools.code_analysis.lsp.hover_tool import HoverTool
from tools.code_analysis.lsp.references_tool import ReferencesTool

# Tree-sitter base (available)
from tools.code_analysis.tree_sitter.base import BaseTreeSitterTool, TreeSitterToolInput

# Types (from main types.py)
from tools.code_analysis.types import (
    BlastRadius,
    Definition,
    Diagnostic,
    DiagnosticsResult,
    FileSkeleton,
    HoverInfo,
    Import,
    Position,
    Range,
    Reference,
    Symbol,
    SymbolKind,
    SymbolUsage,
)

# Tree-sitter tools (optional - may not be implemented yet)
TREE_SITTER_TOOLS_AVAILABLE = False
BlastRadiusTool = None  # type: ignore[misc,assignment]
ImportsTool = None  # type: ignore[misc,assignment]
QueryTool = None  # type: ignore[misc,assignment]
QUERY_TEMPLATES = {}  # type: ignore[misc,assignment]
SkeletonTool = None  # type: ignore[misc,assignment]
SymbolsTool = None  # type: ignore[misc,assignment]

__all__ = [
    # Types
    "Position",
    "Range",
    "Symbol",
    "SymbolKind",
    "Import",
    "FileSkeleton",
    "SymbolUsage",
    "BlastRadius",
    "HoverInfo",
    "Definition",
    "Reference",
    "Diagnostic",
    "DiagnosticsResult",
    # Context
    "CodeContext",
    # Language support
    "EXTENSION_MAP",
    "LANGUAGE_MAP",
    "LanguageSupport",
    "get_language_support",
    # Tree-sitter base
    "BaseTreeSitterTool",
    "TreeSitterToolInput",
    # Tree-sitter tools (if available)
    "SkeletonTool",
    "SymbolsTool",
    "ImportsTool",
    "QueryTool",
    "QUERY_TEMPLATES",
    "BlastRadiusTool",
    "TREE_SITTER_TOOLS_AVAILABLE",
    # LSP base
    "BaseLSPTool",
    "LSPToolInput",
    "PositionInput",
    # LSP client management
    "LSPClient",
    "LSPClientPool",
    "LSPServerConfig",
    "LSP_SERVERS",
    "get_client_pool",
    "close_client_pool",
    # LSP tools
    "HoverTool",
    "DefinitionTool",
    "ReferencesTool",
    "DiagnosticsTool",
]


def create_lsp_tools(project_root: str | Path) -> list:
    """Create LSP-based code analysis tools for a project.

    Args:
        project_root: Path to project root

    Returns:
        List of LSP tool instances ready for use with CrewAI agents
    """
    project_root = Path(project_root).resolve()

    return [
        HoverTool(),
        DefinitionTool(),
        ReferencesTool(),
        DiagnosticsTool(),
    ]


def create_tree_sitter_tools(project_root: str | Path, include_lsp: bool = True) -> list:
    """Create all code analysis tools for a project.

    Args:
        project_root: Path to project root
        include_lsp: Whether to include LSP-based tools

    Returns:
        List of tool instances ready for use with CrewAI agents

    Note:
        Tree-sitter tools are only included if TREE_SITTER_TOOLS_AVAILABLE is True.
    """
    project_root = Path(project_root).resolve()
    tools = []

    # Add tree-sitter tools if available
    if TREE_SITTER_TOOLS_AVAILABLE:
        tools.extend(
            [
                SkeletonTool(project_root=project_root),  # type: ignore[misc]
                SymbolsTool(project_root=project_root),  # type: ignore[misc]
                ImportsTool(project_root=project_root),  # type: ignore[misc]
                QueryTool(project_root=project_root),  # type: ignore[misc]
                BlastRadiusTool(project_root=project_root),  # type: ignore[misc]
            ]
        )

    # Add LSP tools
    if include_lsp:
        tools.extend(create_lsp_tools(project_root))

    return tools


def create_code_analysis_tools(project_root: str | Path) -> list:
    """Create all available code analysis tools.

    This is the recommended entry point for creating tools.

    Args:
        project_root: Path to project root

    Returns:
        List of tool instances ready for use with CrewAI agents
    """
    return create_tree_sitter_tools(project_root, include_lsp=True)
