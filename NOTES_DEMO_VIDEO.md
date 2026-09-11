# AIVOA Complaint Management — Demo Video Script (Working Demonstration)

The 5-10 min "working demonstration of all implemented AI tools and frontend features" video.

---

## Opening One-Liner

> "I built an AI copilot for a pharmaceutical QMS Customer Complaints module. A user pastes text or uploads a PDF/email; a LangGraph agent classifies intent, extracts complaint fields into a form, produces an ICH Q9 risk assessment, checks completeness, and flags duplicates — but nothing is saved to the database until the human clicks Save."

**Framing (say this to show domain research):** The module maps to the QMS process *Log → Assess → Investigate → CAPA*. References: ICH Q9 (risk management), ICH Q10 (CAPA / quality systems), FDA 21 CFR (regulatory reporting obligations). You do not need to be a domain expert — show you researched the problem and its compliance context.

**Stack (30 sec):** React 18 + Redux Toolkit / FastAPI / LangGraph / Groq LLM / PostgreSQL / Google Inter font. UI = left "Log Customer Complaint" form (read-only) + right "AI Copilot" chat & risk panel.

---

## Demo Script (what to click, what to say)

### A1. Open the app
- Run backend: `uvicorn app.main:app --reload --port 8000` (from `backend/`)
- Run frontend: `npm run dev` (from `frontend/`)
- Point at layout: form left, AI Copilot chat right, pharma-blue/purple theme, Inter font.
- Optional: open FastAPI docs at `http://localhost:8000/docs` and note SSE + REST endpoints exist.

**Say:** "The left form is read-only — the AI fills it; a human reviews and saves."

### A2. Text intake — the main flow
Paste into the chat:

> "Apollo Pharmacy reported discolored Aspirin 500mg tablets from batch B-1412. Quality issue."

While it streams, narrate the event sequence:
1. "Thinking: *Extracting complaint details...*"
2. Tool-call badge: `log_complaint`
3. Form auto-fills with a highlight animation (product name, batch, type, description...)
4. AI Copilot Risk Assessment panel populates: severity, risk-score bar (1-10), recommended action, root-cause hypothesis, CAPA flag + steps, recall/regulatory flags
5. Final AI message appears in chat

**Say:** "Nothing touched the database yet — this is all in-memory agent state inside LangGraph."

### A3. Completeness follow-up (expanded feature)
Because source, dates, expiry, and quantity were not given, the agent replies with:

> "Form is complete... only a few optional details are still missing: complaint source, complaint date, expiry date, manufacturing date, and quantity affected. Do you want to provide these, or save the complaint as it is?"

Reply:

> "Expiry is June 2028, quantity 48 tablets, source Apollo Pharmacy."

Show that **only those fields update** — product/batch/type/description are preserved (edit tool merges, never overwrites). Risk panel re-evaluates on the fuller form.

### A4. Duplicate detection (bonus)
Submit the same complaint again. Show:
- Warning banner: *"Possible duplicate of CC-XXXX... (same product, issue, source, date)."*
- The chat message is prefixed with the duplicate notice.
- **Save button is disabled**.
- **Override checkbox** "I've reviewed it — save anyway" re-enables it.

**Say:** "The AI detects and warns, but only a human can overrule — the copilot never silently creates or deletes records."

### A5. PDF / email upload (bonus flow)
Drag-drop `complaint_amoxicillin.pdf` (generated once by `backend/sample_data/generate_sample_data.py`).
- Progress bar 0% → 100%
- "Document parsed successfully. Running AI extraction..."
- Form fills from the document; risk assessment generated.

**Say:** "Uploads go through a POST (not GET), which is why I hand-rolled the SSE reader instead of using the browser's EventSource."

### A6. Save (the only persistence point) + verify
Click **Save Complaint**.
- Button shows "Saving..." then success message: `Complaint CC-2026-XXXX saved — status Under Investigation.`
- Status badge flips to **Under Investigation**.
- Open the complaints list/detail page: record, risk assessment, audit trail visible.

**Say:** "Every conversation turn was zero-database; this one button is the single source of record."

---

## Cue Sheet (print beside you)

| Step | Action | Key line to say |
|---|---|---|
| A1 | launch, orient | "form is read-only, AI fills, human reviews" |
| A2 | paste prompt | "classify → extract → risk → completeness; no DB write yet" |
| A3 | reply with missing fields | "edit merges only new fields, preserves the rest" |
| A4 | re-submit same complaint | "detect yes, decide only human; Save gated" |
| A5 | upload PDF | "POST-based SSE, progress, doc extraction" |
| A6 | Save + open list | "the Save button is where the record is born" |

## Delivery tips
- Keep the demo under ~5-6 minutes; leave time for the code walkthrough video.
- Do the A2 and A3 flows with the same complaint so it reads as one narrative.
- If the duplicate step feels slow, reuse the DUPLICATE warning by saving once first, then typing the same complaint from a fresh thread.