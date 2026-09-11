"""Pydantic schemas for risk assessment data."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


def _coerce_list_to_text(value):
    """LLMs sometimes emit list/array values for string fields."""
    if isinstance(value, list):
        return "\n".join(str(x) for x in value)
    return value


class RiskAssessmentData(BaseModel):
    """
    AI-generated risk assessment output.
    Returned by risk_assessment_tool and populates the AI Copilot panel.
    """
    severity_level: Optional[str] = Field(
        None, description="Critical / Major / Minor per ICH Q9"
    )
    risk_score: Optional[int] = Field(
        None, ge=1, le=10, description="Composite risk score 1-10"
    )
    recommended_action: Optional[str] = Field(
        None, description="Recommended next step (e.g., Route to QA Investigation)"
    )
    root_cause_hypothesis: Optional[str] = Field(
        None, description="AI-hypothesized root cause using 5 Whys reasoning"
    )
    capa_required: Optional[bool] = Field(
        None, description="Whether CAPA (Corrective and Preventive Action) is needed"
    )
    regulatory_report_required: Optional[bool] = Field(
        None, description="Whether FDA/regulatory notification is required"
    )
    recall_risk: Optional[str] = Field(
        None, description="High / Medium / Low / None"
    )
    ai_reasoning: Optional[str] = Field(
        None, description="Full AI chain-of-thought reasoning displayed in copilot"
    )
    capa_steps: Optional[str] = Field(
        None, description="Specific CAPA action steps (bonus feature)"
    )

    @field_validator(
        "severity_level",
        "recommended_action",
        "root_cause_hypothesis",
        "recall_risk",
        "ai_reasoning",
        "capa_steps",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, v):
        return _coerce_list_to_text(v)


class RiskAssessmentResponse(RiskAssessmentData):
    """Full risk assessment record from DB."""
    id: uuid.UUID
    complaint_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
