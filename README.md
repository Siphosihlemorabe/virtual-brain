# Virtual Brain

A learning companion for people studying from online courses and classes. It turns what you watch into
retrieval practice, keeps a model of what you know (what you've learned, what you're forgetting, how sure you are,
what you confuse) and tells you what to review next. First focus: AWS Certified Cloud Practitioner.

**Status:** stage 0 (foundations) is being built: backend, database, jobs, language-model layer, dev login and
frontend shells. No learning features yet; slice 1 adds them.

## Run everything

Needs Docker Desktop (running), [uv](https://docs.astral.sh/uv/) and Node.js. First time only:
`cd frontend && npm install`.

```
python tools/dev.py
```

This starts PostgreSQL in Docker, applies migrations, loads seed data, then runs the API
(http://localhost:8000/docs), the background worker and the web app (http://localhost:5173) together.
Ctrl+C stops them; the database keeps running (`docker compose stop` stops it).

To use the local Claude CLI as the language model (development, no API key), add `VB_LLM_PROVIDER=claude_cli`
to the repo-root `.env`. The default is a fake model with recorded replies.

## Where things are

| Path | What |
|---|---|
| `backend/` | FastAPI app, database, jobs, language-model layer. See `backend/README.md` |
| `frontend/` | Web app, Chrome extension, shared UI and the generated API client (npm workspaces) |
| `docs/learning-guide.md` | **What has been built, the concepts behind it, and every decision with its alternatives** |
| `docs/research/` | The research behind every feature, and the evaluation of the old stack |
| `docs/design/` | Product spec, slice 1 design, architecture, tech stack, database design |
| `docs/validation/` | The self-test protocol and the learner interview guide |
| `tools/` | `dev.py` (run everything) and `validation/` (self-test helpers) |
| `legacy/` | The original hackathon app (Grade 10 maths), kept runnable for demos. See `legacy/README.md` |

Working rules for this repo are in `CLAUDE.md`.
