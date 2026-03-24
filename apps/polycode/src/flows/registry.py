"""Flow registry for managing flow definitions."""

import logging
from typing import TYPE_CHECKING, Any

from project_manager.config import settings

from .protocol import FlowDef

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


class FlowRegistry:
    """Registry for flow definitions contributed by modules."""

    def __init__(self) -> None:
        self._flows: dict[str, FlowDef] = {}

    def register(self, flow_def: FlowDef) -> None:
        """Register a flow definition.

        Args:
            flow_def: Flow definition to register.

        Raises:
            ValueError: If flow name is empty or kickoff_func is not callable.
        """
        if not flow_def.name:
            raise ValueError("Flow name cannot be empty")
        if not callable(flow_def.kickoff_func):
            raise ValueError(f"Flow '{flow_def.name}' kickoff_func must be callable")

        if flow_def.name in self._flows:
            log.warning(f"⚠️ Flow '{flow_def.name}' already registered, overwriting")

        self._flows[flow_def.name] = flow_def
        log.info(f"📜 Registered flow: {flow_def.name}")

    def get_flow(self, name: str) -> FlowDef | None:
        """Get a flow by name.

        Args:
            name: Flow identifier.

        Returns:
            FlowDef if found, None otherwise.
        """
        return self._flows.get(name)

    def get_flow_for_label(self, label: str) -> FlowDef | None:
        """Find a flow that handles the given label.

        Matches label against each flow's supported_labels (with prefix stripping).
        Returns highest priority match.

        Args:
            label: Full label string (e.g., "polycode:implement").

        Returns:
            FlowDef if match found, None otherwise.
        """
        prefix = settings.FLOW_LABEL_PREFIX
        if not label.startswith(prefix):
            log.debug(f"Label '{label}' missing prefix '{prefix}'")
            return None

        stripped_label = label[len(prefix) :]
        matches: list[FlowDef] = []

        for flow in self._flows.values():
            if stripped_label in flow.supported_labels:
                matches.append(flow)

        if not matches:
            log.debug(f"No flow found for label '{label}'")
            return None

        matches.sort(key=lambda f: f.priority, reverse=True)
        best_match = matches[0]
        log.info(f"🎯 Flow '{best_match.name}' matched label '{label}' (priority: {best_match.priority})")
        return best_match

    def list_flows(self) -> list[str]:
        """List all registered flow names."""
        return list(self._flows.keys())

    def collect_from_modules(self, modules: dict[str, Any]) -> int:
        """Collect flows from all modules.

        Called by bootstrap() after modules are loaded.

        Args:
            modules: Dict of module_name -> module class.

        Returns:
            Number of flows collected.
        """
        count = 0
        for name, module in modules.items():
            if hasattr(module, "get_flows"):
                try:
                    flows = module.get_flows()
                    for flow in flows:
                        self.register(flow)
                        count += 1
                except Exception as e:
                    log.error(f"🚨 Module '{name}' get_flows() failed: {e}")

        log.info(f"📜 Collected {count} flows from modules")
        return count


_flow_registry: FlowRegistry | None = None


def get_flow_registry() -> FlowRegistry:
    """Get the singleton flow registry."""
    global _flow_registry
    if _flow_registry is None:
        _flow_registry = FlowRegistry()
    return _flow_registry
