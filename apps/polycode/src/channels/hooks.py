"""Hook implementations for the channels module.

Sends notifications through configured channels at various flow phases.
"""

import logging
from typing import Any

from channels.dispatcher import ChannelDispatcher
from channels.types import (
    ChannelConfig,
    ChannelType,
    Notification,
    NotificationLevel,
)
from modules.hooks import FlowPhase, hookimpl

log = logging.getLogger(__name__)


class ChannelHooks:
    """Lifecycle hooks for sending notifications through channels."""

    @hookimpl
    def on_flow_phase(self, phase: FlowPhase, flow_id: str, state: Any, result: Any = None) -> None:
        """Send notifications at key flow phases.

        Args:
            phase: Current flow phase
            flow_id: Flow identifier
            state: Flow state object
            result: Phase result (if any)
        """
        if (
            not hasattr(state, "project_config") or not state.project_config  # type: ignore[attr-defined]
        ):
            return

        dispatcher = self._get_dispatcher(state)
        if not dispatcher:
            return

        notification = self._create_notification(phase, flow_id, state, result)
        if not notification:
            return

        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(dispatcher.dispatch(notification))
            else:
                loop.run_until_complete(dispatcher.dispatch(notification))
        except Exception as e:
            log.error(f"🚨 Failed to send notification: {e}")

    def _get_dispatcher(self, state: Any) -> ChannelDispatcher | None:
        """Get channel dispatcher from state configuration.

        Args:
            state: Flow state object

        Returns:
            ChannelDispatcher or None if no channels configured
        """
        if not hasattr(state, "project_config"):
            return None

        extra = state.project_config.extra or {}  # type: ignore[attr-defined]
        channel_configs_data = extra.get("channels", [])

        if not channel_configs_data:
            return None

        configs = [
            ChannelConfig(
                channel_type=ChannelType(c["channel_type"]),
                enabled=c.get("enabled", True),
                extra=c.get("extra", {}),
            )
            for c in channel_configs_data
        ]

        return ChannelDispatcher(
            configs,
            state.project_config,  # type: ignore[attr-defined]
        )

    def _create_notification(self, phase: FlowPhase, flow_id: str, state: Any, result: Any) -> Notification | None:
        """Create notification for a flow phase.

        Args:
            phase: Current flow phase
            flow_id: Flow identifier
            state: Flow state object
            result: Phase result

        Returns:
            Notification or None if phase doesn't need notification
        """
        phase_messages = {
            FlowPhase.POST_SETUP: (
                "Flow setup complete",
                NotificationLevel.INFO,
            ),
            FlowPhase.POST_COMMIT: (
                f"Committed changes: {getattr(result, 'hexsha', 'unknown')[:7]}",
                NotificationLevel.SUCCESS,
            ),
            FlowPhase.POST_PR: (
                f"Pull request created: {getattr(state, 'pr_url', 'N/A')}",
                NotificationLevel.SUCCESS,
            ),
            FlowPhase.POST_MERGE: (
                "Pull request merged successfully",
                NotificationLevel.SUCCESS,
            ),
            FlowPhase.ON_ERROR: (
                f"Flow error: {result}",
                NotificationLevel.ERROR,
            ),
            FlowPhase.ON_COMPLETE: (
                "Flow completed successfully",
                NotificationLevel.SUCCESS,
            ),
        }

        if phase not in phase_messages:
            return None

        content, level = phase_messages[phase]

        context = {}
        if hasattr(state, "issue_id"):
            context["issue_id"] = state.issue_id  # type: ignore[attr-defined]

        return Notification(
            content=content,
            level=level,
            context=context,
            metadata={"flow_id": flow_id, "phase": phase.value},
        )
