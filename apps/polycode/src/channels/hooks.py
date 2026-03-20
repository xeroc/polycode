"""Hook implementations for the channels module.

Sends notifications through configured channels at various flow events.
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
from modules.hooks import FlowEvent, hookimpl

log = logging.getLogger(__name__)


class ChannelHooks:
    """Lifecycle hooks for sending notifications through channels."""

    @hookimpl
    def on_flow_event(
        self,
        event: FlowEvent,
        flow_id: str,
        state: Any,
        result: Any | None = None,
        label: str = "",
    ) -> None:
        """Send notifications at key flow events.

        Args:
            event: Current flow event
            flow_id: Flow identifier
            state: Flow state object
            result: Event result (if any)
            label: Context label (e.g., "plan", "implement")
        """
        log.info(f"🎣 Hook called in {__name__}")
        if not hasattr(state, "project_config") or not state.project_config:  # type: ignore[attr-defined]
            return

        dispatcher = self._get_dispatcher(state)
        if not dispatcher:
            return

        notification = self._create_notification(event, flow_id, state, result, label)
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

    def _create_notification(
        self,
        event: FlowEvent,
        flow_id: str,
        state: Any,
        result: Any | None,
        label: str,
    ) -> Notification | None:
        """Create notification for a flow event.

        Args:
            event: Current flow event
            flow_id: Flow identifier
            state: Flow state object
            result: Event result
            label: Context label

        Returns:
            Notification or None if event doesn't need notification
        """
        event_messages = {
            FlowEvent.FLOW_STARTED: (
                f"Flow started: {label}" if label else "Flow started",
                NotificationLevel.INFO,
            ),
            FlowEvent.STORY_COMPLETED: (
                f"Story completed: {label}" if label else "Story completed",
                NotificationLevel.SUCCESS,
            ),
            FlowEvent.FLOW_FINISHED: (
                f"Flow finished: {getattr(state, 'pr_url', 'N/A')}",
                NotificationLevel.SUCCESS,
            ),
            FlowEvent.FLOW_ERROR: (
                f"Flow error: {result}",
                NotificationLevel.ERROR,
            ),
            FlowEvent.CREW_FINISHED: (
                f"Crew finished: {label}" if label else "Crew finished",
                NotificationLevel.INFO,
            ),
        }

        if event not in event_messages:
            return None

        content, level = event_messages[event]

        context: dict[str, Any] = {}
        if hasattr(state, "issue_id"):
            context["issue_id"] = state.issue_id  # type: ignore[attr-defined]

        return Notification(
            content=content,
            level=level,
            context=context,
            metadata={"flow_id": flow_id, "event": event.value, "label": label},
        )
