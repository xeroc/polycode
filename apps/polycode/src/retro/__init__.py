"""Retrospective module for continuous improvement.

Provides:
- LLM-powered retrospective generation via CrewAI
- Git-notes storage for transportability
- PostgreSQL indexing for querying and aggregation
- Pattern analysis for identifying recurring issues
"""

from .analyzer import PatternAnalyzer
from .git_notes import GitNotes, GitNotesError
from .persistence import RetroStore, init_db
from .types import RetroEntry, RetroQuery

__all__ = [
    "RetroEntry",
    "RetroQuery",
    "GitNotes",
    "GitNotesError",
    "RetroStore",
    "init_db",
    "PatternAnalyzer",
]
