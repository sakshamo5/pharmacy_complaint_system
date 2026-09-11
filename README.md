# AIVOA – AI-Powered Customer Complaint Management System
### Pharmaceutical QMS | Round 1 AI Product Engineer Assignment

---

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Redux Toolkit |
| Backend | Python 3.11+ + FastAPI |
| AI Agent | LangGraph StateGraph |
| LLMs | Groq (`openai/gpt-oss-20b`, configurable, with fallback) |
| Database | PostgreSQL (asyncpg + SQLAlchemy 2.0) |
| Font | Google Inter |

---

## LLM Model Note (important)

The assignment specifies **Groq `gemma2-9b-it`** (and optionally `llama-3.3-70b-versatile`).
As of submission, **both models are no longer available on Groq**:

- `gemma2-9b-it` → *decommissioned* (HTTP 400, model_decommissioned)
- `llama-3.3-70b-versatile` → *removed / no access* (HTTP 404, model_not_found)

Verified live via `groq.models.list()` — accessible models are the OpenAI-preview
family (`openai/gpt-oss-20b`, `openai/gpt-oss-120b`) and Qwen 3.x.

The project therefore defaults to **`openai/gpt-oss-20b`** with
**`openai/gpt-oss-120b`** as an automatic fallback if the primary fails
(rate limit, 5xx, model rotation). Both are fully configurable via
`PRIMARY_MODEL` / `FALLBACK_MODEL` in `backend/.env`, so pointing back at any
Groq model (including a future `gemma` re-release) is a one-line change.

Structured outputs are kept deterministic: `temperature=0.0` + a strict ICH Q9
rubric for risk assessment, a static completeness checker, and a deterministic
(rule-based) duplicate detector — no floating retrieval similarity.

---

## Quick Start

### 1. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment (edit .env with your keys)
# .env already created — add your GROQ_API_KEY and DATABASE_URL

# Generate sample demo files
python sample_data/generate_sample_data.py

# Start backend
uvicorn app.main:app --reload --port 8000
```
Backend API docs: http://localhost:8000/docs

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend: http://localhost:5173

---

## Features Implemented

### Mandatory AI Tools
1. **Log Complaint Tool** — Natural language → auto-populates the Log Customer Complaint form
2. **Edit Complaint Tool** — Correction / follow-up prompts → only changed fields update, others preserved
3. **Document Extraction Tool** — PDF / DOCX / TXT / EML → extracts and populates the form

### AI Copilot Risk Assessment
- ICH Q9 severity classification (Critical / Major / Minor)
- Risk score 1-10 (additive band model)
- Recommended next action (canonical strings)
- Root cause hypothesis (5 Whys reasoning)
- CAPA required flag + numbered CAPA steps
- Regulatory report / recall risk flags
- Streamed live over SSE into the risk panel

### Bonus Features
- **Complaint Completeness Checker** — asks for missing critical fields (batch, type, description…)
  and offers a choice for optional fields (expiry date, quantity, source, dates): *provide them or save as-is*
- **Duplicate Complaint Detection** — deterministic field matching on product + issue (facility + date when
  present), SQL pre-filter with date window, self-exclusion on edits, blocks duplicate saves in the UI
- **CAPA Recommendation** with specific steps
- **Root Cause Analysis** hypothesis
- **AI Risk Classification** with visual risk score bar
- **Full audit trail** (GxP-oriented action logging)

---

## Architecture / LangGraph Flow

```
User (chat | PDF/DOCX/TXT/EML upload)
  └─ POST /api/v1/agent/chat | /api/v1/agent/upload   (SSE)
       └─ LangGraph StateGraph:
            classify_intent ─┬─ log   → log_complaint
                             ├─ edit  → edit_complaint   (merges only new fields)
                             ├─ doc   → document_extract → log_complaint
                             └─ query → query_answer     (Q&A, no form change)
                 → risk_assessment (ICH Q9)
                 → completeness_check (follow-up questions)
  └─ SSE events: thinking → tool_call → complaint_update → risk_update
                  → warning (duplicates) → message → done
  └─ POST /api/v1/agent/save   (the ONLY persistence point; user clicks Save)
```

`AgentState` (see `backend/app/agent/state.py`) carries: `messages`, `intent`,
`complaint_data`, `risk_assessment`, `document_text`, `complaint_id`,
`thread_id`, `error`, `duplicate_warning`.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/agent/chat` | SSE stream for text prompt intake |
| POST | `/api/v1/agent/upload` | SSE stream for PDF/DOCX/TXT/EML intake |
| POST | `/api/v1/agent/save` | Explicit save (create or update + risk upsert) |
| GET | `/api/v1/complaints` | Paginated complaint list |
| GET | `/api/v1/complaints/{id}` | Complaint detail + risk + audit trail |
| GET | `/health` | Health check |

---

## Testing

```bash
cd backend
pytest                                   # fast unit tests (no DB / network)
pytest -m integration                    # smoke tests (needs Postgres + Groq key)
```

- `tests/test_duplicate_detector.py` — normalization, date parsing, strict
  validation, duplicate matching rules
- `tests/test_risk_coercion.py` — list→text, score clamping, boolean + enum
  normalization of messy LLM output
- `tests/test_completeness.py` — completeness checker messages / field tiers
- `tests/test_api_flow.py` — integration: `/chat` SSE round-trip, `/save`
  create + read-back, dedup self-exclusion pre-filter

Integration tests are skipped automatically unless Postgres is reachable and
`GROQ_API_KEY` is set.

---

## Environment Variables (`backend/.env`)
```env
GROQ_API_KEY=gsk_xxxxx          # Get from console.groq.com
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/pharmacy_complaints
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
PRIMARY_MODEL=openai/gpt-oss-20b
FALLBACK_MODEL=openai/gpt-oss-120b
MAX_FILE_SIZE_MB=10
DATE_TOLERANCE_DAYS=7
APP_ENV=development
```

---

## Deliverables for the assignment
- **GitHub repository** (this repo)
- **Two demo videos**: (1) working demo of all AI tools + frontend features,
  (2) end-to-end code walkthrough (frontend input → API → LangGraph nodes →
  response populating Log Customer Complaint form + AI Copilot risk panel)