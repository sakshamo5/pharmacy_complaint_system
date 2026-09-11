"""Unit tests for the completeness check node messages."""
from app.agent.nodes import completeness_check_node, _format_field_list

COMPLETE = {
    "product_name": "Aspirin 500mg Tablets",
    "batch_number": "B-123",
    "complaint_type": "Quality",
    "description": "Tablet discoloration",
    "complaint_source": "Apollo Pharmacy",
    "complaint_date": "2026-06-15",
    "expiry_date": "2028-06-30",
    "manufacturing_date": "2025-10-01",
    "quantity_affected": "48 tablets",
}


def _run(**kw):
    return completeness_check_node({"messages": [], "complaint_data": kw})


class TestFormatFieldList:
    def test_single(self):
        assert _format_field_list(["batch_number"]) == "**batch number**"

    def test_two(self):
        assert _format_field_list(["batch_number", "expiry_date"]) == (
            "**batch number and expiry date**"
        )

    def test_three(self):
        assert _format_field_list(["a", "b", "c"]) == "**a, b, and c**"

    def test_unknown_field_falls_back_to_raw_name(self):
        assert _format_field_list(["noodle_tier"]) == "**noodle tier**"


class TestMissingCritical:
    def test_asks_for_missing_critical(self):
        data = dict(COMPLETE)
        del data["batch_number"]
        msg = _run(**data)
        result = list(msg["messages"])[0].content
        assert "batch number" in result
        assert "Could you provide" in result
        assert "Save Complaint" in result

    def test_also_mentions_optional_fields(self):
        data = dict(COMPLETE)
        data["product_name"] = ""
        del data["expiry_date"]
        msg = _run(**data)
        result = list(msg["messages"])[0].content
        assert "product name" in result
        assert "optional details" in result
        assert "expiry date" in result


class TestMissingImportantOnly:
    def test_offers_choice(self):
        data = dict(COMPLETE)
        del data["expiry_date"]
        msg = _run(**data)
        result = list(msg["messages"])[0].content
        assert "optional details" in result
        assert "Do you want to provide these" in result
        assert "save the complaint as it is" in result
        assert "Aspirin" in result


class TestComplete:
    def test_log_intent_success_message(self):
        result = list(_run(**COMPLETE)["messages"])[0].content
        assert "Aspirin" in result
        assert "Save Complaint" in result

    def test_edit_intent_success_message(self):
        state = {"messages": [], "complaint_data": COMPLETE, "intent": "edit"}
        result = list(completeness_check_node(state)["messages"])[0].content
        assert "Updated complaint details" in result
        assert "Save Complaint" in result

    def test_severity_and_source_included_when_present(self):
        state = {
            "messages": [],
            "complaint_data": COMPLETE,
            "risk_assessment": {"severity_level": "Major"},
        }
        result = list(completeness_check_node(state)["messages"])[0].content
        assert "Apollo" in result
        assert "Major" in result


class TestEmpty:
    def test_empty_form_asks_for_everything(self):
        msg = _run()
        result = list(msg["messages"])[0].content
        assert "product name" in result
        assert "batch number" in result
        assert "complaint type" in result
        assert "complaint details" in result