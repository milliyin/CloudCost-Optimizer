# Architecture Overview

## Final Production Architecture (Stages 0–6 Complete)

CloudCost Optimizer is a multitenant cloud financial management and machine learning forecasting platform.

### Component Layers

1. **Frontend (`frontend/`)**:
   - Built with React 18, Vite, and Recharts.
   - Routes for authentication, persistent JWT session handling, Organization tenant management, and live AWS onboarding with embedded IAM policy JSON.
   - Interactive Dashboard: KPI cards, service spend charts, spend by region, inventory tables, topbar date range presets (`30D`, `90D`, `6M`, `1Y`).
   - Waste Findings Workbench: Filterable finding cards, CPU telemetry evidence sidepanel, resolved finding history.
   - Human Recommendation Workflow: Approve / Reject action cards backed by non-destructive safety rules and audit logging.
   - Machine Learning Cost Forecast Workbench: Ridge ML model controls, horizon selectors (`14D`, `30D`, `60D`, `90D`), model metric cards (ML MAE vs Baseline MAE, RMSE), statistical confidence bounds visualization, retrain controls, and readable in-app backend error handling.
   - Operations Panel: Multi-pattern dataset pattern selector (*Organic Growth, High Volatility, Rapid Escalation, Strict Seasonal*).
   - Export Engine: Executive PDF and CSV report downloads.

2. **Backend (`backend/`)**:
   - Built with Python 3.10+ and FastAPI.
   - Async endpoints for authentication, token refresh, organization management, dashboard summary, findings, recommendations, budgets, reports, and forecasting.
   - Security \& Encryption: Fernet symmetric encryption for stored AWS keys, RBAC role validation dependencies (`require_role(UserRole.ADMIN)`).
   - Ingestion Pipeline: Boto3 AWS Cost Explorer client (`ce:GetCostAndUsage`), resource inventory collectors (`ec2`, `rds`, `s3`, `lambda`, `elb`, `ecs`, `dynamodb`), and CloudWatch telemetry collectors (`cloudwatch:GetMetricData`).
   - Waste Detection Rules Engine: Sustained CPU telemetry band analysis ($< 5.0\%$ idle compute, $15\%-20\%$ underutilized compute), orphan volume detection ($state = \text{available}$).
   - Machine Learning Forecasting Engine (`app/ml/forecaster.py` \& `app/ml/feature_engineering.py`): Continuous daily reindexing, 7-day Fourier seasonal harmonics ($\sin_7, \cos_7$), autoregressive lag features (`lag_1`, `lag_7`, `lag_14`), rolling aggregations ($\mu_{7d}, \sigma_{7d}$), regularized `Ridge(alpha=0.1)` regression model, 80/20 chronological time-aware train/test split validation, statistical confidence bounds calculations, proactive budget breach warnings, and a guarded low-history `Fallback Zero` path when the cost series is still too sparse to train a trustworthy model.

3. **Database (`postgres`)**:
   - PostgreSQL 18 relational database managed via SQLAlchemy 2.0 ORM and Alembic migrations.
   - Tables: `organizations`, `users`, `aws_connections`, `cost_records`, `cloud_resources`, `metric_samples`, `findings`, `recommendations`, `budgets`, `alerts`, and `audit_logs`.
   - All query paths enforce tenant boundary isolation (`WHERE organization_id = tenant_id`).

4. **Containerization (`docker-compose.yml`)**:
   - Docker Compose orchestrating `frontend`, `backend`, and `postgres` containers with live host-to-container volume mounts (`./backend:/app` and `./frontend:/app`).

---

## End-to-End Data Flow

1. Admin saves AWS credentials or seeds workspace with selected demo pattern.
2. Ingestion job collects Cost Explorer billing data, resource inventory, and CloudWatch performance telemetry.
3. Billing rows and resources are upserted into PostgreSQL using natural unique key constraints to ensure idempotency.
4. Waste detection rules evaluate telemetry metrics and generate evidence records.
5. Recommendation cards are generated for review. Approvals record immutable entries in PostgreSQL `AuditLog` (enforcing zero mutating AWS API calls).
6. Machine learning forecasting engine trains a regularized `Ridge` time-series model on historical cost records, evaluates accuracy against moving average baselines, and returns multi-step horizon predictions with statistical confidence bounds.
7. If the synced billing history is too short, the forecast API returns a safe fallback response instead of pretending a low-sample prediction is meaningful.
8. Proactive budget engines check cumulative predicted spend against thresholds and emit alert warnings before month end.
