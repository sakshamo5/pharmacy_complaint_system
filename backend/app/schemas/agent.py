"""Pydantic schemas for AI agent chat messages and SSE events."""
from __future__ import annotations
from typing import Optional, Any
from pydantic import BaseModel
from app.schemas.complaint import ComplaintData
from app.schemas.risk_assessment import RiskAssessmentData


class ChatHistoryItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    """Incoming chat message from frontend."""
    message: str
    thread_id: str
    complaint_id: Optional[str] = None  # Set when editing an existing complaint
    current_complaint: Optional[dict] = None  # Current form values in frontend
    history: Optional[list[ChatHistoryItem]] = None  # Previous message history


class SaveComplaintRequest(BaseModel):
    """
    Explicit save — called when the user clicks "Save Complaint".
    The graph streams extraction/assessment but no longer persists until this.
    """
    thread_id: str
    complaint_id: Optional[str] = None  # Present when updating an existing record
    complaint: dict                          # Form fields (ComplaintData shape)
    risk_assessment: Optional[dict] = None   # AI Copilot risk output
    intake_source: str = "text_prompt"


class SaveComplaintResponse(BaseModel):
    id: str
    complaint_number: str
    status: str


class SSEEvent(BaseModel):
    """
    Server-Sent Event envelope.
    type values consumed by the frontend useSSEStream hook:
      - "thinking"         : Agent is reasoning (shows typing indicator)
      - "tool_call"        : Which tool is being invoked
      - "complaint_update" : Triggers populateFromAI() in Redux
      - "risk_update"      : Populates AI Copilot risk panel
      - "message"          : Final AI text response shown in chat
      - "warning"          : Duplicate complaint warning (bonus)
      - "error"            : Recoverable error message
      - "done"             : Stream complete
    """
    type: str
    content: Optional[str] = None
    tool: Optional[str] = None
    data: Optional[Any] = None
    progress: Optional[int] = None   # 0–100 for document extraction progress bar


class DuplicateWarning(BaseModel):
    """Emitted when duplicate detection finds a similar complaint."""
    similar_complaint_number: str
    similarity_score: float
    similar_complaint_id: str
    message: str
