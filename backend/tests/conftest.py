"""
Shared pytest fixtures.
Unit tests are hermetic (no DB, no network).
Integration tests (tests/test_api_flow.py) require Postgres + a Groq API key.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def unit_state():
    """Minimal AgentState dict for testing graph nodes directly."""
    return {
        "messages": [],
        "intent": "log",
        "complaint_data": None,
        "risk_assessment": None,
        "document_text": None,
        "complaint_id": None,
        "thread_id": None,
        "error": None,
        "duplicate_warning": None,
    }