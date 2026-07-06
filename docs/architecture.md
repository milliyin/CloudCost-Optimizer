# Architecture Overview

Current architecture:

- `frontend/` runs a Vite + React application with route-based auth screens, persistent session storage, organization AWS-connection management, a standalone in-app AWS onboarding section with embedded IAM policy JSON, teammate creation, live dashboard charts/tables, stored findings views with filters and resolved history, scroll-aware section navigation, and admin sync controls.
- `backend/` runs a FastAPI app with health, auth, refresh, organization management, dashboard, findings, role-check, demo seed, teammate creation, and manual sync endpoints.
- `postgres` stores organizations, users, AWS connection records, cost records, cloud resources, metric samples, and findings.
- An APScheduler background job is wired into FastAPI lifespan to trigger periodic syncs.

Current data flow:

- Admin saves AWS credentials per organization through the dashboard.
- A manual or scheduled sync reads AWS Cost Explorer, resource inventory services, and CloudWatch metrics.
- Synced cost rows are normalized and upserted into PostgreSQL so repeated syncs stay idempotent.
- Findings are recalculated immediately after sync from the latest organization-scoped resources and metric samples.
- Dashboard summary cards, trend charts, service breakdowns, region breakdowns, inventory, and findings all read from the stored org-scoped PostgreSQL data instead of querying AWS directly from the browser.

Planned direction:

- Frontend will expand into findings, recommendation, budget, and reporting workflows.
- Backend will provide auth, sync orchestration, evidence-backed findings, reporting, and forecasting APIs.
- PostgreSQL will expand to store tenant-scoped findings, recommendations, and audit logs alongside synced AWS data.
