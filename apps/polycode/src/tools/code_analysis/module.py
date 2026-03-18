"""Code Analysis module for Polycode.

Provides tree-sitter (structural) and LSP (semantic) code analysis
tools for Polycode agents.
"""

import logging
import os
from pathlib import Path
from typing import ClassVar

import pluggy

from modules.context import ModuleContext
from modules.hooks import FlowPhase, hookimpl

log = logging.getLogger(__name__)


class CodeAnalysisModule:
    """Code Analysis module: structural and semantic code analysis.

    This module provides:
        - Tree-sitter based structural analysis (skeleton, symbols, imports/queries)
        - LSP based semantic analysis (hover/definitions/references/diagnostics)

        The tools integrate with CrewAI agents for code understanding tasks.
    """

    name: ClassVar[str] = "code_analysis"
    version: ClassVar[str] = "0.0.1"
    dependencies: ClassVar[list[str]] = []

    @classmethod
    def on_load(cls, context: ModuleContext) -> None:
        """Initialize code analysis module.

        - Configure project root from context
        - Verify LSP servers are available (optional)
        - Initialize tree-sitter parsers
        """
        config = context.get_module_config("code_analysis")
        project_root = config.get("project_root", context.project_root)

        # Ensure project_root is set
        if not project_root:
            project_root = os.getcwd()

        cls._project_root = Path(project_root)
        log.info(f"📊 Code analysis module initialized with project_root={project_root}")

        # Pre-warm tree-sitter parsers for common languages
        from tools.code_analysis.language_support import get_language_support

        lang_support = get_language_support()
        available = lang_support.get_available_languages()
        log.info(f"📊 Available tree-sitter grammars: {available}")

    @classmethod
    def register_hooks(cls, hook_manager: pluggy.PluginManager) -> None:
        """Register code analysis hooks.

        Hooks provide automatic code analysis at flow phases:
        - POST_IMPLEMENT: Analyze changed files for issues
        - PRE_COMMIT: Run diagnostics on staged files
        """
        hook_manager.register(CodeAnalysisHooks())

    @classmethod
    def get_models(cls) -> list[type]:
        """Return ORM model classes for this module.

        Returns:
            Empty list - no models in this module
        """
        return []

    @classmethod
    def get_tools(cls, project_root: Path | None = None) -> list:
        """Get all code analysis tools for agent use.

        Args:
            project_root: Optional project root override

        Returns:
            List of CrewAI tool instances
        """
        from tools.code_analysis import create_lsp_tools

        root = project_root or cls._project_root
        return create_lsp_tools(root)


class CodeAnalysisHooks:
    """Lifecycle hooks for code analysis."""

    @hookimpl
    def on_flow_phase(self, phase: FlowPhase, flow_id: str, state: object, result: object | None = None) -> None:
        """Run code analysis at relevant phases.

        Args:
            phase: Current flow phase
            flow_id: Flow instance identifier
            state: Flow state (read-only)
            result: Result from the phase method (if any)
        """
        if phase == FlowPhase.POST_IMPLEMENT:
            log.debug(f"📊 Code analysis hook: {phase} for flow {flow_id}")
            # Could analyze changed files here

        elif phase == FlowPhase.PRE_COMMIT:
            log.debug(f"📊 Code analysis hook: {phase} for flow {flow_id}")
            # Could run diagnostics on staged files

    @hookimpl
    def on_flow_error(self, flow_id: str, state: object, error: Exception) -> bool | None:
        """Analyze code when errors occur.

        Could provide diagnostic context for errors.

        Returns:
            None to let error propagate, True to suppress.
        """
        log.debug(f"📊 Code analysis error hook for flow {flow_id}: {error}")
        return None


# Module-level export
MODULE = CodeAnalysisModule
