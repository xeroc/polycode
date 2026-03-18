"""Hover tool - get type information at cursor position."""

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from tools.code_analysis.lsp.base import BaseLSPTool, PositionInput
from tools.code_analysis.lsp.client_pool import get_client_pool
from tools.code_analysis.types import HoverInfo, Position

log = logging.getLogger(__name__)


class HoverToolInput(PositionInput):
    """Input schema for hover tool."""



class HoverTool(BaseLSPTool):
    """Get type information and documentation at a cursor position.

    Uses LSP hover to provide type signatures and docstrings.
    """

    name: str = "hover_info"
    description: str = (
        "Get type information and documentation at a specific position in a file. "
        "Returns type signature, documentation, and hover info from LSP."
    )
    args_schema: type[BaseModel] = HoverToolInput

    def _run(self, file_path: str, line: int, column: int) -> str:
        """Get hover info at position."""
        return self._run_async(self._run_async_hover(file_path, line, column))

    async def _run_async_hover(self, file_path: str, line: int, column: int) -> str:
        """Async implementation of hover."""
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

        # Request hover
        params = {
            "textDocument": {"uri": resolved_path.as_uri()},
            "position": self._get_position(line, column),
        }

        response = await client.send_request("textDocument/hover", params)

        if not response or "result" not in response:
            return json.dumps({"error": "No hover information available at this position"})

        result = response["result"]
        if not result:
            return json.dumps({"error": "No hover information available"})

        # Parse hover result
        hover_info = self._parse_hover_result(result, resolved_path, line, column)

        return hover_info.model_dump_json(indent=2)

    def _parse_hover_result(self, result: dict[str, Any], file_path: Path, line: int, column: int) -> HoverInfo:
        """Parse LSP hover result into HoverInfo model."""
        contents = result.get("contents", "")
        # lsp_range available if needed: result.get("range")

        type_info = None
        documentation = None
        signature = None

        # Parse contents
        if isinstance(contents, str):
            documentation = contents
        elif isinstance(contents, list):
            # MarkedString array
            parts = []
            for item in contents:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get("value", ""))
            documentation = "\n\n".join(parts)
        elif isinstance(contents, dict):
            # MarkupContent
            value = contents.get("value", "")
            kind = contents.get("kind", "plaintext")

            if kind == "markdown":
                # Try to extract type from markdown
                lines = value.split("\n")
                type_lines = []
                doc_lines = []
                in_code = False

                for line_text in lines:
                    if line_text.startswith("```"):
                        in_code = not in_code
                        continue
                    if in_code:
                        type_lines.append(line_text)
                    else:
                        doc_lines.append(line_text)

                if type_lines:
                    type_info = "\n".join(type_lines)
                if doc_lines:
                    documentation = "\n".join(doc_lines).strip()
            else:
                type_info = value

        # Build relative path
        try:
            relative_path = str(file_path.relative_to(self.context.project_root))
        except ValueError:
            relative_path = str(file_path)

        return HoverInfo(
            file_path=relative_path,
            position=Position(line=line, column=column),
            type_info=type_info,
            documentation=documentation,
            signature=signature,
        )
