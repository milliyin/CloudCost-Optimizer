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

- Current stage: Stage 3 complete; Stage 4 waste detection is the next implementation target
- Last completed milestone: 2026-06-29 - Stage 1 auth, RBAC, and manual verification completed
- Known broken / in-progress things right now:
  - Stage 2 sync code has been verified for inventory and CloudWatch metric collection, but Cost Explorer data is still not returning usable spend rows from the sandbox account.
  - Stage 3 dashboard queries and UI are working with org-scoped data, including opt-in demo seeding, real-sync cleanup behavior, and role-aware admin controls.
  - Cost charts may legitimately be empty until Cost Explorer data becomes available for the organization's AWS account or the date range includes billable usage.
  - Resource inventory intentionally mixes inventory-only rows with EC2 metric-backed rows, so the table now labels telemetry availability instead of showing repeated `n/a` values for non-EC2 resources.
  - Stage 4 findings are still frontend-derived heuristics right now; they are not yet persisted backend findings with evidence records.

## 3. Architecture Summary

The repository now contains a FastAPI backend, a Vite + React frontend, and a
PostgreSQL service defined in Docker Compose. The backend exposes `/health`,
auth endpoints, organization endpoints, dashboard endpoints, admin-only test
endpoints, and a manual `POST /sync/run` endpoint. The data model includes
organizations and organization-specific AWS connections so synced AWS data is
scoped to a client workspace instead of one shared global dataset. The frontend
now includes an actual dashboard layer with summary cards, cost charts, trend
chart, resource table, and retained admin tools. See `docs/architecture.md` for
the high-level structure.

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

### 2026-07-01 - Existing organizations need admin-created teammates, not public re-registration

Once public registration was changed to create a brand-new organization, it no
longer made sense for a second user in the same client account to use that same
flow. We therefore added an admin-only teammate creation path inside the
organization dashboard instead of reopening public signup against existing org
names.

### 2026-07-01 - Resume dashboard work only after multitenant foundations landed

Once organizations and org-owned AWS connections existed, we resumed Stage 3
dashboard work against org-scoped endpoints instead of the old global sync
assumption. That keeps every chart, summary card, and resource table aligned
with the actual product direction.

### 2026-07-01 - Admins need in-app sync controls, not only curl commands

Once organizations started saving AWS connections through the dashboard, it no
longer made sense to force admins back to the terminal just to trigger a sync.
We therefore added a dashboard card with a manual sync button and inline sync
summary so org admins can run and inspect their own workspace syncs directly in
the UI.

### 2026-07-02 - Dashboard API routes must all proxy through Vite in local dev

Once Stage 3 introduced `/dashboard/*` endpoints, the Vite dev proxy needed to
forward those routes just like `/auth`, `/organization`, and `/sync`. Without
that proxy entry, the frontend received HTML from the dev server instead of API
JSON, which surfaced as a JSON parse error in the dashboard.

### 2026-07-02 - Stage 3 side panels need explicit grid spans

The first dashboard grid pass gave the main summary/chart cards explicit spans,
but the workspace/settings/sync/teammate panels inherited the default 1-column
behavior in the 12-column layout. Adding a dedicated side-panel span keeps
those admin tools readable on desktop without collapsing the main data views.

### 2026-07-02 - Demo workspaces should use clearly seeded org-scoped data

Cost Explorer can stay empty for a while on fresh AWS accounts, but the product
still needs a convincing Stage 3 demo path. For that case, we are adding an
admin-triggered org-scoped demo seed that clears only the current
organization's synced tables, removes its saved AWS connection if needed, and
loads obviously simulated spend, resource, and metric rows instead of pretending
they came from AWS.

### 2026-07-02 - The visual system should follow the Cloud Intelligence design brief

The earlier UI was functional but drifted from the product reference: it used a
glassmorphism-style container, green-heavy accents, and a centered card shell.
The design brief in `design/DESIGN.md` instead calls for an indigo-led FinOps
dashboard with fixed navigation, white data cards, subtle tonal layering, and a
more executive, high-density information hierarchy. The frontend is therefore
being restyled around that system rather than incrementally polishing the older
look.

### 2026-07-02 - Demo data must never silently coexist with real sync data

The demo seed is useful for presentation mode, but it should be explicitly
loaded by the admin and easy to discard. The sync flow is therefore being
updated so a real `Run sync now` clears any demo-seeded rows first, then fetches
 live AWS data. If no live AWS data is returned, the dashboard should stay empty
 rather than silently falling back to old demo rows.

### 2026-07-05 - Inventory coverage should match the resources users test with

By this point the dashboard was already showing EC2, EBS, Elastic IP, RDS, and
load balancer inventory, but a newly launched Lambda function did not appear
because Lambda was not part of the Stage 2 inventory collector yet. Since users
will naturally validate the app with lightweight AWS resources like Lambda, the
inventory sync is being extended to include Lambda functions in the same
organization-scoped resource table.

### 2026-07-05 - Mixed inventory tables should explain telemetry availability

Once Lambda and other non-EC2 resources started appearing in the shared
inventory table, the EC2-specific CPU/network columns made the UI look broken
because many rows naturally showed `n/a`. Instead of pretending every resource
has the same metrics, the dashboard now adds a telemetry label and uses `-` for
non-applicable values so mixed resource types read as intentional.

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

### 2026-07-01 - Public registration no longer supported adding users to an existing organization

- Symptom:
  - After multitenancy was introduced, creating `admin` in `org1` worked, but trying to create a `viewer` in `org1` through the public registration screen failed because the organization name already existed.
- Root cause:
  - Public registration intentionally creates new organizations and rejects duplicate organization names, but there was no same-org teammate onboarding path yet.
- Fix:
  - Added an admin-only teammate creation endpoint and dashboard form so organization admins can create additional users inside their existing workspace.
- How to verify it's still fixed:
  - Log in as an organization admin, create a teammate from the dashboard, then log in as that teammate and confirm both users belong to the same organization.

### 2026-07-02 - Dashboard loaded HTML instead of JSON for new Stage 3 endpoints

- Symptom:
  - The dashboard showed a red parse error like `Unexpected token '<'` and admin panels rendered with a broken layout.
- Root cause:
  - `/dashboard/*` was missing from the Vite proxy, so requests hit the frontend dev server instead of FastAPI.
  - The Stage 3 right-side admin cards also lacked explicit grid span classes in the 12-column layout.
- Fix:
  - Added the `/dashboard` proxy entry in `frontend/vite.config.js`.
  - Added `side-panel-card` classes and matching CSS grid spans for workspace/admin tool cards.
- How to verify it's still fixed:
  - Rebuild the frontend, reload the dashboard, and confirm the red JSON parse error disappears.
  - Confirm the workspace, AWS connection, manual sync, and teammate cards render at readable widths.

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

### 2026-07-01 - Admin-only teammate onboarding
- What changed:
  - Added `POST /auth/teammates` as an admin-only API for creating users inside the current organization.
  - Added a dashboard form so org admins can create viewer or admin teammates without public re-registration.
- Why:
  - Multiple users in the same client organization need a secure same-org onboarding path after public signup was repurposed to create new organizations.
- Files touched:
  - Auth API, auth schemas, dashboard UI, and project memory.
- Manual test performed:
  - Not yet in this session; manual verification is pending.
- Anything the next session needs to know:
  - The correct flow is now: public registration creates a new org, then admins create additional teammates inside that org.

### 2026-07-01 - Dashboard manual sync controls
- What changed:
  - Added an admin-only `Run sync now` button to the dashboard.
  - Added inline sync feedback showing message, counts, and warnings directly in the UI.
- Why:
  - Organization admins should be able to test and operate their own sync flow without dropping to `curl`.
- Files touched:
  - Dashboard UI, styling, and project memory.
- Manual test performed:
  - Confirmed the dashboard button ran sync successfully for `org1`.
  - Confirmed the UI showed `resources: 2`, `metric samples: 3`, and the expected Cost Explorer warm-up warning.
- Anything the next session needs to know:
  - The next multitenant verification step is to repeat the same flow in `org2` and confirm the success message names `org2`.

### 2026-07-01 - Stage 3 dashboard foundation on multitenant data
- What changed:
  - Added org-scoped backend dashboard endpoints for summary, by-service, by-region, trend, and resources.
  - Added a real dashboard UI with spend summary, pie charts, trend chart, date filters, resource table, loading states, and empty states.
  - Kept organization admin tools for AWS connection management, manual sync, and teammate creation inside the dashboard layout.
- Why:
  - Resume Stage 3 with a dashboard that reflects the correct multitenant data model instead of the earlier shared-data shell.
- Files touched:
  - Dashboard API/service/schema files, frontend dashboard page and styling, package dependencies, and project memory/docs.
- Manual test performed:
  - Backend compile pass only so far; manual dashboard verification is still pending.
- Anything the next session needs to know:
  - Rebuild the frontend to install `recharts`.
  - Empty cost charts are expected until Cost Explorer data exists for that organization.

### 2026-07-02 - Stage 3 dashboard follow-up fixes
- What changed:
  - Added `/dashboard` to the Vite proxy configuration.
  - Added explicit side-panel grid sizing for workspace and admin tool cards.
- Why:
  - Fix a local-dev API routing bug and make the Stage 3 layout readable.
- Files touched:
  - Frontend Vite config, dashboard page classes, styles, and project memory.
- Manual test performed:
  - The issue was reproduced from the dashboard screenshot and fixed in code; browser re-verification is still pending for this exact follow-up patch.
- Anything the next session needs to know:
  - If the dashboard ever shows HTML/JSON parse errors again, check the Vite proxy coverage first.

### 2026-07-05 - Stage 3 multitenant dashboard polish and broader AWS inventory
- What changed:
  - Expanded org-scoped AWS inventory collection to include Lambda, S3, DynamoDB, SQS, SNS, ECS, ECR, and API Gateway alongside the existing EC2, EBS, Elastic IP, RDS, and load balancer coverage.
  - Added explicit org-scoped demo seed loading plus real-sync cleanup so demo rows never silently coexist with live AWS data.
  - Redesigned the frontend around the Cloud Intelligence shell with fixed navigation, operations controls, findings, cleaner filters, and mixed-resource telemetry labels in the inventory table.
  - Added admin-only teammate creation, org AWS connection management, persistent sessions, and org-scoped sync controls into the dashboard experience.
- Why:
  - Complete the interactive Stage 3 dashboard around the actual multitenant product direction and make the real AWS validation path usable even while Cost Explorer remains empty.
- Files touched:
  - Backend org/sync/AWS service files, frontend dashboard/auth files, styles, docs, and project memory.
- Manual test performed:
  - Confirmed admin login, viewer login, and same-org teammate access work.
  - Confirmed `org1` sync loads real EC2, EBS, and Lambda inventory from AWS.
  - Confirmed viewer access works and admin-only controls are hidden from viewers.
  - Confirmed the resource inventory table now handles mixed resource types without a wall of misleading `n/a` values.
- Anything the next session needs to know:
  - Stage 4 should replace the current frontend-only findings cards with stored backend findings and evidence-backed detection rules.
  - Cost Explorer messaging may need refinement because the current warning still mentions the initial 24-hour warm-up pattern even when AWS simply returns no usable spend yet.

## 8. Manual Test Checklist Status

- Stage 0: base Docker/frontend flow confirmed during local setup; AWS setup still being completed separately for Stage 2 readiness
- Stage 1: passed on 2026-06-29
- Stage 2: partially verified on 2026-07-01; resource inventory and metrics confirmed, waiting on Cost Explorer readiness for full gate coverage
- Stage 3: passed for multitenant dashboard, real inventory sync, viewer/admin separation, demo seeding behavior, and mixed-resource inventory handling; spend charts remain dependent on AWS Cost Explorer data availability
- Multitenancy pivot: landed; org-scoped auth, AWS connections, sync data, teammate creation, and dashboard views are implemented

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
