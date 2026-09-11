"""CRUD operations for risk assessments."""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.risk_assessment import RiskAssessment
from app.models.audit_log import AuditLog
from app.schemas.risk_assessment import RiskAssessmentData


async def upsert_risk_assessment(
    db: AsyncSession,
    complaint_id: str,
    risk_data: RiskAssessmentData,
    thread_id: str | None = None,
) -> RiskAssessment:
    """
    Create or update the risk assessment for a complaint.
    One complaint has at most one risk assessment (upsert pattern).
    """
    cid = uuid.UUID(complaint_id)

    # Check if one already exists
    result = await db.execute(
        select(RiskAssessment).where(RiskAssessment.complaint_id == cid)
    )
    existing = result.scalar_one_or_none()

    data_dict = risk_data.model_dump(exclude_none=True)

    if existing:
        for field, value in data_dict.items():
            setattr(existing, field, value)
        assessment = existing
        action = "risk_assessment_updated"
    else:
        assessment = RiskAssessment(complaint_id=cid, **data_dict)
        db.add(assessment)
        action = "risk_assessment_created"

    # Audit
    audit = AuditLog(
        complaint_id=cid,
        action=action,
        changed_fields=data_dict,
        performed_by="risk_assessment_tool",
        thread_id=thread_id,
    )
    db.add(audit)

    await db.commit()
    await db.refresh(assessment)
    return assessment


async def get_risk_assessment(
    db: AsyncSession, complaint_id: str
) -> RiskAssessment | None:
    """Fetch risk assessment for a given complaint."""
    result = await db.execute(
        select(RiskAssessment).where(
            RiskAssessment.complaint_id == uuid.UUID(complaint_id)
        )
    )
    return result.scalar_one_or_none()
