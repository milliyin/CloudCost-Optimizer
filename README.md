# CloudCost Optimizer

CloudCost Optimizer is a portfolio SaaS-style dashboard for analyzing AWS
spend, surfacing waste, and presenting safe human-reviewed cost-saving
recommendations. This repository is being built in stages, with a manual test
gate at the end of each stage.

## Current Stack

- FastAPI for the backend API
- React + Vite for the frontend
- PostgreSQL for application storage
- Docker Compose for local orchestration

## Quick Start

1. Copy `.env.example` to `.env` and adjust values as needed for local work.
2. Run:

```bash
docker-compose up --build
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
- Stage 4 initial findings pipeline with stored waste/risk detections, evidence-backed rules, and a dashboard evidence panel

Current session behavior:

- Access and refresh tokens are persisted locally so users stay signed in across refreshes
- Each organization can save its own AWS credentials for isolated sync behavior
- Per-organization AWS credentials are encrypted before storage on the backend
- Admins can create same-organization teammates directly from the dashboard
- Real sync clears any demo-seeded workspace rows before loading live AWS data

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

AWS sync notes:

- Cost Explorer can take about 24 hours after first enablement to begin returning data
- The sync layer is designed to keep resource inventory and CloudWatch ingestion working even when Cost Explorer data is still unavailable
- Non-EC2 resources intentionally appear as inventory-only rows in the dashboard; only EC2 rows currently show CPU and network telemetry columns
- Findings are recalculated as part of each sync and currently cover idle EC2 instances, underutilized EC2 instances, sustained high-CPU EC2 mismatches, unattached EBS volumes, and unassociated Elastic IPs
