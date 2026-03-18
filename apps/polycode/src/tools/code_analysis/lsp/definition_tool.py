"""Definition tool - go to definition via LSP."""

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from tools.code_analysis.lsp.base import BaseLSPTool, PositionInput
from tools.code_analysis.lsp.client_pool import get_client_pool
from tools.code_analysis.types import Definition

log = logging.getLogger(__name__)


class DefinitionToolInput(PositionInput):
    """Input schema for definition tool."""



class DefinitionTool(BaseLSPTool):
    """Go to definition of symbol at position.

    Uses LSP textDocument/definition to find where a symbol is defined.
    """

    name: str = "go_to_definition"
    description: str = (
        "Find the definition of a symbol at a specific position in a file. "
        "Returns the file path and range where the symbol is defined."
    )
    args_schema: type[BaseModel] = DefinitionToolInput

    def _run(self, file_path: str, line: int, column: int) -> str:
        """Get definition at position."""
        return self._run_async(self._run_async_impl(file_path, line, column))

    async def _run_async_impl(self, file_path: str, line: int, column: int) -> str:
        """Async implementation of definition lookup."""
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

        # Request definition
        params = {
            "textDocument": {"uri": resolved_path.as_uri()},
            "position": self._get_position(line, column),
        }

        response = await client.send_request("textDocument/definition", params)

        if not response or "result" not in response:
            return json.dumps({"error": "No definition found"})

        result = response["result"]
        if not result:
            return json.dumps({"error": "No definition found at this position"})

        # Parse definition result
        definitions = self._parse_definition_result(result, resolved_path)

        if not definitions:
            return json.dumps({"error": "Could not parse definition result"})

        # Return as JSON
        output = {
            "query": {
                "file_path": file_path,
                "line": line,
                "column": column,
            },
            "definitions": [d.model_dump() for d in definitions],
            "count": len(definitions),
        }

        return json.dumps(output, indent=2)

    def _parse_definition_result(self, result: Any, source_file: Path) -> list[Definition]:
        """Parse LSP definition result.

        Args:
            result: LSP definition result (Location, LocationLink, or array)
            source_file: The file where the query was made

        Returns:
            List of Definition models
        """
        definitions = []

        # Handle single Location
        if isinstance(result, dict):
            if "uri" in result:
                definitions.append(self._parse_location(result))
            elif "targetUri" in result:
                # LocationLink
                definitions.append(self._parse_location_link(result))

        # Handle array of locations
        elif isinstance(result, list):
            for item in result:
                if isinstance(item, dict):
                    if "uri" in item:
                        definitions.append(self._parse_location(item))
                    elif "targetUri" in item:
                        definitions.append(self._parse_location_link(item))

        return definitions

    def _parse_location(self, location: dict[str, Any]) -> Definition:
        """Parse LSP Location to Definition.

        Args:
            location: LSP Location dict

        Returns:
            Definition model
        """
        uri = location.get("uri", "")
        file_path = self._uri_to_path(uri)
        lsp_range = location.get("range", {})

        return Definition(
            file_path=file_path,
            range=self._lsp_range_to_range(lsp_range),
            preview=None,  # Could add file content preview here
        )

    def _parse_location_link(self, link: dict[str, Any]) -> Definition:
        """Parse LSP LocationLink to Definition.

        Args:
            link: LSP LocationLink dict

        Returns:
            Definition model
        """
        uri = link.get("targetUri", "")
        file_path = self._uri_to_path(uri)
        lsp_range = link.get("targetSelectionRange", link.get("targetRange", {}))

        return Definition(
            file_path=file_path,
            range=self._lsp_range_to_range(lsp_range),
            preview=None,
        )

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
