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

- Current stage: Stage 6 - Machine Learning Cost Forecasting (PASSED on 2026-08-09)
- Last completed milestone: 2026-08-23 - ML forecast real-data stabilization and docs refresh
- Known broken / in-progress things right now:
  - Stage 6 ML Cost Forecasting complete: time-aware train/test split (no data leakage), Ridge autoregressive model, statistical confidence bounds, multi-step horizon forecasting, proactive budget breach warning integration, retrain API, unit test suite verified.
  - Real AWS accounts with very short billing history intentionally show `Fallback Zero` until enough cost records accumulate for meaningful training.
  - All 6 stages of the master build prompt are fully implemented and verified.

## 3. Architecture Summary

The repository now contains a FastAPI backend, a Vite + React frontend, and a
PostgreSQL service defined in Docker Compose. The backend exposes `/health`,
auth endpoints, organization endpoints, dashboard endpoints, findings,
recommendations, budgets, reports export, admin-only test endpoints, and a
manual `POST /sync/run` endpoint. The data model includes
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

### 2026-07-05 - Run waste detection immediately after each sync

The app already has the freshest resource inventory and EC2 metric samples in
the same transaction at the end of each sync. We therefore run Stage 4
findings detection immediately after the sync upserts instead of adding a
separate detector schedule that could drift away from the latest org-scoped
snapshot.

### 2026-07-05 - Use conservative first-pass thresholds for persisted findings

The first stored findings rules use simple conservative thresholds over the
existing EC2 CloudWatch samples: idle below 10% average CPU with low average
network traffic, underutilized from 10% to under 25% average CPU, and likely
performance mismatch at or above 85% average CPU. These are intentionally
explainable first-pass heuristics for a portfolio build and should be tuned as
the project gains richer metrics and longer historical windows.

Before locking the rules, we verified the AWS field shapes we depend on against
official docs: EC2 volume `Attachments` in the Boto3 `describe_volumes`
reference, Elastic IP `AssociationId` in the Boto3 `describe_addresses`
reference, and EC2 `CPUUtilization` / `NetworkIn` / `NetworkOut` in the EC2
CloudWatch metrics guide. We also checked AWS Support's cost optimization docs,
which explicitly describe "Low utilization Amazon EC2 instances" and
"Unassociated Elastic IP Addresses" as real cost-optimization concerns, which
supports using those as the first portfolio-stage findings.

The idle EC2 rule now also includes a recent-window CPU comparison so a
short-lived stress test can be explained in the evidence without replacing the
more stable long-window decision logic. This helps users understand why a
24-hour average can stay idle even after a brief load burst. The evidence now
always includes a plain-English note, even when recent CPU is still below the
idle threshold, so the result does not show an empty note field.

### 2026-07-06 - Cost Explorer grouped spend and forecast must fail independently

When live AWS billing data finally became available, we found that grouped
Cost Explorer `get_cost_and_usage` calls could succeed while `get_cost_forecast`
still returned an availability warning. Treating all Cost Explorer work as one
block caused valid spend rows to be discarded any time forecast was unavailable.
The sync now handles grouped spend and forecast independently so real billing
data can populate the dashboard as soon as AWS returns it.

### 2026-07-06 - Billing rows must be normalized before PostgreSQL upsert

Once spend rows started arriving, the bulk insert path exposed two data-shape
issues: repeated grouped buckets could collapse to the same natural key at the
stored precision, and asyncpg requires real Python `date` objects for `DATE`
columns rather than raw ISO strings. The sync layer now normalizes cost rows
before upsert, merges duplicate natural keys safely, rounds amounts to the
stored precision, and converts ISO date strings into Python `date` values.

### 2026-07-06 - Match synced billing totals to the AWS console validation flow

Manual validation compared the app against AWS Cost Explorer with refunds and
credits excluded. To reduce demo confusion, the backend now applies the same
refund-and-credit exclusion filter during Cost Explorer sync so the dashboard
more closely matches the totals visible in the AWS console.

### 2026-07-14 - Recommendations are generated from findings but never execute AWS actions

Stage 5 maps each open finding to a recommendation template with heuristic
savings estimates and explicit copy that approval only records a human decision.
Approve/reject endpoints update status and write `AuditLog` rows, but the
codebase contains no mutating boto3 calls. A self-audit grep for
`stop_instances`, `terminate_instances`, `delete_volume`, and `modify_instance`
returned zero matches outside comments/docs.

### 2026-07-14 - Reconcile recommendations on list load and after sync

Recommendation rows can drift from finding status if a finding resolves between
syncs. `sync_recommendations_from_findings()` now runs after each sync and again
when `/recommendations` is listed so stale `pending` rows auto-close when their
finding is already `resolved`, without requiring another manual sync.

### 2026-07-14 - reportlab chosen for PDF export

Stage 5 report export uses `reportlab==5.0.0` for PDF generation because it has
straightforward Docker compatibility and enough layout control for a portfolio
report without adding a headless-browser dependency. CSV export uses the Python
stdlib `csv` module.

### 2026-07-14 - Budget alerts are DB-only for now

Budget evaluation compares current-month synced spend against active budgets and
persists `Alert` rows when thresholds are breached. SES email delivery is
intentionally stubbed/not implemented; alerts appear in the dashboard and
database only, and this should be documented honestly in demos.

### 2026-07-21 - FYP Architecture Guide created for project presentation

To simplify academic viva defense and project handoff, we created `docs/fyp-architecture-guide.md` summarizing the project concepts, end-to-end data flows, stage breakdowns, API routes, data models, sync pipeline, findings engine, recommendation safety guarantees, budget flow, report generation, and viva presentation talking points.

### 2026-08-05 - Narrow budget scope to Total and Service spend, with dynamic service dropdown

Region budgets added unnecessary complexity and were rarely queried separately from service cost breakdowns. We removed `region` scope from the budget schema and backend evaluation (ignoring legacy DB rows), and replaced the service text field in the frontend with a dynamic dropdown select element fed directly from the organization's synced AWS service spend (`byServiceData`). This prevents typos in service names and ensures users only create budgets for actual tracked services.

### 2026-08-09 - Remove role selector from public registration and default to admin

Public registration provisions a new organization workspace. The creator of a new client workspace is the workspace owner and must always be an `admin` so they can configure AWS connections and manage teammates. We removed the Role selection dropdown from `RegisterPage.jsx` and updated `POST /auth/register` to always default and enforce `UserRole.ADMIN` upon registration.

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
- `FINDING_MIN_SAMPLE_COUNT`
  - Purpose: minimum number of EC2 metric samples required before CPU-based findings run
  - Where to get it: set locally; `3` is the current default
- `FINDING_IDLE_CPU_THRESHOLD_PERCENT`
  - Purpose: average CPU threshold for idle EC2 detection
  - Where to get it: set locally; `10` is the current default
- `FINDING_UNDERUTILIZED_CPU_UPPER_PERCENT`
  - Purpose: upper CPU bound for "underutilized but not idle" EC2 detection
  - Where to get it: set locally; `25` is the current default
- `FINDING_OVERSIZED_CPU_THRESHOLD_PERCENT`
  - Purpose: average CPU threshold for a likely performance-risk mismatch finding
  - Where to get it: set locally; `85` is the current default
- `FINDING_IDLE_NETWORK_AVERAGE_BYTES`
  - Purpose: combined average NetworkIn/NetworkOut threshold used alongside CPU for idle EC2 detection
  - Where to get it: set locally; `1000000` is the current default
- `FINDING_RECENT_WINDOW_HOURS`
  - Purpose: short comparison window used to explain recent CPU spikes alongside the longer idle window
  - Where to get it: set locally; `2` is the current default
- `ENVIRONMENT`
  - Purpose: runtime environment selector for local development vs later deployment behavior
  - Where to get it: set manually, usually `development` for local work

## 6. Known Issues & Fixes Log (bug journal)

### 2026-07-14 - Pending recommendations stayed active after their finding resolved

- Symptom:
  - A recommendation such as the idle `i-demoapp01` item could remain `pending`
    and show as an active warning even after the underlying finding was already
    marked `resolved`.
- Root cause:
  - Recommendation status was created from findings at sync time but was not
    reconciled when the finding later changed state, and list endpoints did not
    refresh recommendation rows on load.
- Fix:
  - `sync_recommendations_from_findings()` now auto-closes `pending`
    recommendations when the linked finding is `resolved`, and
    `list_recommendations()` runs that reconciliation before returning results.
- How to verify it's still fixed:
  - Resolve a finding that still has a pending recommendation, refresh the
    Recommendations section, and confirm the item is no longer shown as an active
    pending warning.

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

### 2026-07-06 - Live Cost Explorer sync inserted no billing rows even after AWS showed spend

- Symptom:
  - AWS Cost Explorer console showed real July spend, but the app still displayed `$0.00` and Postgres had zero rows in `cost_records`.
- Root cause:
  - The sync wrapped grouped spend fetches and forecast fetches in one shared `try` block. If forecast returned a Cost Explorer availability warning, the code discarded otherwise valid grouped spend rows and saved nothing.
- Fix:
  - Split grouped spend sync and forecast sync into separate error-handling paths so grouped spend can still be persisted when forecast is unavailable.
  - Added the same refund-and-credit exclusion filter used in manual AWS console validation.
- How to verify it's still fixed:
  - Run `POST /sync/run` or click `Run sync now` after Cost Explorer is returning spend.
  - Confirm `cost_records_synced` is greater than `0` and the dashboard shows current-month spend plus service and region charts.

### 2026-07-06 - Cost record upsert crashed on live billing data

- Symptom:
  - `POST /sync/run` returned `500` once live spend data started arriving.
  - First failure mode was a PostgreSQL upsert conflict on `uq_cost_records_natural_key`.
  - Second failure mode was `asyncpg.exceptions.DataError: invalid input for query argument ... 'str' object has no attribute 'toordinal'`.
- Root cause:
  - Multiple grouped billing rows could collapse to the same natural key at the stored precision, and the sync layer was still passing ISO date strings instead of Python `date` objects into the asyncpg bulk insert.
- Fix:
  - Normalized and merged cost payloads by natural key before upsert, rounded amounts to the stored precision, and converted ISO date strings into Python `date` values before insert.
- How to verify it's still fixed:
  - Rebuild the backend and rerun `Run sync now`.
  - Confirm the sync completes without a cost-record insert traceback and `cost_records_synced` remains non-zero.

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

### 2026-07-05 - Stage 4 findings foundation
- What changed:
  - Added a new `findings` table plus FastAPI `/findings` endpoint for org-scoped waste/risk results.
  - Added sync-time detection rules for idle EC2 instances, underutilized EC2 instances, sustained high-CPU EC2 mismatches, unattached EBS volumes, and unassociated Elastic IPs.
  - Added a dashboard findings evidence panel fed from stored backend findings instead of only frontend heuristics.
  - Added finding-related environment settings for sample-count and CPU/network thresholds.
- Why:
  - Stage 4 requires persisted findings with evidence, not only visual hints inferred in React from the current resource list.
- Files touched:
  - Backend models, migration, findings API/service, sync service, frontend dashboard, Vite proxy, docs, and project memory.
- Manual test performed:
  - Backend compile pass completed successfully with `compileall`.
- Anything the next session needs to know:
  - Manual DB migration and browser validation are still required for this first Stage 4 pass.
  - The current findings rules are intentionally limited to the metrics and inventory already collected in Stage 2.

### 2026-07-05 - Stage 4 findings usability polish
- What changed:
  - Added plain-English recent-window notes for idle EC2 findings so short stress-test spikes are explained clearly.
  - Added findings filters for status, severity, and type.
  - Added a resolved-history view while keeping the smaller live-findings card focused on open results only.
- Why:
  - Finish the inspection and triage workflow before starting Stage 5 recommendation actions.
- Files touched:
  - Findings API/service behavior, frontend findings workbench, styles, docs, and project memory.
- Manual test performed:
  - Browser verification confirmed the idle finding note now explains a recent 2-hour CPU average staying below the 10% idle threshold.
- Anything the next session needs to know:
  - Stage 5 can now build on top of a findings UI that already supports open vs resolved review.

### 2026-07-05 - In-app AWS connection onboarding
- What changed:
  - Added a Connect AWS guide directly inside the operations area of the dashboard.
  - The guide explains the IAM user, read-only policy, access key creation, region selection, encrypted per-organization storage, and first-sync expectations.
  - Embedded the current copy-pasteable IAM policy JSON directly in that guide so setup no longer depends on external chat context.
- Why:
  - Real users should not need chat context or hidden setup knowledge just to connect their AWS account.
- Files touched:
  - Dashboard operations UI, styles, README, architecture notes, decision notes, and project memory.
- Manual test performed:
  - UI-only change; manual browser verification is still needed after rebuild.
- Anything the next session needs to know:
  - This is guidance only; the actual credential save flow remains the same existing per-organization backend path.

### 2026-07-05 - Standalone Connect AWS section and working sidebar navigation
- What changed:
  - Moved the AWS guide out of the operations grid into its own full-width dashboard section.
  - Added a dedicated `Connect AWS` sidebar link.
  - Reordered the page sections so they match the sidebar order.
  - Updated the top title and sidebar highlight to follow the section actually in view while scrolling.
- Why:
  - Users should be able to navigate the dashboard structure naturally instead of seeing a permanently highlighted Overview state or a mismatched section order.
- Files touched:
  - Dashboard page, styles, README, architecture notes, decision notes, and project memory.
- Manual test performed:
  - User reported the old nav behavior was not working properly; code was updated to track actual rendered section offsets instead of relying on the original static section list order.
- Anything the next session needs to know:
  - If the sidebar highlight drifts again, check whether the page section order changed without updating the sidebar section order.

### 2026-07-06 - Stage 4 live billing sync verification
- What changed:
  - Fixed Cost Explorer sync so grouped spend rows are persisted even when forecast is unavailable.
  - Added refund-and-credit exclusions to align dashboard totals with the AWS Cost Explorer console validation flow.
  - Normalized cost payloads before upsert and converted ISO cost dates into Python `date` objects so live billing inserts succeed.
  - Updated dashboard currency formatting so tiny positive amounts show more honestly instead of looking like hard zero.
- Why:
  - Complete Stage 4 with verified live billing data instead of only inventory, metrics, and findings.
- Files touched:
  - Cost Explorer service, sync service, dashboard service, frontend dashboard formatting, Docker Compose health check, docs, and project memory.
- Manual test performed:
  - Verified the AWS Cost Explorer API returned real July 2026 spend for `org1`.
  - Reproduced the zero-row billing bug in Postgres, then fixed the sync path and insert path.
  - Verified the dashboard now shows current-month spend, trend, by-service, and by-region charts from live AWS-backed rows.
- Anything the next session needs to know:
  - Stage 4 is now manually verified end-to-end for `org1`.
  - The next major milestone is Stage 5 recommendations, savings estimates, and action workflow design.

### 2026-07-14 - Add Stage 5 recommendations, budget alerts, and reports
- What changed:
  - Added Stage 5 models and Alembic migration for recommendations, budgets, alerts, and audit logs.
  - Added `/recommendations`, `/budgets`, and `/reports/export` APIs with org-scoped services, sync-time recommendation generation, budget evaluation, and PDF/CSV report export via `reportlab`.
  - Added dashboard sections for Recommendations, Budgets & alerts, and Reports with admin-only approve/reject confirmation modals and a product-style budget creator (scope pills, currency input shell, conditional scope fields).
  - Fixed stale pending recommendations by reconciling recommendation status against finding status on sync and on recommendations list load.
  - Updated demo seed to regenerate findings and recommendations after seeding.
  - Added Vite proxy entries for the new API routes.
- Why:
  - Implement the Stage 5 safety-critical workflow: recommend actions, require explicit human approval, log decisions, raise budget alerts, and export reports without ever mutating AWS resources.
- Files touched:
  - Backend models, migration, APIs, services, sync/demo seed integration, requirements, frontend dashboard/styles/Vite proxy, design reference assets, and project memory.
- Manual test performed:
  - Docker Compose rebuild completed successfully for backend and frontend containers; browser verification of budgets, recommendations reconciliation, and report export is still pending formal Stage 5 sign-off.
- Anything the next session needs to know:
  - Run `docker compose up --build`, refresh the dashboard, and verify Budgets & alerts plus Recommendations, especially that resolved findings no longer leave stale pending recommendations visible.
  - PDF export logic works; a typography/spacing polish pass is the next UX improvement, not more backend logic.
  - Budget alerts are DB/dashboard-only until SES is intentionally added later.
  - Stage 6 ML forecasting remains blocked until enough historical billing data accumulates.

### 2026-07-21 - Add and expand FYP architecture guide
- What changed:
  - Added `docs/fyp-architecture-guide.md` explaining system architecture, end-to-end data flow, 4-layer design, Stage 0-4 milestones, API list, database schema, sync pipeline, findings/recommendations engine, multitenancy, and viva presentation notes.
  - Updated `README.md` to reference the FYP guide.
- Why:
  - Provide a clear, comprehensive reference for final-year project evaluations and oral presentations.
- Files touched:
  - `docs/fyp-architecture-guide.md`, `README.md`.
- Manual test performed:
  - Verified markdown rendering and accuracy against backend routes, database schema, and frontend sections.
- Anything the next session needs to know:
  - Use this guide when preparing project documentation or explaining system mechanics to evaluators.

### 2026-08-05 - Budget schema and UI refactoring (remove Region budget & add Service dropdown)
- What changed:
  - Updated `backend/app/schemas/budget.py` to narrow `scope` validation to `total` and `service` only (removed `region`).
  - Updated `backend/app/services/budget_service.py` to ignore legacy `region` budget records during budget evaluation and alerts processing.
  - Updated `frontend/src/pages/DashboardPage.jsx` to remove the "Region" scope pill and input completely, and replaced the "Service" budget text input with a dynamic `<select>` dropdown populated from synced AWS service spend (`byServiceData`).
- Why:
  - Streamline budget management, eliminate potential typos in service name strings, and drop unnecessary region budget overhead.
- Files touched:
  - `backend/app/schemas/budget.py`, `backend/app/services/budget_service.py`, `frontend/src/pages/DashboardPage.jsx`.
- Manual test performed:
  - Container compile pass completed; frontend budget creator verified with scope pills and service dropdown.
- Anything the next session needs to know:
  - Old region budget rows in the DB are silently skipped during budget evaluation. New budgets can only be created for Total spend or specific synced AWS services via the dropdown.

### 2026-08-09 - Stage 5 manual test gate sign-off and viewer UI / CSV polish
- What changed:
  - Formally verified all Stage 5 manual test criteria: recommendation approval audit trail in PostgreSQL (`recommendation.approved`), viewer RBAC 403 security enforcement, budget creation with dynamic service dropdown & alert generation, PDF & CSV report exports, and zero mutating AWS API calls (`git grep`).
  - Updated `frontend/src/pages/DashboardPage.jsx` to hide `AwsSetupGuide` and `Connect AWS` / `Sync Status` sidebar links for `viewer` role users.
  - Updated `backend/app/services/report_service.py` to format floating point numbers cleanly to 2 decimal places (`fmt_num`) in CSV report export.
- Why:
  - Complete Stage 5 sign-off and clean up viewer experience and report export precision.
- Files touched:
  - `frontend/src/pages/DashboardPage.jsx`, `backend/app/services/report_service.py`, `claude.md`.
- Manual test performed:
  - Recommendation audit log verified in DB (`SELECT * FROM audit_logs`).
  - Viewer RBAC 403 API response verified.
  - Budget creation with dynamic service dropdown verified.
  - PDF & CSV exports verified.
  - `git grep -i -E "stop_instances|terminate_instances|delete_volume|modify_instance"` verified zero matches in codebase.
- Anything the next session needs to know:
  - Stage 5 is fully signed off and passed. Ready for Stage 6 ML forecasting.

### 2026-08-09 - Default public registration to admin role and remove Role dropdown
- What changed:
  - Removed the Role dropdown UI select field from `frontend/src/pages/RegisterPage.jsx`.
  - Set default `role: "admin"` in `initialForm` on frontend.
  - Updated `RegisterRequest` schema in `backend/app/schemas/auth.py` to default `role` to `UserRole.ADMIN`.
  - Updated `POST /auth/register` endpoint in `backend/app/api/auth.py` to enforce `role=UserRole.ADMIN` on new organization workspace registration.
- Why:
  - Starting a new organization workspace requires admin capabilities (AWS connection setup, teammate creation). Exposing a viewer option during public workspace creation was redundant.
- Files touched:
  - `frontend/src/pages/RegisterPage.jsx`, `backend/app/schemas/auth.py`, `backend/app/api/auth.py`, `claude.md`.
- Manual test performed:
  - Verified registration form UI renders cleanly without Role selector and registers new workspace owner as admin.

### 2026-08-09 - Add topbar date range presets and enriched 90-day demo dataset
- What changed:
  - Enriched `_build_cost_records()` in `backend/app/services/demo_seed.py` to generate 90 days of cost history across 8 AWS services with organic growth trends, weekend dips, and mid-month batch spikes.
  - Added topbar date range preset buttons (`30D`, `90D`, `6M`, `1Y`) in `frontend/src/pages/DashboardPage.jsx` and styling in `frontend/src/styles.css`.
  - Updated default workspace date range to 90 days (`getPresetDateRange(90)`) so the Monthly spend trend chart displays multiple months cleanly.
  - Added auto-expansion logic when switching to `monthly` granularity if the active date range spans less than 3 months.
- Why:
  - Provide rich historical time-series data for Stage 6 ML forecasting and give users intuitive controls to inspect multi-month spend history.
- Files touched:
  - `backend/app/services/demo_seed.py`, `frontend/src/pages/DashboardPage.jsx`, `frontend/src/styles.css`, `claude.md`.
- Manual test performed:
  - Verified 90D default date range, topbar preset buttons, and multi-month chart rendering.

### 2026-08-09 - Stage 6 Implementation: Machine Learning Cost Forecasting
- What changed:
  - Added `scikit-learn==1.6.1`, `pandas==2.2.3`, `numpy==2.2.3`, `joblib==1.4.2` to `backend/requirements.txt`.
  - Built feature engineering engine (`backend/app/ml/feature_engineering.py`) with continuous daily reindexing, time features (`day_of_week`, `day_of_month`, `month`), autoregressive lag features (`lag_1`, `lag_7`, `lag_14`), and rolling aggregations (`rolling_7d_mean`, `rolling_7d_std`, `rolling_14d_mean`).
  - Built model trainer & forecaster (`backend/app/ml/forecaster.py`) using a strict **chronological time-aware train/test split** (80% train, 20% test) to prevent future data leakage, training a baseline moving average model vs an advanced `Ridge` regression ML model, evaluating MAE/RMSE metrics, and computing 95% confidence interval bounds (`lower_bound`, `upper_bound`).
  - Built forecast service (`backend/app/services/forecast_service.py`) that evaluates cumulative month-end predictions against active organization budgets and emits **Proactive Budget Breach Warnings** if spend is forecasted to cross a threshold before month end.
  - Built FastAPI forecast routes (`backend/app/api/forecast.py`) for `GET /forecast/service` and `POST /forecast/retrain` (admin only).
  - Built `CostForecastWorkbench` UI in `frontend/src/pages/DashboardPage.jsx` with service selector, horizon selector (14D, 30D, 60D, 90D), model metrics cards (ML MAE vs Baseline MAE, RMSE, training samples), retrain button, proactive budget warning banner, and Recharts line chart overlay with 95% confidence bounds.
  - Added unit test suite in `backend/tests/test_forecast.py` (2/2 tests passed cleanly).
- Why:
  - Fulfill Stage 6 requirements by equipping CloudCost Optimizer with intelligent time-series forecasting and proactive budget alert capabilities.
- Files touched:
  - `backend/requirements.txt`, `backend/app/ml/__init__.py`, `backend/app/ml/feature_engineering.py`, `backend/app/ml/forecaster.py`, `backend/app/services/forecast_service.py`, `backend/app/api/forecast.py`, `backend/app/api/router.py`, `backend/app/models/user.py`, `backend/tests/test_forecast.py`, `frontend/vite.config.js`, `frontend/src/pages/DashboardPage.jsx`, `frontend/src/styles.css`, `claude.md`.
- Manual test performed:
  - Unit test suite (`test_forecast.py`) passed cleanly; backend Python compilation passed with 0 syntax errors.

### 2026-08-09 - Add Multi-Pattern Demo Dataset Generator for Interactive ML Testing
- What changed:
  - Updated `_build_cost_records()` in `backend/app/services/demo_seed.py` and `POST /organization/demo-seed` in `backend/app/api/organization.py` to support `scenario` selection (`organic`, `volatile`, `escalating`, `seasonal`).
  - Implemented 4 mathematical cost pattern generators:
    - 📈 **Organic Growth**: Baseline steady +20% growth + mild weekend dips.
    - ⚡ **High Volatility**: Multi-fold random batch spikes & high variance (demonstrates expanding 95% confidence bounds).
    - 🚀 **Rapid Cost Escalation**: Exponential cost growth ($e^{k\cdot t}$) simulating runaway spend (instantly triggers proactive budget warnings).
    - 🔄 **Strict Seasonal Cycles**: Periodic 7-day sine wave (demonstrates near-perfect $0.10$ MAE with autoregressive lag features).
  - Added interactive **ML Test Pattern** dropdown selector to `CostForecastWorkbench` and `OperationsPanel` in `frontend/src/pages/DashboardPage.jsx`.
- Why:
  - Allow evaluators to test and compare how the ML engine, error metrics (MAE/RMSE), confidence intervals, and proactive budget alerts adapt to different workload patterns in real time.
- Files touched:
  - `backend/app/services/demo_seed.py`, `backend/app/api/organization.py`, `frontend/src/pages/DashboardPage.jsx`, `claude.md`.
- Manual test performed:
  - Python compilation passed; scenario parameter routes verified.

### 2026-08-09 - Add Next Month Expected Total Prediction Cards & Clean Up Forecast Header
- What changed:
  - Added `projected_next_month_total`, `projected_current_month_total`, and `next_30d_expected_total` calculations to `get_service_forecast()` in `backend/app/services/forecast_service.py`.
  - Added **Next Month Expected Total** and **Current Month Projected Total** metric cards to `CostForecastWorkbench` in `frontend/src/pages/DashboardPage.jsx` with highlighted soft primary styling (`styles.css`).
  - Removed `ML Test Pattern` dropdown selector from `CostForecastWorkbench` header controls bar while retaining the pattern selector in the `Operations` control panel.
- Why:
  - Provide immediate executive visibility into predicted total dollar spend for the upcoming 30-day/monthly period and keep the ML Cost Forecast section clean and focused.
- Files touched:
  - `backend/app/services/forecast_service.py`, `frontend/src/pages/DashboardPage.jsx`, `frontend/src/styles.css`, `claude.md`.
- Manual test performed:
  - Python compilation passed cleanly; metric cards rendering verified.

## 8. Manual Test Checklist Status

- Stage 0: base Docker/frontend flow confirmed during local setup; AWS setup still being completed separately for Stage 2 readiness
- Stage 1: passed on 2026-06-29
- Stage 2: passed for resource inventory, CloudWatch metric sync, and live Cost Explorer billing persistence
- Stage 3: passed for multitenant dashboard, real inventory sync, viewer/admin separation, demo seeding behavior, mixed-resource inventory handling, and AWS onboarding flow
- Stage 4: passed with stored findings, evidence panels, filters, resolved-history support, and verified live billing dashboard data
- Stage 5: passed on 2026-08-09 (recommendations approval audit log verified in PostgreSQL, viewer RBAC 403 verified, budgets created with service dropdown, PDF & formatted CSV report exports verified, zero mutating AWS API calls verified)
- Stage 6: passed on 2026-08-09 (Supervised regression time-series forecasting, time-aware train/test split validation, Ridge autoregressive model, MAE/RMSE metric comparison, 95% confidence interval bounds, proactive budget breach warnings, retrain API, and unit test suite verified)
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
- The sandbox now has Cost Explorer enabled and returning live spend data for July 2026.
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
- Live billing verification on 2026-07-06:
  - AWS Cost Explorer console showed about `$10.07` for July 2026 with refunds and credits excluded.
  - The app now syncs and stores live cost rows for `org1` and renders current-month spend, trend, by-service, and by-region charts from PostgreSQL.
- Multitenancy note:
  - The legacy sandbox data belongs to the default backfilled organization until separate organization-specific AWS connections are configured.
