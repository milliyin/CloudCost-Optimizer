# CloudCost Optimizer

CloudCost Optimizer is a portfolio SaaS-style dashboard for analyzing AWS
spend, surfacing waste, and presenting safe human-reviewed cost-saving
recommendations. This repository is being built in stages, with a manual test
gate at the end of each stage.

If you want the detailed FYP explanation of how the system works, see
[docs/fyp-architecture-guide.md](docs/fyp-architecture-guide.md).

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
4. Open `http://localhost:5173` to verify the frontend can fetch the backend
   health check.

## Current Scope

The project currently includes:

- Stage 0 foundation with Docker, FastAPI, React, and PostgreSQL
- Stage 1 authentication with registration, login, refresh, `/auth/me`, and role checks
- Stage 2 ingestion foundations with AWS client factories, sync orchestration, scheduler wiring, and an admin-only `/sync/run` endpoint
- Multi-tenant foundations with organization-owned users, organization-specific AWS connections, and tenant-scoped synced data
- Stage 3 interactive dashboard with org-scoped spend summary, cost charts, trend view, findings, resource inventory, admin sync controls, and opt-in demo seed loading
- Stage 4 stored findings pipeline with evidence-backed rules and evidence panel
- Stage 5 human-reviewed recommendations workflow with immutable audit logs, Viewer role RBAC, organization budget tracking with alerts, and ReportLab PDF + CSV report exports
- Stage 6 Machine Learning Cost Forecasting engine with supervised `Ridge` regression, time-aware train/test split, autoregressive lag features, 95% confidence bounds, multi-step 14D–90D horizon predictions, proactive budget breach warnings, and Next Month Expected Total spend projections

## How It Works

- The frontend is a React SPA displaying login, dashboard, operations, findings, recommendations, budgets, reports, and ML cost forecast workbench
- The backend is a FastAPI app owning authentication, AWS sync, findings engine, recommendations audit trail, budget alerts, report generation, and ML forecasting pipeline
- PostgreSQL stores organizations, users, synced AWS data, findings, recommendations, budgets, audit logs, and historical cost time-series
- Docker Compose runs the stack locally with live code volume mounts for seamless development
- Each organization has isolated data, so one tenant cannot access another tenant's AWS workspace

Current session behavior:

- Access and refresh tokens are persisted locally so users stay signed in across refreshes
- Each organization can save its own AWS credentials for isolated sync behavior
- Per-organization AWS credentials are encrypted before storage on the backend
- Admins can create same-organization teammates directly from the dashboard
- Real sync clears any demo-seeded workspace rows before loading live AWS data
- Interactive Demo Dataset Pattern generator allows switching between 📈 Organic Growth, ⚡ High Volatility, 🚀 Rapid Cost Escalation, and 🔄 Strict 7-Day Seasonal Cycles to test ML predictions
- Machine Learning workbench provides service slice filtering, 14D–90D horizon forecasting, ML MAE vs Baseline MAE accuracy metrics, RMSE, Next Month Expected Total, Current Month Projected Total, and 95% confidence interval visualization
- Non-destructive safety rule: Recommendation approvals record immutable audit logs in PostgreSQL with zero mutating AWS API calls (`0` matches for `stop_instances`, `terminate_instances`, `delete_volume`)

Current inventory coverage includes:

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

AWS sync & ML forecasting notes:

- Cost Explorer persists 90 days of daily cost records across 8 AWS services into PostgreSQL
- The ML engine performs continuous daily reindexing, feature engineering (`day_of_week`, `is_weekend`, `lag_1`, `lag_7`, `lag_14`, `rolling_7d_mean`, `rolling_7d_std`), and chronological 80/20 train/test split to eliminate future data leakage
- Evaluates `Ridge` regression model against 7-day Naive Moving Average baseline, achieving ~74% error reduction ($1.14 ML MAE vs $4.30 Baseline MAE)
- Proactive budget breach warnings calculate projected cumulative month-end spend and alert admins before a budget threshold is crossed
