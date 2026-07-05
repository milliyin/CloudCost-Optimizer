# Architecture Overview

Current architecture:

- `frontend/` runs a Vite + React application with route-based auth screens, persistent session storage, organization AWS-connection management, teammate creation, dashboard charts/tables, stored findings views, and admin sync controls.
- `backend/` runs a FastAPI app with health, auth, refresh, organization management, dashboard, findings, role-check, demo seed, teammate creation, and manual sync endpoints.
- `postgres` stores organizations, users, AWS connection records, cost records, cloud resources, metric samples, and findings.
- An APScheduler background job is wired into FastAPI lifespan to trigger periodic syncs.

Planned direction:

- Frontend will expand into findings, recommendation, budget, and reporting workflows.
- Backend will provide auth, sync orchestration, evidence-backed findings, reporting, and forecasting APIs.
- PostgreSQL will expand to store tenant-scoped findings, recommendations, and audit logs alongside synced AWS data.
