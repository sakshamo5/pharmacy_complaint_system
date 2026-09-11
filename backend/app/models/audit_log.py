import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class AuditLog(Base):
    """
    Immutable audit trail for every state change to a complaint.
    Required for GxP compliance — records who/what changed each field and when.
    """
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    complaint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False
    )

    # Action: "complaint_created" | "complaint_updated" | "document_extracted"
    #         | "risk_assessed" | "capa_recommended"
    action: Mapped[str] = mapped_column(String(100), nullable=False)

    # JSON snapshot of fields that were changed: {"batch_number": {"old": None, "new": "BMX24602"}}
    changed_fields: Mapped[dict | None] = mapped_column(JSONB)

    # Either "AI_AGENT" or specific tool name
    performed_by: Mapped[str] = mapped_column(String(100), default="AI_AGENT")

    # The LangGraph thread (conversation) that triggered this change
    thread_id: Mapped[str | None] = mapped_column(String(100))

    # Optional notes from AI about this change
    notes: Mapped[str | None] = mapped_column(Text)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} on {self.complaint_id} at {self.timestamp}>"
