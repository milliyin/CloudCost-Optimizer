# CloudCost Optimizer

CloudCost Optimizer is a portfolio SaaS-style dashboard for analyzing AWS
spend, surfacing waste, and presenting safe human-reviewed cost-saving
recommendations. This repository is being built in stages, with a manual test
gate at the end of each stage.

## Stage 0 Stack

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

This initial stage only includes the project skeleton, a backend `/health`
endpoint, and a frontend page that displays the health result. AWS ingestion,
authentication, dashboarding, and recommendations will be added in later stages.
