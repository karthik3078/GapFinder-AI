# GapFinder AI — Project Walkthrough & Architecture Guide

This document is an architectural guide and technical walkthrough of **GapFinder AI**, prepared for interview discussion and assessment evaluation. It explains the project rationale, technical design choices, security boundaries, mathematical formulas, and demonstration steps.

---

## 1. Executive Summary & Problem Statement

### The Problem
When students prepare for cumulative exams, they typically face three major challenges:
1. **Uncalibrated intuition:** Students often spend study time reviewing comfortable topics rather than identifying and confronting their actual knowledge gaps.
2. **Disconnected materials:** Course syllabi, lecture notes/textbooks, and past exam papers reside in separate documents. Students rarely know the relative exam weight of each syllabus topic.
3. **Hallucinatory AI study tools:** Standard generative AI chatbots easily hallucinate factual explanations, fail to cite course materials, and lack deterministic grading or time-bounded study schedules.

### The Solution: GapFinder AI
GapFinder AI is a local-first, evidence-grounded diagnostic application. It ingests the student's own syllabus, notes, and past papers, constructs a reviewable topic hierarchy, extracts past-paper exam weights, generates cited diagnostic assessments, categorizes demonstrated mastery, and builds a time-budgeted daily revision schedule.

---

## 2. Complete End-to-End Learning Loop

The application is structured around a closed, measurable loop:

```
[1. Materials Upload]
       │ (PDF / TXT: syllabus, notes, past exam papers)
       ▼
[2. Topic Hierarchy & Paper Mapping]
       │ (Units + leaf topics; past questions mapped via vector similarity; Laplace-smoothed weights)
       ▼
[3. Diagnostic Assessment]
       │ (MCQ + short-answer questions generated from source chunks; keys hidden until submission)
       ▼
[4. Gap Report (Central Screen)]
       │ (Categorizes topics: Weak <50%, Medium 50-79%, Strong ≥80%, Not assessed)
       ▼
[5. Revision Plan]
       │ (Priority = (1 - score) * weight; unassessed = 0.75 * weight; time-bounded daily schedule)
       ▼
[6. Retest & Updated Plan]
         (Submitting a retest immediately updates topic accuracy and refreshes the plan to Version N+1)
```

1. **Upload:** User uploads syllabus, notes, and past papers. Texts are chunked with overlap, sanitized, and stored in SQLite + ChromaDB.
2. **Topic map:** The system builds the syllabus hierarchy (units and leaf topics). Past paper questions are matched to leaf topics with vector retrieval and reviewable confidence scores.
3. **Diagnostic:** Student selects topics (or takes an adaptive diagnostic). Server withholds answer keys, rubrics, and quotes until submission.
4. **Gap report:** Upon submission, the server deterministically grades MCQs and performs evidence-based rubric scoring for short answers. Topics update to Weak, Medium, or Strong. Untested topics explicitly remain **Not assessed**.
5. **Revision plan:** Student specifies daily study minutes and total days. The system allocates tasks prioritizing the weakest, highest-weight topics.
6. **Retest & Refresh:** Retesting updates the latest topic score, adjusts the gap report, and increments the plan version while preserving completion history.

---

## 3. Architecture & File Breakdown

### Backend (`/backend`)

| File | Primary Responsibility |
| --- | --- |
| `main.py` | FastAPI server, cookie sessions, endpoint authorization, request throttling, error handlers, and static file hosting. |
| `config.py` | Typed Pydantic settings: AI mode (`demo` vs `live`), embedding providers (`local` vs `google`), model IDs, upload thresholds. |
| `database.py` | SQLAlchemy database models (`User`, `LoginSession`, `Course`, `Document`, `Chunk`, `Topic`, `PaperQuestion`, `Quiz`, `RevisionPlan`, `TutorMessage`). |
| `security.py` | Password hashing (PBKDF2-HMAC-SHA256, 600,000 iterations), opaque token hashing (SHA-256), and prompt-injection regex heuristics. |
| `ingestion.py` | PyMuPDF and TXT extraction, 700-character chunking with 100-character overlap, section tagging, and malicious instruction quarantining. |
| `retrieval.py` | Persistent vector store abstraction using ChromaDB. Handles deterministic local MD5 lexical hashing or Google GenAI embeddings. |
| `generation.py` | Model interaction layer with strict Pydantic schemas. Supports live Gemini API calls and offline deterministic fixture/extractive fallbacks. Validates verbatim quote citations. |
| `schemas.py` | Input validation schemas (Pydantic v2) for logins, courses, quiz submissions, plans, and tutor questions. |
| `topics.py` | Hierarchy parser (Markdown `# Unit` and `## Topic` outlines), vector-based past-paper mapping, and Laplace-smoothed topic weighting. |
| `diagnostic.py` | Core algorithmic logic: hidden answer keys, deterministic MCQ scoring, lexical/Gemini rubric grading, gap classification, and largest-remainder plan scheduling. |
| `demo_bank.py` | Curated offline question fixtures matching sample biology materials, used only when exact source evidence is verified. |
| `reindex.py` | CLI utility to rebuild Chroma vector collections when switching embedding models or dimensions. |

### Frontend (`/frontend/src`)

The frontend was refactored from a monolithic 1900-line file into modular, single-responsibility React components:

| Component | Responsibility |
| --- | --- |
| `main.jsx` | Application state orchestrator, authentication lifecycle, course selection, and routing. |
| `api.js` | Fetch wrapper handling JSON/FormData serialization, credentials, and standardized error parsing. |
| `styles.css` | Cohesive, accessible, single-accent (Indigo) styling with high-contrast text and responsive layout. |
| `components/Common.jsx` | Reusable primitives: `Button`, `Badge`, `MetricCard`, `EmptyState`, `CitationsList`, `ModeIndicator`. |
| `components/Login.jsx` | Clean authentication screen with direct one-click demo credentials fill (`student@demo.com` / `demo123`). |
| `components/Sidebar.jsx` | Responsive navigation sidebar featuring concise labels and an active diagnostic badge. |
| `components/Header.jsx` | Breadcrumbs, course selector, new course creation, and compact mode indicator. |
| `components/GapReport.jsx` | **The central screen.** Displays assessed mastery, topic status breakdown (Weak, Medium, Strong, Not assessed), exam weights, review points, and retest triggers. |
| `components/Diagnostic.jsx` | Topic selection, active test interface (MCQ + Short Answer), and post-submission rubric review with unlocked source quotes. |
| `components/RevisionPlan.jsx` | Time-budget configuration and daily schedule visualization with task checkboxes and direct retest/tutor links. |
| `components/TopicMap.jsx` | Syllabus tree view and past-paper question mapping table with confidence badges and review/confirm controls. |
| `components/Materials.jsx` | Document upload dropzone, processing pipeline explanation, and document repository table. |
| `components/Progress.jsx` | Real historical activity metrics and interactive diagnostic attempt score chart. |
| `components/Tutor.jsx` | Topic-scoped Q&A interface with source citations and explicit "evidence needed" warnings when grounding is missing. |
| `components/SourceModal.jsx` | Accessible dialog displaying exact source chunk text, filename, page, section, and quarantine warnings. |

---

## 4. Key Architectural & Design Decisions

### 1. Strict Separation of Retrieval and Generation
- **Retrieval (`retrieval.py`)** only queries Chroma collections and returns raw SQL chunks filtered by `user_id` and `course_id`. It never generates answers or modifies text.
- **Generation (`generation.py`)** receives retrieved excerpts as inputs. It has no access to Chroma or the database.
- **Citation validation (`validate_citations`):** The model cannot cite arbitrary documents. Every citation returned must match an allowed chunk ID from the retrieval stage, and its quoted text must appear verbatim within that chunk.

### 2. Multi-Tenant User Isolation & Security
- Courses and documents are strictly partitioned by `user_id` and `course_id`.
- Chroma collections are named using `f"user_{user_id}_course_{course_id}"` and further filtered by query metadata.
- SQL ownership checks re-validate every chunk returned by Chroma to prevent vector poisoning or cross-user data leakage.
- Passwords are encrypted with PBKDF2 (600,000 rounds). Sessions use cryptographic 32-byte tokens; only SHA-256 hashes of tokens are stored in the database.

### 3. Answer Key Withholding & Atomic Submissions
- When a diagnostic quiz is created, questions are sent to the frontend **without** `answer_index`, `reference_answer`, `rubric`, `explanation`, or `quote`.
- Answer keys are held server-side in the SQLite `quizzes` table until submission.
- Submissions are atomic: `UPDATE quizzes SET status = 'grading' WHERE id = ... AND status = 'ready'`. If grading fails or a provider times out, the database rolls back, enabling retry without data corruption.

### 4. Honest Evaluation & No Hallucinated Scores
- Untested topics are strictly labeled **`not_assessed`** with `accuracy = null`. They are **never** shown as demonstrated weaknesses.
- Assessed mastery is calculated **only** across topics that have at least one submitted assessment.
- Completing a task in the revision plan marks off that day's task, but does **not** artificially increase topic mastery (only diagnostic answers can change mastery).

---

## 5. Mathematical & Algorithmic Foundations

### A. Topic Exam Weighting (Laplace Smoothing)
Past-paper marks are allocated to leaf topics based on confirmed vector matches. To ensure topics not appearing in past papers still receive revision time, GapFinder applies Laplace smoothing:

$$\text{Weight}(T) = \frac{\text{Accepted Marks}(T) + 1}{\sum_{i} \text{Accepted Marks}(T_i) + N_{\text{leaves}}}$$

- If no past papers are uploaded, all leaf topics have equal weight: $\frac{1}{N_{\text{leaves}}}$.
- Unseen topics retain a non-zero baseline weight so they are never ignored.

### B. Gap Classification Thresholds
Topic accuracy is computed as the mean score across all questions for that topic in its **latest submitted assessment**:

- **Weak:** $\text{Accuracy} < 50\%$
- **Medium:** $50\% \le \text{Accuracy} < 80\%$
- **Strong:** $\text{Accuracy} \ge 80\%$
- **Not assessed:** No submitted questions yet ($\text{Accuracy} = \text{null}$)

### C. Revision Priority & Scheduling Budget
Each leaf topic is assigned a priority value:

$$\text{Priority}(T) = \begin{cases} 
(1 - \text{Accuracy}(T)) \times \text{Weight}(T), & \text{if assessed} \\
0.75 \times \text{Weight}(T), & \text{if not assessed}
\end{cases}$$

- Unassessed topics use a $0.75$ heuristic so the plan schedules a diagnostic before detailed revision.
- Strong topics ($\ge 80\%$) have low priority and are omitted from intensive revision schedules unless all topics are mastered.
- **Budget Allocation:** Daily study minutes are divided among prioritized topics using a largest-remainder integer algorithm, guaranteeing each day fits within the student's specified time budget without fractional minutes.

---

## 6. Offline Demo vs. Live AI Behavior

| Feature | Offline Demo Mode (`AI_MODE=demo`) | Live AI Mode (`AI_MODE=live`) |
| --- | --- | --- |
| **API Key** | None required; zero external network calls. | Google GenAI API key (`GEMINI_API_KEY`). |
| **Embeddings** | Deterministic 768-dim MD5 lexical hashing. | Google `gemini-embedding-001` (768-dim). |
| **Topic Hierarchy** | Regex-based Markdown outline parser (`#`, `##`). | Gemini structured topic tree extraction. |
| **Paper Mapping** | Chroma vector search with local embeddings. | Chroma vector search with Google embeddings. |
| **Diagnostic Questions** | Curated demo fixtures (admitted only on exact citation match) + extractive cloze fallback. | Gemini structured question generation citing retrieved chunks. |
| **MCQ Grading** | Deterministic comparison to server-held index. | Deterministic comparison to server-held index. |
| **Short-Answer Grading** | Lexical rubric coverage and keyword matching. | Gemini rubric grading with partial credit and citation validation. |
| **Tutor** | Returns exact retrieved excerpts. | Grounded conversational explanations citing source chunks; abstains if evidence is insufficient. |

---

## 7. Step-by-Step Interview Demonstration

Follow these steps to demonstrate the working application during an assessment review:

### Step 1: Launch & Sign In
1. Start the server (if not already running):
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```
2. Open `http://127.0.0.1:8000` in the browser.
3. Observe the login screen: note the clear demo credential box. Click **Fill demo credentials** (populates `student@demo.com` / `demo123`) and click **Sign in**.

### Step 2: Load Demo Course
1. If no course is loaded, click **Load sample biology course** (or use the button in the header/materials).
2. The system loads three sample files: `syllabus.txt`, `biology_notes.txt`, and `past_paper.txt`.
3. It extracts 3 units, 6 leaf topics, and 8 past-paper questions.

### Step 3: Inspect Gap Report (Initial State)
1. Navigate to **Gap report** (the default central screen).
2. Point out:
   - Assessed Mastery displays `—` (no fake scores are invented).
   - All 6 topics are categorized under **Not assessed**.
   - Topics have calculated exam weights derived from the past paper.

### Step 4: Take a Diagnostic Assessment
1. Click **Take diagnostic**.
2. Leave topics unchecked to take an adaptive diagnostic of the highest-weight topics (or select specific topics).
3. Click **Start adaptive diagnostic**.
4. Point out:
   - Source citations show filename and page, but text quotes and answer keys are hidden.
   - Answer some questions (select MCQ choices, type short-answer responses). Leave one blank to demonstrate zero credit.
5. Click **Submit diagnostic**.

### Step 5: Review Feedback & Updated Gap Report
1. Review the immediate diagnostic evaluation:
   - MCQ answers show correct/incorrect badges.
   - Short answers show reference answers, rubric criteria, and exact quoted source evidence.
2. Return to the **Gap report**:
   - Assessed Mastery now shows a real percentage.
   - Assessed topics are classified into **Weak**, **Medium**, or **Strong**.
   - Topics not tested remain properly labeled **Not assessed**.

### Step 6: Generate a Time-Budgeted Revision Plan
1. Navigate to **Revision plan**.
2. Set **Days available: 3** and **Minutes per day: 45**.
3. Click **Generate plan**.
4. Observe:
   - Tasks are prioritized by knowledge gaps and exam weight.
   - Each day's schedule strictly honors the 45-minute budget.
   - Check off a task: completion state persists without artificially inflating topic mastery.

### Step 7: Demonstrate Retesting & Plan Refresh
1. Click **Retest** on a weak topic in the Gap report or Revision plan.
2. Answer the questions correctly and submit.
3. Observe that:
   - The topic status updates to **Strong**.
   - The Revision plan automatically refreshes to **Version 2**, removing the mastered topic from the priority schedule.
4. Open **Progress** to see both historical attempts plotted on the attempt score chart.

### Step 8: Verify Tutor Source Grounding
1. Navigate to **Tutor**.
2. Select a leaf topic (e.g., *Active transport*).
3. Ask: *"What role does ATP play in active transport?"*
4. Inspect the answer and click the citation pill to view the exact underlying text chunk in the source modal.
5. Ask an unsupported question (e.g., *"What is quantum entanglement?"*) to observe the explicit "Evidence needed" notice.

---

## 8. Verification Results & Test Suite

The test suite runs against real SQLite databases, persistent ChromaDB vector stores, and PyMuPDF PDF extractions:

```sh
.\.venv\Scripts\python.exe -m pytest -v
```

**Results:**
- `tests/test_evidence.py`: 19 passed (PDF extraction, OCR failure handling, chunk overlapping, prompt injection quarantine, citation validation, gap boundaries).
- `tests/test_persistence.py`: 1 passed (database schema integrity and roundtrip persistence).
- `tests/test_workflow.py`: 10 passed (complete end-to-end learning loop, hidden answer keys, atomic submission, plan versioning, tutor grounding, multi-user isolation).
- **Total:** **30 passed in ~38 seconds.**
- **Frontend build:** `vite build` completed with 0 errors (`dist/index.html` and bundled assets generated cleanly).

---

## 9. Likely Interview Questions & Answers

**Q1: How do retrieval and generation stay separate?**  
`retrieval.py` only reads from ChromaDB and returns raw `Chunk` objects filtered strictly by `user_id` and `course_id`. It has no imports from `generation.py`. `generation.py` receives a list of text excerpts and chunk IDs; it cannot access the vector store or database. The boundary is a plain Python function call with a typed list.

**Q2: How are answer keys protected before submission?**  
When a quiz is created, `public_quiz()` strips `answer_index`, `reference_answer`, `rubric`, `explanation`, and `citations` before returning the response. The keys remain in the SQLite `quizzes.questions_json` column server-side. `submit_quiz()` loads the full stored question to grade each answer. The API schema uses `Literal['ready', 'submitted']` to prevent double-submission.

**Q3: How is atomic submission guaranteed?**  
The submit endpoint executes `UPDATE quizzes SET status='grading' WHERE id=? AND status='ready'` before any grading computation. If grading fails (provider error, validation failure), the transaction rolls back and the status reverts to `'ready'`, allowing a clean retry. The idempotency check on `status='submitted'` returns the existing result without re-grading.

**Q4: How is the exam weight calculated?**  
Past-paper marks are assigned to leaf topics via vector similarity. Laplace smoothing gives every leaf topic a non-zero weight even if it never appeared in past papers: `Weight(T) = (marks(T) + 1) / (total_marks + N_leaves)`. Parent node weights are roll-ups for display only; planning and gap reporting use leaf weights exclusively.

**Q5: How are gap thresholds set?**  
The latest quiz score for each topic is used (not an average across all quizzes). Thresholds: Weak < 50%, Medium 50–79%, Strong ≥ 80%. Topics with no submitted quiz remain `not_assessed` with `accuracy = null` and are never shown as demonstrated weaknesses.

**Q6: How does the revision plan scheduling work?**  
Priority per topic = `(1 - accuracy) * weight` for assessed topics, or `0.75 * weight` for unassessed. Total "ideal" minutes are proportional to priority. A largest-remainder integer algorithm allocates these minutes across days, ensuring no day exceeds the student's budget and no fractional-minute tasks appear.

**Q7: How is prompt injection prevented?**  
`security.py` applies a regex heuristic to flag chunks containing instruction-like phrases before indexing. Flagged chunks are marked `quarantined = True` and excluded from retrieval. The tutor and grading prompts prepend a system boundary that labels untrusted content. All generated schemas are Pydantic-validated with `extra='forbid'`; unexpected fields from the model raise a `ValidationError` before they touch the database.

**Q8: How is multi-tenant isolation enforced?**  
Every database query filters by `course.user_id` via the `course_access` FastAPI dependency. ChromaDB collections are named `user_{uid}_course_{cid}`. After a vector search, each returned chunk ID is re-validated against the SQL `chunks` table with the same ownership filter — so a poisoned vector collection cannot return another user's data. Cross-user course access returns HTTP 404 (not 403) to avoid leaking course existence.

**Q9: What happens when the Gemini API fails?**  
In `generation.py`, every live call is wrapped in a try/except. On error, the exception propagates to the endpoint, which rolls back the quiz grading transaction. The student can retry. Demo mode never calls the API; it uses local fixture matching and lexical fallbacks. Offline mode is explicitly selected via `AI_MODE=demo`, not silently activated on failure.

**Q10: How does citation validation work?**  
After the model returns a `TutorAnswer` or `Grade`, `validate_citations()` checks each `Citation` object: (1) the `chunk_id` must appear in the allowed set returned by retrieval, and (2) the verbatim `quote` field must be a substring of the actual chunk text from the database. If either check fails, the citation is rejected and the response is treated as having insufficient evidence. The model cannot fabricate citations to arbitrary documents.

**Known Limitations:**
- Demo lexical rubric grading does not detect paraphrases or contradictions — it only checks keyword coverage. Scores may be misleading for borderline answers. This is explicitly labelled in the feedback (`method: demo_lexical_rubric`).
- Local MD5 lexical embeddings are deterministic but not semantic. Topic mapping and retrieval quality are significantly lower than with real embeddings.
- The application serves a single process from one SQLite file. It is not designed for concurrent multi-user load beyond the demo scenario.
- No email verification or password reset exists in the demo.
