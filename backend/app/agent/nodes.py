"""
LangGraph Graph Node Functions
Each function is one node in the StateGraph.
Nodes receive AgentState, do work, and return a dict of state updates.

Uses raw groq.Groq() client. Model comes from settings (default
openai/gpt-oss-20b) with a fallback on the secondary Groq model.
"""
import json
import logging
import re
from typing import Union
from groq import Groq
from langchain_core.messages import AIMessage
from app.agent.state import AgentState
from app.agent.prompts import (
    SYSTEM_PROMPT,
    INTENT_CLASSIFICATION_PROMPT,
    LOG_COMPLAINT_PROMPT,
    EDIT_COMPLAINT_PROMPT,
    DOCUMENT_EXTRACTION_PROMPT,
    RISK_ASSESSMENT_PROMPT,
)
from app.core.config import settings
from app.services.duplicate_detector import validate_complaint_fields
from app.schemas.risk_assessment import RiskAssessmentData

logger = logging.getLogger(__name__)

# ── Groq client singleton ──────────────────────────────────────────────────────
_groq_client: Groq | None = None

def _get_client() -> Groq:
    """Return (or create) the Groq client singleton."""
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
    return _groq_client


def _chat(
    system: str,
    user: str,
    reasoning_effort: str = "medium",
    temperature: float = 0.0,
) -> str:
    """
    Call settings.PRIMARY_MODEL (default: openai/gpt-oss-20b) via the raw Groq
    client. Streams and returns the full assistant text.

    If the primary model fails (decommissioned, rate-limited, 5xx, ...), retries
    once with settings.FALLBACK_MODEL.

    temperature defaults to 0.0 so structured outputs (extraction, risk
    assessment) are as deterministic and uniform as possible.
    """
    models = [settings.PRIMARY_MODEL, settings.FALLBACK_MODEL]
    last_error: Exception | None = None

    for model in models:
        try:
            client = _get_client()
            stream = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                temperature=temperature,
                max_completion_tokens=4096,
                top_p=1,
                reasoning_effort=reasoning_effort,
                stream=True,
                stop=None,
            )
            # Collect all stream chunks into a single string
            content = ""
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    content += delta.content
            return content
        except Exception as e:
            last_error = e
            if model != models[-1]:
                logger.warning(
                    f"[_chat] model '{model}' failed ({e}); "
                    f"falling back to '{settings.FALLBACK_MODEL}'"
                )

    raise last_error


def _extract_json(text: str) -> dict:
    """
    Robustly extract JSON from LLM response.
    LLMs sometimes wrap JSON in markdown code blocks.
    """
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not extract JSON from LLM response: {text[:200]}")


def _extract_and_validate(response_text: str, original_prompt: str) -> tuple:
    """
    Extract JSON from LLM response, validate complaint fields, retry once on any failure.
    Returns (valid_dict_or_None, error_string_or_None).
    """
    # Step 1: Parse JSON
    try:
        extracted = _extract_json(response_text)
    except ValueError:
        retry_prompt = (
            original_prompt
            + "\n\nYour previous response was not valid JSON. Return ONLY the corrected JSON object."
        )
        response_text = _chat(SYSTEM_PROMPT, retry_prompt, reasoning_effort="medium")
        try:
            extracted = _extract_json(response_text)
        except ValueError:
            return None, "Could not parse response as JSON."

    valid = {k: v for k, v in extracted.items() if v and v != "null" and v != "None"}

    # Step 2: Validate fields
    errors = validate_complaint_fields(valid)
    if errors:
        error_detail = "; ".join(errors)
        retry_prompt = (
            original_prompt
            + f"\n\nYour previous response failed validation:\n{error_detail}"
            + "\nReturn ONLY the corrected JSON with valid values."
        )
        response_text = _chat(SYSTEM_PROMPT, retry_prompt, reasoning_effort="medium")
        try:
            extracted = _extract_json(response_text)
            valid = {k: v for k, v in extracted.items() if v and v != "null" and v != "None"}
            errors = validate_complaint_fields(valid)
            if errors:
                return None, f"Validation failed: {'; '.join(errors)}"
        except ValueError:
            return None, "Could not parse corrected response as JSON."

    return valid, None


# ── Node 1: Classify Intent ────────────────────────────────────────────────────

def classify_intent_node(state: AgentState) -> dict:
    """
    First node — reads the latest user message and conversation history
    to determine what the user wants to do.
    Returns {"intent": "log" | "edit" | "document" | "query"}
    """
    if state.get("document_text"):
        return {"intent": "document"}

    last_message = state["messages"][-1].content if state["messages"] else ""

    prompt = INTENT_CLASSIFICATION_PROMPT.format(
        complaint_data=json.dumps(state.get("complaint_data") or {}),
        message=last_message,
    )

    response_text = _chat(
        system=SYSTEM_PROMPT,
        user=prompt,
        reasoning_effort="low",   # Fast classification — low reasoning needed
    )

    intent = response_text.strip().lower().strip('"\'')

    valid_intents = {"log", "edit", "document", "query"}
    if intent not in valid_intents:
        intent = "log"

    logger.info(f"[classify_intent] thread={state['thread_id']} intent={intent}")
    return {"intent": intent}


# ── Node 2a: Log Complaint ─────────────────────────────────────────────────────

def log_complaint_node(state: AgentState) -> dict:
    """
    Extracts complaint data from the user's natural language message.
    Merges any newly extracted fields with existing complaint_data.
    Validates complaint_type and complaint_date against strict rules.
    """
    last_message = state["messages"][-1].content if state["messages"] else ""
    current = state.get("complaint_data") or {}
    prompt = LOG_COMPLAINT_PROMPT.format(complaint_text=last_message)

    response_text = _chat(
        system=SYSTEM_PROMPT,
        user=prompt,
        reasoning_effort="medium",
    )

    valid, error = _extract_and_validate(response_text, prompt)
    if error:
        logger.error(f"[log_complaint] extraction/validation failed: {error}")
        return {
            "error": f"I had trouble extracting complaint details: {error}",
            "complaint_data": current,
        }

    merged = {**current, **valid}
    logger.info(f"[log_complaint] total fields now: {len(merged)} (newly extracted: {list(valid.keys())})")
    return {"complaint_data": merged, "error": None}


# ── Node 2b: Edit Complaint ────────────────────────────────────────────────────

def edit_complaint_node(state: AgentState) -> dict:
    """
    Updates ONLY the fields mentioned in the user's edit/supplement instruction.
    Preserves all existing complaint data not mentioned.
    """
    last_message = state["messages"][-1].content if state["messages"] else ""
    current = state.get("complaint_data") or {}

    prompt = EDIT_COMPLAINT_PROMPT.format(
        current_complaint=json.dumps(current, indent=2),
        edit_instruction=last_message,
    )

    response_text = _chat(
        system=SYSTEM_PROMPT,
        user=prompt,
        reasoning_effort="medium",
    )

    # Same strict validation/retry path as log & document — keeps complaint_type
    # and complaint_date canonical even for edit turns.
    valid_changes, error = _extract_and_validate(response_text, prompt)
    if error:
        logger.error(f"[edit_complaint] validation failed: {error}")
        return {
            "error": f"I couldn't apply your update: {error}",
            "complaint_data": current,
        }

    # Merge: start from current, apply only valid changes
    updated = {**current, **valid_changes}
    logger.info(f"[edit_complaint] changed/added fields: {list(valid_changes.keys())} | total fields: {len(updated)}")
    return {"complaint_data": updated, "error": None}


# ── Node 2c: Document Extraction ──────────────────────────────────────────────

def document_extract_node(state: AgentState) -> dict:
    """
    Extracts complaint data from pre-parsed document text.
    Uses high reasoning_effort for long-form document understanding.
    Validates complaint_type and complaint_date against strict rules.
    """
    document_text = state.get("document_text", "")
    current = state.get("complaint_data") or {}

    if not document_text:
        return {"error": "No document text found. Please re-upload the file.", "complaint_data": current}

    prompt = DOCUMENT_EXTRACTION_PROMPT.format(document_text=document_text[:8000])

    response_text = _chat(
        system=SYSTEM_PROMPT,
        user=prompt,
        reasoning_effort="high",   # More careful for document parsing
    )

    valid, error = _extract_and_validate(response_text, prompt)
    if error:
        logger.error(f"[document_extract] extraction/validation failed: {error}")
        return {
            "error": f"Could not extract valid data from document: {error}",
            "complaint_data": current,
        }

    merged = {**current, **valid}
    logger.info(f"[document_extract] extracted {len(valid)} fields | total: {len(merged)}")
    return {"complaint_data": merged, "error": None}


# ── Node 3: Risk Assessment ────────────────────────────────────────────────────

_RISK_BOOL_WORDS = {"true", "yes", "y", "1", "required", "needed"}


def _resolved_annotation(field) -> type:
    """Unwrap Optional[X] / Union[X, None] so target-type checks match the inner type."""
    ann = field.annotation
    if getattr(ann, "__origin__", None) is Union:
        args = [a for a in getattr(ann, "__args__", ()) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return ann


def _coerce_risk_types(risk_data: dict) -> dict:
    """
    Normalize messy LLM output to match RiskAssessmentData field types.
    gpt-oss-20b occasionally returns list/array values for string fields
    (e.g. capa_steps, recommended_action) or stringified numbers/bools.
    """
    for name, field in RiskAssessmentData.model_fields.items():
        if name not in risk_data or risk_data[name] is None:
            continue
        val = risk_data[name]
        target = _resolved_annotation(field)
        if isinstance(val, list):
            if target is str:
                risk_data[name] = "\n".join(str(x) for x in val)
        elif target is int:
            try:
                value = int(val)
                risk_data[name] = max(1, min(10, value)) if name == "risk_score" else value
            except (TypeError, ValueError):
                risk_data[name] = None
        elif target is bool and not isinstance(val, bool):
            risk_data[name] = str(val).strip().lower() in _RISK_BOOL_WORDS

    # Enforce canonical enum values so identical complaints map to one output
    severity = risk_data.get("severity_level")
    if isinstance(severity, str):
        sev = severity.strip().lower()
        if "crit" in sev:
            risk_data["severity_level"] = "Critical"
        elif "major" in sev or "high" in sev:
            risk_data["severity_level"] = "Major"
        else:
            risk_data["severity_level"] = "Minor"

    recall = risk_data.get("recall_risk")
    if isinstance(recall, str):
        rec = recall.strip().lower()
        if "high" in rec:
            risk_data["recall_risk"] = "High"
        elif "medium" in rec or "moderate" in rec:
            risk_data["recall_risk"] = "Medium"
        elif "low" in rec:
            risk_data["recall_risk"] = "Low"
        else:
            risk_data["recall_risk"] = "None"

    return risk_data


def risk_assessment_node(state: AgentState) -> dict:
    """
    Generates ICH Q9 risk assessment strictly on the full accumulated complaint form.
    Automatically synchronizes severity_level and priority into complaint_data.
    """
    complaint_data = dict(state.get("complaint_data") or {})
    if not complaint_data:
        return {"risk_assessment": None}

    prompt = RISK_ASSESSMENT_PROMPT.format(
        complaint_data=json.dumps(complaint_data, indent=2)
    )

    response_text = _chat(
        system=SYSTEM_PROMPT,
        user=prompt,
        reasoning_effort="medium",
    )

    try:
        try:
            risk_data = _extract_json(response_text)
        except ValueError:
            retry_prompt = (
                prompt
                + "\n\nYour previous response was not valid JSON. Return ONLY the corrected risk assessment JSON."
            )
            logger.warning("[risk_assessment] invalid JSON, retrying once")
            response_text = _chat(SYSTEM_PROMPT, retry_prompt, reasoning_effort="medium")
            risk_data = _extract_json(response_text)

        risk_data = _coerce_risk_types(risk_data)
        if "risk_score" in risk_data and risk_data["risk_score"] is not None:
            risk_data["risk_score"] = int(risk_data["risk_score"])

        # Sync severity and priority back into complaint form data
        if risk_data.get("severity_level"):
            complaint_data["initial_severity"] = risk_data["severity_level"]
            if not complaint_data.get("priority"):
                complaint_data["priority"] = (
                    "Immediate" if risk_data["severity_level"] == "Critical"
                    else "High" if risk_data["severity_level"] == "Major"
                    else "Medium"
                )

        logger.info(
            f"[risk_assessment] full form evaluated: severity={risk_data.get('severity_level')} "
            f"score={risk_data.get('risk_score')}"
        )
        return {"risk_assessment": risk_data, "complaint_data": complaint_data, "error": None}
    except Exception as e:
        logger.error(f"[risk_assessment] failed: {e}")
        return {"risk_assessment": None, "complaint_data": complaint_data}


# ── Node 4: Query Answer ──────────────────────────────────────────────────────

def query_answer_node(state: AgentState) -> dict:
    """
    Handles general questions about the current complaint or pharma QMS.
    Does NOT modify complaint_data.
    """
    current = state.get("complaint_data")
    system = SYSTEM_PROMPT
    if current:
        system += f"\n\nCurrent complaint data:\n{json.dumps(current, indent=2)}"

    last_message = state["messages"][-1].content if state["messages"] else ""

    response_text = _chat(
        system=system,
        user=last_message,
        reasoning_effort="medium",
    )

    return {
        "messages": [AIMessage(content=response_text)],
    }


# ── Node 5: Completeness Check (bonus) ──────────────────────────────────────

COMPLETENESS_TIERS = {
    "critical": ["product_name", "batch_number", "complaint_type", "description"],
    "important": [
        "complaint_source",
        "complaint_date",
        "expiry_date",
        "manufacturing_date",
        "quantity_affected",
    ],
}

_FIELD_LABELS = {
    "product_name": "product name",
    "batch_number": "batch number",
    "complaint_type": "complaint type",
    "description": "complaint details",
    "complaint_source": "complaint source",
    "complaint_date": "complaint date",
    "expiry_date": "expiry date",
    "manufacturing_date": "manufacturing date",
    "quantity_affected": "quantity affected",
}


def _format_field_list(fields: list[str]) -> str:
    """Human-friendly, grammar-aware list of missing fields for messages."""
    labels = [_FIELD_LABELS.get(f, f.replace("_", " ")) for f in fields]
    if len(labels) == 1:
        return f"**{labels[0]}**"
    if len(labels) == 2:
        return f"**{labels[0]} and {labels[1]}**"
    return f"**{', '.join(labels[:-1])}, and {labels[-1]}**"


def completeness_check_node(state: AgentState) -> dict:
    """
    Checks which complaint form fields are still missing and generates an
    appropriate acknowledgment or follow-up question.

    - Missing critical fields → asks the user to provide them (still allows
      "save as-is").
    - Only optional "important" fields missing → offers a choice: provide the
      remaining details, or save the complaint as it is.
    - Everything present → success message pointing at Save Complaint.
    """
    complaint_data = state.get("complaint_data") or {}
    missing_critical = [
        f for f in COMPLETENESS_TIERS["critical"] if not complaint_data.get(f)
    ]
    missing_important = [
        f for f in COMPLETENESS_TIERS["important"] if not complaint_data.get(f)
    ]

    risk_data = state.get("risk_assessment") or {}
    severity = risk_data.get("severity_level") or complaint_data.get("initial_severity") or ""
    product = complaint_data.get("product_name", "the product")
    source = complaint_data.get("complaint_source") or complaint_data.get("customer_name") or ""
    source_text = f" from **{source}**" if source else ""
    sev_text = f" The complaint is classified as **{severity}** severity per ICH Q9." if severity else ""

    if missing_critical:
        ask = _format_field_list(missing_critical)
        extra = ""
        if missing_important:
            extra = (
                f" A few optional details would also help: "
                f"{_format_field_list(missing_important)}."
            )
        msg = (
            f"I've updated the form with what you provided, but we're still missing "
            f"{ask}.{extra} Could you provide this information? "
            f"If you'd rather proceed, you can click **Save Complaint** to log it as-is."
        )
    elif missing_important:
        msg = (
            f"✅ Form is complete for **{product}**{source_text}.{sev_text} "
            f"Only a few optional details are still missing: "
            f"{_format_field_list(missing_important)}. "
            f"Do you want to provide these, or save the complaint as it is?"
        )
    elif state.get("intent") == "edit":
        msg = (
            f"✅ Updated complaint details for **{product}**{source_text}.{sev_text} "
            f"All required fields are present. Review the form and click **Save Complaint** to finalize."
        )
    else:
        msg = (
            f"✅ I've extracted the complaint details for **{product}**{source_text}.{sev_text} "
            f"Review the populated form and the AI Copilot Risk Assessment panel, "
            f"then click **Save Complaint** to log it."
        )

    return {"messages": [AIMessage(content=msg)]}
