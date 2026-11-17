# Tech stack evaluation: is the current app ready to become a product?

Date: 17 November 2026. Measured on the repo as it stands (hackathon build plus uncommitted changes).

**Verdict:** the backend language and the core idea are right for a product. The way the app is built around them
(data, runtime, language-model connection, frontend, no tests) is hackathon-grade. New features and new contributors
would hit friction almost everywhere.

## Facts

- About 4,200 lines in total. The backend is 17 Python files; the UI is **one 985-line `index.html`** with 121 inline
  functions.
- **0 tests**, no CI, no linting.
- 22 commits from 3 authors.
- `.env` is correctly ignored by git.

## Scorecard

| Area | Today | Fit for a product? | What it needs |
|---|---|---|---|
| Language and framework (Python, FastAPI) | Fine | Yes | Keep. Whisper, FSRS and the LLM libraries are Python-first. |
| Core idea (code checks the language model; Reviewer gate) | Strong | Yes, it's the edge | Keep the pattern; make it a reusable module. |
| User data and identity | Brains are JSON files keyed by a random id **per browser tab** (`app/main.py:22`); closing the tab orphans the Brain. No users. | No | Real accounts and a database. |
| Runtime state | Sessions in an in-memory dict, capped at 300, idle ones evicted; jobs in daemon threads (`app/main.py:171`) | No | A restart loses work; can't run two servers. Job queue and worker, state in the database. |
| Storage | Whole JSON file rewritten under one global lock | Fine for one user | A database with migrations. |
| Language-model connection | Default provider launches the **Claude Code CLI on the developer's login** per call; Gemini via hand-rolled HTTP; JSON pulled out of replies with a regex | Not shippable | One provider interface backed by a production API, structured outputs, prompts as versioned, testable files. |
| Frontend | One HTML file, inline CSS, global JavaScript | No | Component-based TypeScript app with a build, shared by the extension side panel and the web Brain page. |
| Tests and CI | None | No | Unit tests for the Brain formulas, recorded tests for agents, CI on every push. |
| Coupling to maths | Grade 10 maths runs through `orchestrator.py`, `agents.py`, `main.py` | Gets in the way | The course product shares the agent pattern, not the maths. Archive or isolate the maths path. |
| Privacy and security | No auth, no rate limits, no deletion | Needed before launch | Transcripts are personal data (POPIA): accounts, delete-my-data, usage limits. |
| Deployment | Dockerfile, key injected at run time | Good start | Keep; pin dependency versions (`requirements.txt` uses `>=`). |

## Adding a feature today

**Hard.** Most features touch the same four central files: `main.py` (routes), `orchestrator.py` (a 330-line class
mixing the maths flow, careers and the Spam Lab), `index.html` (all UI), and often `agents.py`. With no tests,
nothing catches what breaks.

## Bringing in a partner today

- **A new developer** can read the code (small, documented) but can't easily work in parallel: two people editing
  one `index.html` will conflict. Running it needs the original developer's Claude Code login or a Gemini key. There
  are no tests to say whether a change is safe, and the conventions live only in `CLAUDE.md`.
- **A new platform or integration partner** has no extension point: capture, transcript and model are hard-wired.
  Needed: a **transcript source** interface and a **language-model provider** interface, so a partner is one new
  adapter, not a change to the core.

## Recommendation

Keep Python, FastAPI, three.js, Docker and the agent/Reviewer pattern. Replace identity and storage, the job runtime,
the language-model layer and the frontend, with tests and CI from the first commit. Build the course product as
**new, modular code next to the old app**, rather than bending the maths orchestrator into it. See
`docs/design/architecture.md`.
