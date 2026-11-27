# GapFinder AI — Verification Report

**Date:** 2026-11-27  
**Session:** Assessment preparation — final verification  
**Environment:** Windows 11, Python 3.12.9, Node.js 24.12.0

---

## 1. Backend Tests

```
.\.venv\Scripts\python.exe -m pytest -v
```

**Result: 30 passed in 49.11s — 0 failures, 0 errors**

| Test File | Tests | Coverage |
|---|---|---|
| `test_evidence.py` | 19 | Gap boundary thresholds, password salting, PDF/TXT extraction, OCR failure handling, chunk overlap/quarantine, citation fail-closed, prompt injection quarantine, live-mode key requirements, embedding mismatch, provider schema validation, grading rollback, tutor abstention, vector-to-SQL ownership check |
| `test_persistence.py` | 1 | SQLite + ChromaDB schema roundtrip after server restart |
| `test_workflow.py` | 10 | Complete learning loop, idempotent demo load, idempotent submission, partial assessment preserves `not_assessed`, course/user isolation, password hash + session logout, CSRF/origin protection, invalid answer no mutation, plan completion + stale version, mapping correction changes weight |

---

## 2. Frontend Build

```
npm --prefix frontend run build
```

**Result: ✓ Built in 5.71s — 1591 modules transformed, 0 errors**

| Artifact | Size | Gzip |
|---|---|---|
| `dist/index.html` | 0.62 kB | 0.38 kB |
| `dist/assets/index-CrDRgIOF.css` | 34.91 kB | 7.54 kB |
| `dist/assets/index-Bb4y_m_t.js` | 280.79 kB | 85.77 kB |

---

## 3. API Verification (automated, observed this session)

All checks were run against the live server (`http://127.0.0.1:8000`) using Python `requests`. These are **API tests**, not browser UI tests.

### 3.1 Health & Authentication

| Check | Result |
|---|---|
| `GET /api/health` → 200, mode=demo, demo_user_available=true | ✓ PASS |
| `POST /api/auth/login` with `student@demo.com`/`demo123` → 200 | ✓ PASS |
| Response contains `name`, `email`; no `password` or `hashed_password` | ✓ PASS |
| `GET /api/auth/me` → 200 (session valid) | ✓ PASS |
| `POST /api/auth/logout` → 200 | ✓ PASS |
| `GET /api/auth/me` → 401 after logout | ✓ PASS |

### 3.2 Demo Course Load

| Check | Result |
|---|---|
| `POST /api/demo/load` → 200, returns course `id` and `name` | ✓ PASS |
| Notice field: "Sample material loaded. No attempts or scores were seeded." | ✓ PASS |
| Second call returns same course `id` (idempotent) | ✓ PASS |
| 3 documents loaded: `syllabus.txt`, `biology_notes.txt`, `past_paper.txt` | ✓ PASS |

### 3.3 Topic Hierarchy

| Check | Result |
|---|---|
| 9 total topics (3 parent units + 6 leaf topics) | ✓ PASS |
| `is_leaf` flag present on all topics | ✓ PASS |
| Leaf topic weights sum to 1.000 (Laplace-normalized) | ✓ PASS |
| Parent weights are roll-ups of their children (sum = leaf_sum) | ✓ PASS |

### 3.4 Past Papers

| Check | Result |
|---|---|
| 8 past-paper questions present | ✓ PASS |
| All 8 have `confidence` values | ✓ PASS |
| All 8 have `citation.chunk_id` (nested in `citation` object) | ✓ PASS |

### 3.5 Quiz Creation & Security

| Check | Result |
|---|---|
| `POST /api/courses/{id}/quizzes` → 201 | ✓ PASS |
| 12 questions generated: 6 MCQs + 6 short-answer | ✓ PASS |
| MCQs have `kind=mcq`, short answers have `kind=short` | ✓ PASS |
| All 4 MCQ options present per question | ✓ PASS |
| `answer_index = null` in quiz response (not leaked before submission) | ✓ PASS |
| `reference_answer = null` in quiz response (not leaked before submission) | ✓ PASS |

### 3.6 Submission & Grading

| Check | Result |
|---|---|
| MCQ answers submitted as strings (`"0"`, `"1"`, ...) → 200 | ✓ PASS |
| Short answer text submitted as strings → 200 | ✓ PASS |
| Score returned as float in [0, 1] | ✓ PASS |
| Per-question `results` array: `answer_index` revealed post-submission | ✓ PASS |
| MCQ grading: `method=deterministic_mcq`, cited evidence quote | ✓ PASS |
| Short-answer grading: `method=demo_lexical_rubric` (correctly labelled offline) | ✓ PASS |
| Resubmit returns same score (idempotent) | ✓ PASS |

### 3.7 Gap Report

| Check | Result |
|---|---|
| `GET /api/courses/{id}/gaps` → 200 | ✓ PASS |
| After submission: assessed topics show `weak`/`medium`/`strong` status | ✓ PASS |
| Untested topics explicitly show `not_assessed` (not fabricated as weak) | ✓ PASS |

### 3.8 Revision Plan

| Check | Result |
|---|---|
| `POST /api/courses/{id}/plan` with `days=3, minutes_per_day=45` → 200 | ✓ PASS |
| Plan has 3 days | ✓ PASS |
| Day 1 total = 45 min (within budget) | ✓ PASS |
| Day 2 total = 45 min (within budget) | ✓ PASS |
| Day 3 total = 45 min (within budget) | ✓ PASS |
| `PATCH /api/courses/{id}/plan/{plan_id}` mark task complete → 200 | ✓ PASS |

### 3.9 Progress

| Check | Result |
|---|---|
| `GET /api/courses/{id}/progress` → 200 | ✓ PASS |
| `attempts > 0` after quiz submission | ✓ PASS |
| `history` array populated with attempt records | ✓ PASS |

### 3.10 Tutor

| Check | Result |
|---|---|
| `POST /api/courses/{id}/tutor` during open quiz → 409 "Submit or discard first" | ✓ PASS |
| After quiz closed: tutor returns 200 with `answer` and `citations` | ✓ PASS |
| Supported question (membrane transport / active transport): offline excerpts returned | ✓ PASS |
| Offline mode answer clearly labelled "Offline source excerpts (not an AI explanation)" | ✓ PASS |
| Out-of-scope question (capital of France): `insufficient_evidence=true` | ✓ PASS |
| Insufficient evidence response: "Your uploaded study material does not provide enough evidence…" | ✓ PASS |

### 3.11 Security Boundaries

| Check | Result |
|---|---|
| Cross-user `GET /api/courses/{other_user_course_id}/gaps` → 404 | ✓ PASS |
| Cross-user `POST /api/courses/{other_user_course_id}/quizzes` → 404 | ✓ PASS |
| No password/hashed_password fields in any user response | ✓ PASS |
| No answer keys in pre-submission quiz response | ✓ PASS |

### 3.12 Source Inspection

| Check | Result |
|---|---|
| `GET /api/courses/{id}/sources/{chunk_id}` → 200 | ✓ PASS |
| Returns `text`, `filename`, `page`, `section`, `quote`, `quarantined` | ✓ PASS |

---

## 4. Live Gemini Check

**Status: NOT RUN — no API key configured.**

The `.env` file has `GEMINI_API_KEY=` (empty) and `AI_MODE=demo`. All checks above used demo/offline mode.

### To run the live smoke test

1. Edit `.env`:
   ```dotenv
   AI_MODE=live
   EMBEDDING_PROVIDER=google
   GEMINI_API_KEY=<your_key>
   GEMINI_MODEL=gemini-2.5-flash
   EMBEDDING_MODEL=gemini-embedding-001
   EMBEDDING_DIMENSIONS=768
   ```

2. Rebuild the vector index (required when switching embedding providers):
   ```powershell
   .\.venv\Scripts\python.exe -m backend.reindex
   ```

3. Restart the server:
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```

4. Run the smoke test (uses only the fictional sample materials; at most 6 generation calls):
   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests/ -v -k "not persistence"
   ```

5. To verify live embedding on an isolated test index without touching the main collection:
   ```powershell
   .\.venv\Scripts\python.exe -c "
   from backend.retrieval import VectorStore
   vs = VectorStore('test_smoke_index')
   vs.add([('chunk-1', 'Active transport uses ATP.', {'user_id': 'test', 'course_id': 'test', 'quarantined': False})])
   results = vs.query('ATP energy', 'test', 'test', k=1)
   print('Embedding OK:', len(results) == 1)
   vs.delete_collection()
   "
   ```

**Stop immediately** if the API returns `401`, `403`, quota exhaustion, or a billing error. Do not retry.

---

## 5. Browser UI Verification

**Status: NOT VERIFIED** — browser automation was unavailable during this session. Visual UI checks could not be performed programmatically.

The following items were checked via API tests (section 3) and are functionally confirmed at the HTTP layer:
- Authentication flow, demo load, topic hierarchy, past papers, quiz creation, submission, gap report, plan, tutor, source inspection, cross-user isolation, logout.

The following require manual browser verification by the evaluator:
- Login screen renders with demo credential fill button.
- Gap Report is the central/default screen after login.
- Weak/Medium/Strong/Not assessed displayed clearly with correct colours.
- MCQ option selection, short-answer text input, and submit button work correctly in-browser.
- Post-submission feedback shows correct/incorrect badges, rubric criteria, and cited quotes.
- Source modal opens on citation click and displays chunk text.
- Revision plan checkboxes persist after refresh without changing mastery.
- Sidebar navigation, course selector, and mobile layout function correctly.
- Mode indicator visible and labelled ("Demo mode" in top header area).

---

## 6. Known Limitations

| Limitation | Impact |
|---|---|
| Demo lexical rubric grading (keyword matching) | May miss paraphrases or accept superficial answers. Explicitly labelled as `demo_lexical_rubric` in results. |
| Local MD5 lexical embeddings | Retrieval quality is lower than semantic embeddings. Topic mapping may group unrelated topics. Only affects demo mode. |
| SQLite single-process | Not designed for concurrent multi-user load. For the demo scenario this is not relevant. |
| No email verification or password reset | Expected for a demo/assessment prototype. |
| No live Gemini test this session | No API key was configured. Live behaviour requires a valid `GEMINI_API_KEY`. |
