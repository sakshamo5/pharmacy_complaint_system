# AIVOA Complaint Management — Code Walkthrough & Thought Process (Video 2)

The 5-10 min "explain the code by walking through the complete end-to-end workflow" video notes.
Cover: user input (prompt or PDF/email) in the frontend → frontend code → API endpoints → backend processing → AI/LangGraph workflow → how the response populates the Log Customer Complaint form and the AI Copilot Risk Assessment.

---

## Section 0 — One-liner & Stack

> "React + Redux front-end, FastAPI backend, a LangGraph agent, Groq LLMs, PostgreSQL. Users type or upload; the agent extracts into a form and produces an ICH Q9 risk assessment; nothing persists until the human clicks Save."

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + Redux Toolkit (+ react-dropzone) |
| Backend | FastAPI + SQLAlchemy 2.0 async (asyncpg) + PostgreSQL |
| AI Agent | LangGraph `StateGraph` |
| LLMs | Groq (`openai/gpt-oss-20b` default, fallback `openai/gpt-oss-120b`) |
| Font | Google Inter |

---

## Section 1 — Feature → Code Cheat Sheet

| Feature | Where in code |
|---|---|
| Text prompt → form | `frontend/src/components/AICopilot/AICopilotPanel.jsx` → `hooks/useSSEStream.js:42` → `backend/app/api/v1/endpoints/agent.py:167` |
| PDF/DOCX/TXT/EML upload | `AICopilotPanel.jsx:56` (dropzone) → `useSSEStream.js:117` → `agent.py:235` → `services/document_parser.py:15` |
| Intent classification | `agent/nodes.py:158` + `agent/prompts.py:49` |
| Extract form fields | `nodes.py:192` (log), `nodes.py:223` (edit), `nodes.py:260` (document) |
| Risk assessment | `nodes.py:357` + `_coerce_risk_types` `nodes.py:308` (prompt `prompts.py:212`) |
| Completeness checks | `nodes.py:473` + `COMPLETENESS_TIERS` `nodes.py:439` |
| Duplicate detection | `services/duplicate_detector.py:97` + SQL pre-filter `crud/complaint.py:146` |
| Save (the only persist) | `agent.py:315` `POST /api/v1/agent/save` → `crud/complaint.py:25` |
| SSE event streaming | `agent.py:46` `_run_graph_stream` → `useSSEStream.js:161` |
| Agent state | `agent/state.py:12` (`AgentState` TypedDict) + `agent/graph.py:65` |
| Form state (Redux) | `features/complaint/complaintSlice.js` |
| Chat state (Redux) | `features/agent/agentSlice.js` |
| Risk state (Redux) | `features/riskAssessment/riskSlice.js` |

---

## Part B — End-to-End Code Walkthrough

### B1. Frontend input → Redux

**Entry:** `frontend/src/main.jsx:6` renders `<App/>`; the store is Redux Toolkit in `src/app/store.js` with three slices = three UI regions:

- **`features/complaint/complaintSlice.js` — the form.** `populateFromAI:75` maps backend `snake_case → camelCase` via `FIELD_MAP:44` and records `filledFields` for the fill animation. The form is **read-only by design** (`EMPTY_FORM:13`) — the AI populates it; the human reviews + saves.
- **`features/agent/agentSlice.js` — the chat panel.** Holds `messages`, a session-scoped `threadId` (generated once at `:16`), `isStreaming`, `activeToolCall`, `duplicateWarning`/`duplicateOverride`, `error`.
- **`features/riskAssessment/riskSlice.js` — the risk panel.** Filled by `populateRiskFromAI:26`.

**SSE hook — `hooks/useSSEStream.js`:**
- `streamChat:42` maps current form state to backend snake_case (`fieldMapping` at `:48`), sends the last 10 messages as history, and POSTs `{message, thread_id, complaint_id, current_complaint, history}` to `/api/v1/agent/chat`.
- `_consumeSSEStream:161` reads `response.body.getReader()`, buffers complete `\n\n` blocks, parses each `data: {...}` line, and `switch`es on `event.type` → dispatches the right action: `thinking`/`tool_call`/`complaint_update` → `populateFromAI`, `risk_update` → `populateRiskFromAI`, `warning` → duplicate banner, `message` → final chat bubble, `progress` → upload bar, `error`, `done`.
- `SSE_TIMEOUT_MS = 120_000` (`:17`) + an `AbortController` — a hung LLM can never spin the UI forever.

### B2. Backend API — the streaming endpoint

**`app/api/v1/endpoints/agent.py`:**
- `_sse_line:41` — formats each `data: {…}\n\n` event.
- `chat_with_agent:167`:
  1. Recovers any previously saved record for this thread and **whitelists** it into agent state using `ComplaintData.model_fields` — never carries DB-only columns (status, number, timestamps) into the form.
  2. Overlays the frontend's `current_complaint` (so form edits are respected).
  3. Rebuilds LangChain `HumanMessage`/`AIMessage` history.
  4. Builds `AgentState` and returns a `StreamingResponse`.
- `_run_graph_stream:46` — the heart: emits `thinking` + `tool_call`, awaits ONE `complaint_graph.ainvoke(initial_state)`, syncs severity/priority into the form, emits `complaint_update` + `risk_update`, runs duplicate detection (`:122`, DB pre-filter at `crud/complaint.py:146` then `duplicate_detector.py:97`), emits `message` (the last AI message) then `done`. Any exception becomes an `error` SSE event.
- **Key decision:** single `ainvoke` rather than per-node streaming — simpler and far more reliable; we emit our own step events around it so the UI stays informative.

### B3. The LangGraph agent

- **`app/agent/state.py:12` `AgentState`** — a `TypedDict` shared by every node. `messages` uses LangGraph's `add_messages` reducer (`:26`) so new messages append across turns; `complaint_data` is a plain dict for easy serialization; everything is Optional.
- **`app/agent/graph.py:65`** — compiled once at startup (`graph.py:119`):
  - `START → classify_intent` → `route_by_intent:32` (pure Python map, no LLM) → `log` / `edit` / `document` / `query`.
  - After each extraction node, `route_after_extraction:51` gates: if `state["error"]` is set, skip risk (don't score empty data) → completeness; else `risk_assessment → completeness_check → END`. `query ⇒ query_answer → END`.
- **Nodes — `app/agent/nodes.py`** (full detail in Part F):
  - `_chat:41` — one helper for every LLM call: Groq, `temperature=0.0`, `max_completion_tokens=4096`, per-call `reasoning_effort`, and primary→fallback model retry.
  - `_extract_json:94` + `_extract_and_validate:113` — strip code fences / grab `{...}`, validate, retry once with a corrective prompt.
  - `classify_intent_node:158` (shortcut for documents, `low` reasoning), `log_complaint_node:192` (fresh extract), `edit_complaint_node:223` (merge-only), `document_extract_node:260` (`high` reasoning), `risk_assessment_node:357` (deterministic ICH Q9 + `_coerce_risk_types:308`), `query_answer_node:414` (Q&A only), `completeness_check_node:473` (rule-based, no LLM).
- The five prompts live in `app/agent/prompts.py`: `SYSTEM_PROMPT:7`, intent `:49`, log `:65`, edit `:126`, document `:151`, risk `:212`.

### B4. How the response populates form + risk

- Backend `risk_update` SSE → `useSSEStream.js:207` → `riskSlice.populateRiskFromAI` → risk panel.
- `complaint_update` SSE → `complaintSlice.populateFromAI` → the Log Customer Complaint form.
- `message` SSE → `agentSlice.setFinalMessage` → chat bubble.
- **Single contract:** both sides share the `ComplaintData` schema (`schemas/complaint.py:15`). Backend returns snake_case, frontend maps to camelCase. One source of truth removes field drift between the LLM output, the form, and the DB.

### B5. Save — the only write

- `ComplaintForm.jsx:47 handleSave` POSTs `{thread_id, complaint_id, complaint, risk_assessment}` → `/api/v1/agent/save`.
- Server (`agent.py:315`): validates via `ComplaintData`, **creates** a record (status *Under Investigation*) or **updates** the existing one, upserts the risk row, writes audit logs. Returns `id`, `complaint_number` (`CC-YYYY-XXXX`, `crud/complaint.py:16`), `status`.
- Frontend: `setComplaintId` + `markSaved` (`complaintSlice.js:115`) → status badge shows *Under Investigation*.

---

## Part C — Architectural Decisions & Disagreements (your judgment calls)

Frame as: "Here are the places I pushed back on the default AI suggestions and made product/engineering calls."

1. **Duplicate detection — rejected ML, chose deterministic.** The repo had `scikit-learn` and the README originally claimed TF-IDF cosine similarity. I chose **rule-based field matching** (`duplicate_detector.py`): normalize product `normalize_product:37` (strip strength/dosage forms), normalize facility with repeated suffix-stripping `normalize_hospital:46`, parse dates, match on product + issue (mandatory), facility + date only when both present, ±`DATE_TOLERANCE_DAYS` (7). *Why:* explainable ("matched 4 of 4 criteria"), zero training data, no false positives on brand names, deterministic for demos. Testing exposed (and fixed) two real cases: `"Apollo Pharmacy Ltd"` vs `"Apollo Pharmacy"` now normalize identically; `"MedPlus Pvt Ltd"` fully strips to `medplus`.
2. **Explicit Save over auto-persist (GxP mindset).** The first build auto-saved after extraction. I chose: the graph **never writes**; `POST /save` is the single persistence point, gated by duplicates (Save disabled until the human overrides). Rationale: a quality record should not exist before human review, and it shows an audit-friendly lifecycle.
3. **Deterministic risk assessment.** Identical complaints returned different scores run-to-run — unacceptable for a QA artifact. Fix: `temperature=0`, strict additive ICH Q9 rubric with canonical output strings (`prompts.py:212`), and `_coerce_risk_types:308` (list→text, string→int/bool, clamp 1–10, canonical enums). Identical input → identical structured output.
4. **Rule-based completeness checker (deleted an LLM prompt).** I initially built an LLM-based "what's missing?" prompt. I replaced it with a deterministic tiered checker (`COMPLETENESS_TIERS:439`) that also asks a **polite choice** — "provide these, or save as it is?" — because nagging users is bad UX. The dead LLM prompt was removed.
5. **Model reality vs. the brief.** The assignment said Groq `gemma2-9b-it` (optionally `llama-3.3-70b-versatile`). Live probes showed both are gone on Groq (400 decommissioned / 404 not found). I default to `openai/gpt-oss-20b` with `openai/gpt-oss-120b` fallback via `settings.PRIMARY_MODEL` / `settings.FALLBACK_MODEL` — a one-line switch to any Groq model re-released later. (Documented in README "LLM Model Note"; state this early so it doesn't look like the stack was ignored.)
6. **SSE by hand instead of EventSource.** Native `EventSource` only supports GET; our endpoint needs POST (message + history + current form). So: `fetch` POST + `ReadableStream` parser (`useSSEStream.js:161`) + a 120s `AbortController` timeout.
7. **One schema = one truth.** `ComplaintData` is used by the LLM output format, the Redux form, and the DB write path (whitelisted on restore) — removes drift across the whole pipeline.

---

## Part D — Testing (engineering proof)

- `backend/tests/` — 40 tests. **37 unit** (hermetic): `test_duplicate_detector.py`, `test_risk_coercion.py`, `test_completeness.py`. **3 integration** (`pytest -m integration`): `/chat` SSE round-trip, `/save` create + read-back, dedup self-exclusion pre-filter. Integration tests auto-skip when Postgres/Groq are unavailable.
- **Story to tell:** the tests caught a real bug — `_coerce_risk_types` compared against `Optional[str]` instead of `str`, so list→string coercion silently never ran. Also the async engine's pooled connections broke across pytest-asyncio's per-test event loops; fixed with a session-scoped loop in `pytest.ini`.
- Run: `cd backend && pytest` (unit) / `pytest -m integration` (smoke).

---

## Part E — Pocket Q&A (quick drills)

- *Why Postgres?* SQLAlchemy 2.0 async + asyncpg; idempotent startup backfills indexes on `thread_id` and `(product_name, complaint_date)` (`database.py:41,48`).
- *Why LangGraph vs a chain?* Real state graph with conditional routing, `add_messages` reducer history, reusable/testable nodes; every edge is explainable in `graph.py`.
- *Determinism?* `temperature=0` + strict prompts + `_coerce_risk_types` + rule-based duplicate/completeness logic.
- *How do edits work?* Edit intent merges only the provided fields into `complaint_data`; risk re-evaluates and re-syncs severity/priority.
- *Where's the data before Save?* Only in `AgentState` + Redux. DB untouched until `POST /save`.
- *What if the LLM returns junk?* `_extract_json` + validate + one corrective retry; risk failures degrade to a "couldn't generate risk" warning (`agent.py:112`).

---

## Part F — LangGraph Nodes Explained

### F0. Mental model
"LangGraph is a graph of Python functions. A node is `fn(state) -> dict` — it reads the shared `AgentState`, returns a **partial update** LangGraph merges back in. Edges pick the next node; some are fixed, some are conditional routers. All of it is compiled once and invoked with `ainvoke(state)`."

- `messages` uses the `add_messages` reducer (`state.py:26`) — node returns `{"messages":[AIMessage(...)]}` = append, never overwrite. Other keys are overwritten with the returned value.
- Nodes return only the keys they own (intent node → `{"intent": ...}`, extraction → `{"complaint_data": ...}`).

### F0b. Flow
```
START → classify_intent
   ├─ "log"      → log_complaint     ┐
   ├─ "edit"     → edit_complaint    ├─ route_after_extraction (error? skip risk)
   ├─ "document" → document_extract  ┘     ├─ risk_assessment → completeness_check → END
   └─ "query"    → query_answer ─────────  └─ (error) → completeness_check → END
```

### F1. Routers (`graph.py:32`, `graph.py:51`)
- `route_by_intent` — pure Python dict map intent → node. No LLM (only one classification call happens, in the node). Deterministic.
- `route_after_extraction` — if `state["error"]` set, go straight to completeness (a risk score on empty data is meaningless) so the user still hears back.

### Node cards

1. **`classify_intent_node` — `nodes.py:158`** — What's the user doing?
   - **Zero-LLM shortcut:** if `document_text` is present → `{"intent": "document"}` (UI already classified the upload; don't burn tokens).
   - Else `_chat` with `INTENT_CLASSIFICATION_PROMPT` (includes current `complaint_data` + last message) at `reasoning_effort="low"` — one word, cheapest pass.
   - Response lowercased/stripped; anything outside `{log, edit, document, query}` **defaults to "log"** (fail-safe).

2. **`log_complaint_node` — `nodes.py:192`** — fresh extraction.
   - `LOG_COMPLAINT_PROMPT` (`prompts.py:65`) asks for ONLY a JSON object shaped like `ComplaintData`.
   - `_extract_and_validate:113` = extract JSON → validate → retry once with corrective prompt; then merge over any existing fields (`nodes.py:216`).

3. **`edit_complaint_node` — `nodes.py:223`** — merge-only updates.
   - Prompt carries the **full current complaint JSON** + the correction (`prompts.py:126`); LLM returns **only changed fields**.
   - Merge starts from `current` and overlays → a follow-up can never wipe prior extraction. Same strict validate/retry path, so `complaint_type`/`complaint_date` stay canonical on edits.

4. **`document_extract_node` — `nodes.py:260`** — text → fields.
   - Text pre-parsed by `document_parser.py:15` (pdfplumber / python-docx / txt / email stdlib) before the graph.
   - `DOCUMENT_EXTRACTION_PROMPT` (`prompts.py:151`), text capped at `[:8000]`; `reasoning_effort="high"` — long-form documents deserve the most careful pass (contrast with classification's `low`; this per-node effort knob is a deliberate cost/quality trade).

5. **`risk_assessment_node` — `nodes.py:357`** — the AI Copilot panel.
   - Evaluates the **full accumulated form**, not one message.
   - Deterministic ICH Q9 rubric (`prompts.py:212`): severity triggers → additive score 1–10 with band-wins clamping → rule-based recall/CAPA/regulatory → canonical `recommended_action` → fixed output format.
   - `_extract_json` → retry once on JSON failure → `_coerce_risk_types:308` cleans messes (list→text, string→int/bool, clamp, canonical enums).
   - **Syncs back into the form:** `severity_level → initial_severity` and derived `priority` (`nodes.py:386+`). One node, two state keys.
   - On failure returns `risk_assessment=None`; API emits a "couldn't generate risk" warning (`agent.py:112`).

6. **`query_answer_node` — `nodes.py:414`** — pure Q&A. Appends current complaint JSON to system prompt, answers with `_chat`, returns an `AIMessage`. **Never touches `complaint_data`** — side questions can't corrupt the form.

7. **`completeness_check_node` — `nodes.py:473`** — rule-based, no LLM.
   - `COMPLETENESS_TIERS:439`: 4 critical + 5 important fields.
   - Three paths (unit-tested): critical missing → "give me X (or save as-is)"; only important missing → "provide these, or save as it is?"; complete → success message with product + severity → prompts Save.
   - Returns an `AIMessage`; the `add_messages` reducer appends it — this is the last message the API streams.

### One example walking the graph
"User types: *'expiry is June 2028, quantity 48, source Apollo'*":
1. `classify_intent` sees existing `complaint_data` → returns `edit`.
2. `edit_complaint` outputs only `{expiry_date, quantity_affected, complaint_source}` → merged, everything else preserved → validated.
3. `route_after_extraction` → no error → `risk_assessment` re-evaluates the fuller form → `_coerce_risk_types` → severity/priority re-synced.
4. `completeness_check` → no critical missing → success message appended.
5. `_run_graph_stream` streams `complaint_update` + `risk_update` + `message` → frontend re-fills form + risk panel.

### "I understand LangGraph" soundbites
- "One LLM call adds one message; the whole conversation lives in `AgentState`, the graph never mid-flow blocks on the DB."
- "Nodes are ordinary functions — I unit-test them without running the LLM (see `tests/test_completeness.py`), which is the payoff of keeping routing + completeness rule-based."
- "Deterministic pieces are pure Python; LLM pieces are prompt + validate + retry — so the graph degrades gracefully instead of throwing."

---

## Suggested Video 2 Timing (5-10 min)
0:00–0:45 → Section 0 one-liner + stack
0:45–2:00 → cheat-sheet overview (Section 1)
2:00–4:00 → B1–B5 walkthrough: one strawman complaint from input → form → save
4:00–6:00 → Part F: open `graph.py` + `nodes.py`, walk every node on the same complaint
6:00–8:00 → Part C: the disagreement/decision slides (deterministic over ML, Save-gated GxP, temp-0 risk, model reality)
8:00–9:00 → Part D: run `pytest` live, show the coercion test that caught a real bug
9:00–9:30 → Part E: 3 soundbytes + wrap