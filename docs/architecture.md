# Architecture Overview

Current architecture:

- `frontend/` runs a Vite + React application with route-based auth screens.
- `backend/` runs a FastAPI app with health, auth, refresh, role-check, and manual sync endpoints.
- `postgres` stores user accounts, cost records, cloud resources, and metric samples.
- An APScheduler background job is wired into FastAPI lifespan to trigger periodic syncs.

Planned direction:

- Frontend will become the authenticated dashboard UI.
- Backend will provide auth, sync orchestration, reporting, and forecasting APIs.
- PostgreSQL will store users, synced AWS data, findings, recommendations, and audit logs.
