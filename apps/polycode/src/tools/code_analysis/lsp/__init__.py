"""LSP-based code analysis tools.

Provides semantic analysis capabilities through Language Server Protocol:
- Hover information (types, docs)
- Go to definition
- Find references
- Diagnostics (errors, warnings)
"""

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

__all__ = [
    # Base classes
    "BaseLSPTool",
    "LSPToolInput",
    "PositionInput",
    # Client management
    "LSPClient",
    "LSPClientPool",
    "LSPServerConfig",
    "LSP_SERVERS",
    "get_client_pool",
    "close_client_pool",
    # Tools
    "HoverTool",
    "DefinitionTool",
    "ReferencesTool",
    "DiagnosticsTool",
]
