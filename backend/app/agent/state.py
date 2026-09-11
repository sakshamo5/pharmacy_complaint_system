"""
LangGraph Agent State Definition
The AgentState TypedDict is the single shared data structure 
passed between every node in the LangGraph StateGraph.
"""
from __future__ import annotations
from typing import Annotated, Optional, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    The complete state passed between every node in the complaint graph.
    
    LangGraph uses this as a checkpoint — it persists this between
    conversation turns so the agent remembers past messages and 
    the current complaint state without needing a DB lookup.
    
    Key design decisions:
    - messages uses add_messages reducer (appends, never overwrites)
    - complaint_data is a plain dict (not Pydantic) for easy LangGraph serialization
    - All fields Optional so the graph can start with minimal input
    """
    # Full conversation history — add_messages reducer appends new messages
    messages: Annotated[list, add_messages]

    # Intent classified by the first node
    # Values: "log" | "edit" | "document" | "query"
    intent: Optional[str]

    # The extracted complaint form data (mirrors ComplaintData schema)
    complaint_data: Optional[dict]

    # AI Copilot risk assessment output
    risk_assessment: Optional[dict]

    # Raw text from uploaded document — populated by the API layer before graph invocation
    document_text: Optional[str]

    # DB record ID — set after first save, used for updates
    complaint_id: Optional[str]

    # LangGraph conversation thread — same across all turns in one session
    thread_id: str

    # Recoverable error message (shown in UI as error SSE event)
    error: Optional[str]

    # Whether a duplicate was detected (bonus feature)
    duplicate_warning: Optional[dict]
