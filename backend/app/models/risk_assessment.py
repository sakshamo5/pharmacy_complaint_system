import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class RiskAssessment(Base):
    """
    AI-generated risk assessment for a complaint.
    Populated by the risk_assessment_tool in LangGraph.
    Maps to the 'AI Copilot Risk Assessment' section in the UI.
    """
    __tablename__ = "risk_assessments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    complaint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False
    )

    # Severity: "Critical" | "Major" | "Minor"
    severity_level: Mapped[str | None] = mapped_column(String(50))
    # Risk score 1-10 per ICH Q9 (severity × probability)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    # E.g., "Route to QA Investigation + Issue Replacement"
    recommended_action: Mapped[str | None] = mapped_column(Text)
    # E.g., "Probable root cause: Moisture ingress due to compromised blister seal"
    root_cause_hypothesis: Mapped[str | None] = mapped_column(Text)
    # CAPA required per ICH Q10
    capa_required: Mapped[bool | None] = mapped_column(Boolean)
    # Whether regulatory body must be notified (FDA 21 CFR Part 314)
    regulatory_report_required: Mapped[bool | None] = mapped_column(Boolean)
    # "High" | "Medium" | "Low" | "None"
    recall_risk: Mapped[str | None] = mapped_column(String(50))
    # Full AI reasoning text displayed in copilot
    ai_reasoning: Mapped[str | None] = mapped_column(Text)
    # CAPA action steps from bonus tool
    capa_steps: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<RiskAssessment complaint={self.complaint_id} severity={self.severity_level}>"
