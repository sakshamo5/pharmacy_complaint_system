import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Complaint(Base):
    """
    Core complaint table — mirrors the Log Customer Complaint form exactly.
    Each field maps directly to a form field shown in the UI.
    """
    __tablename__ = "complaints"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Human-readable complaint reference number (e.g., CC-2024-0001)
    complaint_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Triage status: "Pending Triage" | "Under Investigation" | "Closed" | "Escalated"
    status: Mapped[str] = mapped_column(String(50), default="Pending Triage")

    # ── Section 1: Origin & Customer Details ──────────────────────────────────
    complaint_source: Mapped[str | None] = mapped_column(String(255))
    customer_name: Mapped[str | None] = mapped_column(String(255))
    customer_contact: Mapped[str | None] = mapped_column(String(255))
    reporter_type: Mapped[str | None] = mapped_column(String(100))

    # ── Section 2: Product & Batch Identification ─────────────────────────────
    product_name: Mapped[str | None] = mapped_column(String(255))
    product_strength: Mapped[str | None] = mapped_column(String(100))
    product_type: Mapped[str | None] = mapped_column(String(50))   # API or FDF
    batch_number: Mapped[str | None] = mapped_column(String(100))
    lot_number: Mapped[str | None] = mapped_column(String(100))
    manufacturing_date: Mapped[str | None] = mapped_column(String(50))
    expiry_date: Mapped[str | None] = mapped_column(String(50))
    quantity_affected: Mapped[str | None] = mapped_column(String(100))

    # ── Section 3: Complaint Details ──────────────────────────────────────────
    complaint_type: Mapped[str | None] = mapped_column(String(100))
    complaint_date: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)

    # ── Section 4: Initial Assessment & Priority ──────────────────────────────
    initial_severity: Mapped[str | None] = mapped_column(String(50))
    priority: Mapped[str | None] = mapped_column(String(50))

    # ── AI / Session Metadata ─────────────────────────────────────────────────
    # The LangGraph thread_id links this complaint to its conversation history
    thread_id: Mapped[str | None] = mapped_column(String(100), index=True)

    # Source of complaint data: "text_prompt" | "document_upload" | "manual"
    intake_source: Mapped[str | None] = mapped_column(String(50))

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Complaint {self.complaint_number}: {self.product_name}>"


# Composite index used by duplicate detection (product + date window).
__table_args__ = (
    Index("ix_complaints_product_date", "product_name", "complaint_date"),
)
