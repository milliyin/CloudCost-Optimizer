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

- Current stage: Stage 1 - Authentication & Role-Based Access Control, in progress
- Last completed milestone: 2026-06-27 - Stage 0 foundation scaffold committed and pushed
- Known broken / in-progress things right now:
  - Stage 1 has been implemented in code but not fully manually verified yet.
  - AWS sandbox setup is happening in parallel and is still needed before Stage 2.
  - Session persistence is intentionally memory-only, so refreshing the frontend signs the user out.

## 3. Architecture Summary

The repository now contains a FastAPI backend, a Vite + React frontend, and a
PostgreSQL service defined in Docker Compose. The backend exposes `/health`,
registration, login, refresh, current-user, and admin-only test endpoints. The
frontend uses React Router with an auth provider, a protected route wrapper,
and an API client that retries once on `401` by calling `/auth/refresh`. See
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
- `ENVIRONMENT`
  - Purpose: runtime environment selector for local development vs later deployment behavior
  - Where to get it: set manually, usually `development` for local work

## 6. Known Issues & Fixes Log (bug journal)

No known application bugs logged yet.

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
- Why:
  - Implement the Stage 1 authentication and authorization flow needed before the AWS dashboard stages.
- Files touched:
  - Backend auth, DB, and Alembic files; frontend routing/auth files; docs and project memory.
- Manual test performed:
  - Not yet in this session. Stage 1 manual gate is still pending.
- Anything the next session needs to know:
  - Tokens are memory-only by design, so refresh should log the user out unless that behavior is intentionally changed later.

## 8. Manual Test Checklist Status

- Stage 0: base Docker/frontend flow confirmed during local setup; AWS setup still being completed separately for Stage 2 readiness
- Stage 1: pending as of 2026-06-29

## 9. AWS Account / Sandbox Notes

- Cost Explorer must be enabled manually in the AWS Cost Management console.
- AWS documents that current-month Cost Explorer data becomes available in about
  24 hours after enablement, with additional historical processing taking longer.
- AWS documents that IAM access to Billing and Cost Management console pages is
  controlled by the root-user-only Activate IAM Access setting, but AWS also
  notes that this setting does not control access to the Billing and Cost
  Management SDK APIs themselves. Keep that distinction in mind when Stage 2
  service integrations are implemented.
