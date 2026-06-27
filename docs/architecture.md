# Architecture Overview

Stage 0 architecture is intentionally minimal:

- `frontend/` runs a Vite + React development server.
- `backend/` runs a FastAPI app with a `/health` endpoint.
- `postgres` is provisioned in Docker Compose for upcoming persistence work.

Planned direction:

- Frontend will become the authenticated dashboard UI.
- Backend will provide auth, sync orchestration, reporting, and forecasting APIs.
- PostgreSQL will store users, synced AWS data, findings, recommendations, and audit logs.
