"""
Duplicate Complaint Detector
Deterministic field-based comparison: product name, issue type, facility, and date.
"""
import re
import logging
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)

# ── Issue Taxonomy (strict) ──────────────────────────────────────────────────
ISSUE_TAXONOMY = ["Quality", "Packaging", "Labeling", "Safety", "Efficacy"]

# ── Normalization Helpers ────────────────────────────────────────────────────

_DOSAGE_FORMS = re.compile(
    r"\b(capsules?|tablets?|injection|injectable|syrup|drops?|cream|ointment|gel|"
    r"solution|suspension|powder|granules?|suppository|oral)\b",
    re.IGNORECASE,
)
_STRENGTH = re.compile(r"\b\d+(\.\d+)?\s*(mg|g|ml|mcg|iu|μg)\b", re.IGNORECASE)
_FACILITY_SUFFIXES = [
    "pvt ltd", "pvt. ltd.",
    "laboratories", "laboratory",
    "hospital", "clinic", "pharmacy",
    "centre", "center",
    "inc", "ltd", "llc", "pvt.", "pvt", "lab",
]
_DATE_FORMATS = [
    "%Y-%m-%d", "%Y/%m/%d",
    "%m/%d/%Y", "%m-%d-%Y",
    "%B %d, %Y", "%B %d %Y",
    "%b %d, %Y", "%b %d %Y",
    "%d %B %Y", "%d %b %Y",
]


def normalize_product(name: str) -> str:
    """Strip strength and dosage forms to get the core API/drug name."""
    name = name.lower().strip()
    name = _STRENGTH.sub("", name)
    name = _DOSAGE_FORMS.sub("", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def normalize_hospital(name: str) -> str:
    """Lowercase, strip common facility suffixes (repeatedly), collapse whitespace."""
    name = name.lower().strip()
    changed = True
    while changed:
        changed = False
        for suffix in sorted(_FACILITY_SUFFIXES, key=len, reverse=True):
            # Never strip the entire name away — keep at least the core word
            if len(name) > len(suffix) and name.endswith(suffix):
                name = name[: -len(suffix)].strip()
                changed = True
                break
    name = re.sub(r"[^\w\s.]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def parse_date(date_str: str) -> Optional[date]:
    """Try multiple date formats, return date or None."""
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


# ── Validation ───────────────────────────────────────────────────────────────

def validate_complaint_fields(data: dict) -> list[str]:
    """
    Validate complaint_type and complaint_date from extracted data.
    Returns a list of error strings (empty = valid).
    Only validates fields that are present — missing fields are allowed.
    """
    errors = []
    ct = data.get("complaint_type")
    if ct is not None and str(ct).strip():
        if str(ct).strip().lower() not in [t.lower() for t in ISSUE_TAXONOMY]:
            errors.append(
                f"complaint_type must be one of {ISSUE_TAXONOMY}, got '{ct}'"
            )
    cd = data.get("complaint_date")
    if cd is not None and str(cd).strip():
        if parse_date(str(cd)) is None:
            errors.append(
                f"complaint_date must be YYYY-MM-DD format, got '{cd}'"
            )
    return errors


# ── Core Duplicate Check ─────────────────────────────────────────────────────

def check_for_duplicates(
    new_complaint: dict,
    existing_complaints: list[dict],
    date_tolerance_days: int = 7,
) -> Optional[dict]:
    """
    Compare a new complaint against all existing records using deterministic
    field matching on: product name, issue type, facility, and date.

    Matching rules (product + issue mandatory):
    - product: normalized core API name must match (ignore strength/dosage forms)
    - issue: complaint_type must match exactly (from ISSUE_TAXONOMY)
    - facility: if both present, normalized hospital/facility must match
    - date: if both present, must be within ±date_tolerance_days

    Returns the best-matching existing complaint dict, or None.
    """
    if not existing_complaints:
        return None

    new_product = normalize_product(new_complaint.get("product_name") or "")
    new_issue = (new_complaint.get("complaint_type") or "").strip()
    new_hospital = normalize_hospital(
        new_complaint.get("complaint_source")
        or new_complaint.get("customer_name")
        or ""
    )
    new_date = parse_date(new_complaint.get("complaint_date"))

    # product + issue are mandatory for a match
    if not new_product or not new_issue:
        return None

    new_issue_lower = new_issue.lower()

    best_match = None
    best_count = 0

    for c in existing_complaints:
        ex_product = normalize_product(c.get("product_name") or "")
        ex_issue = (c.get("complaint_type") or "").strip().lower()
        ex_hospital = normalize_hospital(
            c.get("complaint_source") or c.get("customer_name") or ""
        )
        ex_date = parse_date(c.get("complaint_date"))

        # Mandatory: product + issue
        if new_product != ex_product or new_issue_lower != ex_issue:
            continue

        # Facility: if both present, must match
        if new_hospital and ex_hospital and new_hospital != ex_hospital:
            continue

        # Date: if both present, must be within tolerance
        if new_date and ex_date:
            if abs((new_date - ex_date).days) > date_tolerance_days:
                continue

        # Count matched criteria for ranking
        match_count = 2  # product + issue always matched at this point
        if new_hospital and ex_hospital:
            match_count += 1
        if new_date and ex_date:
            match_count += 1

        if match_count > best_count:
            best_match = c
            best_count = match_count

    if best_match:
        logger.info(
            f"Duplicate detected: {best_match['complaint_number']} "
            f"(matched {best_count} criteria)"
        )
        return {
            "id": best_match["id"],
            "complaint_number": best_match["complaint_number"],
            "matched_criteria": best_count,
            "similarity_score": 1.0,
        }

    return None
