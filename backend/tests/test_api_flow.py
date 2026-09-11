"""
Integration / smoke tests: Postgres + Groq + the full FastAPI app.
These hit the real DB and the real LLM, so they're marked `integration`
and skipped automatically when prerequisites are missing.

Run with:  pytest tests/ -m integration
"""
import json
import uuid
from datetime import date

import httpx
import pytest
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, AsyncSessionLocal
from app.schemas.complaint import ComplaintCreate
from app.crud.complaint import create_complaint, get_all_complaints_for_dedup

pytestmark = pytest.mark.integration


async def _db_ok() -> tuple[bool, str]:
    """Return (reachable, reason)."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:150]}"


async def _client():
    from app.main import app
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    )


def _parse_sse(text: str) -> list[dict]:
    events = []
    for block in text.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


async def _hard_delete(thread_id: str):
    async with AsyncSessionLocal() as session:
        # complaints.thread_id FK ondelete=CASCADE clears audit_log + risk_assessments
        await session.execute(
            text("DELETE FROM complaints WHERE thread_id = :tid"),
            {"tid": thread_id},
        )
        await session.commit()


# ── /chat SSE smoke test ────────────────────────────────────────────────────

async def test_chat_stream_completes():
    db_ok, reason = await _db_ok()
    if not db_ok or not settings.GROQ_API_KEY:
        pytest.skip(f"precheck failed: db_ok={db_ok} groq={bool(settings.GROQ_API_KEY)} {reason}")

    thread_id = f"test-{uuid.uuid4().hex}"
    try:
        async with await _client() as client:
            resp = await client.post(
                "/api/v1/agent/chat",
                json={
                    "message": (
                        "Apollo Pharmacy reported discolored Aspirin 500mg Tablets "
                        "from batch B-1412. Quality issue."
                    ),
                    "thread_id": thread_id,
                },
            )
        assert resp.status_code == 200
        events = _parse_sse(resp.text)
        types = [e["type"] for e in events]

        assert types[0] == "thinking"
        assert "done" in types
        assert "message" in types
        # Extraction + risk assessment should both have streamed
        assert "complaint_update" in types
        assert "risk_update" in types
        payload = next(e["data"] for e in events if e["type"] == "complaint_update")
        assert payload.get("product_name")
    finally:
        await _hard_delete(thread_id)


# ── /save REST smoke test ───────────────────────────────────────────────────

async def test_save_creates_complaint():
    db_ok, reason = await _db_ok()
    if not db_ok or not settings.GROQ_API_KEY:
        pytest.skip(f"precheck failed: db_ok={db_ok} groq={bool(settings.GROQ_API_KEY)} {reason}")

    thread_id = f"test-{uuid.uuid4().hex}"
    try:
        async with await _client() as client:
            resp = await client.post(
                "/api/v1/agent/save",
                json={
                    "thread_id": thread_id,
                    "intake_source": "text_prompt",
                    "complaint": {
                        "product_name": "Amoxicillin 250mg Capsules",
                        "batch_number": "B-999",
                        "complaint_type": "Quality",
                        "description": "Broken seals on blister packs",
                        "complaint_date": date.today().isoformat(),
                        "complaint_source": "MedPlus Pharmacy",
                        "expiry_date": "2028-06-30",
                    },
                },
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"]
        assert body["complaint_number"].startswith("CC-")
        assert body["status"] == "Under Investigation"

        # Confirm it's queryable + persistable round-trip
        async with AsyncSessionLocal() as session:
            row = await session.execute(
                text("SELECT product_name FROM complaints WHERE id = :cid"),
                {"cid": body["id"]},
            )
            assert row.scalar_one() == "Amoxicillin 250mg Capsules"
    finally:
        await _hard_delete(thread_id)


# ── Dedup pre-filter + self-exclusion (DB only, no LLM) ─────────────────────

async def test_dedup_excludes_self():
    if not await _db_ok():
        pytest.skip("precheck failed: DB unreachable")

    thread_id = f"test-{uuid.uuid4().hex}"
    created_ids = []
    try:
        async with AsyncSessionLocal() as session:
            a = await create_complaint(
                session,
                ComplaintCreate(
                    product_name="Metformin 500mg Tablets",
                    complaint_type="Efficacy",
                    complaint_source="Apollo Pharmacy",
                    complaint_date=date.today().isoformat(),
                ),
                thread_id=thread_id,
                status="Pending Triage",
            )
            created_ids.append(str(a.id))
            b = await create_complaint(
                session,
                ComplaintCreate(
                    product_name="Paracetamol 500mg Tablets",
                    complaint_type="Quality",
                    complaint_source="Apollo Pharmacy",
                    complaint_date=date.today().isoformat(),
                ),
                thread_id=thread_id,
                status="Pending Triage",
            )
            created_ids.append(str(b.id))

            new = {
                "product_name": "Metformin 500mg Tablets",
                "complaint_type": "Efficacy",
                "complaint_source": "Apollo Pharmacy",
                "complaint_date": date.today().isoformat(),
            }
            candidates = await get_all_complaints_for_dedup(
                session, new_complaint=new, exclude_complaint_id=str(a.id)
            )

        ids = [c["id"] for c in candidates]
        assert str(a.id) not in ids, "self-match must be excluded"
        assert str(b.id) in ids, "other recent complaints should be candidates"
    finally:
        await _hard_delete(thread_id)