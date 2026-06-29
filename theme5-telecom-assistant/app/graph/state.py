"""
state.py — LangGraph state definition for the Telecom Assistant.

TelecomState is a TypedDict that is passed between every node in the graph.
LangGraph merges partial dicts returned by nodes into the running state,
so node functions only need to return the keys they modify.
"""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class TelecomState(TypedDict):
    """Shared state threaded through every LangGraph node.

    Fields
    ------
    session_id          : Unique session identifier (UUID).
    query               : The user's raw question or request.
    intent              : "qa" or "summarize" — set by the router node.
    history             : Conversation history, list of {role, content} dicts.
    retrieved_docs      : Documents returned by the retrieval agent.
    answer              : Generated answer text.
    confidence          : Validation confidence score (0.0 – 1.0).
    needs_human_approval: True when confidence is below the threshold.
    human_approved      : Human decision (None = not yet decided).
    sources             : List of source document identifiers.
    error               : Error message if any node failed.
    """

    session_id: str
    query: str
    intent: str
    history: List[Dict[str, str]]
    retrieved_docs: List[Dict[str, Any]]
    answer: str
    confidence: float
    needs_human_approval: bool
    human_approved: Optional[bool]
    sources: List[str]
    error: Optional[str]
