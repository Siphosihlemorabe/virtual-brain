# Architecture proposal: Virtual Brain as a product

Date: 17 November 2026. Status: proposal, for review.
Inputs: `docs/research/stack-evaluation.md` (what's wrong today), `docs/design/slice-1-design.md` (what we build
first), `docs/research/brain-research.md` (why).

## 1. What the architecture must make easy

1. **Adding a feature** touches one module, not four central files, and tests say whether anything broke.
2. **Bringing in a developer**: `docker compose up` works on day one with no API keys, and two people can work in
   parallel without conflicts.
3. **Bringing in a platform partner**: write one adapter (a transcript source) without changing the core.
4. **Trusting the Brain**: the learning maths is pure, tested code, and can be recomputed when we refit parameters.
5. **Running for real**: accounts, data that survives restarts, background jobs, privacy controls, and all of it
   inside our AWS project's limits.

## 2. Constraints this design respects (checked 17 November)

| Constraint | Effect |
|---|---|
| AWS project Region is **eu-north-1**; no cross-Region features | Everything regional runs in eu-north-1. CloudFront is global (allowed). |
| Project is on the **free plan** | All services used here are on the free-plan list. **Amazon Transcribe is Paid-plan only**, so it isn't used. App Runner isn't offered. |
| **No Claude model runs in-Region** on Bedrock in eu-north-1 (cross-Region only) | The language model is called through the **Anthropic API**, behind our own provider interface so it can change later. |
| Platform terms (research §7) | No content scripts and no reading of course pages: tab audio only. |
| Learning data is personal (POPIA) | Accounts, delete-my-data, transcripts only (audio deleted after transcription). |

## 3. The shape: a modular monolith with adapters

One backend codebase and one deployable image, split into modules with hard boundaries. That gives most of the
benefit of microservices (clear ownership, parallel work) without the cost of running many services for a small team.

```
                      ┌────────────── Browser ──────────────┐
                      │ Extension (MV3)        Web app      │
                      │ side panel, capture    Brain page   │
                      └──────────┬──────────────────┬───────┘
                                 │ HTTPS /v1 (OpenAPI, Cognito tokens)
                      ┌──────────▼──────────────────▼───────┐
                      │ API service (FastAPI)               │
                      │  modules: courses · learning ·      │
                      │  quiz · capture · accounts          │
                      └──────┬──────────────────────┬───────┘
                             │ jobs table           │ SQL
                      ┌──────▼───────┐       ┌──────▼───────┐
                      │ Worker       │──────▶│ PostgreSQL   │
                      │ transcribe,  │       └──────────────┘
                      │ agents       │──▶ Anthropic API (LLM provider)
                      └──────────────┘
```

### Backend modules

| Module | Owns | Talks to others only through |
|---|---|---|
| `accounts` | Users, consent records, delete-my-data | `accounts.service` |
| `capture` | Upload of segment audio, **transcript sources** (adapters), transcription | Emits "segment transcribed" |
| `courses` | Courses, lectures, segments, concepts, prerequisite links | `courses.service` |
| `agents` | Planner, Tutor, Reviewer for courses, plus the **review gate** framework (check → flag → fix → re-check) | `agents.service`; uses `llm` |
| `quiz` | Items, attempts, the answer flow (confidence first) | `quiz.service` |
| `learning` | The Brain: BKT, FSRS, calibration, confusions, review queue, outer fringe. **Pure functions, no I/O.** | Called by `quiz` and the Brain endpoint |
| `llm` | Provider interface, prompt files, structured-output validation, call log and cost | `llm.complete(prompt_id, inputs, schema)` |
| `core` | Config, database, auth middleware, job queue, logging | Imported by all |

**The rule that keeps this easy to change:** a module never reads another module's tables. It calls that module's
service. A boundary test in CI enforces it (import rules).

### Three adapter interfaces: where features and partners plug in

```python
class TranscriptSource(Protocol):      # tab audio today; Zoom host VTT, partner APIs, manual upload later
    def segments(self, job) -> list[TranscriptLine]: ...

class Transcriber(Protocol):           # faster-whisper today; Amazon Transcribe if we move to the Paid plan
    def transcribe(self, audio_path) -> list[TranscriptLine]: ...

class LLMProvider(Protocol):           # Anthropic today; a fake provider for tests and local dev
    def complete(self, prompt: str, schema: type[BaseModel]) -> BaseModel: ...
```

A new platform partner is one `TranscriptSource` with its own contract tests. A new model vendor is one
`LLMProvider`. Neither touches the core.

### Data that can be recomputed

- **Attempts are the source of truth**: an append-only log of every answer, with confidence and timing.
- The Brain's per-concept state (mastery, FSRS card, calibration) is **derived** from attempts and can be rebuilt.
  When we refit the BKT or FSRS parameters (slice 1 design §8), we recompute everyone's Brain instead of migrating
  numbers by hand.

### The language-model layer

- **Prompts are files** (`llm/prompts/tutor_items.v1.md`) with a version in the name. Every stored item records which
  prompt version and model made it.
- **Structured outputs** are validated with Pydantic schemas. This replaces today's regex JSON extraction.
- **One call log** (who called, prompt version, tokens, latency, cost) feeds the agent log and a spend dashboard.
- **A fake provider** with recorded replies means tests and local dev need no API key.
- The model per task (cheap for extraction, stronger for item writing) is set in config, not in code.

### Jobs

- Transcription and agent runs are **jobs in Postgres** (a jobs table claimed with `SELECT … FOR UPDATE SKIP LOCKED`).
  That's one less service to run, and it behaves the same locally and in AWS.
- Behind a small `jobs` interface, so it can move to Amazon SQS (free plan) if volume demands.
- Each job writes its agent log lines to the database, so the extension can show progress and a restart loses
  nothing.

## 4. Frontend: one TypeScript workspace, two apps

```
frontend/
  packages/ui          design tokens, components (React + TypeScript)
  packages/brain3d     the three.js Brain view, drawn only from Brain data (slice 1 design §10)
  packages/api-client  generated from the backend's OpenAPI schema, so both sides always agree
  apps/web             Brain page, reviews, account and data settings (Vite)
  apps/extension       MV3: side panel (React), service worker, offscreen capture (Vite)
```

- **React + TypeScript**: the most common skills to hire or partner for, and typed to match the API.
- **A generated API client** means a backend change that breaks the frontend fails the build, not production.
- The extension and the web app share components, so the quiz looks the same in both.
- npm workspaces (Node 22 is already installed; pnpm isn't), Vite, ESLint, Vitest.

## 5. Repository layout

```
virtual-brain/
  backend/
    pyproject.toml            managed with uv (already installed); pinned lockfile
    src/vb/{core,accounts,capture,courses,agents,quiz,learning,llm}/
    src/vb/llm/prompts/       versioned prompt files
    migrations/               Alembic
    tests/{unit,contract,agents}/
  frontend/                   as in §4
  legacy/                     today's hackathon app, moved unchanged and still runnable
  infra/                      AWS CDK (Python)
  docs/{research,design}/
  compose.yaml                postgres + api + worker for local dev
  .github/workflows/ci.yml
```

## 6. Running it

### Locally (every developer)

`docker compose up` starts Postgres, the API and the worker. Running `npm run dev` in `frontend/` starts the web app
and builds the extension. The fake LLM provider is the default, and a real Anthropic key in `.env` switches it on. A
seed script loads one sample course with a recorded transcript.

### In AWS (eu-north-1, all free-plan services)

| Need | Service | Why |
|---|---|---|
| API and worker containers | **Amazon ECS on Fargate**, two services from one image in **ECR** | No servers to manage. The worker needs CPU for Whisper, which suits containers better than Lambda. |
| Database | **Amazon RDS for PostgreSQL**, smallest instance | Plain Postgres, the same as local. Revisit Aurora when load grows. |
| Login | **Amazon Cognito** user pool, hosted login with PKCE | The web app and the extension (`chrome.identity.launchWebAuthFlow`) share one login. |
| Web app hosting | **S3 + CloudFront** | Static build. CloudFront is global, which projects allow. |
| Secrets | **AWS Secrets Manager** | Anthropic API key, database credentials. |
| Logs and metrics | **CloudWatch** | Structured logs, plus alarms on job failures and model spend. |
| Infrastructure as code | **AWS CDK (Python)** | Reviewable, repeatable. Single-Region stacks only (StackSets aren't allowed). |
| Temporary audio | Never stored in S3: uploaded straight to the worker, transcribed, deleted | Privacy by design. |
| Screenshots (F21) | **S3**, private, deleted with the learner's data | Kept until the learner deletes them. |
| Review reminder emails (F23) | **Amazon SES** (on the free plan) | Opt-in digests with unsubscribe. |

**Cost guardrails:** the project has about $140 in free-plan credits, valid until 3 May 2027. Before deploying, we
set a budget alarm, keep one small task per service, and confirm the project's spend limit in AWS Settings →
Billing. Stage 1 below needs no AWS at all.

## 7. Quality gates (from the first commit)

- **CI on every push** (GitHub Actions): ruff, mypy, pytest, ESLint, Vitest, an OpenAPI diff, and the module-boundary
  test.
- **The learning maths** (BKT, FSRS mapping, calibration) gets unit tests with hand-checked numbers.
- **Agents** get recorded-reply tests, plus a small **evaluation set**: transcripts with known-good and known-bad
  items, so a prompt change can't silently lower item quality. This is the Reviewer's audit from slice 1 §12,
  automated.
- **Contract tests** for each adapter: every `TranscriptSource` must pass the same suite.

## 8. How to add things (the payoff)

**A new feature, for example "pretest before a rewatch":**
1. Add a function to `learning` (pure, with unit tests) and an endpoint in `quiz`.
2. Add a component in `packages/ui` and use it in the side panel.
3. The API client regenerates, CI runs, done. No central file to edit.

**A new platform partner, for example a host's Zoom transcripts:**
1. Implement `TranscriptSource` in `capture/sources/zoom_host.py`.
2. Make it pass the contract tests, and register it in config.

**A new developer:** clone, `docker compose up`, `npm run dev`, read `CONTRIBUTING.md` and `docs/`. No keys needed,
and CI tells them if a change is safe.

## 9. Migration plan

| Stage | What | AWS needed? |
|---|---|---|
| 0. Foundation | New layout; move the hackathon app to `legacy/`; compose, Postgres, Alembic, CI, fake LLM provider, dev login | No |
| 1. Slice 1 M1–M4 | Capture, transcription, agents with the review gate, quiz, Brain model (slice 1 design §13) | No (local) |
| 2. Slice 1 M5–M6 | Brain page with 3D view, reviews, the two-lecture evaluation | No |
| 3. First deploy | Cognito, RDS, ECS, S3+CloudFront via CDK; budget alarm; real accounts | Yes |
| 4. Launch prep | Delete-my-data, privacy notice, legal check on audio capture (research §7.2), Chrome Web Store listing | Yes |

The legacy maths app keeps working throughout, for demos, until we decide to retire it.

## 10. Decisions needed from you

1. ~~Anthropic API~~ **Agreed** (product spec §6.1): a model per job, chosen by the evaluation set. A monthly
   budget is still to set.
2. ~~React for the frontend~~ **Agreed** (product spec D10).
3. ~~Which GitHub repo is home?~~ **Agreed: the fork, `Siphosihlemorabe/virtual-brain`** (product spec D11).
4. **When to deploy:** this plan stays local until slice 1 works (stage 3). Is that right?
