"""Base classes for LSP-based tools.

Provides common functionality for LSP communication, position handling,
and tool input/output schemas.
"""

import json
import logging
from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, model_validator

from tools.code_analysis.context_manager import CodeContext
from tools.code_analysis.types import Range

log = logging.getLogger(__name__)


class LSPToolInput(BaseModel):
    """Base input schema for LSP tools."""

    file_path: str = Field(..., description="Path to file (relative to project root)")


class PositionInput(LSPToolInput):
    """Input schema for position-based LSP tools."""

    line: int = Field(..., description="Line number (1-indexed)")
    column: int = Field(
        ...,
        description="Column number (0-indexed, character offset from line start)",
    )


class BaseLSPTool(BaseTool):
    """Base class for LSP-based code analysis tools.

    Provides common functionality for communicating with LSP servers.
    """

    context: CodeContext = Field(default=None, exclude=True)  # type: ignore[assignment]

    @model_validator(mode="before")
    @classmethod
    def setup_context(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Set up context from project_root if not provided."""
        if isinstance(data, dict):
            if data.get("context") is None:
                project_root = data.get("project_root", Path.cwd())
                if isinstance(project_root, str):
                    project_root = Path(project_root)
                data["context"] = CodeContext(project_root=project_root)
        return data

    def _run_async(self, coro) -> str:
        """Run async coroutine from sync _run method.

        Args:
            coro: Async coroutine to run

        Returns:
            JSON string result
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
            result = loop.run_until_complete(coro)
            return result
        except Exception as e:
            log.error(f"🚨 Failed to run async: {e}")
            return json.dumps({"error": str(e)})

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve file path relative to project root."""
        path = Path(file_path)
        if path.is_absolute():
            return path
        return self.context.project_root / file_path

    async def _open_document(self, client: Any, file_path: Path, language: str) -> None:
        """Open document in LSP server.

        Args:
            client: LSP client instance
            file_path: Path to file
            language: Language name
        """
        try:
            await client.send_notification(
                "textDocument/didOpen",
                {
                    "textDocument": {
                        "uri": file_path.as_uri(),
                        "languageId": language,
                    },
                },
            )
        except Exception as e:
            log.warning(f"Failed to open document: {e}")

    def _get_position(self, line: int, column: int) -> dict[str, int]:
        """Convert line/column to LSP Position.

        Args:
            line: Line number (1-indexed)
            column: Column number (0-indexed)

        Returns:
            LSP Position dict
        """
        return {"line": line - 1, "character": column}

    def _lsp_range_to_range(self, lsp_range: dict[str, Any]) -> Range:
        """Convert LSP Range to our Range model.

        Args:
            lsp_range: LSP Range dict

        Returns:
            Range model
        """
        from tools.code_analysis.types import Position

        start_pos = lsp_range.get("start", {})
        end_pos = lsp_range.get("end", {})

        return Range(
            start=Position(
                line=start_pos.get("line", 0) + 1,
                column=start_pos.get("character", 0),
            ),
            end=Position(
                line=end_pos.get("line", 0) + 1,
                column=end_pos.get("character", 0),
            ),
        )
