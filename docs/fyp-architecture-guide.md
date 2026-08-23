# FYP Architecture Guide & Technical Explainer

This document provides a simple, comprehensive explanation of how **CloudCost Optimizer** works across all 6 stages. It is designed to be easily understood and presented during a Final-Year Project (FYP) demonstration or viva examination.

---

## 1. Core Project Idea

CloudCost Optimizer is a multi-tenant AWS Cloud Financial Management (FinOps) application. Its primary goal is to help software organizations:

1. **Connect AWS Accounts Safely**: Ingest AWS billing and hardware performance metrics using a secure, read-only IAM policy.
2. **Detect Infrastructure Waste & Risk**: Automatically analyze CloudWatch telemetry (CPU utilization, network traffic) and resource status (unattached EBS volumes, unassociated Elastic IPs) to pinpoint wasted spend.
3. **Audit Human-Approved Recommendations**: Provide a human-in-the-loop recommendation workflow backed by immutable audit trails, enforcing a strict **non-destructive safety rule** (zero mutating AWS API calls).
4. **Forecast Future Spend with ML**: Use supervised machine learning to project 14-to-90-day future costs with statistical confidence bounds.
5. **Issue Proactive Budget Breach Alerts**: Alert financial administrators before month-end budgets are exceeded.

### The Fundamental Architectural Principle
> **All AWS data is collected by the FastAPI backend, stored in PostgreSQL, and served to the React frontend over authenticated REST APIs.**

The browser **never** talks directly to AWS. The backend performs secure ingestion, business logic, waste detection, and ML forecasting, while the frontend serves as an interactive dashboard.

---

## 2. Essential Concepts Made Simple

If you understand these 8 core terms, the entire system makes complete sense:

* **Multitenancy**: Isolating data so Organization A can never see Organization B's AWS costs (`WHERE organization_id = tenant_id`).
* **Telemetry**: Measured performance metrics over time (e.g., average CPU utilization $\%$, network bytes in/out).
* **Heuristic Rules Engine**: Automated rules that check telemetry against threshold bands (e.g., sustained CPU $< 5.0\%$ indicates idle compute).
* **Non-Destructive Safety Rule**: The system generates recommendation advice, but **never** deletes or stops AWS resources automatically. An admin must approve actions, creating an immutable audit log entry.
* **Autoregressive (AR) Lags**: Using past spend values ($\text{lag}_1 = \text{yesterday}$, $\text{lag}_7 = \text{last week}$) as inputs to predict tomorrow's spend.
* **Fourier Seasonal Harmonics**: Using mathematical sine ($\sin_7$) and cosine ($\cos_7$) waves to model repeating 7-day weekly calendar cycles so prediction lines never flatten out.
* **Chronological Time-Aware Split**: Training the ML model on the first $80\%$ of dates and testing on the final $20\%$ of dates. This guarantees **zero future data leakage** (unlike random shuffling).
* **Statistical Confidence Bounds**: Displaying an upper and lower boundary around the forecast line to show potential spend volatility risk.

---

## 3. High-Level Architecture (The 4 Layers)

```text
+-----------------------------------------------------------------------+
|                            React SPA Frontend                         |
|  (Dashboard, Cost Forecast Workbench, Operations Panel, Reports)      |
+-----------------------------------+-----------------------------------+
                                    | HTTP / JWT Auth
                                    v
+-----------------------------------------------------------------------+
|                           FastAPI Backend REST API                    |
|   +-------------------+  +-------------------+  +-----------------+   |
|   | Security & RBAC   |  | Ingestion Pipeline|  | Telemetry Engine|   |
|   +-------------------+  +-------------------+  +-----------------+   |
|   | Ridge ML Forecaster| | Budget Warnings   |  | Report Generator|   |
|   +-------------------+  +-------------------+  +-----------------+   |
+-----------------------------------+-----------------------------------+
                                    | AsyncPG SQLAlchemy ORM
                                    v
+-----------------------------------------------------------------------+
|                          PostgreSQL 18 Database                        |
| (organizations, users, cost_records, cloud_resources, findings,      |
|  recommendations, budgets, audit_logs, metric_samples)                |
+-----------------------------------------------------------------------+
```

1. **Frontend (`frontend/`)**: Built with React 18, Vite, and Recharts. Renders interactive KPI cards, service spend charts, waste evidence panels, ML forecast controls, and report downloads.
2. **Backend (`backend/`)**: Built with Python 3.10+ and FastAPI. Handles authentication, Boto3 AWS ingestion, telemetry checks, Ridge ML training/forecasting, and PDF export.
3. **Database (`postgres`)**: PostgreSQL 18 storing org-scoped cost records, inventory, findings, recommendations, budgets, and immutable audit logs.
4. **Docker Compose (`docker-compose.yml`)**: Orchestrates `frontend`, `backend`, and `postgres` with live volume mounts for immediate local synchronization.

---

## 4. How the Machine Learning Forecasting Engine Works (Deep Dive)

### Why Did We Build the ML Forecaster This Way?

Many commercial cloud tools use simple 7-day moving averages ($y_t = \frac{1}{7}\sum y_{t-i}$). However, moving averages lag behind sudden trends and cannot predict future calendar cycles. On the other hand, complex deep learning models (like LSTMs or Transformers) require heavy GPUs, huge datasets, and operate as uninterpretable "black boxes".

We chose **Supervised `Ridge` Regression** ($L_2$ regularized least squares) for five clear engineering reasons:

1. **Sub-15ms Speed**: Trains and generates 90-day predictions in under $15\text{ms}$ on CPU directly inside the FastAPI request handler.
2. **Overfitting Prevention ($L_2$ Regularization)**: Cloud spend has noisy batch processing spikes. The $L_2$ penalty ($\alpha=0.1$) shrinks regression weights to prevent isolated spikes from corrupting long-term trend predictions.
3. **Autoregressive Feature Vector ($X_t$)**:
   - `lag_1` ($y_{t-1}$): Yesterday's spend.
   - `lag_7` ($y_{t-7}$): Spend from 7 days ago (captures weekly corporate cycles).
   - `lag_14` ($y_{t-14}$): Spend from 14 days ago.
   - `rolling_7d_mean` ($\mu_{7d}$): 7-day rolling average spend.
   - `rolling_7d_std` ($\sigma_{7d}$): 7-day rolling volatility.
4. **Trigonometric Fourier Harmonics ($\sin_7, \cos_7$)**:
   - *The Problem*: Linear features like `day_of_week` ($0 \dots 6$) treat Sunday ($6$) as $6 \times$ Monday ($0$), which is mathematically incorrect for cyclical time series and causes multi-step forecasts to damp out into a flat line.
   - *The Solution*: We calculate $\text{sin}_7 = \sin\left(\frac{2\pi \cdot \text{day\_of\_week}}{7}\right)$ and $\text{cos}_7 = \cos\left(\frac{2\pi \cdot \text{day\_of\_week}}{7}\right)$. This forms a continuous circular wave that repeats endlessly into the future, ensuring the prediction curve maintains crisp periodic weekly waves ($4.27 \to 22.60 \to 4.27$).
5. **Zero Data Leakage (Chronological 80/20 Split)**:
   - Standard random shuffling (`train_test_split(shuffle=True)`) leaks future spend into past training samples, yielding fake $99\%$ accuracy.
   - Our pipeline trains strictly on the first $80\%$ of calendar dates and tests on the final $20\%$ of dates, mirroring real-world deployment.

### Why the dashboard sometimes shows `Fallback Zero`

When a real AWS organization has only a very small amount of billing history, the backend deliberately avoids pretending that a serious ML forecast exists. If fewer than about 7 daily points are available, the service returns a safe fallback response named `Fallback Zero`. This is an honest engineering choice: the chart still renders, but the app clearly shows that the model does not yet have enough data to train a trustworthy forecast. As more synced days accumulate, the dashboard automatically transitions from fallback mode to the full Ridge forecasting path.

### ML Accuracy Benchmark Result:
$$\text{Baseline 7-Day MAE: } \$4.30 \quad \longrightarrow \quad \text{\bfseries Ridge ML Model MAE: } \mathbf{\$1.14} \quad (\mathbf{73.5\% \text{ Error Reduction}})$$

---

## 5. End-to-End Data Flow

1. **Ingestion**: Admin triggers sync or periodic scheduler runs. FastAPI calls Boto3 (`ce:GetCostAndUsage`, `cloudwatch:GetMetricData`, `ec2:DescribeInstances`).
2. **Idempotent Upsert**: Cost rows and resources are written to PostgreSQL using natural key unique constraints (`organization_id`, `service`, `date`), preventing duplicate rows on re-sync.
3. **Waste Detection**: Telemetry rules evaluate CloudWatch CPU metrics:
   - Average CPU $< 5.0\% \to$ High severity Idle Compute finding.
   - Average CPU $15.0\% - 20.0\% \to$ Medium severity Underutilized Compute finding.
   - Unattached EBS volumes ($state = \text{available}$) $\to$ High severity Orphan Storage finding.
4. **Recommendation Audit**: Findings create Recommendation cards. An admin clicks **Approve** or **Reject**. Approvals record an entry in PostgreSQL `AuditLog` (enforcing zero mutating AWS API calls).
5. **ML Training \& Prediction**: When the frontend requests `/forecast/service`, FastAPI pulls org cost records, constructs the feature matrix, trains `Ridge(alpha=0.1)` on the first $80\%$ dates, evaluates MAE/RMSE on the final $20\%$ test dates, and generates an iterative multi-step 14-to-90-day forecast.
6. **Proactive Budget Warning**: If the sum of actuals + remaining ML forecast exceeds the user's monthly budget threshold, a warning banner alerts administrators before month end.
7. **Budget Scope Simplification**: The current budget creator supports `total` and `service` scopes only. Service names come from synced AWS services through a dropdown, which avoids typo-prone free-text budget creation.

---

## 6. Complete 6-Stage Development Summary

* **Stage 0: Foundation**: Docker Compose, React scaffolding, FastAPI setup, PostgreSQL database, JWT secret configuration.
* **Stage 1: Multitenant Auth \& RBAC**: User registration, login, JWT refresh tokens, Organization tenant isolation, Admin vs Viewer role permissions.
* **Stage 2: Ingestion Pipeline**: Boto3 AWS Cost Explorer, CloudWatch telemetry, EC2/EBS/RDS/S3 inventory collection, Fernet credential encryption, idempotent upserts.
* **Stage 3: Executive Dashboard**: React Recharts cost visualization, service/region spend breakdowns, inventory tables, topbar date range presets (`30D`, `90D`, `6M`, `1Y`).
* **Stage 4: Waste \& Risk Engine**: Evidence-backed heuristic rules, CPU band analysis, orphan volume detection, evidence sidepanel, finding resolution history.
* **Stage 5: Recommendations, Budgets \& Reports**: Human-in-the-loop recommendation workflow, PostgreSQL audit logging, non-destructive safety rule enforcement, budget threshold tracking, executive PDF/CSV exports, and a simplified Total/Service budget workflow.
* **Stage 6: Machine Learning Forecasting Engine**: `Ridge` regularized time-series forecasting, Fourier seasonal harmonics ($\sin_7, \cos_7$), chronological 80/20 train/test split, statistical confidence bounds, proactive budget breach alerts, retrain API, 4-pattern demo data generators (*Organic, Volatile, Escalating, Seasonal*).
