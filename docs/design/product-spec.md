# Product spec and test plan: what we agree to build, and how we prove it works

Date: 17 November 2026. Status: **agreed 17 November 2026** (all decisions in §3 as recommended; CI on the fork).
§6 records the later gap discussion: its decisions are agreed; the slice for each new feature (§6.6) is proposed.

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

---

## 6. Gap discussion: decisions of 17 November 2026

**Owner:** solo. Siphosihle owns every decision and module for now.

### 6.1 Product direction (agreed)

| Gap | Decision |
|---|---|
| Dynamic or focused | **Dynamic engine, focused launch.** Any course works; the launch adds a curated skeleton for **cloud certifications, starting with AWS** (official exam guide domains and task statements). Other courses run in fully dynamic mode, labelled "less certain". |
| Which AI | **Anthropic API**, a model per job set in config and chosen by measured accuracy on our evaluation set. Start: Sonnet 5 writes questions; Haiku 4.5 for concept matching and the Reviewer's blind check. **No provider that stores learner data outside adequate-protection jurisdictions.** Rough model cost: $0.14–$0.70 per lecture hour; reviews cost nothing. To be measured in slice 1. |
| Over-reliance on AI | The AI rules in §6.2 apply to every feature. |
| AI wrong on purpose, learner corrects | Two features: F19 (deliberate, clearly labelled) and F20 (real errors). |
| Legal check on audio capture | After there is a working app. Until then: personal testing only. |
| Live Zoom classes | Quizzes **after class only**, never during a live class. |
| Success metric | **Exam passes and retention.** Also: insights that help find new ways to give lessons. |
| Privacy notice | Required (F22). |
| The 3D brain | **A secondary view, not the core.** It shows what the learner has learned, touched and is still confused by, for review. The core value is the stored data, which also guides the AI. Next step: define exactly what we save (§6.5). |

### 6.2 AI rules (apply to every feature)

1. The AI only **proposes**; code and sources **decide**. Marking, the Brain, scheduling and calibration never use a
   language model.
2. Every AI claim shown to a learner **cites its source** (a transcript quote, or a screenshot for F21). No source,
   not shown.
3. An **independent Reviewer** checks every item before use, ideally on a different model from the writer.
4. The AI may **abstain** ("not enough testable content here") instead of inventing.
5. Feedback shows **the lecturer's words**, not AI prose.
6. AI outputs are **small and structured** (schema-validated JSON).
7. Quality is **measured**: the evaluation set, plus dispute rates per prompt version (F20).

### 6.3 New features, with acceptance criteria

#### F18. Exam skeleton (the focused launch)
*As a learner preparing for an AWS exam, I see how ready I am for each part of it.*
- An exam skeleton (domains, weights, task statements) is stored as data, entered from the official exam guide. **U**
- Each concept extracted from a lecture is mapped to at most one task statement, or marked "outside the exam". The
  mapping is proposed by the model and checked against the skeleton's list (no invented task statements). **A**
- Readiness per domain = mean mastery of its mapped concepts; overall readiness = weighted by domain weight. **U**
- Courses with no skeleton run in dynamic mode and are labelled "less certain". **API**

#### F19. Spot the error (deliberate)
*As a learner, I strengthen my memory by catching a planted mistake.*
Research: erroneous examples improved one-week delayed learning (McLaren, Adams & Mayer, 2015, d = 0.33);
learners try harder when correcting an agent (protégé effect, Chase et al., 2009).
- Always **clearly labelled** as a "Spot the error" round; never mixed into normal questions. **E**
- The planted statement changes **one** fact from a cited quote. Code confirms it differs from the quote, and the
  Reviewer confirms the quote contradicts it. **A**
- Where the learner has a confirmed confusion (F11), the planted error uses it (e.g. EBS in place of S3). **U**
- Every round ends by showing the correct quote and timestamp, whether or not the learner caught it. **E**
- Catching and correctly fixing the error counts as a correct answer in the Brain; missing it counts as wrong. **U**

#### F20. Report an error (real)
*As a learner, I can tell the system a question is wrong, and it takes me seriously.*
- Every question has "This is wrong", with an optional reason. **E**
- The Reviewer re-checks the item against its quote with the learner's objection. Outcomes:
  - **AI wrong:** item retired for everyone, the attempt is removed from the Brain, the learner is thanked, and the
    case is added to the evaluation set. **A**
  - **Learner wrong:** the quote is shown; the attempt stands. **A**
  - **Unclear:** item marked disputed for that learner; the attempt doesn't count. **A**
- One learner's report never changes content for other learners until the Reviewer confirms it. **API**
- Dispute rate per prompt version is recorded for quality tracking. **API**

#### F21. Screenshots (slides, code, diagrams)
*As a learner, what I see on screen counts too, not only what I hear.*
- The learner presses "Add screenshot"; only then is the visible tab captured. No automatic screenshots. **M**
- Questions from a screenshot cite the screenshot instead of a quote. The Reviewer's blind solve uses the
  screenshot alone. **A**
- Because an image can't be checked word for word in code, screenshot questions are marked "image-based" and
  watched separately in the dispute rate. **API**
- Screenshots are kept until the learner deletes them (same as transcripts). **API**

#### F22. Privacy notice and data controls
- A plain-language privacy notice: what is captured, where it is stored (EU, Stockholm), how long, who sees it,
  how to delete it. Shown before first use; consent recorded with its version. **E**, **API**
- Extends F16 (delete my data) to screenshots and email preferences. **API**

#### F23. Email review reminders
*As a learner, I'm reminded to come back when reviews are due.*
- Opt-in only; frequency chosen by the learner (daily or weekly digest); every email has a one-click unsubscribe. **API**
- The email lists what's due and links to the review. No learning content beyond concept names. **API**
- Sent with Amazon SES (on the free plan) once accounts exist (stage 3). **M**

### 6.4 Planned features (need research or discussion before building)

#### P1. Cross-platform connections
*When something I learned on DataCamp comes up again in a YouTube video, the Brain notices.*
- Idea: a concept recognised in source B that the learner met in source A triggers either a quick question ("You
  learned this on DataCamp. What does it do?") or a note ("You know this: mastery 80%").
- Fits spaced retrieval at a natural moment. **Research still to do** (recognising the same concept across
  sources; when asking beats showing) before it goes into the spec.

#### P2. Classroom teaching
*A teacher records themselves teaching; learners practise from what was taught.*
To discuss fully before any design. Known questions:
- **Children's data:** POPIA treats children's personal information as a special category needing a parent's or
  guardian's consent. Classroom audio may capture learners' voices.
- **Conflict with D8** ("only the learner sees a Brain"): a teacher view would need a separate decision (e.g. a
  class summary without individual names, or per-learner sharing with consent).
- School devices, internet access, and how learners receive the practice.

### 6.5 Still open

| Item | Status |
|---|---|
| Cold start (the Brain knows nothing on day one) | Undecided. Options to discuss: an optional placement quiz per exam domain, or start empty. |
| Transcription accuracy (South African accents, AWS jargon) | Siphosihle researching platforms; test in M1. |
| **What exactly the Brain saves** (the data dictionary) | Next to define: what counts as learned, touched and confused, and how each guides the AI. |
| Which AWS exam the DataCamp course prepares for | **Decided: AWS Certified Cloud Practitioner (CLF-C02).** F18's first skeleton: 4 domains (Cloud Concepts 24%, Security and Compliance 30%, Cloud Technology and Services 34%, Billing, Pricing, and Support 12%) and their task statements, from the official exam guide. |
| Business model and pricing | Individuals and online tutors first; pricing not yet discussed. |

### 6.6 When each new feature is built (proposed)

| Feature | Proposed slice | Why |
|---|---|---|
| F18 Exam skeleton | Slice 1 | Cheap, and it reduces AI mistakes from the start |
| F20 Report an error | Slice 1 | Quality safety net from day one |
| F19 Spot the error | Slice 2 | Builds on confusions (F11) having real data |
| F21 Screenshots | Slice 2 | Needs vision-model checks; DataCamp slides make it valuable early |
| F22 Privacy notice | Before any other user (stage 3) | Legal requirement |
| F23 Email reminders | Stage 3 | Needs accounts |
| P1, P2 | After research or discussion | Not yet specified |
