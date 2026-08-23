# CloudCost Optimizer

CloudCost Optimizer is a portfolio SaaS-style dashboard for analyzing AWS spend, surfacing waste, and presenting safe human-reviewed cost-saving recommendations. The project is built in stages, with a manual test gate at the end of each milestone.

If you want the detailed FYP explanation of how the system works, see [docs/fyp-architecture-guide.md](docs/fyp-architecture-guide.md).

## Current Stack

- FastAPI for the backend API
- React + Vite for the frontend
- PostgreSQL for application storage
- Docker Compose for local orchestration

## Quick Start

1. Copy `.env.example` to `.env` and adjust values as needed for local work.
2. Run:

```bash
docker compose up --build
```

3. Open `http://localhost:8000/health` to verify the backend.
4. Open `http://localhost:5173` to verify the frontend can fetch the backend health check.

## Current Scope

The project currently includes:

- Stage 0 foundation with Docker, FastAPI, React, and PostgreSQL
- Stage 1 authentication with registration, login, refresh, `/auth/me`, and role checks
- Stage 2 ingestion foundations with AWS client factories, sync orchestration, scheduler wiring, and an admin-only `/sync/run` endpoint
- Multi-tenant foundations with organization-owned users, organization-specific AWS connections, and tenant-scoped synced data
- Stage 3 interactive dashboard with org-scoped spend summary, cost charts, trend view, findings, resource inventory, admin sync controls, and opt-in demo seed loading
- Stage 4 stored findings pipeline with evidence-backed rules and evidence panel
- Stage 5 human-reviewed recommendations workflow with immutable audit logs, viewer RBAC, organization budget tracking with alerts, and ReportLab PDF + CSV report exports
- Stage 6 Machine Learning Cost Forecasting with supervised `Ridge` regression, time-aware train/test split, autoregressive lag features, confidence bounds, multi-step 14D-90D horizon predictions, proactive budget breach warnings, and Next Month Expected Total projections

## How It Works

- The frontend is a React SPA displaying login, dashboard, operations, findings, recommendations, budgets, reports, and the ML cost forecast workbench
- The backend is a FastAPI app owning authentication, AWS sync, findings engine, recommendations audit trail, budget alerts, report generation, and the ML forecasting pipeline
- PostgreSQL stores organizations, users, synced AWS data, findings, recommendations, budgets, audit logs, and historical cost time series
- Docker Compose runs the stack locally with live code volume mounts for development
- Each organization has isolated data, so one tenant cannot access another tenant's AWS workspace

## Current Product Behavior

- Access and refresh tokens are persisted locally so users stay signed in across refreshes
- Each organization can save its own AWS credentials for isolated sync behavior
- Per-organization AWS credentials are encrypted before storage on the backend
- Admins can create same-organization teammates directly from the dashboard
- Real sync clears any demo-seeded workspace rows before loading live AWS data
- Demo mode supports Organic Growth, High Volatility, Rapid Cost Escalation, and Strict 7-Day Seasonal Cycles to test the ML views
- The Machine Learning workbench provides service-slice filtering, 14D-90D horizon forecasting, ML MAE vs Baseline MAE metrics, RMSE, Next Month Expected Total, Current Month Projected Total, and confidence-bound visualization
- Forecast API failures are now surfaced as readable backend errors instead of raw JSON parse errors in the dashboard
- Non-destructive safety rule: recommendation approvals record immutable audit logs in PostgreSQL with zero mutating AWS API calls

## Current Inventory Coverage

- EC2 instances
- EBS volumes
- Elastic IPs
- RDS instances
- Load balancers
- Lambda functions
- S3 buckets
- DynamoDB tables
- SQS queues
- SNS topics
- ECS clusters and services
- ECR repositories
- API Gateway APIs

## AWS Sync and Forecasting Notes

- Cost Explorer sync persists daily cost records into PostgreSQL and keeps grouped spend separate from forecast fetches so one failing path does not discard the other
- The ML engine performs continuous daily reindexing, feature engineering (`day_of_week`, `is_weekend`, `sin_7`, `cos_7`, `lag_1`, `lag_7`, `lag_14`, `rolling_7d_mean`, `rolling_7d_std`), and chronological 80/20 train/test split to eliminate future data leakage
- The forecasting model uses `Ridge(alpha=0.1)` and compares its results against a naive moving-average baseline
- Proactive budget breach warnings calculate projected cumulative month-end spend and alert admins before a budget threshold is crossed
- If live cost history is too short, the forecast workbench intentionally falls back to `Fallback Zero` rather than pretending a low-sample forecast is reliable
- Real forecasting becomes useful after roughly 7+ days of synced billing history and improves further with 14-30+ days

## Budget Notes

- New budgets can be created only for `total` or `service` scope
- Service budgets use a dropdown populated from the organization's synced AWS services
- Legacy `region` budget rows are ignored by the current evaluation path
