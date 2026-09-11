"""
Pydantic schemas for complaints.
These validate API request/response bodies and also serve as
the structured output format that LangGraph tools return.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Complaint Data (the form fields extracted by AI) ─────────────────────────

class ComplaintData(BaseModel):
    """
    Represents extracted complaint fields — maps exactly to the form sections.
    All fields are Optional because AI may only extract partial information.
    """
    # Section 1: Origin & Customer
    complaint_source: Optional[str] = Field(None, description="Source of complaint (e.g., Apollo Pharmacy)")
    customer_name: Optional[str] = Field(None, description="Name of the customer or reporter")
    customer_contact: Optional[str] = Field(None, description="Customer contact information")
    reporter_type: Optional[str] = Field(None, description="Patient / Distributor / HCP / Pharmacy")

    # Section 2: Product & Batch
    product_name: Optional[str] = Field(None, description="Full pharmaceutical product name")
    product_strength: Optional[str] = Field(None, description="Dosage strength or API grade (e.g., 500 mg, IP/BP)")
    product_type: Optional[str] = Field(None, description="API or FDF")
    batch_number: Optional[str] = Field(None, description="Manufacturing batch number")
    lot_number: Optional[str] = Field(None, description="Lot number (may differ from batch)")
    manufacturing_date: Optional[str] = Field(None, description="Date of manufacture (YYYY-MM-DD or text)")
    expiry_date: Optional[str] = Field(None, description="Expiry date (YYYY-MM-DD or text)")
    quantity_affected: Optional[str] = Field(None, description="Affected quantity with units (e.g., 48 capsules, 50 kg)")

    # Section 3: Complaint Details
    complaint_type: Optional[str] = Field(None, description="Type: Quality / Packaging / Labeling / Safety")
    complaint_date: Optional[str] = Field(None, description="Date complaint was raised")
    description: Optional[str] = Field(None, description="Detailed description of the complaint")

    # Section 4: Assessment
    initial_severity: Optional[str] = Field(None, description="Critical / Major / Minor")
    priority: Optional[str] = Field(None, description="Immediate / High / Medium / Low")

    class Config:
        # Allow partial updates (none of the fields required)
        populate_by_name = True


# ── API Request / Response Schemas ───────────────────────────────────────────

class ComplaintCreate(ComplaintData):
    """Schema for creating a new complaint record."""
    thread_id: Optional[str] = None
    intake_source: Optional[str] = "text_prompt"


class ComplaintUpdate(ComplaintData):
    """Schema for partial updates — all fields optional."""
    status: Optional[str] = None
    thread_id: Optional[str] = None


class ComplaintResponse(BaseModel):
    """Full complaint record returned from API."""
    id: uuid.UUID
    complaint_number: str
    status: str
    thread_id: Optional[str] = None
    intake_source: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Form fields (re-declared for response)
    complaint_source: Optional[str] = None
    customer_name: Optional[str] = None
    customer_contact: Optional[str] = None
    reporter_type: Optional[str] = None
    product_name: Optional[str] = None
    product_strength: Optional[str] = None
    product_type: Optional[str] = None
    batch_number: Optional[str] = None
    lot_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    quantity_affected: Optional[str] = None
    complaint_type: Optional[str] = None
    complaint_date: Optional[str] = None
    description: Optional[str] = None
    initial_severity: Optional[str] = None
    priority: Optional[str] = None

    class Config:
        from_attributes = True  # Allows ORM model → Pydantic conversion


class ComplaintListResponse(BaseModel):
    """Paginated list response."""
    items: list[ComplaintResponse]
    total: int
    page: int
    page_size: int
