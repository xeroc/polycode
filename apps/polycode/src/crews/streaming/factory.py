"""Factory for creating streaming-enabled LLMs."""

from typing import Any

from crewai import LLM

from .callback import RedisStreamingCallback


def create_streaming_llm(
    model: str,
    session_id: str,
    room: str,
    task_id: str | None = None,
    **llm_kwargs: Any,
) -> LLM:
    """Create a CrewAI LLM with Redis streaming enabled.

    Args:
        model: Model identifier (e.g., "openai/gpt-4o")
        session_id: Unique session/flow identifier
        room: Socket.IO room name (typically "owner/repo")
        task_id: Optional task identifier
        **llm_kwargs: Additional LLM configuration options

    Returns:
        Configured LLM with streaming callback attached

    Example:
        llm = create_streaming_llm(
            model="openai/gpt-4o",
            session_id="flow-123",
            room="owner/repo",
            temperature=0.7,
        )
        agent = Agent(role="Dev", llm=llm, ...)
    """
    callback = RedisStreamingCallback(
        session_id=session_id,
        room=room,
        task_id=task_id,
    )

    return LLM(
        model=model,
        streaming=True,
        callbacks=[callback],
        **llm_kwargs,
    )
