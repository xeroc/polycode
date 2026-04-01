"""Context injection protocol and registry.

ContextInjectors provide key-value pairs that get merged into crew kickoff
inputs. This allows modules to inject context (like AGENTS.md content,
tech stack info, build commands) into task YAML templates without manual
threading through the flow.
"""

import logging
from typing import Any, Protocol, runtime_checkable

log = logging.getLogger(__name__)


@runtime_checkable
class ContextInjector(Protocol):
    """Plugin that provides context key-values for crew task interpolation.

    Each injector declares which keys it provides (e.g., "agents_md",
    "agents_md_map"). The registry calls collect() before each crew kickoff
    and merges all results into the inputs dict.

    Modules register injectors via get_context_injectors() on their
    PolycodeModule implementation.
    """

    name: str
    keys: list[str]

    def collect(self, state: Any) -> dict[str, Any]:
        """Gather context from flow state.

        Called before each crew kickoff. Should be idempotent and fast.

        Args:
            state: The flow's state model (BaseFlowModel or subclass).

        Returns:
            Dict of key-value pairs to merge into crew inputs.
        """
        ...


class ContextRegistry:
    """Global registry of context injectors.

    Follows the same singleton pattern as ModelRegistry. Injectors are
    registered once at bootstrap, then collect_all() is called before
    each crew kickoff to build the merged inputs dict.
    """

    _injectors: dict[str, ContextInjector] = {}

    @classmethod
    def register(cls, injector: ContextInjector) -> None:
        """Register a context injector."""
        cls._injectors[injector.name] = injector
        log.info(f"💉 Registered context injector: {injector.name} (keys: {injector.keys})")

    @classmethod
    def collect_all(cls, state: Any) -> dict[str, Any]:
        """Collect context from all registered injectors.

        Args:
            state: The flow's state model.

        Returns:
            Merged dict from all injectors. Later injectors overwrite
            earlier ones on key collision (logged as warning).
        """
        result: dict[str, Any] = {}
        for injector in cls._injectors.values():
            try:
                collected = injector.collect(state)
                overlap = set(result.keys()) & set(collected.keys())
                if overlap:
                    log.warning(f"⚠️ Injector '{injector.name}' overwrites keys: {overlap}")
                result.update(collected)
            except Exception as e:
                log.warning(f"⚠️ Injector '{injector.name}' collect() failed: {e}")
        return result

    @classmethod
    def get_injectors(cls) -> dict[str, ContextInjector]:
        """Return all registered injectors."""
        return dict(cls._injectors)

    @classmethod
    def reset(cls) -> None:
        """Clear registry (for testing)."""
        cls._injectors.clear()
