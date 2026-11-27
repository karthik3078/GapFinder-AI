# GapFinder AI

GapFinder AI is a local-first learning diagnosis and adaptive revision planning system. It turns a student's own syllabus, study notes, and past exam papers into an evidence-grounded diagnosis of knowledge gaps and generates a time-budgeted daily revision schedule.

Built with **React 19**, **Tailwind CSS**, **FastAPI**, **SQLite / SQLAlchemy**, persistent **ChromaDB**, **PyMuPDF**, and the **Google GenAI SDK**.

The default mode is an explicitly labeled **offline demonstration**. It requires no external API keys and seeds no artificial student scores. Every displayed score originates from submitted assessments. Live Gemini generation and Google embeddings can be configured via environment variables.

---

## 1. Problem & Workflow

### The Problem
Students preparing for comprehensive examinations often struggle with:
- **Blind spots:** Relying on intuition to select study topics rather than measured diagnosis.
- **Uncalibrated effort:** Spending disproportionate time on topics that carry low exam weight.
- **Disconnected resources:** Managing syllabi, lecture notes, and past papers in separate silos without cross-referencing.
- **Unreliable AI tools:** Off-the-shelf generative AI that hallucinates explanations, cites non-existent sources, or offers unbounded study plans.

### The Complete Learning Loop
GapFinder AI enforces a closed, measurable study loop:

```text
Upload Materials ➔ Topic Hierarchy & Paper Mapping ➔ Diagnostic Assessment ➔ Gap Report ➔ Revision Plan ➔ Retest ➔ Updated Plan
```

1. **Materials:** Ingest syllabus (structure), lecture notes / textbooks (knowledge grounding), and past exam papers (weightage estimation).
2. **Topic map:** Build syllabus units and leaf topics, then link past-paper questions to leaf topics using vector retrieval.
3. **Diagnostic:** Generate cited multiple-choice and short-answer questions from indexed course excerpts. Answer keys remain withheld server-side until submission.
4. **Gap report (Central Screen):** Evaluate responses deterministically (MCQs) and against rubrics with evidence citations (short answers). Classify topics as **Weak**, **Medium**, **Strong**, or **Not assessed**.
5. **Revision plan:** Specify available days and minutes per day. The system builds an integer-bounded daily schedule prioritizing high-weight knowledge gaps.
6. **Retest:** Retesting updates topic accuracy immediately, updates the Gap report, and increments the plan version while preserving completion records.

---

## 2. Quick Start

### Prerequisites
- **Python 3.12** (tested on 3.12.9)
- **Node.js 22.12+ or 24**

### Setup (Windows PowerShell)

```powershell
# 1. Create Python 3.12 virtual environment and install dependencies
uv venv --python 3.12 .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt

# 2. Copy default environment settings
Copy-Item .env.example .env

# 3. Install frontend dependencies and build assets
cd frontend
npm ci
npm run build
cd ..

# 4. Start the application server
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Setup (macOS / Linux)

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
cp .env.example .env
(cd frontend && npm ci && npm run build)
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000** in your browser.

---

## 3. Demo Credentials & Evaluation Walkthrough

### Credentials
- **Email:** `student@demo.com`
- **Password:** `demo123`
*(A "Fill demo credentials" shortcut is provided on the sign-in screen.)*

### 5-Minute Evaluation Walkthrough
1. **Sign In & Load Demo Course:** Sign in using the demo account. Click **Load sample biology course** (loads three sample documents: `syllabus.txt`, `biology_notes.txt`, and `past_paper.txt`).
2. **Inspect Gap Report:** Note that all 6 leaf topics are labeled **Not assessed** with no initial scores invented.
3. **Inspect Topic Map:** Navigate to **Topic map** to review the syllabus hierarchy and past-paper question mappings. Questions flagged for review can be manually confirmed or remapped.
4. **Take Diagnostic:** Navigate to **Diagnostic**. Leave topic selection blank to adaptively test the highest-priority topics. Notice that answer keys and quotes are withheld during the quiz. Submit your answers.
5. **Review Feedback & Gaps:** Review the rubric evaluation and quoted source evidence. Open **Gap report** to see updated statuses (**Weak**, **Medium**, or **Strong**). Topics not assessed remain explicitly **Not assessed**.
6. **Build Revision Plan:** Navigate to **Revision plan**, set **3 days at 45 min/day**, and generate the schedule. Tasks are allocated strictly within the time budget. Check off a task to verify persistent completion.
7. **Retest a Topic:** Retest a weak topic. Answering correctly updates the topic diagnosis to **Strong** and increments the Revision plan to **Version 2**.
8. **Consult Grounded Tutor:** Navigate to **Tutor**. Ask `"What role does ATP play in active transport?"` to inspect the source-grounded explanation and chunk citations. Ask an unsupported question to verify the explicit "Evidence needed" notice.

---

## 4. Architecture: Retrieval vs. Generation

Retrieval and generation are strictly separated into dedicated pipeline stages:

```text
PDF / TXT Ingestion
       │
       ▼
Page/Section Chunking (700 chars + 100 overlap) ➔ Security Quarantine Check
       │
       ├─────────────────────────────────┬─────────────────────────────────┐
       ▼                                 ▼                                 ▼
SQLite Storage (SQLChunks)      Vector Store (ChromaDB)          Topic Hierarchy
       │                                 │                                 │
       └────────────────┬────────────────┘                                 │
                        ▼                                                  ▼
                 retrieval.py                                      topics.py
       (Scoped Chroma search + SQL owner recheck)          (Leaf topics & exam weights)
                        │
                        ▼
                 generation.py
       (Structured Gemini output / deterministic demo bank)
                        │
                        ▼
       Citation Validation (Allowed chunk IDs + verbatim quote check)
                        │
                        ▼
       Server-Held Diagnostic / Tutor Response
```

- **`retrieval.py`** queries the vector store and returns raw database chunks filtered by authenticated `user_id` and `course_id`. It performs no text generation.
- **`generation.py`** receives retrieved chunks as context and produces structured output. It has no direct database or vector store access.
- **Citation validation (`validate_citations`):** Ensures that all citations returned by the model reference authorized chunk IDs from the retrieval phase and contain verbatim quotes from those chunks.
- **Security quarantine:** Input chunks containing prompt-injection patterns or instruction-override attempts are quarantined and excluded from AI context.

---

## 5. Scoring, Classification & Planning Rules

### Laplace-Smoothed Exam Weightage
Past-paper marks are allocated to leaf topics through vector similarity matching. To prevent topics without past exam questions from being completely ignored, Laplace smoothing is applied:

$$\text{Weight}(T) = \frac{\text{Accepted Marks}(T) + 1}{\sum_{i} \text{Accepted Marks}(T_i) + N_{\text{leaves}}}$$

If no past papers are uploaded, all leaf topics share equal weight: $\frac{1}{N_{\text{leaves}}}$.

### Gap Classification
Topic accuracy is calculated as the mean score across all questions for that topic in the **most recent submitted assessment**:
- **Weak:** Score $< 50\%$
- **Medium:** $50\% \le \text{Score} < 80\%$
- **Strong:** $\text{Score} \ge 80\%$
- **Not assessed:** No submitted questions yet ($\text{Score} = \text{null}$)

Untested topics are never labeled weak; they receive a diagnostic planning priority.

### Time-Budgeted Revision Schedule
Each topic is assigned a revision priority:

$$\text{Priority}(T) = \begin{cases} 
(1 - \text{Accuracy}(T)) \times \text{Weight}(T), & \text{if assessed} \\
0.75 \times \text{Weight}(T), & \text{if not assessed}
\end{cases}$$

- Topics with high exam weight and low accuracy are scheduled first.
- Daily minutes are allocated using a largest-remainder integer distribution, guaranteeing that the daily total never exceeds the student's available budget.
- Marking tasks complete records progress but does not artificially inflate topic mastery.

---

## 6. Offline Demo vs. Live AI Behavior

| Capability | Offline Demo (`AI_MODE=demo`) | Live AI (`AI_MODE=live`) |
| --- | --- | --- |
| **API Key Requirement** | None; fully local and deterministic. | Google GenAI API key (`GEMINI_API_KEY`). |
| **Embeddings** | Deterministic 768-dim MD5 lexical hashing. | Google `gemini-embedding-001` (768-dim). |
| **Topic Extraction** | Regex Markdown outline parser (`# Unit`, `## Topic`). | Structured Gemini topic tree extraction. |
| **Paper-to-Topic Mapping** | Chroma vector search with local embeddings. | Chroma vector search with Google embeddings. |
| **Quiz Generation** | Curated demo fixtures (verified against source chunks) + extractive fallback. | Structured Gemini question generation grounded in retrieved excerpts. |
| **MCQ Scoring** | Exact comparison against server-held option index. | Exact comparison against server-held option index. |
| **Short-Answer Scoring** | Deterministic lexical rubric coverage matching. | Gemini rubric evaluation with partial credit and citation validation. |
| **Tutor** | Direct retrieval of source excerpts. | Conversational explanations citing retrieved excerpts; abstains when evidence is missing. |

To enable Live AI mode, edit your `.env`:
```dotenv
AI_MODE=live
EMBEDDING_PROVIDER=google
GEMINI_API_KEY=your_actual_gemini_key
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSIONS=768
```
*(After changing embedding configuration, run `python -m backend.reindex` to migrate existing vector collections.)*

---

## 7. Project Layout

```text
GapFinder-AI/
├── backend/
│   ├── config.py           # Typed settings & environment validation
│   ├── database.py         # SQLAlchemy models (User, Course, Quiz, Plan, etc.)
│   ├── security.py         # PBKDF2 hashing, session tokens, injection heuristics
│   ├── ingestion.py        # PyMuPDF/TXT parsing, chunking, and quarantine checks
│   ├── retrieval.py        # Scoped ChromaDB vector retrieval
│   ├── generation.py       # Gemini SDK integration & offline generation fallback
│   ├── schemas.py          # Pydantic v2 schemas for requests & model payloads
│   ├── topics.py           # Syllabus hierarchy & Laplace-smoothed weightage
│   ├── diagnostic.py       # Hidden keys, grading, gap classification, and scheduling
│   ├── main.py             # FastAPI routing, auth middleware, and static hosting
│   ├── demo_bank.py        # Curated server-side offline question fixtures
│   └── reindex.py          # Vector store reindexing CLI utility
├── frontend/
│   ├── src/
│   │   ├── components/     # Modular React components (GapReport, Diagnostic, etc.)
│   │   ├── api.js          # API client wrapper with standardized error handling
│   │   ├── styles.css      # Cohesive, responsive Tailwind CSS styling
│   │   └── main.jsx        # Root application orchestrator
│   ├── package.json
│   └── vite.config.js
├── sample_materials/       # Fictional demo materials (syllabus, notes, past paper)
├── tests/                  # Pytest test suite covering full learning loop & security
├── start.ps1               # Windows PowerShell startup script
├── start.sh                # Linux/macOS startup script
├── PROJECT_WALKTHROUGH.md  # Detailed interview walkthrough & design document
└── README.md
```

---

## 8. Verification & Test Suite

Run the automated test suite:
```sh
.\.venv\Scripts\python.exe -m pytest -v
```

All **30 tests** pass:
- `tests/test_evidence.py`: 19 passed (PyMuPDF PDF parsing, chunking, prompt injection quarantine, citation validation, gap score thresholds).
- `tests/test_persistence.py`: 1 passed (database schema constraints and roundtrip persistence).
- `tests/test_workflow.py`: 10 passed (end-to-end learning loop, hidden answer keys, atomic submissions, retesting, plan incrementing, tutor grounding, and user isolation).

To verify the frontend build:
```sh
cd frontend
npm run build
```
*(Built with Vite 7: 0 errors, production assets bundled cleanly in `frontend/dist`.)*

---

## 9. Limitations & Boundaries

- **Local single-process deployment:** Designed for local evaluation. Not configured for distributed multi-node clustering or external object storage.
- **PDF text extraction:** Relies on embedded fonts in PDFs via PyMuPDF; scanned image-only PDFs require OCR before upload.
- **Citation provenance vs. semantic entailment:** Citation validation proves that quotes exist in the retrieved chunks, but cannot guarantee that a live model does not misinterpret a valid quote.
- **Short-answer offline grading:** Lexical rubric matching in offline demo mode checks keyword presence; it cannot evaluate subtle paraphrases or complex nuances without live AI mode.
