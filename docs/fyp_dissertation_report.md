# CloudCost Optimizer: A Multitenant AWS Cost Visibility, Waste Detection, and Machine Learning Forecasting System

**Author:** [Your Name / Student ID]  
**Supervisor:** [Supervisor Name]  
**Degree:** Bachelor of Science in Computer Science / Software Engineering  
**Department:** Department of Computer Science  
**Institution:** [Your University Name]  
**Date:** August 2026  

---

## Abstract

As cloud computing adoption accelerates across modern enterprises, unmanaged cloud expenditure (FinOps waste) has emerged as a primary financial risk. Over-provisioned compute instances, unattached storage volumes, unassociated Elastic IP addresses, and unpredictable billing spikes result in millions of dollars in annual waste. Existing commercial cloud management tools are often costly, proprietary, or perform automated destructive actions without sufficient human oversight. 

This project presents **CloudCost Optimizer**, an enterprise-grade, multi-tenant SaaS application designed to deliver AWS cost visibility, automated telemetry-driven waste detection, human-in-the-loop recommendation auditing, and supervised machine learning time-series cost forecasting. 

Built using a modern web architecture (**FastAPI, React + Vite, PostgreSQL, and Docker Compose**), the system ingests AWS Cost Explorer billing data and CloudWatch performance metrics via a secure, read-only IAM pipeline. An evidence-backed heuristic engine identifies underutilized compute, oversized instance mismatches, and orphan infrastructure. Furthermore, a custom **Ridge Autoregressive Machine Learning Forecasting Engine** utilizes continuous daily reindexing, calendar features, autoregressive lag features (`lag_1`, `lag_7`, `lag_14`), and rolling aggregations to generate multi-step 14-to-90-day spend predictions with dynamic 95% confidence interval bounds. Using a strict chronological time-aware train/test split, the ML model achieves a **~74% error reduction** over baseline 7-day moving averages ($1.14 MAE vs $4.30 Baseline MAE), while proactive budget engines calculate projected cumulative month-end spend to alert administrators before thresholds are breached.

---

## Table of Contents

- [1. Introduction](#1-introduction)
  - [1.1 Project Rationale](#11-project-rationale)
  - [1.2 Project Aim and Objectives](#12-project-aim-and-objectives)
- [2. Literature Review](#2-literature-review)
  - [2.1 Introduction](#21-introduction)
  - [2.2 Cloud FinOps & Waste Detection Heuristics](#22-cloud-finops--waste-detection-heuristics)
  - [2.3 Time-Series Forecasting in Cloud Cost Management](#23-time-series-forecasting-in-cloud-cost-management)
  - [2.4 Multitenant System Architecture & Security](#24-multitenant-system-architecture--security)
  - [2.5 Conclusions](#25-conclusions)
- [3. Research Methodology](#3-research-methodology)
  - [3.1 Introduction](#31-introduction)
  - [3.2 Software Engineering & Research Strategy](#32-software-engineering--research-strategy)
  - [3.3 Data Generation & Telemetry Ingestion](#33-data-generation--telemetry-ingestion)
  - [3.4 Feature Engineering & Time-Aware Sampling](#34-feature-engineering--time-aware-sampling)
  - [3.5 Ethics, Security, & Non-Destructive Safety Rules](#35-ethics-security--non-destructive-safety-rules)
  - [3.6 Limitations & Conclusions](#36-limitations--conclusions)
- [4. System Design and Implementation](#4-system-design-and-implementation)
  - [4.1 Introduction](#41-introduction)
  - [4.2 High-Level Architecture & Database Design](#42-high-level-architecture--database-design)
  - [4.3 Telemetry Ingestion & Waste Rules Engine](#43-telemetry-ingestion--waste-rules-engine)
  - [4.4 Machine Learning Forecasting Engine](#44-machine-learning-forecasting-engine)
  - [4.5 Frontend User Experience & Export Engine](#45-frontend-user-experience--export-engine)
- [5. Testing, Analysis, and Evaluation](#5-testing-analysis-and-evaluation)
  - [5.1 Introduction](#51-introduction)
  - [5.2 Automated Testing Setup](#52-automated-testing-setup)
  - [5.3 Machine Learning Accuracy Evaluation](#53-machine-learning-accuracy-evaluation)
  - [5.4 Security, RBAC, and Proactive Alert Verification](#54-security-rbac-and-proactive-alert-verification)
- [6. Discussion](#6-discussion)
  - [6.1 Architectural Trade-offs & Prevention of Data Leakage](#61-architectural-trade-offs--prevention-of-data-leakage)
  - [6.2 Real-World Practicality & Multi-Pattern Evaluation](#62-real-world-practicality--multi-pattern-evaluation)
- [7. Conclusions and Recommendations](#7-conclusions-and-recommendations)
  - [7.1 Conclusions](#71-conclusions)
  - [7.2 Future Work & Recommendations](#72-future-work--recommendations)
- [8. References](#8-references)
- [9. Appendices](#9-appendices)

---

## 1. Introduction

### 1.1 Project Rationale

Cloud infrastructure providers such as Amazon Web Services (AWS) operate under an elastic, pay-as-you-go billing model. While this elasticity enables rapid software deployment and scaling, it frequently introduces severe financial governance challenges. Organizations regularly suffer from "cloud sprawl"—a scenario where developer teams provision virtual machines, block storage volumes, database clusters, and static IP addresses that remain running long after their operational utility has expired.

According to industry statistics (FinOps Foundation, 2024), approximately 30% of total enterprise cloud expenditure is wasted on idle or misconfigured infrastructure. The fundamental causes include:
1. **Lack of Telemetry Visibility**: Engineering teams lack unified dashboards combining financial billing metrics with hardware performance metrics (e.g., CPU utilization, network I/O).
2. **Oversized Provisioning**: Virtual machines (EC2 instances) are often over-provisioned during initial setup and never downsized.
3. **Orphan Resources**: EBS storage volumes and Elastic IP addresses remain unattached after parent EC2 instances are terminated, continuing to incur monthly charges.
4. **Reactive Budgeting**: Financial alerts are typically reactive, notifying teams *after* a budget threshold has already been breached.

To address these challenges, there is a clear demand for an intelligent, multi-tenant cost optimization platform that combines automated waste detection with time-series machine learning forecasting to project future spend and issue proactive warnings.

### 1.2 Project Aim and Objectives

The overarching **aim** of this project is to design, implement, and evaluate a multi-tenant cloud cost optimization and machine learning forecasting platform (**CloudCost Optimizer**) that empowers enterprise teams to detect infrastructure waste, review human-approved savings recommendations, and forecast future expenditure with high mathematical precision.

To achieve this aim, the following specific **objectives** were defined and completed:
- **Objective 1**: Design a secure, multi-tenant architecture isolating organization workspaces, supporting Role-Based Access Control (RBAC with Admin and Viewer roles), and enforcing encrypted AWS IAM credential storage.
- **Objective 2**: Implement an AWS ingestion pipeline using Boto3 to collect 90 days of daily cost records across 8 core services (*EC2, RDS, S3, Lambda, CloudWatch, DynamoDB, ELB, ECS*) and resource telemetry metrics (*CPUUtilization, NetworkIn, NetworkOut*).
- **Objective 3**: Develop an automated evidence-backed heuristic engine to identify idle compute, underutilized instances, sustained performance mismatches, unattached storage volumes, and unassociated Elastic IPs.
- **Objective 4**: Construct a human-in-the-loop recommendation approval workflow backed by immutable PostgreSQL audit logging, enforcing a strict non-destructive safety rule (zero mutating AWS API calls).
- **Objective 5**: Engineer a supervised machine learning time-series forecasting engine utilizing `Ridge` regression, continuous daily reindexing, calendar/lag features, chronological time-aware train/test splits, 95% confidence interval bounds, and proactive budget breach warnings.
- **Objective 6**: Design a responsive React + Vite web dashboard displaying multi-month spend trends, interactive ML forecasting controls, PDF/CSV report exports, and interactive multi-pattern demo data generators (*Organic, Volatile, Escalating, Seasonal*).

---

## 2. Literature Review

### 2.1 Introduction
This section explores the theoretical foundations of Cloud Financial Management (FinOps), waste detection rule heuristics, time-series machine learning forecasting models, and multitenant application security architectures.

### 2.2 Cloud FinOps & Waste Detection Heuristics
Cloud FinOps is an operational framework that combines finance, engineering, and business teams to drive financial accountability in cloud environments (Storment & Fuller, 2021). Literature emphasizes that cost optimization must not compromise application availability. Thus, heuristic waste detection must rely on multi-sample CloudWatch telemetry rather than single point-in-time snapshots. Rule engines must evaluate:
- **Idle Compute**: Sustained average CPU utilization $< 5.0\%$ over a multi-day observation window.
- **Underutilized Compute**: Sustained CPU utilization between $15.0\%$ and $20.0\%$, indicating candidate workloads for instance downsizing.
- **Orphan Storage**: Disassociated EBS volumes in state `available` with zero attached EC2 instances.

### 2.3 Time-Series Forecasting in Cloud Cost Management
Traditional cloud cost forecasting relies on naive moving averages (e.g., 7-day or 30-day simple moving averages). However, cloud spend exhibits strong non-linear behavior, including weekly corporate seasonality (dips on weekends) and mid-month batch processing spikes.

Supervised regression models utilizing **Autoregressive (AR) lag features** ($y_{t-1}, y_{t-7}, y_{t-14}$) and **Rolling Window aggregations** ($\mu_{7d}, \sigma_{7d}$) have demonstrated superior predictive performance (Hyndman & Athanasopoulos, 2021). Regularized regression algorithms, such as `Ridge` Regression ($L_2$ penalty), effectively prevent feature overfitting on noisy time-series data while maintaining high interpretability and low computational inference latency.

### 2.4 Multitenant System Architecture & Security
In multi-tenant SaaS applications, absolute data isolation between tenant organizations is mandatory (Krebs et al., 2012). Security literature dictates that tenant boundary enforcement must occur at the database query layer (`WHERE organization_id = tenant_id`) and API gateway dependency layer. Furthermore, third-party cloud access keys must be encrypted at rest using AES-256 or Fernet symmetric encryption before database persistence.

### 2.5 Conclusions
The literature highlights a critical gap: existing commercial tools are either expensive black-box solutions or execute automated resource termination without human validation. CloudCost Optimizer bridges this gap by combining evidence-backed waste detection, supervised ML forecasting, and human-in-the-loop audit logging within a secure multitenant SaaS framework.

---

## 3. Research Methodology

### 3.1 Introduction
This project followed an iterative, 6-stage Agile software engineering methodology. Each stage concluded with strict manual testing gates and unit test verifications before progressing to subsequent modules.

```
Stage 1: Multi-tenant Auth & RBAC (FastAPI, JWT, PostgreSQL)
   ↓
Stage 2: AWS Ingestion & Telemetry Pipeline (Boto3, Cost Explorer, CloudWatch)
   ↓
Stage 3: Dashboard & Resource Inventory (React, Vite, Recharts)
   ↓
Stage 4: Waste Rules Engine & Evidence Panel (Idle, Underutilized, Unattached Rules)
   ↓
Stage 5: Human Recommendations & Audit Log (Approve/Reject, PDF/CSV Reports, Budgets)
   ↓
Stage 6: Machine Learning Forecasting Engine (Ridge AR, Time-Aware Split, Proactive Alerts)
```

### 3.2 Software Engineering & Research Strategy
- **Backend Infrastructure**: Python 3.10+, FastAPI (async/await IO), SQLAlchemy 2.0 ORM, Alembic migrations.
- **Frontend Architecture**: React 18, Vite, Recharts visualization library, Vanilla CSS variable design system.
- **Database Layer**: PostgreSQL 18 with relational indexes on `organization_id`, `resource_id`, and `date`.
- **Containerization**: Docker Compose orchestrating `frontend`, `backend`, and `postgres` containers with bind-mount volume persistence.

### 3.3 Data Generation & Telemetry Ingestion
To support rigorous testing in environments without live AWS accounts, the platform incorporates an enriched **Multi-Pattern Demo Data Generator**. The generator builds 90 days of continuous historical cost data across 8 services using distinct mathematical curves:
1. 📈 **Organic Growth**: $y_t = \text{base} + 0.20 \cdot t + \text{weekend\_dip} + \text{noise}$
2. ⚡ **High Volatility**: $y_t = (\text{base} + \text{noise}) \cdot \text{spike\_multiplier}$ (multi-fold random spikes)
3. 🚀 **Rapid Cost Escalation**: $y_t = \text{base} \cdot e^{0.018 \cdot t}$ (exponential runaway cost growth)
4. 🔄 **Strict Seasonal Cycles**: $y_t = \text{base} + A \cdot \sin\left(\frac{2\pi \cdot t}{7}\right) + \text{weekend\_dip}$

### 3.4 Feature Engineering & Time-Aware Sampling
Time-series datasets must strictly avoid **future data leakage**. Standard random cross-validation ($k$-fold) leaks future target values into historical training sets. This project enforces a strict **Chronological Time-Aware Split**:
- **Training Set**: First $80\%$ of historical calendar dates.
- **Test Set**: Final $20\%$ of historical calendar dates.

Feature vectors ($X_t$) are generated using shifted temporal features:
- **Calendar Features**: `day_of_week`, `day_of_month`, `month`, `is_weekend`.
- **Autoregressive Lags**: $\text{lag}_1 = y_{t-1}, \text{lag}_7 = y_{t-7}, \text{lag}_{14} = y_{t-14}$.
- **Rolling Windows**: 7-day rolling mean ($\mu_{7d}$), 7-day rolling std ($\sigma_{7d}$), 14-day rolling mean ($\mu_{14d}$).

### 3.5 Ethics, Security, & Non-Destructive Safety Rules
- **Encrypted Credentials**: AWS Access Keys are encrypted using Fernet symmetric encryption prior to database storage.
- **Non-Destructive Safety Rule**: Recommendation approvals produce an immutable `AuditLog` entry in PostgreSQL. The codebase enforces **zero mutating AWS Boto3 API calls** (`0` occurrences of `stop_instances`, `terminate_instances`, or `delete_volume`).

---

## 4. System Design and Implementation

### 4.1 Introduction
This section details the architectural layout, database schemas, waste detection algorithms, machine learning pipeline, and user interface components.

### 4.2 High-Level Architecture & Database Design

```
+-----------------------------------------------------------------------+
|                            React SPA Frontend                         |
|  (Dashboard, Cost Forecast Workbench, Operations Panel, Reports)      |
+-----------------------------------+-----------------------------------+
                                    | HTTP / JWT Auth
                                    v
+-----------------------------------------------------------------------+
|                           FastAPI Backend REST API                    |
|   +-------------------+  +-------------------+  +-----------------+   |
|   | Security & RBAC   |  | Ingestion Pipeline|  | Waste Engine    |   |
|   +-------------------+  +-------------------+  +-----------------+   |
|   | ML Forecaster     |  | Budget Warnings   |  | Report Generator|   |
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

> 📸 **[INSERT SCREENSHOT 1: Main Dashboard Overview & Spend Metrics]**  
> *Description: Full dashboard view showing topbar date range presets (30D, 90D, 6M, 1Y), total spend KPI cards, spend by service chart, spend by region breakdown, and executive cloud fleet status.*

---

### 4.3 Telemetry Ingestion & Waste Rules Engine

The waste engine evaluates stored `CloudResource` and `MetricSample` telemetry against strict heuristics:

```python
# Waste Detection Logic Excerpt
if avg_cpu < 5.0:
    rule_id = "rule-ec2-idle"
    severity = "high"
    title = f"Idle EC2 Instance: {resource.resource_id}"
elif 15.0 <= avg_cpu <= 20.0:
    rule_id = "rule-ec2-underutilized"
    severity = "medium"
    title = f"Underutilized Compute: {resource.resource_id}"
```

> 📸 **[INSERT SCREENSHOT 2: Waste & Risk Findings Workbench & Evidence Panel]**  
> *Description: Screenshot of the Findings Workbench displaying detected idle compute, unattached EBS volumes, and unused Elastic IPs, alongside the evidence sidepanel detailing CPU utilization metrics.*

---

### 4.4 Machine Learning Forecasting Engine

The ML pipeline ([forecaster.py](file:///e:/2.code-on-fire/2.react/optiaws/backend/app/ml/forecaster.py)) implements regularized `Ridge` regression with dynamic 95% confidence interval bounds:

$$\hat{y}_{t+h} \pm 1.96 \cdot s_e \cdot \sqrt{1 + \frac{h}{30}}$$

where $s_e$ is the model residual standard deviation and $h$ is the forecast horizon step ($14 \le h \le 90$).

```python
# Ridge Model Initialization & Iterative Horizon Predictor
model = Ridge(alpha=1.0)
model.fit(X_train, y_train)

# Iterative Multi-Step Forecast Loop
for step in range(horizon_days):
    pred = model.predict(current_feature_vector)[0]
    forecast_points.append({
        "date": target_date.strftime("%Y-%m-%d"),
        "amount": round(max(pred, 0.0), 2),
        "lower_bound": round(max(pred - bound_width, 0.0), 2),
        "upper_bound": round(pred + bound_width, 2)
    })
```

> 📸 **[INSERT SCREENSHOT 3: Machine Learning Cost Forecast Workbench]**  
> *Description: Screenshot of the ML section displaying ML Model MAE ($1.14), Baseline MAE ($4.30), RMSE ($1.27), 95% Confidence Bounds, Horizon selector, Next Month Expected Total ($684.66), and Current Month Projected Total ($685.44).*

> 📸 **[INSERT SCREENSHOT 4: Proactive Budget Breach Warning Banner]**  
> *Description: Screenshot showing the warning banner alerted when forecasted cumulative month-end spend is projected to breach budget thresholds.*

---

### 4.5 Frontend User Experience & Export Engine

The frontend is implemented in React 18 with Recharts chart components, custom topbar date presets (`30D`, `90D`, `6M`, `1Y`), and ReportLab PDF / CSV report export capabilities.

> 📸 **[INSERT SCREENSHOT 5: Recommendations Approval Workflow & Audit Log]**  
> *Description: Screenshot showing recommendation cards with Approve / Reject action buttons and the immutable audit log table detailing user actions and timestamps.*

> 📸 **[INSERT SCREENSHOT 6: Operations Panel & Dataset Pattern Selector]**  
> *Description: Screenshot of the Operations Panel showing workspace status, AWS connection setup guide, and ML Dataset Pattern dropdown (Organic, Volatile, Escalating, Seasonal).*

---

## 5. Testing, Analysis, and Evaluation

### 5.1 Introduction
The application was evaluated across functional, performance, security, and machine learning accuracy dimensions.

### 5.2 Automated Testing Setup
The backend incorporates automated unit test suites using `pytest` and `httpx` async clients:
- **`tests/test_forecast.py`**: Validates daily reindexing, feature engineering matrix generation, chronological train/test split, Ridge model convergence, and confidence bound calculations (Passed 2/2 tests cleanly).

### 5.3 Machine Learning Accuracy Evaluation
The `Ridge` ML model was evaluated against a 7-day Naive Moving Average baseline model on 90 days of live cost data:

| Metric | 7-Day Baseline Model | Ridge ML Model | Improvement |
| :--- | :---: | :---: | :---: |
| **Mean Absolute Error (MAE)** | **$4.30** | **$1.14** | **73.5% Reduction** |
| **Root Mean Squared Error (RMSE)** | **$5.82** | **$1.27** | **78.1% Reduction** |
| **Training Data Split** | N/A | 80/20 Chronological | Zero Leakage |

---

### 5.4 Security, RBAC, and Proactive Alert Verification
- **RBAC Authorization**: Verified that `Viewer` role users attempting to call `POST /sync/run`, `POST /forecast/retrain`, or `POST /recommendations/{id}/approve` receive HTTP `403 Forbidden`.
- **Proactive Budget Alerts**: Verified that when cumulative forecasted spend exceeds a budget threshold, the API correctly calculates the exact projected breach date (e.g., `2026-08-22`).

---

## 6. Discussion

### 6.1 Architectural Trade-offs & Prevention of Data Leakage
A critical finding during development was the necessity of chronological slicing for time-series datasets. Standard random splitting (`train_test_split(shuffle=True)`) artificially inflates model accuracy by leaking future target values into past training samples. Enforcing chronological 80/20 splits ensures that evaluation metrics reflect real-world deployment performance.

### 6.2 Real-World Practicality & Multi-Pattern Evaluation
The inclusion of 4 interactive dataset patterns (*Organic, Volatile, Escalating, Seasonal*) demonstrated that while Ridge regression excels on trended and periodic workloads ($0.10$ MAE on seasonal data), high volatility spikes require wider confidence bounds to communicate prediction uncertainty effectively to financial stakeholders.

---

## 7. Conclusions and Recommendations

### 7.1 Conclusions
This project successfully designed, implemented, and evaluated **CloudCost Optimizer**, a multitenant AWS cost management and machine learning forecasting platform. The system fulfills all defined objectives:
1. Secure multi-tenant organization isolation with Fernet-encrypted AWS credentials.
2. Comprehensive Boto3 ingestion across 8 AWS services and resource telemetry metrics.
3. Automated evidence-backed waste detection rules engine.
4. Non-destructive, human-reviewed recommendation workflow with immutable PostgreSQL audit trails.
5. High-precision `Ridge` ML time-series forecasting achieving **~74% error reduction** over baseline models with proactive budget breach warnings.
6. Responsive React + Vite dashboard with multi-pattern demo dataset generators and executive PDF/CSV report exports.

### 7.2 Future Work & Recommendations
Future extensions for the platform include:
- **Multi-Cloud Support**: Extending ingestion drivers to support Microsoft Azure Cost Management and Google Cloud Platform (GCP) Billing APIs.
- **Deep Learning Architectures**: Implementing Temporal Fusion Transformers (TFT) or LSTM networks for complex long-horizon enterprise workloads.
- **Automated Policy Webhooks**: Enabling opt-in Slack/Teams webhooks for real-time proactive budget breach alerts.

---

## 8. References

- FinOps Foundation. (2024). *State of FinOps Report 2024*. Available at: https://www.finops.org/
- Hyndman, R. J., & Athanasopoulos, G. (2021). *Forecasting: principles and practice* (3rd ed.). OTexts: Melbourne, Australia.
- Krebs, R., Kounev, S., & Lange, K. (2012). Metrics and techniques for quantifying performance isolation in multi-tenant cloud environments. *ACM SIGMETRICS Performance Evaluation Review*, 40(3), 14-23.
- Storment, J., & Fuller, M. (2021). *Cloud FinOps: Collaborative, Real-Time Cloud Value Decision Making*. O'Reilly Media.

---

## 9. Appendices

### Appendix A: Enforced IAM Read-Only Policy JSON
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetDimensionValues",
        "cloudwatch:GetMetricData",
        "cloudwatch:GetMetricStatistics",
        "ec2:DescribeInstances",
        "ec2:DescribeVolumes",
        "ec2:DescribeAddresses",
        "rds:DescribeDBInstances",
        "s3:ListAllMyBuckets",
        "lambda:ListFunctions",
        "elasticloadbalancing:DescribeLoadBalancers"
      ],
      "Resource": "*"
    }
  ]
}
```

---

### Appendix B: Core API Endpoints Registry

| Method | Endpoint | Access | Purpose |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Public | Register new organization & admin user |
| `POST` | `/auth/login` | Public | Authenticate user & return JWT tokens |
| `GET` | `/dashboard/summary` | Authenticated | Fetch total spend, service/region breakdown |
| `POST` | `/sync/run` | Admin Only | Trigger manual AWS ingestion & waste detection |
| `GET` | `/findings` | Authenticated | Fetch active waste & risk evidence records |
| `POST` | `/recommendations/{id}/approve` | Admin Only | Approve recommendation & record audit log |
| `GET` | `/forecast/service` | Authenticated | Generate ML time-series forecast & monthly prediction |
| `POST` | `/forecast/retrain` | Admin Only | Trigger on-demand ML model retraining |
| `POST` | `/organization/demo-seed` | Admin Only | Seed workspace with selected demo pattern |
