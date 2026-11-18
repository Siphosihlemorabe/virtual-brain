# Database design

Date: 18 November 2026. Status: **draft for review**. Nothing here is built until it is agreed.
Covers slice 1 plus F18 (exam skeleton) and F20 (report an error). Inputs: `product-spec.md`, `slice-1-design.md`,
`tech-stack.md`.

## 1. Decisions

- **SQLAlchemy 2.0 ORM** for code, **Alembic** for migrations (agreed 18 November).
- **Local and tests:** PostgreSQL 16 in Docker. **Production:** Aurora DSQL (proposed; the rules in §2 keep RDS or
  any other PostgreSQL a drop-in alternative).

## 2. Portability rules: how we stay able to change the database

Each rule exists because of a real difference between databases (mostly DSQL's limits). Together they mean the same
code runs on PostgreSQL, Aurora DSQL and SQLite, and moving is a configuration change plus a dialect.

| # | Rule | Why |
|---|---|---|
| P1 | **One setting picks the database:** `VB_DATABASE_URL` (e.g. `postgresql+psycopg://…`, the DSQL dialect URL, `sqlite:///…`) | Switching is configuration, not code |
| P2 | **Only each module's `repository.py` touches SQLAlchemy.** Services and agents call repository functions with plain Python values and get Pydantic models back | If we ever leave SQLAlchemy, only repository files change |
| P3 | **Generic SQLAlchemy types only:** `Uuid`, `String`, `Text`, `Integer`, `Float`, `Boolean`, `DateTime(timezone=True)`, `JSON`. Never `sqlalchemy.dialects.postgresql.*` (e.g. `JSONB`, `ARRAY`) | Dialect types tie us to one database |
| P4 | **IDs are UUIDs generated in Python** (`uuid4`), not database sequences | Works everywhere; spreads writes evenly in DSQL |
| P5 | **Defaults and timestamps are set in Python**, not by database defaults or triggers | DSQL has no triggers; behaviour stays identical everywhere |
| P6 | **No dialect-specific SQL:** no PostgreSQL-only insert options (e.g. `ON CONFLICT`), no stored procedures, no raw SQL strings outside migrations | Standard SQL ports |
| P7 | **One table change per migration file**, and **no data changes in a migration that changes tables** | DSQL allows one DDL statement per transaction and no mixing of DDL and DML |
| P8 | **Never drop or rename a column.** Change shape by *expand and contract*: add the new column, start writing it, backfill, stop reading the old one; leave the old column unused | DSQL doesn't support `DROP COLUMN`; also the safest way to change a live database |
| P9 | **Small transactions** (well under 3,000 changed rows); bulk work is batched | DSQL limits rows changed per transaction |
| P10 | **Deletes happen in application code, in dependency order** (children first), not via database cascades | Behaviour doesn't depend on each database's cascade support |
| P11 | **No hidden queries:** every relationship is `lazy="raise"`; related rows are loaded explicitly (`selectinload`) | ORM queries stay as visible as plain SQL |
| P12 | **CI runs the test suite on PostgreSQL and on SQLite;** a smoke test runs against real DSQL before each deployment | Proves no database-specific code slipped in |

## 3. Tables

Owner = the module whose repository reads and writes the table (architecture §3). Every table has `id` (UUID,
primary key) and `created_at` (timestamp with time zone) unless stated; these are omitted below.

### 3.1 accounts

**`learner`**: one row per user.

| Column | Type | Notes |
|---|---|---|
| `email` | String, nullable, unique | Null until Cognito login (stage 3); dev uses a fixed learner |
| `display_name` | String, nullable | |

**`consent`**: what the learner agreed to, and when (F1, F22).

| Column | Type | Notes |
|---|---|---|
| `learner_id` | Uuid → learner | |
| `notice_version` | String | e.g. `privacy-2026-11` |
| `accepted_at` | DateTime | |

### 3.2 courses

**`exam_skeleton`**, **`exam_domain`**, **`task_statement`**: shared reference data from official exam guides (F18).
Not per learner.

| Table | Columns |
|---|---|
| `exam_skeleton` | `code` (String, unique, e.g. `CLF-C02`), `name`, `guide_version` |
| `exam_domain` | `skeleton_id` → exam_skeleton, `code` (e.g. `2`), `name`, `weight` (Float, e.g. 0.30) |
| `task_statement` | `domain_id` → exam_domain, `code` (e.g. `2.3`), `text` |

**`course`**: a course the learner studies.

| Column | Type | Notes |
|---|---|---|
| `learner_id` | Uuid → learner | One Brain per learner, grouped by course (D6) |
| `name` | String | e.g. "AWS Cloud Practitioner" |
| `platform` | String, nullable | Free text: "DataCamp", "YouTube" |
| `skeleton_id` | Uuid → exam_skeleton, nullable | Null = dynamic mode, labelled "less certain" |

**`lecture`**

| Column | Type | Notes |
|---|---|---|
| `course_id` | Uuid → course | |
| `title` | String | Typed by the learner in the side panel |

**`segment`**: one captured stretch of a lecture.

| Column | Type | Notes |
|---|---|---|
| `lecture_id` | Uuid → lecture | |
| `start_s`, `end_s` | Float | Seconds from the lecture start |
| `transcript` | JSON | List of `{start, end, text}` lines. **The audio is never stored.** |
| `transcriber` | String | e.g. `faster-whisper/small`, for quality tracking |

**`concept`**

| Column | Type | Notes |
|---|---|---|
| `course_id` | Uuid → course | |
| `name` | String | As the lecture says it |
| `normalized_name` | String | Lower-case, singular; **unique per course** so concepts aren't duplicated (F4) |
| `summary` | Text | |
| `first_segment_id` | Uuid → segment | Where it was first taught |
| `task_statement_id` | Uuid → task_statement, nullable | F18 mapping; null = outside the exam or dynamic mode |

**`prerequisite`**

| Column | Type | Notes |
|---|---|---|
| `concept_id`, `requires_id` | Uuid → concept | "concept requires requires_id"; no cycles (checked in code, F4) |
| `status` | String | `proposed` or `verified` |

### 3.3 quiz

**`item`**: a question. Never deleted: retired items keep their history.

| Column | Type | Notes |
|---|---|---|
| `concept_id` | Uuid → concept | |
| `segment_id` | Uuid → segment | |
| `question` | Text | |
| `options` | JSON | List of 4 strings |
| `key_index` | Integer | 0–3 |
| `cited_start_s`, `cited_end_s` | Float | Timestamp of the evidence |
| `cited_quote` | Text | Exact transcript text; checked in code (F6) |
| `distractor_concepts` | JSON | Concept ID (or null) per wrong option, for confusions (F11) |
| `status` | String | `pending`, `live`, `dropped` (failed review), `retired` (F20, AI was wrong) |
| `review_log` | JSON | Reviewer flags, fixes and re-checks |
| `prompt_version`, `model` | String | Who made it (architecture §3) |

**`attempt`**: every answer. **Append-only: rows are never changed or deleted** (except by delete-my-data).

| Column | Type | Notes |
|---|---|---|
| `learner_id` | Uuid → learner | |
| `item_id` | Uuid → item | |
| `chosen_index` | Integer | |
| `correct` | Boolean | Computed in code from `key_index` |
| `confidence` | Float | 0.25, 0.6 or 0.9 (D5) |
| `seconds_taken` | Float | |
| `answered_at` | DateTime | |

**`attempt_exclusion`**: how F20 removes an attempt from the Brain **without editing the attempts log**.

| Column | Type | Notes |
|---|---|---|
| `attempt_id` | Uuid → attempt, unique | |
| `reason` | String | `ai_wrong` or `disputed_unclear` |
| `report_id` | Uuid → item_report | |

**`item_report`**: "This question is wrong" (F20).

| Column | Type | Notes |
|---|---|---|
| `item_id` | Uuid → item | |
| `learner_id` | Uuid → learner | |
| `reason` | Text, nullable | The learner's words |
| `outcome` | String | `pending`, `ai_wrong`, `learner_wrong`, `unclear` |
| `reviewer_note` | Text, nullable | |
| `resolved_at` | DateTime, nullable | |

### 3.4 learning (the Brain)

**Derived tables:** rebuilt from `attempt` (minus `attempt_exclusion`) whenever parameters change. They exist so
reading the Brain is fast; the attempts log stays the source of truth.

**`concept_state`**: one row per learner per concept.

| Column | Type | Notes |
|---|---|---|
| `learner_id`, `concept_id` | Uuid; **unique together** | |
| `p_mastery` | Float | BKT (F8) |
| `fsrs_card` | JSON | From `Card.to_json()` (F9) |
| `first_attempt_at`, `last_correct_on_later_day_at` | DateTime, nullable | For "mastered" (D4) |
| `recent` | JSON | Last 10 `{confidence, correct}` pairs, for calibration (F10) |
| `overconfident_seen` | Integer | Counts toward the "seen twice" rule |
| `updated_at` | DateTime | |

**`confusion`**: one row per learner per confused pair (F11).

| Column | Type | Notes |
|---|---|---|
| `learner_id`, `concept_id`, `confused_with_id` | Uuid; **unique together** | |
| `count` | Integer | Acts from 2 |
| `evidence` | JSON | Attempt IDs |

### 3.5 core and llm

**`job`**: background work: transcription and agent runs (F15).

| Column | Type | Notes |
|---|---|---|
| `kind` | String | e.g. `process_segment` |
| `status` | String | `queued`, `running`, `done`, `failed` |
| `payload` | JSON | Inputs |
| `attempts` | Integer | Times started; failed for good after 3 (added in stage 0 step 4) |
| `error` | Text, nullable | The last error |
| `started_at`, `finished_at` | DateTime, nullable | |

A runner **claims** a job with `UPDATE … SET status = 'running' WHERE id = … AND status = 'queued'`; only one
runner's update can change the row, so no database-specific locking is needed (rule P6). Jobs still `running` after
30 minutes are treated as crashed and re-queued.

**`job_log`**: the agent log lines the side panel shows.

| Column | Type | Notes |
|---|---|---|
| `job_id` | Uuid → job | |
| `agent` | String | Planner, Tutor, Reviewer… |
| `kind` | String | `info`, `flag`, `fix`, `recheck`, `error` |
| `message` | Text | |

**`llm_call`**: every language-model call, for cost and quality tracking.

| Column | Type | Notes |
|---|---|---|
| `job_id` | Uuid → job, nullable | |
| `prompt_id`, `prompt_version`, `model` | String | |
| `input_tokens`, `output_tokens` | Integer | |
| `latency_ms` | Integer | |
| `cost_usd` | Float | Computed from the model's price |
| `ok` | Boolean | |

## 4. Indexes

| Table | Index | For |
|---|---|---|
| `attempt` | (`learner_id`, `answered_at`) | Rebuilding a Brain; history |
| `attempt` | (`item_id`) | Item quality |
| `concept` | unique (`course_id`, `normalized_name`) | No duplicate concepts |
| `item` | (`concept_id`, `status`) | Live items for a concept |
| `concept_state` | unique (`learner_id`, `concept_id`) | Brain reads |
| `job` | (`status`, `created_at`) | Picking up work |
| `job_log` | (`job_id`, `created_at`) | Showing progress |

## 5. Delete my data (F16)

In application code, in this order (P10): `attempt_exclusion` → `item_report` → `attempt` → `confusion` →
`concept_state` → `item` → `prerequisite` → `concept` → `segment` → `lecture` → `course` → `consent` → `learner`.
Items are per learner's segments, so they go too. Jobs and LLM call records keep no learning content; their
`payload` is cleared. One transaction per table in batches (P9).

## 6. Questions for review

1. Does every column make sense? Anything you'd add or remove?
2. Are you comfortable with **derived tables** (concept_state, confusion) being rebuildable rather than the source of
   truth?
3. Is it OK that **items stay per learner** (made from that learner's own lectures), rather than shared between
   learners on the same course? Sharing would save model cost later but raises copyright questions.
