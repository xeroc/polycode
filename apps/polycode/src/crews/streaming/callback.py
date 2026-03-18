"""CrewAI streaming callback that publishes to Redis."""

import logging
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from .publisher import publish_event, publish_token
from .types import StreamEventType

log = logging.getLogger(__name__)


class RedisStreamingCallback(BaseCallbackHandler):
    """CrewAI callback that streams LLM tokens to Redis for Socket.IO delivery.

    Usage:
        callback = RedisStreamingCallback(
            session_id="flow-123",
            room="owner/repo"
        )

        llm = LLM(
            model="openai/gpt-4o",
            streaming=True,
            callbacks=[callback],
        )

        agent = Agent(role="...", llm=llm, ...)
    """

    def __init__(
        self,
        session_id: str,
        room: str,
        task_id: str | None = None,
    ):
        self.session_id = session_id
        self.room = room
        self.task_id = task_id
        self._current_agent_role: str | None = None

    def on_llm_start(self, serialized, prompts, **kwargs):
        agent_role = kwargs.get("invocation_params", {}).get("agent_role")
        if agent_role:
            self._current_agent_role = agent_role
            publish_event(
                session_id=self.session_id,
                room=self.room,
                event_type=StreamEventType.AGENT_START,
                agent_role=agent_role,
                task_id=self.task_id,
            )

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        publish_token(
            session_id=self.session_id,
            room=self.room,
            token=token,
            agent_role=self._current_agent_role,
            task_id=self.task_id,
        )

    def on_llm_end(self, response, **kwargs: Any) -> None:
        if self._current_agent_role:
            publish_event(
                session_id=self.session_id,
                room=self.room,
                event_type=StreamEventType.AGENT_END,
                agent_role=self._current_agent_role,
                task_id=self.task_id,
            )

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        publish_event(
            session_id=self.session_id,
            room=self.room,
            event_type=StreamEventType.ERROR,
            agent_role=self._current_agent_role,
            task_id=self.task_id,
            data={"error": str(error)},
        )
        log.error(f"LLM error in streaming callback: {error}")

    def on_chain_start(self, serialized, inputs, **kwargs):
        if "task" in kwargs.get("tags", []):
            publish_event(
                session_id=self.session_id,
                room=self.room,
                event_type=StreamEventType.TASK_START,
                task_id=self.task_id,
                data={"inputs": inputs},
            )

    def on_chain_end(self, outputs, **kwargs):
        if "task" in kwargs.get("tags", []):
            publish_event(
                session_id=self.session_id,
                room=self.room,
                event_type=StreamEventType.TASK_END,
                task_id=self.task_id,
                data={"outputs": str(outputs)[:500]},
            )
