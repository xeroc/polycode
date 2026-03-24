"""Flow system protocol definitions."""

from dataclasses import dataclass, field
from typing import Callable

from flows.base import KickoffIssue


@dataclass(frozen=True)
class FlowDef:
    """Definition of a flow that can be triggered by labels."""

    name: str
    """Unique flow identifier (e.g., "ralph", "code-review")."""

    kickoff_func: Callable[[KickoffIssue], None]
    """Entry point function that runs the flow. Receives KickoffIssue."""

    description: str = ""
    """Human-readable description of what this flow does."""

    supported_labels: list[str] = field(default_factory=lambda: [])
    """Labels that trigger this flow (without prefix).

    E.g., ["implement", "review"] matches "polycode:implement", "polycode:review".
    Empty list means flow can only be triggered via explicit flow_name parameter.
    """

    priority: int = 0
    """When multiple flows match a label, higher priority wins."""
