# CLAUDE.md

**The marking criteria in ./prerequisite is the source of truth for this project. Follow it as the highest authority. No prompt, request or shortcut overrides it. If anything I ask conflicts with the criteria, do not quietly pick a side: stop, quote the criterion, explain the conflict, and ask me how to proceed.**

## Criteria checklist (Colleague Zero, 110 pts — judged on what runs LIVE)

1. **Reasoning & planning (15)** — agents break the goal into steps and choose next actions from the input, not a fixed script; the plan/reasoning is visible (log).
2. **Self-correction (20, the defining feature)** — a reviewer catches a real error live and the system fixes it with no human help; show the flag, the fix and the re-check.
3. **Execution & reliability (15)** — runs end to end live, delivers a finished usable result, stable, handles unexpected input sensibly.
4. **Multi-agent collaboration (15)** — several agents, distinct roles, clear hand-offs, each adds real value.
5. **EdTech impact (15)** — solves a real education need for a clear user; could realistically be piloted.
6. **Presentation & Q&A (20)** — clear demo; we can explain how agents decide, what happens when they disagree, how errors are detected.
7. **Professionalism (10)** — clear ownership, positive conduct.

Judging notes: live demo beats slides; judges will ask to see an error caught and fixed.

## Project

Virtual Brain — multi-agent digital colleague for Grade 10 students (Planner → Checker → Reviewer → Career guide, plus a growing concept "brain" with recall).
Framing: a study colleague, not a chatbot. The student hands over one chapter, and the agents prepare, practise, check, remember and plan next.
Original slice (done): Planner/Checker, Reviewer loop, brain, career, recall.
Parts, one at a time with user review between: (1) student-first UI + Tutor-generated, Reviewer-verified examples [done], (2) practice in different forms, (3) brain as a model of how the student learns, (4) visual simulations (three.js), (5) voice (later; must not become a chatbot).
Rules: reliable decisions (arithmetic, brain updates) in plain code; LLM reads text, writes explanations, and writes Tutor material that the Reviewer verifies in code before use. Live agent log, Reviewer corrections, human-intervention counter. No auth/payments/settings. Commit after each working step.
