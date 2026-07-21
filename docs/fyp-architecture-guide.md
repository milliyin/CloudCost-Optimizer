# FYP Architecture Guide

This document explains how CloudCost Optimizer works up to Stage 4 in a way that is easy to present for a final-year project. It focuses on the architecture, the main components, and the end-to-end data flow.

## 1. Project Idea

CloudCost Optimizer is a multi-tenant AWS cost visibility application. Its purpose is to help each organization:

- connect its own AWS account safely
- pull cost, inventory, and telemetry data into the app
- detect waste and risk signals from that data
- show those signals in a dashboard
- let admins review recommendations without executing dangerous AWS actions automatically

The key design idea is simple:

> AWS data is collected by the backend, stored in PostgreSQL, and then shown in the frontend dashboard.

That means the browser never talks directly to AWS. The backend does the secure work, and the frontend only reads app data from the API.

## 2. Core Concepts

These are the main ideas used in the project:

- `Frontend`: the user interface in the browser
- `Backend`: the server that runs business logic and talks to AWS
- `API`: the HTTP routes the frontend calls
- `Database`: PostgreSQL, where the app stores organization data
- `Multitenancy`: each organization gets isolated data
- `Authentication`: login system for users
- `Authorization`: role checks like admin or viewer
- `ORM`: the Python layer that maps code objects to database tables
- `Migration`: a database version change that keeps schema and code aligned
- `Upsert`: insert a record if it is new, or update it if it already exists
- `Encryption`: protecting AWS secret values before storing them
- `Evidence-driven detection`: using measured data to explain why a finding exists

If you understand those concepts, the rest of the system becomes much easier to follow.

## 3. How the System Works

At a high level, the app works like this:

1. The user opens the React frontend.
2. The user logs in, and the frontend stores the session token.
3. The frontend calls FastAPI routes to load dashboard data.
4. An admin saves AWS credentials for the organization.
5. The backend encrypts those credentials and saves them in PostgreSQL.
6. A sync job reads AWS cost, inventory, and telemetry data.
7. The backend stores that AWS data in PostgreSQL.
8. The findings engine checks the stored data against rules.
9. The recommendation engine turns findings into review items.
10. The dashboard reads the stored data back from the API and displays it.

Important point:

- the frontend is only a viewer and controller
- the backend is the brain of the application
- PostgreSQL is the memory of the application

## 4. High-Level Architecture

The project has four main layers:

1. `frontend/`
2. `backend/`
3. `postgres`
4. `Docker Compose`

### Frontend

The frontend is a React + Vite application. It handles:

- login and registration screens
- protected dashboard pages
- AWS connection setup
- inventory, findings, recommendations, budgets, and report sections
- in-app actions such as approve, reject, create budget, and run sync

### Backend

The backend is a FastAPI application. It handles:

- authentication and refresh tokens
- organization and teammate management
- AWS credential storage
- sync orchestration
- dashboard APIs
- findings detection
- recommendation generation
- budgets and alerts
- report export
- demo seed loading

### PostgreSQL

PostgreSQL stores the application state:

- organizations
- users
- AWS connections
- cost records
- cloud resources
- metric samples
- findings
- recommendations
- budgets
- alerts
- audit logs

### Docker Compose

Docker Compose runs the whole stack locally:

- frontend container
- backend container
- PostgreSQL container

This makes the project easy to test on one machine.

## 5. Repository Structure

Important folders:

- `frontend/` React UI
- `backend/` FastAPI API, models, services, and migrations
- `docs/` architecture and project notes
- `design/` UI mockups and design references

Important backend subfolders:

- `backend/app/api/` API routes
- `backend/app/models/` database models
- `backend/app/schemas/` request and response shapes
- `backend/app/services/` business logic
- `backend/alembic/` database migrations

## 6. Stage Breakdown

### Stage 0: Foundation

Stage 0 set up the project skeleton.

What was built:

- Docker-based local environment
- React frontend
- FastAPI backend
- PostgreSQL database
- environment variable setup

Why it matters:

- gives the project a stable starting point
- separates frontend, backend, and database cleanly

### Stage 1: Authentication

Stage 1 added user accounts and access control.

What was built:

- registration
- login
- refresh tokens
- `/auth/me`
- role checks for admin and viewer

How it works:

- the user logs in with email and password
- the backend returns access and refresh tokens
- the frontend stores session state locally
- protected pages check the user before showing dashboard data

Why it matters:

- the app can now distinguish users
- access can be controlled by role

### Stage 2: Ingestion Foundation

Stage 2 created the AWS sync foundation.

What was built:

- AWS client factory and credential handling
- sync orchestration
- scheduler wiring
- manual `/sync/run` endpoint
- organization-specific AWS credential storage

How it works:

- an admin saves AWS access keys for one organization
- the backend uses those credentials to read AWS data
- sync jobs collect cost, inventory, and metric information

Why it matters:

- this is the bridge between AWS and the app database

### Stage 3: Dashboard and Multi-Tenancy

Stage 3 turned the project into a real dashboard application.

What was built:

- organization-scoped dashboard
- cost summary cards
- trend chart
- cost by service
- cost by region
- resource inventory table
- sync status section
- AWS connection section
- teammate creation for the same organization
- opt-in demo seed loading

How it works:

- every user belongs to one organization
- all dashboard data is filtered by organization id
- admin users can manage AWS credentials and teammates
- viewer users can see the dashboard but not manage admin actions

Why it matters:

- the app becomes multi-tenant
- one organization cannot see another organization’s data

### Stage 4: Findings Pipeline

Stage 4 added evidence-backed risk detection.

What was built:

- stored findings table
- finding detection rules
- evidence panel in the dashboard
- resolved/open finding states
- filters for severity, type, and status

How it works:

- the sync process reads cloud resources and metric samples
- rules detect waste or risk conditions
- the backend stores findings in PostgreSQL
- the dashboard reads those findings and shows them as cards

Examples of findings:

- idle EC2 instance
- underutilized EC2 instance
- oversized/high-CPU mismatch
- unattached EBS volume
- unused Elastic IP

Why it matters:

- the app no longer just shows raw data
- it now interprets data and explains why something may need attention

## 7. End-to-End Data Flow

This is the full flow of the app:

1. The user logs in on the frontend.
2. The frontend stores the session and calls the backend API.
3. An admin saves AWS credentials for the organization.
4. The backend encrypts and stores those credentials in PostgreSQL.
5. The sync endpoint reads AWS Cost Explorer, inventory, and CloudWatch data.
6. The backend normalizes that data and writes it into PostgreSQL.
7. Findings are recalculated from the stored cloud data.
8. The frontend dashboard fetches the stored data from the backend.
9. The dashboard renders charts, tables, and evidence cards.

Important rule:

- the frontend does not directly query AWS
- the backend is the only layer that talks to AWS

## 8. Frontend Architecture

The frontend is a single-page app built with React.

### Main responsibilities

- authentication screens
- dashboard navigation
- API calls to backend routes
- form handling for AWS credentials, teammates, budgets, and actions
- presentation of charts and tables

### Key frontend files

- `frontend/src/App.jsx`
- `frontend/src/components/AuthProvider.jsx`
- `frontend/src/components/ProtectedRoute.jsx`
- `frontend/src/pages/LoginPage.jsx`
- `frontend/src/pages/RegisterPage.jsx`
- `frontend/src/pages/DashboardPage.jsx`
- `frontend/src/api/client.js`
- `frontend/src/api/errors.js`

### Dashboard behavior

`DashboardPage.jsx` is the main screen of the product.

It:

- loads all dashboard data after login
- keeps track of the active section in the left navigation
- shows org-scoped spend, inventory, findings, recommendations, budgets, and reports
- lets admins run syncs and create teammates
- gives viewers read-only access

## 9. Backend Architecture

The backend is built with FastAPI and organized by responsibility.

### API layer

Routes live in `backend/app/api/`.

Examples:

- `auth.py`
- `organization.py`
- `sync.py`
- `dashboard.py`
- `findings.py`
- `recommendations.py`
- `budgets.py`
- `reports.py`

### Service layer

Business logic lives in `backend/app/services/`.

This is where the real work happens:

- AWS sync
- findings detection
- recommendation generation
- budget evaluation
- report generation
- audit logging
- demo seeding

### Database layer

Database models live in `backend/app/models/`.

The models define the structure of the data stored in PostgreSQL.

### Migration layer

Alembic migrations in `backend/alembic/` keep the database schema in sync with the code.

## 10. Backend APIs

This project exposes a small set of backend APIs. They are grouped by feature so the frontend can call only the endpoints it needs.

### Health

- `GET /health`
- Simple service check that returns whether the backend is running.

### Authentication

- `POST /auth/register`
- Creates a new organization and the first user account.
- `POST /auth/login`
- Logs a user in and returns access and refresh tokens.
- `POST /auth/refresh`
- Creates a new token pair from a refresh token.
- `GET /auth/me`
- Returns the current logged-in user.
- `GET /auth/admin-check`
- Confirms that the current user has admin access.
- `POST /auth/teammates`
- Admin-only route that creates another user in the same organization.

### Organization

- `GET /organization/me`
- Returns the current organization and whether AWS credentials are connected.
- `PUT /organization/aws-connection`
- Admin-only route that saves or updates encrypted AWS credentials for the organization.
- `POST /organization/demo-seed`
- Admin-only route that loads demo data for the organization and resets the workspace to simulated data.

### Sync

- `POST /sync/run`
- Admin-only route that runs the AWS sync pipeline and stores cost, inventory, and telemetry data.

### Dashboard

- `GET /dashboard/summary`
- Returns current spend summary cards.
- `GET /dashboard/by-service`
- Returns grouped cost totals by AWS service.
- `GET /dashboard/by-region`
- Returns grouped cost totals by AWS region.
- `GET /dashboard/trend`
- Returns spend trend data by day or month.
- `GET /dashboard/resources`
- Returns the synced resource inventory table.

### Findings

- `GET /findings`
- Returns waste and risk findings with optional filters for type, severity, and status.

### Recommendations

- `GET /recommendations`
- Lists recommendation drafts and their current decision state.
- `POST /recommendations/{recommendation_id}/approve`
- Admin-only route that marks a recommendation as approved.
- `POST /recommendations/{recommendation_id}/reject`
- Admin-only route that marks a recommendation as rejected.

### Budgets

- `GET /budgets`
- Lists budgets for the current organization.
- `POST /budgets`
- Admin-only route that creates a new budget.
- `PUT /budgets/{budget_id}`
- Admin-only route that updates an existing budget.
- `GET /budgets/alerts`
- Returns triggered budget alerts.

### Reports

- `GET /reports/export`
- Exports the organization report as CSV or PDF.

## 11. Data Model

The most important tables are:

- `organizations`
- `users`
- `aws_connections`
- `cost_records`
- `cloud_resources`
- `metric_samples`
- `findings`
- `recommendations`
- `budgets`
- `alerts`
- `audit_logs`

### What each table stores

- `organizations`: tenant workspaces
- `users`: login accounts and roles
- `aws_connections`: encrypted AWS credentials per organization
- `cost_records`: synced cost rows from Cost Explorer
- `cloud_resources`: synced inventory records
- `metric_samples`: CPU and network telemetry
- `findings`: detected waste/risk issues
- `recommendations`: review actions linked to findings
- `budgets`: threshold rules for spend
- `alerts`: triggered budget alerts
- `audit_logs`: record of key actions

## 12. Sync Pipeline

The sync pipeline is one of the most important parts of the project.

### Inputs

- AWS Cost Explorer
- AWS resource inventory APIs
- AWS CloudWatch metrics

### Steps

1. read organization credentials
2. call AWS services
3. normalize the returned data
4. upsert rows into PostgreSQL
5. run findings detection
6. generate recommendations
7. evaluate budgets
8. return a sync summary to the dashboard

### Why upsert is used

The app uses upsert so repeated syncs do not duplicate data. If the same record already exists, it gets updated instead of inserted again.

### Why this matters

- sync can be run repeatedly
- the database stays clean and consistent
- the dashboard always reads current stored state

## 13. Findings Logic

Stage 4 introduced the findings engine.

### How a finding is created

The backend checks current data against rules.

For example:

- low CPU for a running EC2 instance can create an idle finding
- a volume with no attachment can create an unattached volume finding
- an Elastic IP with no association can create a waste finding

### What the evidence contains

Each finding stores evidence such as:

- average CPU percent
- sample count
- time window
- threshold values
- resource state
- explanatory note

This is important because the dashboard can show not just the result, but also why the system reached that result.

## 14. Recommendation Flow

Recommendations are built from findings.

### Purpose

The app does not perform AWS actions automatically. Instead, it creates a review item for a human to approve or reject.

### Example

If a finding says an EC2 instance is idle, the recommendation might say:

- review stopping the instance during idle periods
- consider an on-demand schedule

### Why this is safe

- the app only records intent
- nothing is changed in AWS automatically
- the user still has to make the real AWS change manually

## 15. Budget and Alert Flow

Budgets compare the current synced spend to a threshold.

### How it works

- admin creates a budget
- the backend stores the threshold
- sync or evaluation checks current spend
- if spend crosses the threshold, an alert is created

### Scope options

- total spend
- service spend
- region spend

### Why this matters

- the project now covers cost governance, not only detection
- it gives the dashboard a more complete FinOps-style workflow

## 16. Report Export

The reporting feature exports dashboard data outside the app.

### CSV

- simple structured export
- easy for spreadsheets and quick review

### PDF

- a polished shareable report
- contains summary, findings, and recommendations

### What it shows

- current month spend
- prior month spend
- top service
- findings
- recommendations

## 17. Demo Seed Mode

Demo seed mode is used when the user wants a working dashboard without connecting live AWS data.

### What it does

- clears the workspace data
- inserts demo resources, costs, and metrics
- runs findings detection
- generates recommendations

### Why it exists

- useful for presentations
- useful for testing the UI without AWS access
- useful for showing the project during development

## 18. Multitenancy

This is one of the most important design decisions.

### Meaning

Each organization has isolated data.

### Result

- org1 only sees org1 data
- org2 only sees org2 data
- AWS credentials are stored per organization
- dashboard results are filtered by organization id

### Why this is important for FYP

- it demonstrates real SaaS behavior
- it shows isolation and security design

## 19. Security Design

The project includes several safety choices:

- passwords are hashed
- AWS secrets are encrypted before storage
- tokens are used for session auth
- admin actions are protected by role checks
- the browser never talks to AWS directly
- report actions do not change AWS automatically

## 20. How To Explain It In Your Viva

If you need a short presentation summary, you can say:

> CloudCost Optimizer is a multi-tenant AWS cost analysis dashboard. The frontend shows data, but the backend owns all AWS communication, stores the results in PostgreSQL, and runs detection rules to generate findings and recommendations. Each organization has isolated credentials and isolated data, so the system behaves like a SaaS product.

## 21. Stage 4 Summary

By Stage 4, the project has:

- authentication and roles
- organization isolation
- AWS credential management
- manual and scheduled sync foundation
- live dashboard and inventory
- demo seed support
- findings detection with evidence
- resolved/open workflows for findings

That is the point where the app stops being just a starter project and becomes a real cloud cost intelligence system.
