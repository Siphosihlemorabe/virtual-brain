# Virtual Brain backend

FastAPI app, managed with [uv](https://docs.astral.sh/uv/). Design: `../docs/design/architecture.md`.

```
cd backend
uv sync                                  # install exact versions from uv.lock
uv run uvicorn vb.main:app --reload      # http://localhost:8000/v1/health, docs at /docs
uv run pytest                            # tests
uv run ruff check . && uv run ruff format --check . && uv run mypy src tests
```

| Folder | What |
|---|---|
| `src/vb/core/` | Config, health check (later: database, auth, jobs, logging) |
| `src/vb/<module>/` | One folder per module: accounts, capture, courses, agents, quiz, learning, llm. A module never reads another module's tables. |
| `tests/unit/` | Pure code, e.g. the Brain's formulas |
| `tests/contract/` | Shared suites every adapter must pass |
| `tests/agents/` | Agents with a fake language model and recorded replies |
| `tests/api/` | Endpoints, against a test database |

Tests are named after the feature they prove (`test_f8_...`); see `../docs/design/product-spec.md`.
