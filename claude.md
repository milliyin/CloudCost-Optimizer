# CloudCost Optimizer - Project Memory (claude.md)

> Read this entire file before making any changes. This file is updated after every commit.
>
> This file exists so future Claude Code sessions start with full context. Read it entirely before making any changes. If a bug occurs, check this file first to see whether it has already been encountered and fixed, and how - do not re-solve a problem that's already documented here. If a decision seems strange (e.g. "why is there a `--no-verify` flag here", "why didn't we use Mongo"), the reasoning should be in this file.

## 1. Project Overview

CloudCost Optimizer is a solo portfolio project for exploring AWS cost analysis
and optimization workflows in a safe, demoable way. The end goal is a SaaS-like
dashboard that connects to a sandbox AWS account, ingests billing and resource
data, identifies wasteful resources, proposes cost-saving actions, raises
budget alerts, and forecasts future spend.

The project is being built stage by stage with mandatory manual test gates after
each milestone. Safety is a core product requirement: the system may recommend
AWS actions, but it must never directly stop, terminate, resize, or delete AWS
resources.

## 2. Current Status

- Current stage: Stage 2/Architecture Pivot - Multi-tenant foundation in progress
- Last completed milestone: 2026-06-29 - Stage 1 auth, RBAC, and manual verification completed
- Known broken / in-progress things right now:
  - Session persistence is no longer memory-only; the app is being updated to keep users signed in across refreshes.
  - Stage 2 sync code has been partially verified with a real admin-triggered sync.
  - Cost Explorer was only recently enabled in the sandbox account, so cost data may still be unavailable for up to about 24 hours.
  - A multitenant migration is in progress so organizations can own separate AWS connections and isolated synced datasets.

## 3. Architecture Summary

The repository now contains a FastAPI backend, a Vite + React frontend, and a
PostgreSQL service defined in Docker Compose. The backend exposes `/health`,
auth endpoints, organization endpoints, admin-only test endpoints, and a manual
`POST /sync/run` endpoint. The data model now includes organizations and
organization-specific AWS connections so synced AWS data can be scoped to a
client workspace instead of one shared global dataset. APScheduler remains
wired into FastAPI lifespan for background sync execution. See
`docs/architecture.md` for the high-level structure.

## 4. Key Decisions & Why (running ADR log)

### 2026-06-27 - Vite over Create React App

We chose Vite because the current Vite guide presents `npm create vite@latest`
as the default scaffolding flow for React-style frontend setup, and it is the
modern low-friction option for a portfolio project. This keeps the frontend
setup current and easier to explain than using the older Create React App path.

### 2026-06-27 - FastAPI + SQLAlchemy async stack from the start

FastAPI remains a strong fit for a readable Python API, and SQLAlchemy 2.x
continues to document asyncio support directly in the official 2.0 docs. Using
the async-friendly stack from Stage 0 keeps later AWS and database integration
work consistent with the project prompt.

### 2026-06-27 - Pin stable dependency versions in Stage 0

The prompt explicitly warns against guessing library versions. Stage 0 pins the
versions verified during setup so the environment is repeatable and later
sessions can see what was chosen and why.

### 2026-06-29 - PyJWT and pwdlib chosen for Stage 1 auth

Before implementing authentication, we checked the current FastAPI security
docs. The official tutorial now uses `PyJWT` and `pwdlib[argon2]`. Those docs
also note that `passlib` is better suited when you need legacy-hash
compatibility. Because the prompt explicitly asked us to verify whether
`passlib[bcrypt]` was still the right recommendation, we followed the current
documented FastAPI approach instead of defaulting to an older stack.

### 2026-06-29 - Access and refresh tokens are memory-only in the frontend

The frontend intentionally stores tokens only in React state, not in
`localStorage`. This means a browser refresh ends the session. We accepted that
tradeoff because it reduces exposure to token theft via XSS and keeps the
portfolio security story straightforward.

### 2026-06-29 - Portfolio registration allows direct role selection

Stage 1 allows choosing `admin` or `viewer` during registration because the
project prompt explicitly allows that shortcut for a portfolio build. If this
project were production-facing, admin-role assignment would be gated behind an
existing admin or an out-of-band provisioning flow.

### 2026-07-01 - Treat fresh Cost Explorer accounts as a first-class Stage 2 case

AWS documents that Cost Explorer can take about 24 hours to start returning
data after first enablement. Since the sandbox account is newly configured, the
sync service is designed to degrade gracefully: Cost Explorer availability
problems are surfaced as warnings while inventory and CloudWatch collection can
still proceed.

### 2026-07-01 - Use DB uniqueness plus PostgreSQL upserts for sync idempotency

Stage 2 may run on a schedule and can also be triggered manually through the
demo UI/API. To avoid duplicate records on repeated syncs, the ingestion tables
use natural-key uniqueness constraints and `ON CONFLICT DO UPDATE` upserts.

### 2026-07-01 - Pivot to multitenancy before building the full dashboard

During Stage 3 planning we checked the actual Stage 1/2 code and confirmed the
app was only single-tenant with shared AWS credentials from `.env`. Since the
product goal is to let multiple clients use the website and see only their own
AWS data, we paused the dashboard work and introduced organizations,
organization-owned AWS connection records, tenant-scoped sync data, and
organization-aware sync execution first.

### 2026-07-01 - Persist frontend sessions at the user's request

The original Stage 1 design intentionally logged users out on refresh because
tokens lived only in memory. The product direction changed and the user asked
for sessions to survive refresh, so the frontend now persists session data in
browser storage. This improves usability but increases the importance of XSS
hardening later.

## 5. Environment Variables / Secrets Reference

- `DATABASE_URL`
  - Purpose: async SQLAlchemy connection string for the application database
  - Where to get it: local Docker Compose Postgres service in Stage 0, or your
    deployment database later
- `JWT_SECRET_KEY`
  - Purpose: signing key for JWT access and refresh tokens introduced in Stage 1
  - Where to get it: generate a long random secret locally; never commit it
- `AWS_ACCESS_KEY_ID`
  - Purpose: programmatic access key for the dedicated AWS IAM user used by the app
  - Where to get it: IAM user such as `cloudcost-app`, created in the AWS console
- `AWS_SECRET_ACCESS_KEY`
  - Purpose: secret key paired with `AWS_ACCESS_KEY_ID`
  - Where to get it: generated with the IAM access key; store only in local `.env`
- `AWS_REGION`
  - Purpose: default AWS region for CloudWatch and resource inventory operations
  - Where to get it: choose the sandbox region you plan to test with, such as `us-east-1`
- `AWS_CONNECTION_ENCRYPTION_KEY`
  - Purpose: dedicated Fernet key for encrypting organization-specific AWS credentials at rest
  - Where to get it: generate locally with `Fernet.generate_key()`; if omitted, the app derives a fallback key from `JWT_SECRET_KEY`
- `AWS_SYNC_INTERVAL_HOURS`
  - Purpose: scheduler interval for automatic Stage 2 sync jobs
  - Where to get it: set locally; `6` is the current default
- `AWS_COST_LOOKBACK_DAYS`
  - Purpose: number of days of Cost Explorer data requested per sync
  - Where to get it: set locally; `30` is the current default
- `AWS_METRIC_LOOKBACK_HOURS`
  - Purpose: trailing CloudWatch window per EC2 instance sync
  - Where to get it: set locally; `24` is the current default
- `AWS_METRIC_PERIOD_SECONDS`
  - Purpose: CloudWatch aggregation period for EC2 metric samples
  - Where to get it: set locally; `3600` is the current default
- `ENVIRONMENT`
  - Purpose: runtime environment selector for local development vs later deployment behavior
  - Where to get it: set manually, usually `development` for local work

## 6. Known Issues & Fixes Log (bug journal)

### 2026-06-29 - Postgres 18 container failed to start after Stage 1 changes

- Symptom:
  - `postgres` exited during `docker compose up --build` with the Postgres 18 data-directory layout warning about `/var/lib/postgresql/data`.
- Root cause:
  - The compose file was still mounting the pre-18 path `/var/lib/postgresql/data`, but the current `postgres:18.4-bookworm` image expects the parent directory mount layout under `/var/lib/postgresql`.
- Fix:
  - Changed the compose volume mount to `postgres_data:/var/lib/postgresql`.
  - Local recovery requires recreating the Docker volume with `docker compose down -v` before starting again.
- How to verify it's still fixed:
  - Run `docker compose down -v` once, then `docker compose up --build`.
  - Confirm `postgres` remains healthy instead of exiting with the 18+ layout warning.

### 2026-06-29 - Alembic startup migration failed because enum type already existed

- Symptom:
  - Backend startup failed during `alembic upgrade head` with `psycopg.errors.DuplicateObject: type "userrole" already exists`.
- Root cause:
  - The migration created the `userrole` enum explicitly and the table creation path also attempted to create it again through the SQLAlchemy enum column definition.
- Fix:
  - Updated the Alembic migration to create the enum once with an explicit PostgreSQL enum definition and use `create_type=False` on the table column enum binding.
- How to verify it's still fixed:
  - Re-run `docker compose up --build` after the migration change.
  - Confirm Alembic completes `upgrade -> 20260629_0001` without the duplicate enum error and the backend stays up.

### 2026-06-29 - User registration failed because enum values were written in the wrong case

- Symptom:
  - `POST /auth/register` returned `500`, and Postgres logged `invalid input value for enum userrole: "ADMIN"`.
- Root cause:
  - SQLAlchemy's enum mapping was persisting the Python enum member names (`ADMIN`, `VIEWER`) instead of the intended string values (`admin`, `viewer`) expected by the PostgreSQL enum type.
- Fix:
  - Updated the `User.role` column enum mapping to use `values_callable` so SQLAlchemy persists the enum `.value` strings.
- How to verify it's still fixed:
  - Rebuild or restart the backend after the code change.
  - Register both an `admin` and `viewer` user and confirm each request returns `201` instead of `500`.

### 2026-07-01 - Fresh Cost Explorer accounts may return no cost data during Stage 2

- Symptom:
  - Cost Explorer requests can fail or return no usable billing data shortly after first enablement.
- Root cause:
  - AWS documents that new Cost Explorer setups can take about 24 hours to begin serving cost and usage data.
- Fix:
  - Stage 2 sync translates Cost Explorer availability failures into human-readable warnings instead of crashing the whole sync.
- How to verify it's still fixed:
  - Trigger `POST /sync/run` before Cost Explorer is ready.
  - Confirm the response includes a warning about Cost Explorer availability while the rest of the sync can still proceed where possible.

### 2026-07-01 - Initial Stage 2 sync returned zero resources and metrics

- Symptom:
  - `POST /sync/run` completed successfully but returned `resources_synced: 0` and `metric_samples_synced: 0`.
- Root cause:
  - The current sandbox region likely has no EC2/RDS/EBS/EIP/ELB resources yet, so inventory collection has nothing to persist and CloudWatch has no EC2 instances to query.
- Fix:
  - No code fix required at this point. Create one or more lightweight sandbox resources in the configured `AWS_REGION` and rerun sync.
- How to verify it's still fixed:
  - Create at least one EC2 instance or other supported resource in the configured region.
  - Re-run `POST /sync/run` and confirm `resources_synced` becomes non-zero.

### 2026-07-01 - Resource inventory sync failed when AWS payloads contained datetimes

- Symptom:
  - `POST /sync/run` returned `500 Internal Server Error` after a sandbox EC2 instance was launched.
- Root cause:
  - The resource inventory code attempted to `json.dumps()` AWS attachment metadata directly, but boto3 payloads can contain Python `datetime` objects that are not JSON serializable by the default encoder.
- Fix:
  - Added a safe JSON helper that serializes nested AWS objects with `default=str` before storing them in `tags_json`.
- How to verify it's still fixed:
  - Rebuild the backend and rerun `POST /sync/run` after launching an EC2 instance.
  - Confirm the sync completes without a JSON serialization traceback and `resources_synced` becomes non-zero.

### 2026-07-01 - Single-tenant AWS settings blocked real multi-client usage

- Symptom:
  - Multiple users could log into the same app, but they all pointed at the same AWS account because the sync layer used one global credential set from `.env`.
- Root cause:
  - Stage 2 originally modeled AWS configuration as application-wide settings instead of organization-owned data.
- Fix:
  - Added `organizations`, `aws_connections`, tenant ownership on synced tables, organization-aware sync execution, and a frontend path for admins to save organization-specific AWS credentials.
- How to verify it's still fixed:
  - Register a new organization, save a different AWS connection for it, and confirm sync uses that organization's settings instead of the legacy global fallback.

## 7. Change Log (one entry per commit)

### 2026-06-27 - Stage 0 bootstrap scaffold
- What changed:
  - Initialized git.
  - Added backend, frontend, docs, Docker Compose, `.env.example`, and `claude.md`.
  - Implemented a minimal FastAPI `/health` endpoint and a frontend page that fetches it.
- Why:
  - Establish the project foundation required by Stage 0.
- Files touched:
  - Root scaffolding, backend app files, frontend app files, Docker files, docs, and project memory.
- Manual test performed:
  - None yet in this session; manual test gate is still pending.
- Anything the next session needs to know:
  - Read this file first, then run the Stage 0 manual test gate before starting Stage 1.

### 2026-06-29 - Stage 1 auth and RBAC implementation
- What changed:
  - Added SQLAlchemy user model, Alembic migration, async DB session handling, JWT helpers, auth schemas, and auth dependencies.
  - Added `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me`, and `/auth/admin-check`.
  - Added slowapi-based login rate limiting.
  - Replaced the Stage 0 landing page with login/register screens, a protected dashboard shell, and a fetch wrapper that retries once after refresh.
  - Fixed Postgres 18 volume mount compatibility, Alembic enum creation, and enum value serialization bugs found during manual testing.
- Why:
  - Implement the Stage 1 authentication and authorization flow needed before the AWS dashboard stages.
- Files touched:
  - Backend auth, DB, and Alembic files; frontend routing/auth files; docs and project memory.
- Manual test performed:
  - Registered admin and viewer users successfully.
  - Logged in successfully and verified `/auth/me`.
  - Confirmed admin user received `200` from `/auth/admin-check`.
  - Confirmed viewer user was blocked from admin-only route with `403` / "Insufficient role".
  - Confirmed browser refresh signs the user out as documented.
  - Confirmed repeated failed logins trigger `429 Too Many Requests`.
- Anything the next session needs to know:
  - Tokens are memory-only by design, so refresh should log the user out unless that behavior is intentionally changed later.
  - If Postgres fails with an 18+ volume-layout warning, recreate the Docker volume after checking Section 6.
  - If Alembic fails with `type "userrole" already exists`, verify the enum creation fix in Section 6 is present.
  - If registration fails with uppercase enum values, verify the `values_callable` enum mapping fix in Section 6 is present.

### 2026-07-01 - Stage 2 ingestion foundation
- What changed:
  - Added boto3/botocore, tenacity, and APScheduler dependencies.
  - Added ingestion tables for cost records, cloud resources, and metric samples with Alembic migration support.
  - Added AWS service modules for Cost Explorer, CloudWatch, and resource inventory.
  - Added PostgreSQL upsert-based sync orchestration plus an admin-only `POST /sync/run` endpoint.
  - Added a background scheduler hook for periodic syncs.
- Why:
  - Implement the AWS ingestion layer required before the dashboard and waste-detection stages.
- Files touched:
  - Backend config, models, migration files, AWS services, sync services, API routes, docs, and project memory.
- Manual test performed:
  - Logged in as admin and called `POST /sync/run` successfully.
  - Confirmed the response handled fresh Cost Explorer setup gracefully with a warning instead of a crash.
  - Observed `cost_records_synced: 0`, `resources_synced: 0`, `metric_samples_synced: 0`, and `forecast_points: 0` on the initial sync.
  - After launching a sandbox EC2 instance and fixing JSON serialization, reran `POST /sync/run` successfully.
  - Observed `resources_synced: 2` and `metric_samples_synced: 3` with the Cost Explorer warm-up warning still present.
- Anything the next session needs to know:
  - Cost Explorer may still be warming up in the sandbox account.
  - Sync should be tested first with the admin-only `/sync/run` endpoint before relying on the scheduler.
  - The next meaningful verification step is to add at least one sandbox resource in the configured region and rerun sync.
  - If sync crashes while inventory is non-empty, check Section 6 for the AWS datetime JSON serialization fix.

### 2026-07-01 - Multitenant foundation and persistent sessions
- What changed:
  - Added organizations, organization-specific AWS connection storage, tenant ownership columns on synced tables, and a multitenant migration.
  - Updated auth tokens and `/auth/me` responses to include organization context.
  - Added organization endpoints for reading workspace context and saving AWS credentials.
  - Switched frontend auth state to persist across refresh and updated registration to create an organization workspace.
- Why:
  - The product goal requires multiple client organizations to use the app without sharing data or AWS credentials.
- Files touched:
  - Backend models, migrations, auth/sync/org APIs, AWS credential handling, frontend auth/session files, and docs/project memory.
- Manual test performed:
  - Code compile pass only so far; manual multitenant verification is still pending.
- Anything the next session needs to know:
  - Existing tokens from before the subject-format change will no longer be valid; re-login is expected.
  - Organizations without saved AWS credentials will now receive a clear warning instead of attempting a broken sync.

## 8. Manual Test Checklist Status

- Stage 0: base Docker/frontend flow confirmed during local setup; AWS setup still being completed separately for Stage 2 readiness
- Stage 1: passed on 2026-06-29
- Stage 2: partially verified on 2026-07-01; resource inventory and metrics confirmed, waiting on Cost Explorer readiness for full gate coverage
- Multitenancy pivot: implementation in progress as of 2026-07-01; manual verification pending

## 9. AWS Account / Sandbox Notes

- Cost Explorer must be enabled manually in the AWS Cost Management console.
- AWS documents that current-month Cost Explorer data becomes available in about
  24 hours after enablement, with additional historical processing taking longer.
- AWS documents that IAM access to Billing and Cost Management console pages is
  controlled by the root-user-only Activate IAM Access setting, but AWS also
  notes that this setting does not control access to the Billing and Cost
  Management SDK APIs themselves. Keep that distinction in mind when Stage 2
  service integrations are implemented.
- The sandbox now has Cost Explorer enabled, but it was enabled recently enough
  that Stage 2 should expect transient "data not ready yet" behavior.
- Initial manual sync result on 2026-07-01:
  - `cost_records_synced: 0`
  - `resources_synced: 0`
  - `metric_samples_synced: 0`
  - `forecast_points: 0`
  - warning: Cost Explorer data not available yet
- Follow-up sync after launching EC2 on 2026-07-01:
  - `cost_records_synced: 0`
  - `resources_synced: 2`
  - `metric_samples_synced: 3`
  - `forecast_points: 0`
  - warning: Cost Explorer data not available yet
- Multitenancy note:
  - The legacy sandbox data belongs to the default backfilled organization until separate organization-specific AWS connections are configured.
