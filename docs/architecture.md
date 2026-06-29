# Architecture Overview

Current architecture:

- `frontend/` runs a Vite + React application with route-based auth screens.
- `backend/` runs a FastAPI app with health, auth, refresh, and role-check endpoints.
- `postgres` stores user accounts and will hold sync, findings, and reporting data in later stages.

Planned direction:

- Frontend will become the authenticated dashboard UI.
- Backend will provide auth, sync orchestration, reporting, and forecasting APIs.
- PostgreSQL will store users, synced AWS data, findings, recommendations, and audit logs.
