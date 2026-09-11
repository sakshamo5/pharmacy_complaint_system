"""Unit tests for the deterministic duplicate complaint detector."""
import pytest
from datetime import date

from app.services.duplicate_detector import (
    check_for_duplicates,
    normalize_product,
    normalize_hospital,
    parse_date,
    validate_complaint_fields,
)


# ── Normalization ───────────────────────────────────────────────────────────

class TestNormalization:
    def test_normalize_product_strips_strength_and_dosage_form(self):
        assert normalize_product("Aspirin 500mg Tablets") == "aspirin"
        assert normalize_product("Amoxicillin 250 mg capsules") == "amoxicillin"

    def test_normalize_product_keeps_core_name(self):
        assert normalize_product("AZITHROMYCIN") == "azithromycin"

    def test_normalize_hospital_strips_suffix(self):
        assert normalize_hospital("Apollo Pharmacy") == "apollo"
        assert normalize_hospital("City Medical Centre") == "city medical"
        assert normalize_hospital("MedPlus Pvt Ltd") == "medplus"


# ── Date parsing ────────────────────────────────────────────────────────────

class TestParseDate:
    def test_iso_format(self):
        assert parse_date("2026-06-15") == date(2026, 6, 15)

    def test_long_format(self):
        assert parse_date("June 15, 2026") == date(2026, 6, 15)

    def test_invalid_date(self):
        assert parse_date("not-a-date") is None

    def test_empty(self):
        assert parse_date("") is None
        assert parse_date(None) is None


# ── Validation ──────────────────────────────────────────────────────────────

class TestValidateComplaintFields:
    def test_valid_complaint_passes(self):
        errors = validate_complaint_fields(
            {"complaint_type": "Quality", "complaint_date": "2026-06-15"}
        )
        assert errors == []

    def test_invalid_complaint_type(self):
        errors = validate_complaint_fields({"complaint_type": "Random"})
        assert len(errors) == 1
        assert "complaint_type" in errors[0]

    def test_missing_fields_are_allowed(self):
        assert validate_complaint_fields({}) == []
        assert validate_complaint_fields({"product_name": "Aspirin"}) == []


# ── Duplicate check ─────────────────────────────────────────────────────────

BASE_EXISTING = [{
    "id": "11111111-1111-1111-1111-111111111111",
    "complaint_number": "CC-8GH19JQT9",
    "product_name": "Aspirin 500mg Tablets",
    "complaint_type": "Quality",
    "complaint_source": "Apollo Pharmacy",
    "complaint_date": "2026-06-15",
}]

BASE_NEW = {
    "product_name": "Aspirin 500mg Tablets",
    "complaint_type": "Quality",
    "complaint_source": "Apollo Pharmacy",
    "complaint_date": "2026-06-18",
}


class TestCheckForDuplicates:
    def test_exact_duplicate_detected(self):
        result = check_for_duplicates(BASE_NEW, BASE_EXISTING)
        assert result is not None
        assert result["complaint_number"] == "CC-8GH19JQT9"

    def test_dosage_form_spelling_variation_still_matches(self):
        near_dup = {
            **BASE_NEW,
            "product_name": "Aspirin Tablets 500 mg",
            "complaint_source": "Apollo Pharmacy Ltd",
        }
        result = check_for_duplicates(near_dup, BASE_EXISTING)
        assert result is not None

    def test_different_product_not_a_duplicate(self):
        other = {**BASE_NEW, "product_name": "Paracetamol 500mg Tablets"}
        assert check_for_duplicates(other, BASE_EXISTING) is None

    def test_different_issue_not_a_duplicate(self):
        other = {**BASE_NEW, "complaint_type": "Labeling"}
        assert check_for_duplicates(other, BASE_EXISTING) is None

    def test_facility_mismatch_excluded(self):
        other = {**BASE_NEW, "complaint_source": "City Medical Centre"}
        assert check_for_duplicates(other, BASE_EXISTING) is None

    def test_date_beyond_tolerance_excluded(self):
        other = {**BASE_NEW, "complaint_date": "2026-08-01"}
        assert check_for_duplicates(other, BASE_EXISTING) is None

    def test_missing_mandatory_fields_cannot_match(self):
        sparse = {"complaint_source": "Apollo Pharmacy"}
        assert check_for_duplicates(sparse, BASE_EXISTING) is None

    def test_empty_existing_list(self):
        assert check_for_duplicates(BASE_NEW, []) is None

    def test_similarity_score_present(self):
        result = check_for_duplicates(BASE_NEW, BASE_EXISTING)
        assert result["similarity_score"] == 1.0