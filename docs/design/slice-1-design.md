# Slice 1 design: from a lecture to a Brain that knows what you know

Date: 17 November 2026. Status: design, for review before building.
Research behind every choice: `docs/research/brain-research.md` (cited below as **R§n**).

## 1. Goal and success check

**Goal.** While I watch one lecture of my DataCamp AWS course, the plugin turns what I hear into a transcript,
quizzes me after each short segment, and builds a Brain that tracks what I know, what I will remember, how sure I am,
and what I confuse. The next day it tells me exactly what to review.

**Success check (the test that decides if this is useful):**
1. It runs end to end on a real DataCamp lecture with no manual fixing.
2. Questions are trustworthy: in a manual audit of 20 questions, at least 19 are correct and answerable from the
   lecture (R§5 reports about 94–97% answerability for generated questions; the Reviewer should push us above that).
3. **Learning effect:** on a held-out quiz one day and seven days later, I recall more from a lecture studied with the
   loop than from a comparable lecture I just watched (and could rewatch). See §12.

## 2. Scope

**In:** Chrome extension (tab audio capture, side panel quiz), local transcription, concept extraction, question
generation with Reviewer checks, Brain model (mastery, memory, calibration, confusions, prerequisites), spaced review
queue, Brain page with a 3D view and a plain list.

**Out of slice 1:** pretest questions (see §3), free-text "explain why" answers, Zoom host API, cloud transcription,
accounts, multiple learners, mobile.

## 3. Constraint found during design: no pretest on a first viewing

The pretest effect (R§2) needs questions *before* a segment. With tab audio we only learn what a segment says
*after* it has played, so there is nothing to pretest on a first viewing.

**Decision:** slice 1 uses **interpolated testing** right after each segment (R§2, Szpunar et al.), which works live.
Pretesting comes later in two forms that fit our capture method:
- **Before a rewatch** or before a lecture the learner has already captured.
- **Before the next lecture**, from its title or a syllabus the learner pastes (later slice).

## 4. Architecture

```
 Chrome extension (MV3)                          Backend (FastAPI, on my machine: localhost:8000)
 ┌───────────────────────────┐                   ┌──────────────────────────────────────────────┐
 │ Side panel: Start/Stop,   │  segment audio    │ /api/course/segment                           │
 │ "Quiz me", quiz UI        │ ────────────────▶ │  1 Transcribe (faster-whisper, local)         │
 │ Service worker:           │                   │  2 Planner: concepts + prerequisite proposals │
 │  tabCapture stream id     │  questions        │  3 Tutor: questions with cited spans          │
 │ Offscreen doc:            │ ◀──────────────── │  4 Reviewer: checks, flag → fix → re-check    │
 │  MediaRecorder (webm/opus)│  answers          │  5 Brain (plain code): update the model       │
 └───────────────────────────┘ ────────────────▶ │ SQLite: data/brain.db   Agent log (existing)  │
                                                 │ Brain page /brain (three.js + plain list)     │
                                                 └──────────────────────────────────────────────┘
```

- The extension **never reads or changes the course page**: no content scripts, no caption reading (R§7.1). It only
  captures the audio of the tab the learner chose, after a click.
- Audio goes to my own machine, is transcribed, and is **deleted straight after**. Only the transcript is kept (R§7.2).
- New backend code lives in `app/course/`. Reused as-is: `llm.py`, the agent log and counters in `orchestrator.py`,
  the Reviewer pattern. Untouched: the maths modules (`mathcheck`, `practice`, `spamlab`, `career`, `simulate`).

## 5. The extension

| Piece | Job |
|---|---|
| `manifest.json` | MV3; permissions `tabCapture`, `offscreen`, `sidePanel`, `storage`; host permission `http://localhost:8000/*` only |
| Side panel | First-run consent screen; Start/Stop capture; segment timer; "Quiz me"; the quiz itself; link to the Brain page |
| Service worker | On Start (a user click): `chrome.tabCapture.getMediaStreamId` for the active tab; creates the offscreen document |
| Offscreen document (reason `USER_MEDIA`) | Opens the stream, routes it back to the speakers so the learner still hears the lecture, records with `MediaRecorder` |

**Segments.** A segment closes when the learner presses **Quiz me**, or automatically after **5 minutes** of audio
(a design default, adjustable; Szpunar et al. tested between short lecture segments). The blob is POSTed with the
course name, lecture title (typed once per lecture in the side panel), and segment start/end times.

**Consent screen (first run):** what is captured (tab audio only, after Start), where it goes (this computer), what
is kept (transcript only), and that it is for personal study. A red badge shows while capturing.

## 6. Data model (SQLite, `data/brain.db`, Python stdlib `sqlite3`)

| Table | Key fields |
|---|---|
| `course` | id, name (e.g. "AWS Cloud Practitioner"), platform (free text) |
| `lecture` | id, course_id, title, created |
| `segment` | id, lecture_id, start_s, end_s, transcript (JSON list of `{start, end, text}` lines) |
| `concept` | id, course_id, name, summary, first_segment_id |
| `prereq` | concept_id, requires_id, status (`proposed` / `verified`) |
| `item` | id, concept_id, segment_id, question, options (JSON, 4), key, cited span (start_s, end_s, quote), distractor_concepts (JSON), status (`live` / `dropped`), review log |
| `attempt` | id, item_id, chosen, correct, confidence, seconds_taken, at |
| `concept_state` | concept_id, p_mastery, fsrs_card (JSON from `Card.to_json()`), conf_sum, attempts, correct |
| `confusion` | concept_id, confused_with_id, count, evidence (JSON) |

## 7. The pipeline, per segment

Each agent's job, and what the Reviewer checks **in code** before anything reaches the learner.

### 7.1 Transcribe (plain code)

- `faster-whisper`, model `small`, `device="cpu"`, `compute_type="int8"`, `vad_filter=True`.
- The project's benchmark: 13 minutes of audio in about 1m42s on CPU with this setup, so a 5-minute segment should be
  ready in well under a minute. **To be measured on my machine in M1.**
- `initial_prompt` seeded with the course name and known concept names, to help with AWS terms (S3, IAM, VPC).
- Output: timestamped lines. The audio file is deleted.

### 7.2 Planner: concepts and prerequisites

- **Model proposes:** the concepts this segment teaches (reusing existing course concepts by name where they match),
  each with the transcript lines that teach it, and candidate prerequisite links (R§3.3).
- **Code checks:**
  - Every concept cites at least one real transcript line.
  - Names are normalised (case, plurals) to avoid duplicates.
  - Links only join known concepts, and **adding a link may not create a cycle**.
  - Links start as `proposed`. They become `verified` only when learner evidence agrees (a weak prerequisite
    explains a failure, as `recall.py` does today).

### 7.3 Tutor: questions

- 2–3 multiple-choice questions per segment, 4 options each, for the segment's concepts. Each has:
  - the **cited span** (start, end and an exact quote from the transcript);
  - the key;
  - for each distractor, the concept it belongs to, if any (e.g. the question is about S3 and a distractor describes
    EBS). This is what lets us detect confusions (§8.4).

### 7.4 Reviewer: the self-correction gate (R§5)

| Check | How |
|---|---|
| Cited quote really is in the transcript, inside the segment | Code: exact substring match on normalised text |
| Options are four and distinct, and the key is one of them | Code |
| **Blind solve:** answer using only the cited quote | Separate model call that never sees the key; code compares with the key |
| No distractor is also supported by the quote | Same blind call returns "which options does the quote support?"; code requires exactly one |

A failed item is flagged with the reason and sent back to the Tutor **once**. It is re-checked and then either goes
live or is dropped. All of this is logged as FLAG → fix → re-check, and counted. This is the existing pattern in
`tutor.py`.

## 8. The Brain model (all plain code)

### 8.1 Answering

The side panel asks **"How sure are you?" before showing the options**, with three choices: *Guessing*, *Fairly sure*,
*Sure*. These map to confidence values **0.25, 0.6 and 0.9**. 0.25 is chance with 4 options, so "guessing" means
exactly that. Then the learner answers.

### 8.2 Mastery: Bayesian Knowledge Tracing (R§3.1)

Per concept, after each answer to one of its items:

```
correct: P(L|obs) = P(L)(1−S) / [P(L)(1−S) + (1−P(L))·G]
wrong:   P(L|obs) = P(L)·S     / [P(L)·S     + (1−P(L))(1−G)]
then:    P(L)     = P(L|obs) + (1 − P(L|obs))·T
```

Starting values: **P(L0) = 0.2, T = 0.15, G = 0.25** (4-option chance), **S = 0.08**. These are inside Corbett &
Anderson's bounds (G < 0.3, S < 0.1). They are starting guesses, refit once there is data. A concept counts as
**mastered at P(L) ≥ 0.95** (design choice; revisit with data).

### 8.3 Memory: FSRS (R§3.1)

One FSRS card per concept (`pip install fsrs`; `Scheduler`, `Card`, `Rating`). Each answer becomes a rating:

| Outcome | FSRS rating |
|---|---|
| Wrong (any confidence) | `Again` |
| Right, but *Guessing* | `Hard` |
| Right, *Fairly sure* | `Good` |
| Right, *Sure* | `Easy` |

`scheduler.get_card_retrievability(card)` gives "chance you recall this today", which falls every day. The card's due
date drives the review queue. The mapping is a design choice, revisited with data.

### 8.4 Calibration and confusions (R§3.2, R§3.4)

- **Calibration gap** per concept = mean confidence − accuracy over the last 10 answers. **Overconfident** when the
  gap is ≥ 0.2 with at least 4 answers.
- **Confident error** = wrong while *Sure*. The feedback is emphasised (hypercorrection, R§2): "You were sure, and
  here is exactly what the lecture said", with the timestamp. The concept goes to the front of the next review.
- **Confusion:** picking a distractor tagged with concept B while answering about A adds 1 to confusion(A, B).
- **Confirm rule kept:** a confusion or overconfidence flag only changes behaviour after it has been seen **twice**.

### 8.5 Feedback after each answer

Right or wrong, the learner sees the cited quote and a **"Rewatch 0:42–1:10"** timestamp. In slice 1 that timestamp
is shown, not clicked, since we don't control the course player.

## 9. Spaced reviews

The **review queue** holds concepts whose FSRS card is due, ordered:

1. Confident errors from last time.
2. Confirmed overconfident concepts.
3. Lowest retrievability.

Items are interleaved, so two questions in a row are never on the same concept, and confirmed confused pairs are
mixed together (R§2). Each review uses a **different live item** than last time where one exists, so the learner
practises recall rather than remembering one question.

## 10. The Brain page (`/brain`)

**Left: the plain list (always visible; it does the work).**
- Header: course, current lecture and topic.
- Two honest numbers: **"Learned"** (mean P(L) across concepts met) and **"Would recall today"** (mean retrievability).
- **Due now** (n) → Start review. **Overconfident** (n). **Often confused:** "S3 ↔ EBS". **Ready to learn next**
  (concepts whose prerequisites are mastered: the outer fringe, R§3.3).

**Right: the 3D brain (three.js, already bundled in `app/static/vendor/three.min.js`).** Every property encodes data
(R§6):

| Visual | Data |
|---|---|
| Lobe / cluster | A course; sub-clusters are lectures |
| Node | A concept; size = how much of the lecture time teaches it |
| Colour | Mastery P(L), from grey (unknown) to violet (mastered) |
| Glow | Retrievability today; it visibly dims day by day |
| Pulse | Due now |
| Amber ring | Confirmed overconfident |
| Lines | Prerequisites (solid) and confusions (dashed amber) |
| Click | Opens the concept: evidence, last answers, "Review now" |

- **Shape:** a procedural brain outline built from points (no third-party 3D model, so no licence questions).
- **Motion:** slow idle rotation, and none when the system asks for reduced motion.
- **Limit:** up to about 200 concept nodes.
- **Accessibility:** the 3D view is optional; everything in it is also in the list.

## 11. API (new endpoints)

| Endpoint | Purpose |
|---|---|
| `POST /api/course/segment` | Audio blob + course, lecture, times → transcript, concepts, live items (async job; returns job id) |
| `GET /api/course/job/{id}` | Job status plus the agent log lines for it |
| `GET /api/quiz/{segment_id}` | The live items for a segment |
| `POST /api/answer` | item, chosen, confidence, seconds → correctness, feedback, cited span |
| `GET /api/review` | The interleaved review queue |
| `GET /api/brain` | Everything the Brain page draws |

## 12. How we test that it works

1. **Item quality (M3):** audit 20 live items by hand against the lecture. Also report what the Reviewer flagged,
   fixed and dropped.
2. **Learning effect (M6):** pick two comparable lectures from the AWS course.
   - **Lecture A** with the loop. **Lecture B** watched normally, with rewatching allowed.
   - Before starting, write a held-out test of 8 items per lecture. These are Reviewer-verified but never used in
     practice.
   - Take both tests after 1 day and after 7 days, and compare. One learner (me) is an anecdote, not proof, so we
     report it honestly as a pilot signal.
3. **Calibration trend:** does my overconfidence gap shrink over the week?

## 13. Milestones (each one is a commit and a demo)

| | Milestone | Done when |
|---|---|---|
| M1 | Capture + transcript | Extension records a DataCamp segment; backend returns a timestamped transcript; audio deleted; time measured |
| M2 | Concepts + questions + Reviewer | A segment produces concepts and live items; the log shows a real flag → fix → re-check |
| M3 | Quiz in the side panel | Confidence-first answering; feedback with quote and timestamp; item audit passes |
| M4 | Brain model | BKT, FSRS, calibration and confusions update from answers; unit tests on the formulas |
| M5 | Reviews + Brain page | Due queue interleaved; plain list; 3D brain with the §10 encodings |
| M6 | Evaluation | The two-lecture test in §12 run and written up |

## 14. Risks and open questions

| Risk | Plan |
|---|---|
| Whisper speed or accuracy on AWS jargon on my CPU | Measure in M1; seed `initial_prompt`; try the `base` model if too slow |
| Model latency per segment (questions arriving late) | Run the pipeline while the next segment plays; show a "preparing quiz" state |
| Platform terms on recording audio for study | Personal testing only until legal advice (R§7.2) |
| BKT and FSRS defaults don't fit | Log every attempt from day one so we can refit |
| Our three confidence levels are coarse | Good enough for v1; check the calibration trend in §12 |

**Decisions needed from you before M1:**
1. Is the 5-minute default segment length right for DataCamp videos, or should it be "Quiz me" only?
2. Is it fine for the backend to run locally only (no AWS) in slice 1? Transcribe in the cloud can come later.
