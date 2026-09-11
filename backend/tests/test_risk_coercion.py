"""Unit tests for _coerce_risk_types — normalizes messy LLM output."""
from app.agent.nodes import _coerce_risk_types


class TestCoerceRiskTypes:
    def test_list_capa_steps_joined_into_text(self):
        data = _coerce_risk_types(
            {
                "capa_steps": ["step one", "step two"],
                "recommended_action": ["Investigate and contain"],
            }
        )
        assert data["capa_steps"] == "step one\nstep two"
        assert data["recommended_action"] == "Investigate and contain"

    def test_risk_score_stringified_and_clamped(self):
        assert _coerce_risk_types({"risk_score": "7"})["risk_score"] == 7
        assert _coerce_risk_types({"risk_score": 5})["risk_score"] == 5
        assert _coerce_risk_types({"risk_score": 99})["risk_score"] == 10
        assert _coerce_risk_types({"risk_score": 0})["risk_score"] == 1
        assert _coerce_risk_types({"risk_score": -3})["risk_score"] == 1

    def test_risk_score_unparseable_becomes_none(self):
        assert _coerce_risk_types({"risk_score": "abc"})["risk_score"] is None

    def test_bool_coercion(self):
        assert _coerce_risk_types({"capa_required": "yes"})["capa_required"] is True
        assert _coerce_risk_types({"capa_required": "true"})["capa_required"] is True
        assert _coerce_risk_types({"capa_required": "no"})["capa_required"] is False
        assert _coerce_risk_types({"capa_required": True})["capa_required"] is True

    def test_severity_enum_normalized(self):
        assert _coerce_risk_types({"severity_level": "CRITICAL"})["severity_level"] == "Critical"
        assert _coerce_risk_types({"severity_level": "major"})["severity_level"] == "Major"
        assert _coerce_risk_types({"severity_level": "high"})["severity_level"] == "Major"
        assert _coerce_risk_types({"severity_level": "minor"})["severity_level"] == "Minor"

    def test_recall_risk_enum_normalized(self):
        assert _coerce_risk_types({"recall_risk": "High"})["recall_risk"] == "High"
        assert _coerce_risk_types({"recall_risk": "moderate"})["recall_risk"] == "Medium"
        assert _coerce_risk_types({"recall_risk": "low"})["recall_risk"] == "Low"
        assert _coerce_risk_types({"recall_risk": ""})["recall_risk"] == "None"

    def test_unknown_fields_untouched(self):
        data = _coerce_risk_types({"custom_note": "keep me", "risk_score": 4})
        assert data["custom_note"] == "keep me"
        assert data["risk_score"] == 4