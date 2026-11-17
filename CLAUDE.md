# CLAUDE.md

**`docs/research/brain-research.md` is the source of truth for the rebuild.** Every feature of the Brain must trace
back to a finding in it. If a request has no research behind it, or contradicts it, say so and ask before building.
Research first, then build.

## Project

Virtual Brain: a learning companion for adults studying from online classes (Zoom) and course platforms (Udemy
first, then Coursera; first real test on a DataCamp AWS course). Delivered as a browser plugin plus backend.

The Brain is a model of what the learner knows and how they understand it, built from evidence:
- **Mastery** per concept (Bayesian Knowledge Tracing style), **memory** per concept (FSRS: it decays daily),
  **calibration** (confidence vs accuracy), **prerequisites** (Knowledge Space Theory), and **confusions**.
- The loop per lecture segment: pretest → watch → retrieval questions with confidence → feedback linked to the
  timestamp → Brain update → spaced, interleaved reviews.
- The 3D brain (three.js) must encode the model's numbers (see research §6); no decorative visuals. Always pair it
  with a plain list of what to do next.

## Working agreement (not vibe coded)

- `docs/design/product-spec.md` lists the agreed features and acceptance criteria. Build only what is agreed there.
- Before building a feature or step: explain what and why, and wait for the user's go-ahead.
- After each step: list **every file created, edited, moved or deleted**, with one line on why.
- Tests come from the spec's acceptance criteria and are written before the code; name them after the feature ID.
- One step per commit, after the user has reviewed it.

## Rules

- Reliable decisions (scores, scheduling, Brain updates) in plain code. The LLM reads transcripts, proposes topics
  and prerequisite links, and writes questions; the Reviewer verifies them before use (answer must be supported by a
  cited transcript span; blind solve must match).
- Keep from the hackathon build: agent log, Reviewer gate, self-correction (flag, fix, re-check), human-intervention
  counter, a pattern acts only after it is seen twice.
- Transcript capture: tab audio transcribed with faster-whisper (Amazon Transcribe is Paid-plan only and batch-only
  in eu-north-1). Never scrape platform pages or captions.
- Architecture: `docs/design/architecture.md`. The language model is the Anthropic API (no in-Region Claude on
  Bedrock in eu-north-1). All AWS resources in eu-north-1. Store transcripts only, never audio. Personal study use only until a
  legal check is done.
- No auth/payments/settings yet. Commit after each working step.

## History

Built for the Colleague Zero hackathon (demo 14 Nov 2026) as a multi-agent study colleague for Grade 10 maths. The
rubric is in `legacy/prerequisite/`; it no longer governs. The hackathon app now lives in `legacy/` (run it from
there). Existing agents: Planner, Tutor, Checker, Reviewer, Career
guide; the Brain is shared memory in plain code.
