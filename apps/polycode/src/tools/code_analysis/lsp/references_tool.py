"""References tool - find all references via LSP."""

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from tools.code_analysis.lsp.base import BaseLSPTool, PositionInput
from tools.code_analysis.lsp.client_pool import get_client_pool
from tools.code_analysis.types import Reference

log = logging.getLogger(__name__)


class ReferencesToolInput(PositionInput):
    """Input schema for references tool."""

    include_declaration: bool = Field(
        default=True,
        description="Include the symbol declaration in results",
    )


class ReferencesTool(BaseLSPTool):
    """Find all references to symbol at position.

    Uses LSP textDocument/references to find all usages of a symbol.
    """

    name: str = "find_references"
    description: str = (
        "Find all references to a symbol at a specific position in a file. "
        "Returns a list of locations where the symbol is used."
    )
    args_schema: type[BaseModel] = ReferencesToolInput

    def _run(
        self,
        file_path: str,
        line: int,
        column: int,
        include_declaration: bool = True,
    ) -> str:
        """Get references at position."""
        return self._run_async(self._run_async_impl(file_path, line, column, include_declaration))

    async def _run_async_impl(
        self,
        file_path: str,
        line: int,
        column: int,
        include_declaration: bool,
    ) -> str:
        """Async implementation of references lookup."""
        resolved_path = self._resolve_path(file_path)
        language = self.context.detect_language(resolved_path)

        if not language:
            return json.dumps({"error": f"Unknown language for {file_path}"})

        pool = get_client_pool(self.context.project_root)
        client = await pool.get_client(language)

        if not client or not client.initialized:
            return json.dumps({"error": f"LSP server not available for {language}. Install the language server first."})

        # Open document
        await self._open_document(client, resolved_path, language)

        # Request references
        params = {
            "textDocument": {"uri": resolved_path.as_uri()},
            "position": self._get_position(line, column),
            "context": {
                "includeDeclaration": include_declaration,
            },
        }

        response = await client.send_request("textDocument/references", params)

        if not response or "result" not in response:
            return json.dumps({"error": "No references found"})

        result = response["result"]
        if not result:
            return json.dumps({"error": "No references found at this position"})

        # Parse references
        references = self._parse_references_result(result)

        if not references:
            return json.dumps({"error": "Could not parse references result"})

        # Group by file for better readability
        by_file: dict[str, list[dict[str, Any]]] = {}
        for ref in references:
            if ref.file_path not in by_file:
                by_file[ref.file_path] = []
            by_file[ref.file_path].append(ref.model_dump())

        # Return as JSON
        output = {
            "query": {
                "file_path": file_path,
                "line": line,
                "column": column,
                "include_declaration": include_declaration,
            },
            "references": [r.model_dump() for r in references],
            "by_file": by_file,
            "count": len(references),
            "file_count": len(by_file),
        }

        return json.dumps(output, indent=2)

    def _parse_references_result(self, result: list[dict[str, Any]]) -> list[Reference]:
        """Parse LSP references result.

        Args:
            result: List of LSP Location objects

        Returns:
            List of Reference models
        """
        references = []

        for location in result:
            if not isinstance(location, dict) or "uri" not in location:
                continue

            uri = location.get("uri", "")
            file_path = self._uri_to_path(uri)
            lsp_range = location.get("range", {})

            reference = Reference(
                file_path=file_path,
                range=self._lsp_range_to_range(lsp_range),
                preview=None,  # Could add context preview
            )
            references.append(reference)

        return references

    def _uri_to_path(self, uri: str) -> str:
        """Convert file URI to relative path.

        Args:
            uri: file:// URI

        Returns:
            Relative path string
        """
        if uri.startswith("file://"):
            path = Path(uri[7:])
            try:
                return str(path.relative_to(self.context.project_root))
            except ValueError:
                return str(path)
        return uri
