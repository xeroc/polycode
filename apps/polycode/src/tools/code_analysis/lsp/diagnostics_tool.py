"""Diagnostics tool - get errors and warnings via LSP."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from tools.code_analysis.lsp.base import BaseLSPTool, LSPToolInput
from tools.code_analysis.lsp.client_pool import get_client_pool
from tools.code_analysis.types import Diagnostic, DiagnosticsResult

log = logging.getLogger(__name__)


class DiagnosticsToolInput(LSPToolInput):
    """Input schema for diagnostics tool."""

    severity: list[str] | None = Field(
        default=None,
        description="Filter by severity: error, warning, information, hint",
    )


class DiagnosticsTool(BaseLSPTool):
    """Get diagnostics (errors/warnings) for a file.

    Uses LSP textDocument/diagnostic or pull-based diagnostics.
    """

    name: str = "get_diagnostics"
    description: str = (
        "Get all diagnostics (errors, warnings) for a file. "
        "Returns a list of issues with severity, message, and location."
    )
    args_schema: type[BaseModel] = DiagnosticsToolInput

    # LSP severity mapping
    SEVERITY_MAP: ClassVar[dict[int, str]] = {
        1: "error",
        2: "warning",
        3: "information",
        4: "hint",
    }

    def _run(
        self,
        file_path: str,
        severity: list[str] | None = None,
    ) -> str:
        """Get diagnostics for file."""
        return self._run_async(self._run_async_impl(file_path, severity))

    async def _run_async_impl(
        self,
        file_path: str,
        severity: list[str] | None,
    ) -> str:
        """Async implementation of diagnostics."""
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

        # Try pull diagnostics first (LSP 3.17+)
        diagnostics = await self._try_pull_diagnostics(client, resolved_path)

        # Fall back to waiting for publish diagnostics
        if diagnostics is None:
            diagnostics = await self._wait_for_diagnostics(client, resolved_path)

        if diagnostics is None:
            diagnostics = []

        # Filter by severity if requested
        if severity:
            diagnostics = [d for d in diagnostics if d.severity in severity]

        # Count by severity
        error_count = sum(1 for d in diagnostics if d.severity == "error")
        warning_count = sum(1 for d in diagnostics if d.severity == "warning")

        result = DiagnosticsResult(
            file_path=file_path,
            diagnostics=diagnostics,
            error_count=error_count,
            warning_count=warning_count,
        )

        return result.model_dump_json(indent=2)

    async def _try_pull_diagnostics(self, client: Any, file_path: Path) -> list[Diagnostic] | None:
        """Try pull diagnostics (textDocument/diagnostic).

        Args:
            client: LSP client
            file_path: File to get diagnostics for

        Returns:
            List of diagnostics or None if not supported
        """
        try:
            params = {
                "textDocument": {"uri": file_path.as_uri()},
            }

            response = await client.send_request("textDocument/diagnostic", params, timeout=5.0)

            if not response or "result" not in response:
                return None

            result = response["result"]
            if result is None:
                return []

            # Handle full document diagnostic report
            if isinstance(result, dict) and "items" in result:
                items = result["items"]
            elif isinstance(result, list):
                items = result
            else:
                return None

            return [self._parse_diagnostic(d, file_path) for d in items]

        except Exception as e:
            log.debug(f"Pull diagnostics not available: {e}")
            return None

    async def _wait_for_diagnostics(
        self, client: Any, file_path: Path, timeout: float = 3.0
    ) -> list[Diagnostic] | None:
        """Wait for published diagnostics.

        After opening a document, the server may publish diagnostics.
        This method waits for them.

        Args:
            client: LSP client
            file_path: File to get diagnostics for
            timeout: How long to wait for diagnostics

        Returns:
            List of diagnostics or None
        """
        # For now, we'll poll a few times
        # In a full implementation, we'd register a handler for
        # textDocument/publishDiagnostics

        await asyncio.sleep(0.5)  # Give server time to publish

        # Since pygls doesn't easily expose a way to capture notifications,
        # we return an empty list and rely on pull diagnostics
        return []

    def _parse_diagnostic(self, lsp_diagnostic: dict[str, Any], file_path: Path) -> Diagnostic:
        """Parse LSP Diagnostic to our Diagnostic model.

        Args:
            lsp_diagnostic: LSP Diagnostic dict
            file_path: File the diagnostic is for

        Returns:
            Diagnostic model
        """
        severity_code = lsp_diagnostic.get("severity", 3)
        severity = self.SEVERITY_MAP.get(severity_code, "information")

        lsp_range = lsp_diagnostic.get("range", {})

        # Parse related information if available
        related = lsp_diagnostic.get("relatedInformation", [])
        suggested_fixes = []
        for info in related:
            location = info.get("location", {})
            message = info.get("message", "")
            if location and message:
                suggested_fixes.append(
                    {
                        "message": message,
                        "location": self._uri_to_path(location.get("uri", "")),
                    }
                )

        return Diagnostic(
            file_path=str(file_path.relative_to(self.context.project_root)),
            range=self._lsp_range_to_range(lsp_range),
            severity=severity,
            message=lsp_diagnostic.get("message", "Unknown error"),
            source=lsp_diagnostic.get("source"),
            code=str(lsp_diagnostic.get("code", "")) if lsp_diagnostic.get("code") else None,
            suggested_fixes=suggested_fixes,
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
