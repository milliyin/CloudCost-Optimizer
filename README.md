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
- A protected dashboard shell that confirms session and admin-route behavior

Current session behavior:

- Access and refresh tokens are kept in memory only
- Refreshing the browser intentionally signs the user out
- This avoids storing tokens in `localStorage`, reducing XSS exposure for this portfolio build
