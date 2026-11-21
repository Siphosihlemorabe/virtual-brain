# Learning guide: what has been built, the concepts behind it, and why

Last updated: 21 November 2026 (end of stage 0, step 8). Updated after every step.

Read it in order the first time. Each section points to the code, so you can open the file and read it alongside.
When a line of code is unclear, ask: the goal is that you understand every line.

---

## 1. The big picture

```
 Chrome extension (side panel)   Web app (browser)
            \                      /
             typed API client (generated from the backend)
                        |
                 HTTP  /v1/...  (FastAPI)
                        |
   current_learner (who is asking)  ·  get_session (one unit of work per request)
                        |
   modules: accounts · capture · courses · agents · quiz · learning · llm   (repository.py = only DB access)
                        |                                   |
                 PostgreSQL (Docker)              language model (fake / claude CLI / Anthropic API)
                        |
        background worker: runs queued jobs (transcription, agents), logs progress
```

Nothing in the app teaches yet. Stage 0 builds the **foundations every feature stands on**. Slice 1 adds the
learning features (import a transcript → concepts → questions checked by the Reviewer → quiz → the Brain).

## 2. What has been built, step by step

| Step | What | Main files | Concepts it teaches (§3) |
|---|---|---|---|
| 1 | Moved the hackathon app into `legacy/`, history kept | `legacy/`, `.gitignore` | git mv, keeping history, .gitignore |
| 2 | Backend skeleton: FastAPI, 7 empty modules, health check, first test | `backend/pyproject.toml`, `backend/src/vb/main.py`, `core/health.py`, `core/config.py` | Python packages, src layout, uv, FastAPI routes, settings from env vars, pytest |
| 3 | Database layer: Postgres in Docker, SQLAlchemy, Alembic, `learner` table, repository pattern | `compose.yaml`, `core/db.py`, `accounts/models.py`, `schemas.py`, `repository.py`, `migrations/` | Tables, keys, ORM, migrations, transactions, repository pattern, test isolation |
| 4 | Background jobs: queue, claim, retries, crash recovery, progress log | `core/jobs/` | Queues and workers, optimistic claiming, retries, commit-per-step |
| 5 | Language-model layer: one way to call a model, providers, prompt files, call log | `llm/` | Interfaces (Protocol), adapters, structured output, test doubles, cost tracking |
| 6 | Dev login and one unit of work per request; `GET /v1/me` | `accounts/auth.py`, `accounts/api.py`, `core/db.py` | Dependency injection, unit of work, fail-safe configuration |
| 7 | Frontend workspace: web app, extension, shared UI, generated API client; CORS | `frontend/`, `backend/src/vb/main.py` | TypeScript, React, TanStack Query, Vite, Tailwind, monorepos, code generation, CORS, Chrome extensions |
| 8 | One command to run everything; worker loop; seed data | `tools/dev.py`, `core/jobs/worker.py`, `seed.py` | Processes and subprocesses, polling, idempotent seeding |

Also built: `tools/validation/transcribe.py` (self-test helper: record and transcribe locally with Whisper).

## 3. Concepts to learn

Grouped by topic, roughly in the order you'll need them. "Where" points to our code.

### 3.1 Python

| Concept | In one line | Where |
|---|---|---|
| **Type hints** | `def get_learner(session: Session, learner_id: uuid.UUID) -> Learner \| None` says what goes in and out; mypy checks it | Everywhere |
| **Pydantic models** | Classes that validate data: wrong types fail loudly instead of silently | `accounts/schemas.py`, `llm/schemas.py` |
| **Dataclasses** | Small classes that just hold values | `llm/provider.py` (`ProviderResult`), `llm/prompts.py` (`Prompt`) |
| **Protocol** (structural typing) | "Anything with a `complete(...)` method counts as a provider", without inheriting | `llm/provider.py` |
| **Generics (`TypeVar`)** | `complete(..., schema: type[T]) -> T`: ask for a `HealthCheckReply`, get a `HealthCheckReply` back | `llm/provider.py`, `llm/service.py` |
| **Context managers** | `with ... as session:` guarantees clean-up; `@contextmanager` makes your own | `core/db.py` (`unit_of_work`) |
| **Decorators** | `@lru_cache` (compute once), `@router.get("/me")` (register a route) | `core/config.py`, `accounts/api.py` |
| **Packages and the `src/` layout** | Code lives in `src/vb/`, and tests import the installed package | `backend/src/vb/` |
| **uv and lockfiles** | `pyproject.toml` lists what you need; `uv.lock` pins exact versions so every machine matches | `backend/` |

### 3.2 Web and APIs

| Concept | In one line | Where |
|---|---|---|
| **HTTP** | Requests (GET to read, POST to create…) and status codes (200 OK, 404 not found, 501 not implemented) | `/v1/health`, `/v1/me` |
| **Routes / endpoints** | A URL plus method mapped to a function | `accounts/api.py` |
| **Dependency injection** (`Depends`) | An endpoint *declares* what it needs (a session, the learner); FastAPI builds it per request and tests can swap it | `accounts/auth.py`, `tests/api/test_me.py` |
| **OpenAPI** | A machine-readable description of the API, generated by FastAPI (`/docs` shows it) | Used by `frontend/packages/api-client/scripts/generate.mjs` |
| **API versioning** (`/v1`) | Clients keep working when a future `/v2` changes things | `main.py` |
| **CORS** | Browsers block cross-site calls unless the API allows that site | `main.py`, `tests/api/test_cors.py` |

### 3.3 Databases

| Concept | In one line | Where |
|---|---|---|
| **Tables, rows, columns** | The shape of stored data | `docs/design/database.md` §3 |
| **Primary key** | The unique id of a row (we use UUIDs made in Python) | `core/db.py` (`Entity.id`) |
| **Foreign key** | A column pointing at another table's row (`job_log.job_id` → `job.id`) | `core/jobs/models.py` |
| **Unique constraint** | The database refuses duplicates (`learner.email`) | `accounts/models.py` |
| **Index** | A lookup structure that makes a query fast (e.g. "oldest queued job") | `migrations/versions/0004_*` |
| **Transaction** | A group of changes that all happen or none do: `commit` saves, `rollback` undoes | `core/db.py` |
| **Unit of work** | One transaction per request: all saved together, or all undone | `core/db.py` (`unit_of_work`, `get_session`) |
| **Savepoint** | A transaction inside a transaction; how tests undo everything after each test | `tests/conftest.py` |
| **ORM vs SQL** | SQLAlchemy maps tables to Python classes; it writes the SQL for you | `*/models.py` |
| **Migrations (Alembic)** | Versioned, reviewable scripts that change the database shape, applied in order | `backend/migrations/versions/` |
| **DDL vs DML** | DDL changes the *shape* (CREATE TABLE); DML changes the *data* (INSERT, UPDATE) | Rule P7 in `database.md` |
| **Timezone-aware timestamps** | Store UTC with the timezone, never "naive" local time | `core/db.py` (`utcnow`) |
| **Optimistic claiming (compare-and-set)** | `UPDATE … WHERE status = 'queued'`: only one worker's update can succeed, no locks needed | `core/jobs/repository.py` (`claim`) |

### 3.4 Architecture and design patterns

| Concept | In one line | Where |
|---|---|---|
| **Modular monolith** | One app, split into modules with hard boundaries | `backend/src/vb/<module>/` |
| **Repository pattern** | Only `repository.py` touches a module's tables; everything else uses plain values | Every `repository.py` |
| **Ports and adapters** | An interface (port) plus swappable implementations (adapters): fake, Claude CLI, Anthropic | `llm/provider.py`, `fake.py`, `claude_cli_provider.py`, `anthropic_provider.py` |
| **Append-only log and derived data** | Store every event once (attempts); compute the Brain from it, so it can be rebuilt | `database.md` §3.3–3.4 (built in slice 1) |
| **Configuration from the environment** | Behaviour set by `VB_*` variables or `.env`, not code changes | `core/config.py` |
| **Secrets handling** | Keys never in git (`.env` is ignored) or in logs (`SecretStr`) | `.gitignore`, `core/config.py` |
| **Fail-safe defaults** | The app refuses to start in an unsafe setup (prod plus dev login) | `accounts/auth.py` (`check_auth_config`) |

### 3.5 Background work

| Concept | In one line | Where |
|---|---|---|
| **Job queue** | Work is stored as `queued` rows and done later, outside the web request | `core/jobs/` |
| **Worker** | A process that keeps picking up queued jobs | `core/jobs/worker.py` |
| **Polling** | Check every few seconds; simple and reliable at small scale | `worker.py` (`POLL_SECONDS`) |
| **Retries and giving up** | Try up to 3 times, then mark failed with the error | `core/jobs/repository.py` (`fail`) |
| **Crash recovery** | Jobs stuck in `running` too long go back to the queue | `requeue_stale`, `runner.py` |
| **Commit per step** | Save progress as you go, so a crash loses almost nothing | `runner.py` (the `log` function) |

### 3.6 The AI layer

| Concept | In one line | Where |
|---|---|---|
| **Prompts as versioned files** | Prompt changes are reviewable in git; every call records the version used | `llm/prompts/`, `llm/prompts.py` |
| **Structured output / JSON Schema** | The model must answer in a shape we define; anything else is an error | `llm/schemas.py`, `anthropic_provider.py`, `claude_cli_provider.py` |
| **Provider abstraction** | The app talks to "a provider", never to a vendor directly | `llm/service.py` |
| **Cost and quality tracking** | Every call logged: tokens, time, cost, errors | `llm_call` table, `llm/pricing.py` |
| **"AI proposes, code decides"** | Marking, scheduling and the Brain are plain code; the AI only writes and reads text | `product-spec.md` §6.2 |

### 3.7 Testing

| Concept | In one line | Where |
|---|---|---|
| **Test levels** | unit (pure code), contract (every adapter passes the same suite), db (against a real test database), api (HTTP endpoints) | `backend/tests/` |
| **Fixtures** | Reusable test setup (`engine`, `session`, `client`) | `tests/conftest.py`, `tests/api/test_me.py` |
| **Test isolation** | Each test runs in a transaction that's rolled back, so tests never affect each other | `tests/conftest.py` |
| **Test doubles** | A fake that behaves like the real thing (fake model, fake server) | `llm/fake.py`, `MeCard.test.tsx` |
| **Contract tests** | One suite every implementation must pass | `tests/contract/test_llm_provider_contract.py` |
| **Opt-in expensive tests** | Real-model tests only run when you allow them | `VB_RUN_CLI_TESTS`, `VB_RUN_PAID_TESTS` |
| **Tests from the spec** | Acceptance criteria become tests, named after the feature (`test_f15_…`) | `tests/db/test_f15_jobs.py` |

### 3.8 Tools

| Concept | In one line | Where |
|---|---|---|
| **Git branches and commits** | Small, reviewed commits on `docs/rebuild-plan`, each with a clear message | `git log` |
| **Docker** | **Image** (a packaged program), **container** (a running image), **volume** (data that survives), **port mapping** (`5434:5432`) | `compose.yaml` |
| **Linter, formatter, type checker** | ruff and ESLint (mistakes), ruff format and Prettier (layout), mypy and tsc (types) | `pyproject.toml`, `frontend/eslint.config.js` |
| **Processes and subprocesses** | A program starting other programs, reading their output, stopping their whole tree | `tools/dev.py` |
| **Idempotent scripts** | Safe to run again and again with the same result | `seed.py` |

### 3.9 Frontend

| Concept | In one line | Where |
|---|---|---|
| **TypeScript** | JavaScript with types; strict mode catches mistakes early | `frontend/tsconfig.base.json` |
| **React components and props** | Functions that return UI; props are their inputs | `packages/ui/src/Card.tsx` |
| **Hooks** | Functions like `useQuery` that give a component data and state | `packages/ui/src/MeCard.tsx` |
| **TanStack Query** | Fetching with caching, loading and error states handled for you | `MeCard.tsx`, `apps/web/src/main.tsx` |
| **Vite** | Dev server (instant reload) and bundler (production build) | `apps/*/vite.config.ts` |
| **Tailwind CSS** | Styling with small classes like `rounded-xl p-6` | `Card.tsx`, `index.css` |
| **npm workspaces (monorepo)** | Several packages in one repo, sharing code and tools | `frontend/package.json` |
| **Code generation** | Types written by a script from the API, so frontend and backend can't drift apart | `packages/api-client/scripts/generate.mjs` |
| **Component tests (RTL + jsdom)** | Render a component in a simulated browser and check what a user would see | `MeCard.test.tsx` |

### 3.10 Chrome extensions

| Concept | In one line | Where |
|---|---|---|
| **Manifest V3** | The file declaring what an extension is and may do | `apps/extension/public/manifest.json` |
| **Service worker** | The extension's background script (wakes on events) | `apps/extension/src/background.ts` |
| **Side panel** | A page docked beside the website you're on | `sidepanel.html`, `sidepanel.tsx` |
| **Permissions and host permissions** | What the extension may use, and which sites it may call | `manifest.json` |
| **Content scripts** (we have none) | Code injected into web pages. We avoid them so we never read course pages | `manifest.test.ts` |

## 4. Decisions made, with alternatives

| Date | Decision | Alternatives considered | Why this one | Revisit when |
|---|---|---|---|---|
| 17 Nov | Research first; every feature traces to research | Build first, research later | You asked for useful, not gimmicky | — |
| 17 Nov | Rebuild beside the old app, old app in `legacy/` | Bend the old orchestrator into the new product | Little shared code; the old app keeps working for demos | — |
| 17 Nov | Modular monolith | Microservices; one big module | Clear boundaries without running many services | Many teams or very different scaling needs |
| 17 Nov | Python + FastAPI | Django, Node/TypeScript backend | Whisper, FSRS and the Anthropic SDK are Python-first; typed; OpenAPI built in | — |
| 17 Nov | Dynamic engine, focused AWS launch | Fully dynamic; fully curated | Exam skeleton reduces AI mistakes; concrete promise | After the first launch |
| 17 Nov | Anthropic API in production, model per job | Bedrock (no in-Region Claude in eu-north-1), Gemini, OpenAI, Chinese models (data residency) | Quality; checks catch errors; data stays in adequate jurisdictions | Measured accuracy or cost says otherwise |
| 18 Nov | Claude CLI for development | Wait for an API key | No key yet; free; tested | When the API key arrives |
| 17 Nov | Tab audio + local Whisper for transcripts | Reading platform captions (terms forbid); Amazon Transcribe (paid plan only) | Works everywhere, data stays local | Legal advice; paid plan |
| 18 Nov | SQLAlchemy 2.0 ORM + Alembic, with portability rules | Plain SQL (psycopg), SQLAlchemy Core, SQLModel | Your choice; switching databases stays a setting | Complex queries or a database change |
| 18 Nov | PostgreSQL locally; Aurora DSQL proposed for production | RDS (+ NAT ~$34/mo), Aurora Serverless v2 (15 s wake-up), DynamoDB | Free tier, no private network needed | Stage 3 deployment decision (open) |
| 18 Nov | One table change per migration; never drop columns | Free-form migrations | DSQL limits; also the safest way to change live data | — |
| 18 Nov | Job queue in Postgres locally; SQS + Lambda planned in AWS | Celery + Redis; always-on worker | Simple locally; pay-per-job in AWS | Volume grows |
| 18 Nov | Optimistic claim (`WHERE status = 'queued'`) | `SELECT … FOR UPDATE SKIP LOCKED` (PostgreSQL-only) | Portable, DSQL-friendly | — |
| 18 Nov | Fake model as the default provider | Always call a real model | Tests are free and repeatable | — |
| 18 Nov | Dev login now, Cognito later behind one file | Build real login now; no login until stage 3 | Every feature knows "who" from day one, at no cost | Stage 3 |
| 18 Nov | React + TypeScript + Vite + TanStack Query + Tailwind | Svelte, Vue; hand-written fetch; CSS modules | Most common skills; typed; consistent | — |
| 20 Nov | Generated API client (openapi-typescript + openapi-fetch) | Hand-written client, orval | Front and back can't drift apart | — |
| 20 Nov | Plain Vite for the extension, hand-written manifest | WXT framework | You can see every piece | Extension grows complex or goes cross-browser |
| 20 Nov | CORS for the web app only | Also the extension | `host_permissions` already lets the extension call the API; stricter | — |
| 21 Nov | Database in Docker, everything else run natively by `tools/dev.py` | Everything in Docker Compose | Claude CLI works; lighter on memory | Stage 3 (containers needed for Lambda) |
| 17–19 Nov | Ports 5434 for our database | 5432/5433 | Two local PostgreSQL installs already use them | — |

Planned but not yet decided: deployment option (A serverless / B one server / C containers), DSQL vs RDS,
cold start, pricing (see `docs/design/tech-stack.md` §6 and `product-spec.md` §6.5).

## 5. Things that went wrong and what they teach

Real mistakes from this project, kept because each one is a lesson.

| What happened | Lesson |
|---|---|
| I wrote "six agents" in the pitch; the code has five (the Brain is memory, not an agent) | Check claims against the code before saying them |
| The research doc said "store JSON as text" for DSQL; DSQL had since added JSON support | Facts about cloud services go stale: check current docs |
| Our database on 5433 clashed with a local PostgreSQL ("password authentication failed") | When a connection fails oddly, check *what* is listening on the port |
| Docker brought back an old copy of the container (port 5433) while the machine was out of memory | Recreate (`--force-recreate`) when the running thing doesn't match the config |
| Tests and Vite failed only under memory pressure | Some failures are the environment, not the code: check memory and CPU first |
| My first fake provider passed the prompt id as the "model name" | A hack that "works" still makes the next reader guess; fix it before moving on |
| npm and uv installed newer major versions than the docs I had (Anthropic SDK 2.x, Vite 8, TypeScript 6) | Check the installed library's real API before writing code against it |

## 6. A study order and good sources

1. **Python typing and Pydantic** → https://docs.pydantic.dev/latest/concepts/models/
2. **FastAPI tutorial** (routes, dependencies, testing) → https://fastapi.tiangolo.com/tutorial/
3. **pytest** (fixtures) → https://docs.pytest.org/en/stable/how-to/fixtures.html
4. **SQL basics, then SQLAlchemy 2.0** → https://docs.sqlalchemy.org/en/20/tutorial/
5. **Alembic tutorial** → https://alembic.sqlalchemy.org/en/latest/tutorial.html
6. **Docker: images, containers, volumes, Compose** → https://docs.docker.com/get-started/
7. **TypeScript handbook** → https://www.typescriptlang.org/docs/handbook/intro.html
8. **React: "Learn" section** → https://react.dev/learn
9. **TanStack Query: overview and queries** → https://tanstack.com/query/latest/docs/framework/react/overview
10. **Chrome extensions (MV3, side panel)** → https://developer.chrome.com/docs/extensions
11. **Learning science behind the product** → `docs/research/brain-research.md`

Tip: for each topic, read the guide, then open the matching file in §2 and trace one request or one test through it.
