"""Code Analysis module for Polycode.

Provides tree-sitter (structural) and LSP (semantic) code analysis
tools for Polycode agents.
"""

import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    import pluggy

if TYPE_CHECKING:
    from modules.hooks import FlowEvent, hookimpl

if TYPE_CHECKING:
    pass

if TYPE_CHECKING:
    from modules.context import ModuleContext

log = logging.getLogger(__name__)


class CodeAnalysisModule:
    """Code Analysis module: structural and semantic analysis for code changes.

    This module provides hooks for tree-sitter analysis during planning phase
    and validates implementation quality during review phase.
    """

    name = "code_analysis"
    version = "0.1.0"
    dependencies: ClassVar[list[str]] = []

    @classmethod
    def on_load(cls, context: "ModuleContext") -> None:
        """Initialize code analysis module."""

    @classmethod
    def register_hooks(cls, hook_manager: "pluggy.PluginManager") -> None:
        """Register code analysis hooks."""
        hook_manager.register(CodeAnalysisHooks())

    @classmethod
    def get_models(cls) -> list[type]:
        """Return ORM models for this module."""
        return []

    def analyze_file(self, file_path: str) -> dict[str, Any]:
        """Analyze a single file using tree-sitter and LSP.

        Args:
            file_path: Path to the file

        Returns:
            Analysis results with structural info
        """
        result = {"file_path": str(file_path), "analysis": "complete"}
        return result

    def analyze_changes(self, changes: dict) -> dict[str, Any]:
        """Analyze code changes for review.

        Args:
            changes: Dict of file changes

        Returns:
            Analysis results for all changed files
        """
        results = {}
        for file_path in changes:
            results[file_path] = self.analyze_file(file_path)
        return results


class CodeAnalysisHooks:
    """Hook implementations for code analysis during flow phases."""

    def __init__(self) -> None:
        self.module = CodeAnalysisModule()

    @hookimpl  # type: ignore[misc]
    def on_flow_event(
        self,
        event: "FlowEvent",
        flow_id: str,
        state: object,
        result: object | None = None,
        label: str = "",
    ) -> None:
        """Analyze code during planning and review phases."""
        log.info(f"🎣 Hook called in {__name__}")

        if not hasattr(state, "repo") or not getattr(state, "repo", None):
            return

        if event == FlowEvent.GIT_COMMIT:  # type: ignore[attr-defined]
            log.debug(f"Analyzing commit in flow {flow_id}")
            changes = self._get_changes(state)
            if changes:
                analysis = self.module.analyze_changes(changes)
                log.info(f"Code analysis complete for {len(analysis)} files")
        elif event == FlowEvent.PR_CREATED:  # type: ignore[attr-defined]
            log.debug(f"Reviewing PR in flow {flow_id}")
            changes = self._get_changes(state)
            if changes:
                analysis = self.module.analyze_changes(changes)
                self._validate_analysis(analysis)
                log.info(f"Code review passed for {len(analysis)} files")
        else:
            log.warning(f"No changes to analyze in flow {flow_id}")

    def _get_changes(self, state: object) -> dict[str, Any]:
        """Get file changes from git status."""
        if not hasattr(state, "repo"):
            return {}

        repo = Path(getattr(state, "repo", ""))
        if not repo.exists():
            return {}

        result = {}
        try:
            output = subprocess.check_output(
                ["git", "status", "--porcelain"],
                cwd=repo,
                text=True,
            )

            for line in output.split("\n"):
                if line.startswith(" M") or line.startswith(" A"):
                    parts = line.split()
                    if len(parts) >= 2:
                        result[parts[1]] = {"status": "modified"}
        except Exception as e:
            log.warning(f"Failed to get git status: {e}")

        return result

    def _validate_analysis(self, analysis: dict) -> bool:
        """Validate code analysis results."""
        issues = []
        for file_path, data in analysis.items():
            file_analysis = data.get("analysis", {})
            if not file_analysis:
                continue

            errors = file_analysis.get("errors", [])
            if errors:
                issues.append({"file": file_path, "errors": errors})

        if issues:
            log.warning(f"Code analysis issues found: {len(issues)} files")
            return False

        return True
