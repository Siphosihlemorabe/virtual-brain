# Virtual Brain backend

FastAPI app, managed with [uv](https://docs.astral.sh/uv/). Design: `../docs/design/architecture.md`;
database rules: `../docs/design/database.md`.

```
docker compose up -d                     # from the repo root: PostgreSQL 16 on localhost:5434
cd backend
uv sync                                  # install exact versions from uv.lock
uv run alembic upgrade head              # apply database migrations
uv run uvicorn vb.main:app --reload      # http://localhost:8000/v1/health, docs at /docs
uv run pytest                            # tests (database tests need the container running)
uv run ruff check . && uv run ruff format --check . && uv run mypy src tests
```

Port 5434 because local PostgreSQL installs on this machine already use 5432 and 5433. To use another database,
set `VB_DATABASE_URL` (portability rule P1).

| Folder | What |
|---|---|
| `src/vb/core/` | Config, health check, database connection and base table class (later: auth, jobs, logging) |
| `src/vb/<module>/` | One folder per module: accounts, capture, courses, agents, quiz, learning, llm. Each has `models.py` (tables), `schemas.py` (what it hands out) and `repository.py` (the only code touching its tables). |
| `migrations/versions/` | Alembic migrations, one table change each, never dropping a column |
| `tests/unit/` | Pure code, e.g. the Brain's formulas |
| `tests/contract/` | Shared suites every adapter must pass |
| `tests/agents/` | Agents with a fake language model and recorded replies |
| `tests/db/` | Repositories and migrations, against a fresh test database (`vb_test`) |
| `tests/api/` | Endpoints |

Tests are named after the feature they prove (`test_f8_...`); see `../docs/design/product-spec.md`.
