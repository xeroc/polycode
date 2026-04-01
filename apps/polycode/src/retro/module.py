"""Retro module — continuous improvement via git-notes retrospectives."""

import logging
from typing import Any

import pluggy

from modules.context import ModuleContext

log = logging.getLogger(__name__)


class RetroModule:
    """Retro module: per-commit retrospectives attached via git-notes."""

    name: str = "retro"
    version: str = "0.1.0"
    dependencies: list[str] = ["gitcore"]

    @classmethod
    def on_load(cls, context: ModuleContext) -> None:
        log.info(f"📦 Retro module loaded (v{cls.version})")

    @classmethod
    def get_tasks(cls) -> list[dict[str, Any]]:
        return []

    @classmethod
    def get_flows(cls) -> list:
        return []

    @classmethod
    def register_hooks(cls, hook_manager: pluggy.PluginManager) -> None:
        from retro.hooks import RetroHooks

        hook_manager.register(RetroHooks())
        log.info("🏹 Registered RetroHooks")

    @classmethod
    def get_models(cls) -> list[type]:
        return []

    @classmethod
    def get_context_collectors(cls) -> list[tuple[str, Any]]:
        return [("retro", cls._collect_retro_context)]

    @classmethod
    def _collect_retro_context(cls, state: Any) -> dict[str, Any]:
        repo = getattr(state, "repo", None)
        if not repo:
            return {"retro_context": ""}

        repo_owner = getattr(state, "repo_owner", "")
        repo_name = getattr(state, "repo_name", "")

        from retro.analyzer import PatternAnalyzer

        try:
            analyzer = PatternAnalyzer(repo)
            context = analyzer.generate_context_injection(
                repo_owner=repo_owner,
                repo_name=repo_name,
                limit=5,
            )
            return {"retro_context": context}
        except Exception as e:
            log.warning(f"⚠️ Retro context collection failed: {e}")
            return {"retro_context": ""}
