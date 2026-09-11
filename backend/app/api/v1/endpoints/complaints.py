"""
Complaint CRUD REST Endpoints
Standard REST API for complaint management.
These endpoints are used for listing, viewing, and manually managing complaints.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.complaint import ComplaintResponse, ComplaintListResponse, ComplaintUpdate
from app.crud.complaint import (
    get_complaint,
    list_complaints,
    update_complaint,
    get_complaint_history,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=ComplaintListResponse)
async def get_complaints(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all complaints with pagination."""
    items, total = await list_complaints(db, page=page, page_size=page_size)
    return ComplaintListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


@router.get("/{complaint_id}", response_model=ComplaintResponse)
async def get_single_complaint(
    complaint_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single complaint by ID."""
    complaint = await get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


@router.patch("/{complaint_id}", response_model=ComplaintResponse)
async def patch_complaint(
    complaint_id: str,
    update_data: ComplaintUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Partial update a complaint.
    Called by the agent endpoint — also usable for status updates.
    """
    updated = await update_complaint(db, complaint_id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return updated


@router.get("/{complaint_id}/history")
async def get_history(
    complaint_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return full audit trail for a complaint (GxP compliance)."""
    history = await get_complaint_history(db, complaint_id)
    return [
        {
            "action": h.action,
            "changed_fields": h.changed_fields,
            "performed_by": h.performed_by,
            "timestamp": h.timestamp.isoformat(),
        }
        for h in history
    ]
