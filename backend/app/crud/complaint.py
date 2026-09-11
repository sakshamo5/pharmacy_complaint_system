"""
CRUD operations for complaints.
Pure data-access layer — no business logic here.
All methods are async and accept an AsyncSession dependency.
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, or_, and_
from app.models.complaint import Complaint
from app.models.audit_log import AuditLog
from app.schemas.complaint import ComplaintCreate, ComplaintUpdate
from app.services.duplicate_detector import parse_date


def _generate_complaint_number() -> str:
    """Generate a sequential-looking complaint number: CC-YYYY-XXXX"""
    year = datetime.now().year
    # Use partial UUID for uniqueness without needing a DB sequence
    unique_part = str(uuid.uuid4())[:4].upper()
    timestamp_part = str(int(datetime.now().timestamp()))[-4:]
    return f"CC-{year}-{timestamp_part}{unique_part}"


async def create_complaint(
    db: AsyncSession,
    complaint_in: ComplaintCreate,
    thread_id: str | None = None,
    status: str = "Pending Triage",
) -> Complaint:
    """Insert a new complaint record and write an audit log entry."""
    data = complaint_in.model_dump(exclude_none=True)
    resolved_thread_id = thread_id or data.pop("thread_id", None)
    data.pop("thread_id", None)

    complaint = Complaint(
        complaint_number=_generate_complaint_number(),
        thread_id=resolved_thread_id,
        status=status,
        **data,
    )
    db.add(complaint)
    await db.flush()  # Get the ID before committing

    # Write audit log
    audit = AuditLog(
        complaint_id=complaint.id,
        action="complaint_created",
        changed_fields=complaint_in.model_dump(exclude_none=True),
        performed_by="AI_AGENT",
        thread_id=thread_id,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(complaint)
    return complaint


async def get_complaint(db: AsyncSession, complaint_id: str) -> Complaint | None:
    """Fetch a single complaint by UUID."""
    result = await db.execute(
        select(Complaint).where(Complaint.id == uuid.UUID(complaint_id))
    )
    return result.scalar_one_or_none()


async def get_complaint_by_thread(db: AsyncSession, thread_id: str) -> Complaint | None:
    """Find the complaint associated with a LangGraph conversation thread."""
    result = await db.execute(
        select(Complaint).where(Complaint.thread_id == thread_id)
        .order_by(Complaint.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_complaints(
    db: AsyncSession, page: int = 1, page_size: int = 20
) -> tuple[list[Complaint], int]:
    """Return paginated complaint list plus total count."""
    offset = (page - 1) * page_size

    count_result = await db.execute(select(func.count(Complaint.id)))
    total = count_result.scalar_one()

    result = await db.execute(
        select(Complaint)
        .order_by(Complaint.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    return result.scalars().all(), total


async def update_complaint(
    db: AsyncSession,
    complaint_id: str,
    update_data: ComplaintUpdate,
    thread_id: str | None = None,
    performed_by: str = "AI_AGENT",
) -> Complaint | None:
    """
    Partially update a complaint — only non-None fields are written.
    Records audit log with before/after values for each changed field.
    """
    complaint = await get_complaint(db, complaint_id)
    if not complaint:
        return None

    update_dict = update_data.model_dump(exclude_none=True)
    changed_fields = {}

    for field, new_value in update_dict.items():
        old_value = getattr(complaint, field, None)
        if old_value != new_value:
            changed_fields[field] = {"old": str(old_value) if old_value else None, "new": new_value}
            setattr(complaint, field, new_value)

    if changed_fields:
        audit = AuditLog(
            complaint_id=complaint.id,
            action="complaint_updated",
            changed_fields=changed_fields,
            performed_by=performed_by,
            thread_id=thread_id,
        )
        db.add(audit)

    await db.commit()
    await db.refresh(complaint)
    return complaint


async def get_complaint_history(
    db: AsyncSession, complaint_id: str
) -> list[AuditLog]:
    """Return all audit log entries for a specific complaint."""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.complaint_id == uuid.UUID(complaint_id))
        .order_by(AuditLog.timestamp.asc())
    )
    return result.scalars().all()


async def get_all_complaints_for_dedup(
    db: AsyncSession,
    new_complaint: dict,
    exclude_complaint_id: str | None = None,
    date_tolerance_days: int = 7,
    limit: int = 2000,
) -> list[dict]:
    """
    Return lightweight records for deterministic duplicate detection.
    Fetches the 4 comparison fields: product_name, complaint_type, facility, date.

    Pre-filters at the DB level:
    - Optionally excludes the current record (avoids self-match on edits)
    - Restricts to a conservative date window around the new complaint's date
      (canonical complaint_date is ISO YYYY-MM-DD, so string comparison is valid)
    - Caps the candidate set to avoid unbounded scans as the table grows
    """
    conditions = [Complaint.product_name.isnot(None)]

    if exclude_complaint_id:
        conditions.append(Complaint.id != uuid.UUID(str(exclude_complaint_id)))

    new_date = parse_date(new_complaint.get("complaint_date") or "")
    if new_date:
        slack = date_tolerance_days + 31  # safety margin so we never miss a borderline match
        lower = (new_date - timedelta(days=slack)).isoformat()
        upper = (new_date + timedelta(days=slack)).isoformat()
        conditions.append(
            or_(
                Complaint.complaint_date.is_(None),
                and_(
                    Complaint.complaint_date >= lower,
                    Complaint.complaint_date <= upper,
                ),
            )
        )

    result = await db.execute(
        select(
            Complaint.id,
            Complaint.complaint_number,
            Complaint.product_name,
            Complaint.complaint_type,
            Complaint.complaint_source,
            Complaint.customer_name,
            Complaint.complaint_date,
        )
        .where(*conditions)
        .order_by(Complaint.created_at.desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "id": str(r.id),
            "complaint_number": r.complaint_number,
            "product_name": r.product_name,
            "complaint_type": r.complaint_type,
            "complaint_source": r.complaint_source,
            "customer_name": r.customer_name,
            "complaint_date": r.complaint_date,
        }
        for r in rows
    ]
