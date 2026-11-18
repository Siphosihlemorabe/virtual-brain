# Tech stack: every tool, the alternatives, and why

Date: 18 November 2026. Status: **proposed**. Items marked *(agreed)* or *(in place)* are settled; the rest await
decisions (§6). When the deployment choice is agreed, `architecture.md` is updated to match.

Use this as the map of the codebase: what each tool does, why it was chosen, and what to study (§5).

## 1. Credits and the free plan

- AWS reported on 17 November: **free plan, $139.96 credits, plan end date 3 May 2027**. AWS's rules: the free plan
  lasts **6 months or until credits run out**, whichever is first. Then the project must **upgrade to the paid plan**
  (real billing) or it is suspended. *(To confirm in AWS Settings → Billing; Siphosihle mentioned 3 months.)*
- Design goal: near-zero monthly cost, so credits last and the bill stays tiny after the free plan.

## 2. The full stack

| Layer | Choice | Alternatives | Why this one | What it means for the app |
|---|---|---|---|---|
| Backend language | **Python 3.11** *(in place)* | TypeScript, Go | Whisper, FSRS and the Anthropic SDK are Python-first; legacy code is Python | Two languages: Python backend, TypeScript frontend |
| Web framework | **FastAPI** *(in place)* | Django, Flask, Litestar | Typed, fast; generates the API description the frontend client is built from | No built-in admin panel |
| Validation and settings | **Pydantic, pydantic-settings** *(in place)* | attrs, marshmallow | Same library as FastAPI; also validates the AI's JSON (AI rule 6) | One way to validate everything |
| Database (production) | **Aurora DSQL** (proposed, §3) | RDS PostgreSQL, Aurora Serverless v2, DynamoDB | Permanent free tier; serverless; no private network needed | Some PostgreSQL features missing |
| Database (local, tests) | **PostgreSQL 16 in Docker** | SQLite | Closest local match (DSQL has no local version) | Code stays within what DSQL supports, plus a smoke test against real DSQL |
| Database access | **SQLAlchemy 2.0 ORM + Alembic** *(agreed 18 Nov)*, with portability rules (`database.md` §2) | Plain SQL with psycopg 3, SQLAlchemy Core, SQLModel | Standard, typed; dialects for PostgreSQL, SQLite and **Aurora DSQL** (official AWS dialect `aurora-dsql-sqlalchemy`); switching databases is a setting plus a dialect | ORM guardrails stop hidden queries (`lazy="raise"`) |
| Background jobs | **SQS triggering Lambda** in AWS; in-process runner locally | Postgres jobs table (earlier plan), Celery + Redis | Pay per job, scales to zero; DSQL doesn't suit the Postgres locking queue | Job progress stored in the database either way |
| Transcription | **faster-whisper**, on Lambda in AWS | Amazon Transcribe (paid plan only), OpenAI Whisper API (data to the US) | Free, tested on this machine, data stays in the EU | About $0.10 of compute per lecture hour (estimate) |
| Language model | **Anthropic API**, a model per job *(agreed)* | Bedrock (no in-Region Claude in eu-north-1), Gemini, OpenAI, self-hosted | Quality, fits our checks | Learner text goes to Anthropic; the privacy notice says so |
| Learning maths | **py-fsrs** (memory); **own code** for BKT (mastery) | pyBKT | FSRS reference implementation; BKT is ~15 lines, tested by hand | We fit BKT parameters later from logged attempts |
| Login | **Amazon Cognito** | Auth0, Clerk, own | Free plan, AWS-native, shared by web app and extension | Hosted login pages, styled to match |
| Email | **Amazon SES** | Resend, SendGrid | Free plan, cheap | Needs a verified domain |
| Secrets | **SSM Parameter Store** (SecureString) | Secrets Manager | Standard parameters are free; Secrets Manager is about $0.40 per secret per month | Same security for our needs |
| Frontend | **React + TypeScript + Vite** *(agreed)* | Svelte, Vue | Most common skills; typed against the API | — |
| Data fetching | **TanStack Query** | Hand-written fetch | Caching, retries, loading states done properly | One more library |
| 3D brain | **three.js via react-three-fiber** | Plain three.js | The 3D scene as React components | Same engine as the legacy lab |
| Styling | **Tailwind CSS** | CSS modules, plain CSS | Consistent spacing and colours; works in the extension | Class names live in the markup |
| API client | **Generated** (openapi-typescript) | Hand-written | A breaking backend change fails the frontend build | Regenerate after API changes |
| Extension | **Chrome Manifest V3, built with Vite**; WXT compared in step 7 | — | MV3 is required for new Chrome extensions | Chrome and Edge first |
| Tests | **pytest, Vitest**; Playwright later | — | Standard per language | — |
| Code quality | **uv, ruff, mypy** *(in place)*; **ESLint, Prettier** | — | Fast, standard | CI runs all of them |
| CI | **GitHub Actions on the fork** *(agreed)* | AWS CodeBuild | Free allowance, standard | — |
| Infrastructure as code | **AWS CDK (Python)** | Terraform, SAM, CloudFormation | Same language as the backend; reviewable | Deploys are commands, not console clicks |
| Web hosting | **S3 + CloudFront** | Amplify Hosting | Pennies a month | — |
| Logs | **CloudWatch**, structured JSON logs | Sentry, Datadog | Included with AWS | Sentry later if needed |

## 3. The database

### 3.1 Which database

| Option | Monthly cost (rough) | Pros | Cons |
|---|---|---|---|
| **Aurora DSQL** (proposed) | **About $0**: permanent free tier of 100,000 compute units and 1 GB per month | Serverless; **reachable without a private network**, so Lambda needs no NAT gateway (about $34/month in eu-north-1); official SQLAlchemy dialect with Alembic support | Not full PostgreSQL: no triggers, no extensions, limits on rows changed per transaction, **one DDL statement per transaction, no `DROP COLUMN`**. JSON/JSONB supported since May–June 2026; foreign keys since August 2026; sequences since February 2026. No local version |
| RDS PostgreSQL (`db.t4g.micro`) | About $12 + storage | Full PostgreSQL, identical locally | Always on; Lambda would need a private network and a NAT gateway: **about $34 more per month** |
| Aurora Serverless v2 | Near $0 idle (scales to zero) | Full PostgreSQL | **About 15 s to wake** (30+ s after a day idle); same network issue as RDS |
| DynamoDB | Near $0 | Serverless, no network issue | Not relational; our data is relational |

**For our code, DSQL means:** UUID keys, small transactions, no triggers, one table change per migration, and
never dropping a column. These rules are written so the same code also runs on plain PostgreSQL or SQLite
(`database.md` §2). Fallback if something essential is missing: RDS + NAT.

### 3.2 How the code talks to the database

**Decided 18 November: SQLAlchemy 2.0 ORM + Alembic**, with portability rules so the database can be changed by
configuration (`database.md`). The options considered:

| Option | What the code looks like | Pros | Cons |
|---|---|---|---|
| **Plain SQL with psycopg 3** | SQL written out in full, in small repository functions; results mapped to Pydantic models | You see exactly what runs; best for learning SQL; DSQL limits are visible in the SQL itself | More code for mapping rows; we write a small migration runner (or use a tool like yoyo-migrations) |
| **SQLAlchemy Core** | Python query builder (`select(users).where(...)`), no ORM | Explicit; composable queries; works with Alembic migrations | A query language to learn on top of SQL |
| **SQLAlchemy ORM** | Python classes that load and save themselves | Least code for simple cases | Most hidden behaviour (lazy loading, sessions); hardest to understand line by line |
| SQLModel | ORM classes that are also Pydantic models | Less duplication | Same hidden behaviour as the ORM, fewer docs |

## 4. Deployment options

| | **A. Serverless** (proposed) | B. One server | C. Containers (earlier plan) |
|---|---|---|---|
| How | Lambda (API), SQS + Lambda (jobs, Whisper), DSQL, S3 + CloudFront | One Lightsail/EC2 server running the local Docker Compose setup | ECS Fargate (API + worker), RDS, load balancer |
| Cost at pilot scale (rough) | **About $0–5 / month** | About $20–25 / month (~4 GB for Whisper) | **About $40–50 / month** (load balancer ~$18, RDS ~$12, Fargate ~$9 + jobs) |
| Credits last | Easily | Yes | Barely |
| After the free plan | Pennies | ~$25 / month | ~$45 / month |
| Matches local? | Mostly (DSQL vs Postgres, Lambda vs local server) | Exactly | Closely |
| Maintenance | AWS | **You**: OS updates, backups, HTTPS | Mostly AWS |
| Scaling | Automatic | Manual | Automatic |
| Trade-offs | First request after idle ~0.5–1 s; Whisper's first job loads the model; more AWS services to learn | Single point of failure | Cost |

**Recommendation: A.** Solo, limited credits, no revenue yet: near-zero idle cost, nothing to patch, and it survives
the end of the free plan. **B is the fallback** if A proves too complex. Fargate, load balancer and Lightsail figures
are estimates, to be confirmed with AWS pricing tools before any deployment.

## 5. What to study, in build order

| When | Study | Why you need it | Where in the code |
|---|---|---|---|
| Now (steps 2–3) | **Python typing and Pydantic** | Every function is typed; Pydantic validates inputs and AI output | `backend/src/vb/` |
| Now | **FastAPI basics**: routes, dependencies, `TestClient` | The API | `backend/src/vb/main.py`, `core/health.py` |
| Now | **pytest** | Tests come before code | `backend/tests/` |
| Step 3 | **SQL and PostgreSQL**: tables, keys, indexes, transactions | The database (whatever library we pick) | `backend/src/vb/*/repository.py` (planned) |
| Step 3 | **Database migrations** | Changing tables safely | `backend/migrations/` (planned) |
| Step 3 | **Docker and Docker Compose** | Running Postgres locally | `compose.yaml` (planned) |
| Step 4 | **Background jobs and queues** (SQS concepts) | Transcription and agents run as jobs | `backend/src/vb/core/jobs.py` (planned) |
| Step 5 | **Anthropic API, structured outputs** | The AI layer | `backend/src/vb/llm/` (planned) |
| Slice 1 | **The learning maths**: BKT, FSRS | The Brain | `backend/src/vb/learning/` (planned) |
| Step 7 | **TypeScript, React, Vite, TanStack Query, Tailwind** | Web app and extension | `frontend/` (planned) |
| Slice 1 | **Chrome extensions (MV3)**: service worker, offscreen document, side panel | Capture and quiz | `frontend/apps/extension/` (planned) |
| Slice 1 | **three.js / react-three-fiber** | The 3D brain | `frontend/packages/brain3d/` (planned) |
| Stage 3 | **AWS**: Lambda, SQS, DSQL, Cognito, S3, CloudFront, IAM, CDK | Deployment | `infra/` (planned) |
| Always | **Git and GitHub Actions** | Commits, CI | `.github/workflows/` (planned) |

## 6. Decisions still needed

1. Deployment: A, B or C.
2. Database: Aurora DSQL with local PostgreSQL, or RDS PostgreSQL.
3. ~~Database access~~ **Decided: SQLAlchemy 2.0 ORM + Alembic**, portable (§3.2, `database.md`).
4. Confirm credits and plan end date.
5. Library choices: TanStack Query, Tailwind, react-three-fiber, openapi-typescript.

## Sources

- AWS free plan: https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/
- Aurora DSQL pricing: https://aws.amazon.com/rds/aurora/dsql/pricing/
- Aurora DSQL limitations: https://newsletter.simpleaws.dev/p/aurora-dsql-the-postgresql-compatible-database-that-will-break-your-app-and-how-to-fix-it ; https://hidekazu-konishi.com/entry/amazon_aurora_dsql_design_decision_guide.html
- Aurora DSQL dialect for SQLAlchemy: https://docs.aws.amazon.com/aurora-dsql/latest/userguide/SECTION_program-with-dsql-dialect-for-sqlalchemy.html ; https://github.com/awslabs/aurora-dsql-orms
- Aurora DSQL JSON / JSONB support: https://aws.amazon.com/about-aws/whats-new/2026/05/aurora-dsql-json-support/ ; https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-aurora-dsql-supports-jsonb/
- Aurora Serverless v2 scale to zero: https://dev.to/aws-builders/scaling-to-zero-with-amazon-aurora-serverless-v2-553n
- Lambda Web Adapter cold starts: https://rafrasenberg.com/fastapi-lambda/
- RDS and NAT gateway prices: https://www.bytebase.com/dbcost/rds/instance/db.t4g.micro/ ; https://outboundgateway.com/blogs/aws-nat-gateway-pricing/
