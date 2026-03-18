"""Hook implementations for the code analysis module."""

import logging

from modules.hooks import FlowPhase, hookimpl

log = logging.getLogger(__name__)


class CodeAnalysisHooks:
    """Lifecycle hooks for code analysis."""

    @hookimpl
    def on_flow_start(self, flow_id: str, state: object) -> None:
        """Called when a flow begins.

        Could trigger initial code analysis setup.
        """
        log.debug(f"🔍 Code analysis hook: flow {flow_id} started")

    @hookimpl
    def on_flow_phase(
        self,
        phase: FlowPhase,
        flow_id: str,
        state: object,
        result: object | None = None,
    ) -> None:
        """Called at each flow phase transition.

        Could perform analysis based on phase changes.
        """
        # Only log significant phases
        if phase in (
            FlowPhase.PRE_PLAN,
            FlowPhase.POST_PLAN,
            FlowPhase.PRE_IMPLEMENT,
            FlowPhase.POST_IMPLEMENT,
        ):
            log.debug(f"🔍 Code analysis hook: {phase} in flow {flow_id}")

    @hookimpl
    def on_flow_complete(self, flow_id: str, state: object) -> None:
        """Called when flow finishes successfully.

        Could perform final analysis or cleanup.
        """
        log.debug(f"🔍 Code analysis hook: flow {flow_id} completed")
