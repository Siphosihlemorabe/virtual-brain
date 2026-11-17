# Product spec and test plan: what we agree to build, and how we prove it works

Date: 17 November 2026. Status: **agreed 17 November 2026** (all decisions in §3 as recommended; CI on the fork).

How to read this: each feature has a short user story, **acceptance criteria** written so each one becomes a test,
and the test level that proves it. Section 3 lists the product decisions to agree first. Section 4 is the test
groundwork that stage 0 lays.

Sources: research (`docs/research/brain-research.md`, R§), slice 1 design (`docs/design/slice-1-design.md`, D§),
architecture (`docs/design/architecture.md`, A§).

---

## 1. Who it is for and what one session looks like

**User:** an adult learning from online videos or live classes (DataCamp, Udemy, Coursera, Zoom) who wants to
actually remember it.

**One session:**
1. I open my course video, open the Virtual Brain side panel, and press **Start**.
2. I watch. After a segment (I press **Quiz me**, or the timer ends it), I get 2–3 questions about what I just heard.
3. For each question I say **how sure I am**, then answer, then see the lecture quote and timestamp that settles it.
4. My Brain updates. Tomorrow it tells me what to review, and the 3D brain shows what I know and what is fading.

## 2. Features and acceptance criteria

Test levels: **U** unit (pure code), **C** contract (adapter suite), **A** agent (fake model, recorded replies),
**API** endpoint with a test database, **E** extension or browser test, **M** manual checklist (Chrome capture
can't be fully automated), **Q** quality evaluation set.

### F1. Consent and account
*As a learner, I understand what is captured before anything is recorded.*
- Before the first capture, the side panel shows what is captured, where it goes, what is kept, and that it is
  for personal study. Capture can't start until I accept. **E**
- My acceptance is stored with a timestamp and the consent text version. **API**
- Stage 0 uses a fixed dev user; Cognito replaces it in stage 3 without changing other modules. **API**

### F2. Start and stop capture
*As a learner, I control exactly when audio is captured.*
- Capture starts only after I click **Start**, and only for the tab I'm on. **M**
- I still hear the lecture while it's being captured. **M**
- A visible badge shows while capturing; **Stop** ends capture immediately. **M**
- The extension has no content scripts and never reads the course page (enforced by a manifest check in CI). **U**

### F3. Segment and transcribe
*As a learner, what I heard becomes text without me doing anything.*
- A segment closes on **Quiz me** or after the configured length; it is uploaded with course, lecture and times. **E**
- The worker transcribes it into timestamped lines. **C** (Transcriber contract, using a short recorded clip)
- **The audio file is deleted after transcription, including when transcription fails.** **API**
- A failed transcription shows a clear error and a retry, and nothing else breaks. **API**

### F4. Concepts and prerequisites (Planner)
*As a learner, the Brain knows which ideas a lecture taught.*
- Each segment yields concepts; every concept cites at least one real transcript line, or it is rejected. **A**
- A concept that matches an existing one in the course is reused, not duplicated (case and plurals). **U**
- A proposed prerequisite link that would create a cycle is rejected. **U**
- New links start as `proposed`. **A**

### F5. Questions (Tutor)
*As a learner, I get questions about what I just heard.*
- 2–3 four-option questions per segment, each with a key, a cited quote with timestamps, and distractor concepts. **A**
- Every stored question records the prompt version and model that made it. **API**

### F6. The review gate (Reviewer): self-correction
*As a learner, I never see a wrong or unanswerable question.*
- The cited quote must be found in the segment's transcript, or the item is flagged. **U**
- Exactly four distinct options, and the key is one of them. **U**
- Blind solve from the quote alone (without the key) must match the key. **A**
- Exactly one option may be supported by the quote. **A**
- A flagged item goes back to the Tutor **once**, is re-checked, then goes live or is dropped. The log shows FLAG,
  fix, re-check, with the reason. **A**
- **Quality bar:** on the evaluation set, at least 95% of live items are correct and answerable, and every
  planted bad item is caught. **Q**

### F7. Answer with confidence first
*As a learner, I say how sure I am before I answer.*
- The confidence choice (Guessing / Fairly sure / Sure) appears **before** the options are shown. **E**
- The answer, confidence and time taken are stored in the attempts log, which is never edited. **API**
- Feedback shows right or wrong, the cited quote and the timestamp range. **E**
- A wrong answer given while *Sure* is shown as a confident error, with emphasised feedback. **E**

### F8. Mastery (knowledge tracing)
*As a learner, the Brain knows whether I have learned each idea.*
Hand-checked values with P(L0)=0.2, T=0.15, G=0.25, S=0.08 (D§8.2). **U**

| Start P(L) | Answer | After the answer | After learning step |
|---|---|---|---|
| 0.2 | correct | 0.4792 | **0.5573** |
| 0.2 | wrong | 0.0260 | **0.1721** |
| 0.2 | correct ×3 | | 0.5573 → 0.8491 → **0.9608** |

- **Mastered** (D4) = P(L) ≥ 0.95 **and** at least one correct answer on a later calendar day than the concept's
  first attempt. Three correct answers in one sitting reach 0.9608 but are **not** mastered until a later-day
  correct answer. **U** (with the fake clock)

### F9. Memory (FSRS)
*As a learner, the Brain knows what I'm about to forget.*
- Each answer maps to an FSRS rating: wrong → Again; right + Guessing → Hard; right + Fairly sure → Good;
  right + Sure → Easy. **U**
- Retrievability for a concept falls as days pass with no review (checked with a fixed clock). **U**
- The card round-trips through the database unchanged (`to_json` / `from_json`). **API**

### F10. Calibration
*As a learner, I can see when I think I know something but don't.*
- Gap = mean confidence − accuracy over the last 10 answers per concept. Example: confidences 0.9, 0.9, 0.9, 0.6
  with right, wrong, wrong, right gives **0.325**. **U**
- A concept is flagged overconfident at a gap of at least 0.2 with at least 4 answers, and the flag only acts after
  it has been seen twice. **U**

### F11. Confusions
*As a learner, the Brain knows which ideas I mix up.*
- Choosing a distractor tagged with concept B while answering about A adds 1 to confusion(A, B). **U**
- A confusion acts (interleaved practice) only after it has been seen twice. **U**

### F12. Review queue
*As a learner, I know exactly what to review and in what order.*
- Due concepts are ordered: confident errors, then confirmed overconfident, then lowest retrievability. **U**
- No two questions in a row are on the same concept, when an alternative exists. **U**
- A review uses a different live item from last time, when one exists. **U**

### F13. Brain page: the plain list
*As a learner, I can see what to do next at a glance.*
- Shows course, current lecture, **Learned** (mean mastery) and **Would recall today** (mean retrievability), plus
  Due now, Overconfident, Often confused, and Ready to learn next. **API** for the numbers, **E** for display
- Every number matches what the learning module computes for the same data. **API**

### F14. Brain page: the 3D brain
*As a learner, I can see my knowledge as a brain, and every part of it means something.*
- Each encoding in D§10 is driven by data: colour = mastery, glow = retrievability, pulse = due, amber ring =
  overconfident, lines = prerequisites and confusions. Tested on the mapping functions, not pixels. **U**
- Clicking a node opens the same information as the list. **E**
- Reduced-motion setting: no rotation or pulse. **E**

### F15. Agent log and job progress
*As a learner, I can see what the agents are doing and why.*
- Every job writes its agent log lines to the database; the side panel shows progress. **API**
- **A restart of the worker mid-job loses nothing**: the job resumes or is retried. **API**

### F16. Delete my data
*As a learner, I can remove everything about me.*
- One action deletes my transcripts, items, attempts and Brain, and confirms the result. **API**

### F17. The legacy app keeps working
- The hackathon maths app, moved to `legacy/`, still starts and passes a smoke test. **API**

## 3. Product decisions to agree first

**All agreed as recommended on 17 November 2026.**

| # | Decision | Recommendation | Alternative |
|---|---|---|---|
| D1 | Segment trigger | "Quiz me" button **plus** a 5-minute auto segment | "Quiz me" only, if DataCamp videos are short |
| D2 | Question format in slice 1 | Multiple choice only (checkable in code) | Add "explain in your words", graded by the model (later) |
| D3 | Questions per segment | 2–3 | Fixed 3 |
| D4 | When is a concept "mastered"? | **Raise the bar:** P(L) ≥ 0.95 **and** at least one correct review on a later day | Keep 0.95 alone (3 correct in a row, possibly all on the same day) |
| D5 | Confidence scale | 3 levels (Guessing 0.25, Fairly sure 0.6, Sure 0.9) | A slider (more precise, slower) |
| D6 | Scope of a Brain | One Brain per learner, concepts grouped by course | One Brain per course (no links across courses) |
| D7 | Language | English only in slice 1 | Others later; Whisper supports many |
| D8 | Who sees a Brain | Only the learner | Sharing with a tutor (later, needs consent) |
| D9 | Transcript retention | Kept until the learner deletes it | Auto-delete after N days |
| D10 | Frontend | React + TypeScript | Svelte |
| D11 | Repo home for CI | **Agreed: the fork, `Siphosihlemorabe/virtual-brain`** (git remote `fork`) | |

## 4. Test groundwork laid in stage 0

**Principle: tests are written from this spec before the code.** Each acceptance criterion above becomes a test
named after its ID (e.g. `test_f8_correct_answer_from_0_2_gives_0_5573`), so failures point straight back here.

| Piece | What stage 0 sets up |
|---|---|
| Backend test runner | `pytest` with coverage; folders `tests/unit`, `tests/contract`, `tests/agents`, `tests/api` |
| Test database | A real PostgreSQL in Docker, rebuilt per test session, with migrations applied (no SQLite stand-in) |
| Fake clock | Time is injected, so memory decay (F9) is tested without waiting days |
| Fake language model | Returns recorded replies keyed by prompt version and input; **no API key needed for any test** |
| Factories | Small helpers to create a course, lecture, segment, items and attempts in one line |
| Contract suites | One shared suite per adapter interface (TranscriptSource, Transcriber, LLMProvider); every adapter must pass it |
| Evaluation set | A folder of short transcripts with known-good and deliberately bad items (wrong key, quote not in transcript, two correct options), scored against the F6 quality bar |
| Frontend tests | Vitest for logic and components; a manifest check (no content scripts, minimal permissions) |
| Manual checklist | `docs/testing/manual-checklist.md` for what Chrome won't let us automate (F2) |
| CI | Every push: ruff, mypy, pytest, ESLint, Vitest, the module-boundary test, the manifest check |

**Definition of done for every feature:** its acceptance tests exist and pass in CI; every file changed is listed
in the step report; you have reviewed it.

## 5. Working agreement

- I explain each feature before building it, and wait for your go-ahead.
- After each step I list **every file created, edited, moved or deleted**, with one line on why.
- One feature or step per commit, after your review.
