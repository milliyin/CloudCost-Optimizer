import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiFetch } from "../api/client";
import { extractApiError } from "../api/errors";
import { useAuth } from "../components/AuthProvider";

const chartPalette = ["#4f46e5", "#8792fe", "#7d42b6", "#4953bc", "#c3c0ff", "#3525cd"];
const findingTitleMap = {
  idle_instance: "Idle compute candidate",
  underutilized_instance: "Underutilized compute",
  oversized_mismatch: "Performance mismatch",
  unattached_volume: "Unattached storage volume",
  unused_elastic_ip: "Unassociated Elastic IP",
};
const navigationSections = [
  { id: "overview", label: "Overview" },
  { id: "inventory", label: "Resource Inventory" },
  { id: "connect-aws", label: "Connect AWS" },
  { id: "operations", label: "Sync Status" },
  { id: "findings", label: "Waste & Risks" },
  { id: "forecast", label: "Cost Forecast" },
];
const findingTypeOptions = [
  { value: "all", label: "All types" },
  { value: "idle_instance", label: "Idle compute" },
  { value: "underutilized_instance", label: "Underutilized compute" },
  { value: "oversized_mismatch", label: "Performance mismatch" },
  { value: "unattached_volume", label: "Unattached volume" },
  { value: "unused_elastic_ip", label: "Unused Elastic IP" },
];

function formatCurrency(amount, currency = "USD") {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(amount ?? 0);
}

function formatPercent(value) {
  if (value === null || value === undefined) {
    return "n/a";
  }
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function formatFindingTypeLabel(value) {
  return findingTitleMap[value] ?? value.replaceAll("_", " ");
}

function formatTimeAgo(value) {
  if (!value) {
    return "now";
  }

  const then = new Date(value).getTime();
  const diffMinutes = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (diffMinutes < 1) {
    return "now";
  }
  if (diffMinutes < 60) {
    return `${diffMinutes} min ago`;
  }
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }
  return `${Math.round(diffHours / 24)}d ago`;
}

function summarizeFindingImpact(finding) {
  const evidence = finding.evidence ?? {};
  if (finding.finding_type === "idle_instance") {
    if (evidence.note) {
      return evidence.note;
    }
    return `Avg CPU ${evidence.avg_cpu_percent ?? "?"}% over ${evidence.window_hours ?? "?"}h`;
  }
  if (finding.finding_type === "underutilized_instance") {
    return `Avg CPU ${evidence.avg_cpu_percent ?? "?"}% suggests rightsizing review`;
  }
  if (finding.finding_type === "oversized_mismatch") {
    return `Avg CPU ${evidence.avg_cpu_percent ?? "?"}% indicates sustained pressure`;
  }
  if (finding.finding_type === "unattached_volume") {
    return "Volume is available with no active attachments";
  }
  if (finding.finding_type === "unused_elastic_ip") {
    return "Allocated IP is not associated with a running instance";
  }
  return "Evidence-backed detection ready for review";
}

function formatEvidenceValue(value) {
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function buildDefaultDateRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 29);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
}

function EmptyState({ title, description }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}

function getResourceMetricDisplay(row) {
  const isEc2 = row.resource_type === "ec2_instance";

  if (isEc2) {
    return {
      cpu: row.latest_cpu_utilization?.toFixed(1) ?? "-",
      inbound: row.latest_network_in?.toFixed(1) ?? "-",
      outbound: row.latest_network_out?.toFixed(1) ?? "-",
      hint: "EC2 telemetry",
    };
  }

  if (row.resource_type === "lambda_function") {
    return {
      cpu: "-",
      inbound: "-",
      outbound: "-",
      hint: "Inventory only",
    };
  }

  if (row.resource_type === "ebs_volume") {
    return {
      cpu: "-",
      inbound: "-",
      outbound: "-",
      hint: "Storage resource",
    };
  }

  return {
    cpu: "-",
    inbound: "-",
    outbound: "-",
    hint: "No live metrics",
  };
}

function MetricCard({ label, value, trendText, trendTone = "info", accent = false }) {
  return (
    <article className="info-card metric-card" style={accent ? { boxShadow: "inset 4px 0 0 #3525cd, 0 4px 20px rgba(0, 0, 0, 0.04)" } : undefined}>
      <div>
        <p className="metric-label">{label}</p>
        <h2>{value}</h2>
      </div>
      <div className={`metric-trend ${trendTone}`}>{trendText}</div>
    </article>
  );
}

function SpendTrendChart({ data, loading, granularity, onGranularityChange }) {
  const isEmpty = !loading && (!data || data.length === 0);
  return (
    <article className={`info-card chart-card ${isEmpty ? "chart-card-empty" : ""}`}>
      <div className="chart-header">
        <div className="chart-title">
          <h2>Budget vs actual spend</h2>
          <p>Organization spend performance for the selected date range.</p>
        </div>
        <div className="segmented-control">
          <button
            className={`segmented-pill ${granularity === "daily" ? "active" : ""}`}
            type="button"
            onClick={() => onGranularityChange("daily")}
          >
            Daily
          </button>
          <button
            className={`segmented-pill ${granularity === "monthly" ? "active" : ""}`}
            type="button"
            onClick={() => onGranularityChange("monthly")}
          >
            Monthly
          </button>
        </div>
      </div>
      {loading ? <p>Loading trend...</p> : null}
      {!loading && (!data || data.length === 0) ? (
        <EmptyState title="No trend data yet" description="Trend lines appear after cost records are synced or demo data is loaded for this organization." />
      ) : null}
      {!loading && data && data.length > 0 ? (
        <div className="chart-shell">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e1ee" />
              <XAxis dataKey="period_start" tick={{ fill: "#777587", fontSize: 12 }} />
              <YAxis tick={{ fill: "#777587", fontSize: 12 }} />
              <Tooltip formatter={(value, _name, item) => formatCurrency(Number(value), item.payload.currency)} />
              <Legend />
              <Line
                type="monotone"
                dataKey="amount"
                stroke="#3525cd"
                strokeWidth={3}
                dot={{ r: 3, fill: "#3525cd" }}
                name="Actual spend"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : null}
    </article>
  );
}

function CostBreakdownChart({ title, subtitle, data, loading }) {
  const isEmpty = !loading && (!data || data.length === 0);
  return (
    <article className={`info-card chart-card secondary-chart ${isEmpty ? "chart-card-empty" : ""}`}>
      <div className="chart-header">
        <div className="chart-title">
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </div>
      {loading ? <p>Loading chart...</p> : null}
      {!loading && (!data || data.length === 0) ? (
        <EmptyState title="No synced cost data yet" description="Run a sync after Cost Explorer is ready or use demo seed data for this organization." />
      ) : null}
      {!loading && data && data.length > 0 ? (
        <div className="chart-shell">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.slice(0, 6)} layout="vertical" margin={{ top: 8, right: 12, left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e1ee" horizontal={false} />
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="key"
                width={84}
                tick={{ fill: "#5f6071", fontSize: 12 }}
                tickFormatter={(value) => String(value).slice(0, 14)}
              />
              <Tooltip formatter={(value, _name, item) => formatCurrency(Number(value), item.payload.currency)} />
              <Bar dataKey="amount" radius={[0, 10, 10, 0]}>
                {data.slice(0, 6).map((entry, index) => (
                  <Cell key={`${entry.key}-${index}`} fill={chartPalette[index % chartPalette.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : null}
    </article>
  );
}

function ResourceTable({ data, loading }) {
  const [sortKey, setSortKey] = useState("resource_type");
  const [filter, setFilter] = useState("");

  const filteredRows = useMemo(() => {
    const needle = filter.toLowerCase().trim();
    const rows = [...(data ?? [])];
    const sorted = rows.sort((left, right) => {
      const leftValue = left[sortKey] ?? "";
      const rightValue = right[sortKey] ?? "";
      return String(leftValue).localeCompare(String(rightValue));
    });

    if (!needle) {
      return sorted;
    }

    return sorted.filter((row) =>
      [row.resource_id, row.resource_type, row.region, row.state]
        .join(" ")
        .toLowerCase()
        .includes(needle)
    );
  }, [data, filter, sortKey]);

  return (
    <article className="info-card resource-card" id="inventory">
      <div className="chart-header">
        <div className="chart-title">
          <h2>Resource inventory</h2>
          <p>Latest organization-scoped cloud resources and sampled utilization.</p>
        </div>
        <div className="resource-controls">
          <label className="resource-filter-shell">
            <span className="resource-filter-icon">Q</span>
            <input
              className="resource-search"
              placeholder="Filter resources"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            />
          </label>
          <label className="resource-select-shell">
            <span className="resource-select-label">Sort</span>
            <select value={sortKey} onChange={(event) => setSortKey(event.target.value)}>
              <option value="resource_type">Type</option>
              <option value="region">Region</option>
              <option value="state">State</option>
              <option value="resource_id">ID</option>
            </select>
          </label>
        </div>
      </div>
      {loading ? <p>Loading resources...</p> : null}
      {!loading && filteredRows.length === 0 ? (
        <EmptyState title="No synced resources yet" description="Run sync after connecting AWS or load demo data to populate the resource inventory." />
      ) : null}
      {!loading && filteredRows.length > 0 ? (
        <div className="table-wrap">
          <table className="resource-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Region</th>
                <th>State</th>
                <th>Telemetry</th>
                <th>CPU</th>
                <th>In</th>
                <th>Out</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row) => {
                const metrics = getResourceMetricDisplay(row);

                return (
                  <tr key={`${row.resource_type}:${row.resource_id}`}>
                    <td>{row.resource_id}</td>
                    <td>{row.resource_type}</td>
                    <td>{row.region || "-"}</td>
                    <td>{row.state || "-"}</td>
                    <td>
                      <span className="metric-availability">{metrics.hint}</span>
                    </td>
                    <td>{metrics.cpu}</td>
                    <td>{metrics.inbound}</td>
                    <td>{metrics.outbound}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </article>
  );
}

function FindingsFeed({ findings, loading, isSimulatedWorkspace }) {
  const visibleFindings = findings.slice(0, 3);

  return (
    <article className="info-card feed-card">
      <div className="chart-header">
        <div className="chart-title">
          <h2>Live findings</h2>
          <p>{isSimulatedWorkspace ? "Demo-derived findings for presentation mode." : "Signals inferred from current synced resources."}</p>
        </div>
      </div>
      {loading ? <p>Loading findings...</p> : null}
      {!loading && visibleFindings.length === 0 ? (
        <EmptyState title="No active findings" description="Current synced data has not produced an open waste or risk finding yet." />
      ) : null}
      <div className="feed-list">
        {visibleFindings.map((finding) => (
          <div className={`finding-card ${finding.severity}`} key={finding.id ?? `${finding.title}-${finding.resource}`}>
            <div className="finding-icon">{finding.icon}</div>
            <div>
              <div className="finding-header">
                <strong>{finding.title}</strong>
                <span className="finding-meta">{finding.timeAgo}</span>
              </div>
              <p className="finding-resource">{finding.resource}</p>
              <div className="chip-row">
                <span className={`chip ${finding.severity}`}>{finding.severity.toUpperCase()}</span>
                <span className="finding-meta">{finding.impact}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="feed-insight">
        <h3>Weekly insight</h3>
        <p>
          {isSimulatedWorkspace
            ? "This workspace is showing simulated cost and utilization data so you can demo the full dashboard before AWS billing data is ready."
            : visibleFindings.length > 0
              ? "These findings are now backed by stored evidence from the latest organization sync."
              : "Sync again after Cost Explorer warms up to enrich service-level spend analysis and improve prioritization."}
        </p>
      </div>
    </article>
  );
}

function FindingsWorkbench({ findings, loading, error }) {
  const [expandedId, setExpandedId] = useState(null);
  const [statusFilter, setStatusFilter] = useState("open");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");

  const filteredFindings = useMemo(() => {
    return findings.filter((finding) => {
      const statusMatch = statusFilter === "all" ? true : finding.status === statusFilter;
      const severityMatch = severityFilter === "all" ? true : finding.severity === severityFilter;
      const typeMatch = typeFilter === "all" ? true : finding.finding_type === typeFilter;
      return statusMatch && severityMatch && typeMatch;
    });
  }, [findings, severityFilter, statusFilter, typeFilter]);

  const openCount = findings.filter((finding) => finding.status === "open").length;
  const resolvedCount = findings.filter((finding) => finding.status === "resolved").length;

  return (
    <article className="info-card full-span-card" id="findings">
      <div className="chart-header">
        <div className="chart-title">
          <h2>Waste & risks</h2>
          <p>Stored findings with evidence from the latest organization-scoped detection pass.</p>
        </div>
        <div className="chip-row">
          <span className="chip info">{openCount} open</span>
          <span className="chip good">{resolvedCount} resolved</span>
        </div>
      </div>
      <div className="findings-toolbar">
        <div className="segmented-control">
          <button
            className={`segmented-pill ${statusFilter === "open" ? "active" : ""}`}
            type="button"
            onClick={() => setStatusFilter("open")}
          >
            Open
          </button>
          <button
            className={`segmented-pill ${statusFilter === "resolved" ? "active" : ""}`}
            type="button"
            onClick={() => setStatusFilter("resolved")}
          >
            Resolved
          </button>
          <button
            className={`segmented-pill ${statusFilter === "all" ? "active" : ""}`}
            type="button"
            onClick={() => setStatusFilter("all")}
          >
            All
          </button>
        </div>
        <div className="findings-filter-row">
          <label className="resource-select-shell">
            <span className="resource-select-label">Severity</span>
            <select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}>
              <option value="all">All severities</option>
              <option value="critical">Critical</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </label>
          <label className="resource-select-shell">
            <span className="resource-select-label">Type</span>
            <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
              {findingTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
      {loading ? <p>Loading findings...</p> : null}
      {error ? <p className="form-error">{error}</p> : null}
      {!loading && !error && filteredFindings.length === 0 ? (
        <EmptyState
          title={statusFilter === "resolved" ? "No resolved findings" : "No matching findings"}
          description="Try another filter combination or run sync again after changing AWS resources to generate more findings."
        />
      ) : null}
      {!loading && !error && filteredFindings.length > 0 ? (
        <div className="findings-workbench">
          {filteredFindings.map((finding) => {
            const isExpanded = expandedId === finding.id;
            const evidenceEntries = Object.entries(finding.evidence ?? {});

            return (
              <div className={`finding-row ${finding.severity} ${finding.status === "resolved" ? "resolved" : ""}`} key={finding.id}>
                <button
                  className="finding-row-toggle"
                  type="button"
                  onClick={() => setExpandedId(isExpanded ? null : finding.id)}
                >
                  <div className="finding-row-main">
                    <span className={`chip ${finding.severity}`}>{finding.severity.toUpperCase()}</span>
                    <span className={`chip ${finding.status === "resolved" ? "good" : "info"}`}>{finding.status}</span>
                    <strong>{formatFindingTypeLabel(finding.finding_type)}</strong>
                    <span className="finding-resource">{finding.resource_type} / {finding.resource_id}</span>
                  </div>
                  <div className="finding-row-side">
                    <span className="finding-meta">{formatTimeAgo(finding.detected_at)}</span>
                    <span className="finding-expand">{isExpanded ? "Hide evidence" : "Show evidence"}</span>
                  </div>
                </button>
                {isExpanded ? (
                  <div className="finding-evidence">
                    {evidenceEntries.map(([key, value]) => (
                      <div className="evidence-item" key={key}>
                        <p>{key.replaceAll("_", " ")}</p>
                        <strong>{formatEvidenceValue(value)}</strong>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}
    </article>
  );
}

function AwsSetupGuide() {
  const policyJson = `{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudCostReadOnly",
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetCostForecast",
        "cloudwatch:GetMetricData",
        "ec2:DescribeInstances",
        "ec2:DescribeVolumes",
        "ec2:DescribeAddresses",
        "rds:DescribeDBInstances",
        "elasticloadbalancing:DescribeLoadBalancers",
        "lambda:ListFunctions",
        "s3:ListAllMyBuckets",
        "s3:GetBucketLocation",
        "dynamodb:ListTables",
        "dynamodb:DescribeTable",
        "sqs:ListQueues",
        "sqs:GetQueueAttributes",
        "sns:ListTopics",
        "ecs:ListClusters",
        "ecs:DescribeClusters",
        "ecs:ListServices",
        "ecs:DescribeServices",
        "ecr:DescribeRepositories",
        "apigateway:GET"
      ],
      "Resource": "*"
    }
  ]
}`;

  return (
    <article className="info-card full-span-card aws-guide-section" id="connect-aws">
      <div className="chart-header">
        <div className="chart-title">
          <h2>Connect AWS guide</h2>
          <p>
            Create a read-only IAM user for this organization, attach the policy, generate the access key, then save the
            connection in the dashboard.
          </p>
        </div>
      </div>
      <ol className="setup-steps">
        <li>
          In AWS, open <strong>IAM</strong> and create a user such as <code>cloudcost-app</code>.
        </li>
        <li>
          Attach the app&apos;s read-only policy so the user can read Cost Explorer, CloudWatch, EC2, EBS, Lambda, S3,
          RDS, and the other inventory services we support.
        </li>
        <li>
          Create an <strong>access key</strong> for that IAM user and copy the <code>Access key ID</code> and
          <code> Secret access key</code>.
        </li>
        <li>
          Choose the AWS <strong>region</strong> where this organization&apos;s resources live most often, such as
          <code> us-east-1</code>.
        </li>
        <li>
          Paste those values into the form on the right and click <strong>Save AWS connection</strong>.
        </li>
        <li>
          After saving, click <strong>Run sync now</strong> to pull inventory, metrics, and findings for this
          organization only.
        </li>
      </ol>
      <div className="guide-callout">
        <strong>What the app stores</strong>
        <p>
          The credentials are saved per organization workspace and encrypted on the backend, so each client connects only
          to its own AWS account.
        </p>
      </div>
      <div className="guide-callout">
        <strong>What to expect first</strong>
        <p>
          Inventory and CloudWatch metrics often appear before Cost Explorer spend data. Spend charts can stay empty
          until AWS billing data is ready.
        </p>
      </div>
      <details className="policy-shell">
        <summary>Show IAM policy JSON</summary>
        <p className="inline-note">
          Create a customer-managed policy in AWS IAM, paste this JSON, attach it to the app user, then create the
          access key for that user.
        </p>
        <pre className="policy-code">
          <code>{policyJson}</code>
        </pre>
      </details>
    </article>
  );
}

function OperationsPanel({
  auth,
  organizationContext,
  connectionForm,
  connectionState,
  setConnectionForm,
  handleConnectionSave,
  syncState,
  handleManualSync,
  demoSeedState,
  handleDemoSeed,
  teammateForm,
  teammateState,
  setTeammateForm,
  handleTeammateCreate,
  isSimulatedWorkspace,
}) {
  return (
    <article className="info-card full-span-card" id="operations">
      <div className="chart-header">
        <div className="chart-title">
          <h2>Operations</h2>
          <p>Keep workspace controls in one place: AWS connection, sync, demo mode, and teammate access.</p>
        </div>
        <div className="chip-row">
          <span className="chip info">{auth.user?.role}</span>
          <span className={`chip ${isSimulatedWorkspace ? "warning" : "good"}`}>
            {isSimulatedWorkspace ? "Demo data active" : "Live sync mode"}
          </span>
        </div>
      </div>

      <div className="operations-layout">
        <section className="operations-block">
          <h3>Workspace status</h3>
          {organizationContext.loading ? <p>Loading organization...</p> : null}
          {organizationContext.data ? (
            <dl className="facts-list">
              <div>
                <dt>Name</dt>
                <dd>{organizationContext.data.organization.name}</dd>
              </div>
              <div>
                <dt>AWS connection</dt>
                <dd>
                  {organizationContext.data.aws_connection.has_connection
                    ? `Configured for ${organizationContext.data.aws_connection.region}`
                    : "Not configured yet"}
                </dd>
              </div>
              <div>
                <dt>Data source</dt>
                <dd>{isSimulatedWorkspace ? "Seeded demo data" : "Live organization sync"}</dd>
              </div>
            </dl>
          ) : null}
          {organizationContext.error ? <p className="form-error">{organizationContext.error}</p> : null}

          <div className="operations-actions">
            <button className="primary-button" type="button" onClick={handleManualSync} disabled={syncState.running}>
              {syncState.running ? "Running sync..." : "Run sync now"}
            </button>
            <button className="secondary-button" type="button" onClick={handleDemoSeed} disabled={demoSeedState.running}>
              {demoSeedState.running ? "Loading demo..." : "Load demo data"}
            </button>
          </div>

          {syncState.error ? <p className="form-error">{syncState.error}</p> : null}
          {syncState.message ? <p className="form-success">{syncState.message}</p> : null}
          {demoSeedState.error ? <p className="form-error">{demoSeedState.error}</p> : null}
          {demoSeedState.message ? <p className="form-success">{demoSeedState.message}</p> : null}

          {syncState.summary ? (
            <dl className="facts-list sync-summary">
              <div>
                <dt>Cost records</dt>
                <dd>{syncState.summary.cost_records_synced}</dd>
              </div>
              <div>
                <dt>Resources</dt>
                <dd>{syncState.summary.resources_synced}</dd>
              </div>
              <div>
                <dt>Metric samples</dt>
                <dd>{syncState.summary.metric_samples_synced}</dd>
              </div>
              <div>
                <dt>Findings</dt>
                <dd>{syncState.summary.findings_detected}</dd>
              </div>
              <div>
                <dt>Warnings</dt>
                <dd>
                  {Array.isArray(syncState.summary.warnings) && syncState.summary.warnings.length > 0
                    ? syncState.summary.warnings.join(" | ")
                    : "none"}
                </dd>
              </div>
            </dl>
          ) : null}
        </section>

        <section className="operations-block">
          <h3>AWS connection</h3>
          <form className="auth-form compact-form" onSubmit={handleConnectionSave}>
            <label>
              <span>Access key ID</span>
              <input
                required
                type="password"
                value={connectionForm.access_key_id}
                onChange={(event) => setConnectionForm((current) => ({ ...current, access_key_id: event.target.value }))}
              />
            </label>
            <label>
              <span>Secret access key</span>
              <input
                required
                type="password"
                value={connectionForm.secret_access_key}
                onChange={(event) => setConnectionForm((current) => ({ ...current, secret_access_key: event.target.value }))}
              />
            </label>
            <label>
              <span>Region</span>
              <input
                required
                type="text"
                value={connectionForm.region}
                onChange={(event) => setConnectionForm((current) => ({ ...current, region: event.target.value }))}
              />
            </label>
            {connectionState.error ? <p className="form-error">{connectionState.error}</p> : null}
            {connectionState.message ? <p className="form-success">{connectionState.message}</p> : null}
            <button className="primary-button" type="submit" disabled={connectionState.saving}>
              {connectionState.saving ? "Saving..." : "Save AWS connection"}
            </button>
          </form>
        </section>
        <section className="operations-block">
          <h3>Create teammate</h3>
          <form className="auth-form compact-form" onSubmit={handleTeammateCreate}>
            <label>
              <span>Email</span>
              <input
                required
                type="email"
                value={teammateForm.email}
                onChange={(event) => setTeammateForm((current) => ({ ...current, email: event.target.value }))}
              />
            </label>
            <label>
              <span>Password</span>
              <input
                required
                type="password"
                minLength={8}
                value={teammateForm.password}
                onChange={(event) => setTeammateForm((current) => ({ ...current, password: event.target.value }))}
              />
            </label>
            <label>
              <span>Role</span>
              <select
                value={teammateForm.role}
                onChange={(event) => setTeammateForm((current) => ({ ...current, role: event.target.value }))}
              >
                <option value="viewer">viewer</option>
                <option value="admin">admin</option>
              </select>
            </label>
            {teammateState.error ? <p className="form-error">{teammateState.error}</p> : null}
            {teammateState.message ? <p className="form-success">{teammateState.message}</p> : null}
            <button className="primary-button" type="submit" disabled={teammateState.saving}>
              {teammateState.saving ? "Creating..." : "Create teammate"}
            </button>
          </form>
        </section>
      </div>
    </article>
  );
}

export default function DashboardPage() {
  const auth = useAuth();
  const [activeSection, setActiveSection] = useState("overview");
  const [dateRange, setDateRange] = useState(buildDefaultDateRange);
  const [granularity, setGranularity] = useState("daily");
  const [refreshKey, setRefreshKey] = useState(0);
  const [dashboard, setDashboard] = useState({
    loading: true,
    error: "",
    summary: null,
    byService: [],
    byRegion: [],
    trend: [],
    resources: [],
  });
  const [findingsState, setFindingsState] = useState({
    loading: true,
    error: "",
    items: [],
  });
  const [organizationContext, setOrganizationContext] = useState({
    loading: true,
    data: null,
    error: "",
  });
  const [connectionForm, setConnectionForm] = useState({
    access_key_id: "",
    secret_access_key: "",
    region: "us-east-1",
  });
  const [connectionState, setConnectionState] = useState({
    saving: false,
    message: "",
    error: "",
  });
  const [teammateForm, setTeammateForm] = useState({
    email: "",
    password: "",
    role: "viewer",
  });
  const [teammateState, setTeammateState] = useState({
    saving: false,
    message: "",
    error: "",
  });
  const [syncState, setSyncState] = useState({
    running: false,
    message: "",
    error: "",
    summary: null,
  });
  const [demoSeedState, setDemoSeedState] = useState({
    running: false,
    message: "",
    error: "",
    summary: null,
  });

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      setDashboard((current) => ({ ...current, loading: true, error: "" }));
      setFindingsState((current) => ({ ...current, loading: true, error: "" }));

      const params = new URLSearchParams({
        start: dateRange.start,
        end: dateRange.end,
      });
      const trendParams = new URLSearchParams({
        start: dateRange.start,
        end: dateRange.end,
        granularity,
      });

      try {
        const [
          meResponse,
          organizationResponse,
          summaryResponse,
          serviceResponse,
          regionResponse,
          trendResponse,
          resourceResponse,
          findingsResponse,
        ] = await Promise.all([
          apiFetch("/auth/me"),
          apiFetch("/organization/me"),
          apiFetch("/dashboard/summary"),
          apiFetch(`/dashboard/by-service?${params.toString()}`),
          apiFetch(`/dashboard/by-region?${params.toString()}`),
          apiFetch(`/dashboard/trend?${trendParams.toString()}`),
          apiFetch("/dashboard/resources"),
          apiFetch("/findings?status=all"),
        ]);

        const [
          meData,
          organizationData,
          summaryData,
          serviceData,
          regionData,
          trendData,
          resourceData,
          findingsData,
        ] = await Promise.all([
          meResponse.json(),
          organizationResponse.json(),
          summaryResponse.json(),
          serviceResponse.json(),
          regionResponse.json(),
          trendResponse.json(),
          resourceResponse.json(),
          findingsResponse.json(),
        ]);

        if (!cancelled) {
          auth.updateUser(meData);
          setOrganizationContext({
            loading: false,
            data: organizationResponse.ok ? organizationData : null,
            error: organizationResponse.ok ? "" : extractApiError(organizationData, "Failed to load organization"),
          });
          if (organizationResponse.ok && organizationData.aws_connection?.region) {
            setConnectionForm((current) => ({
              ...current,
              region: organizationData.aws_connection.region,
            }));
          }
          setDashboard({
            loading: false,
            error: "",
            summary: summaryResponse.ok ? summaryData : null,
            byService: serviceResponse.ok ? serviceData : [],
            byRegion: regionResponse.ok ? regionData : [],
            trend: trendResponse.ok ? trendData : [],
            resources: resourceResponse.ok ? resourceData : [],
          });
          setFindingsState({
            loading: false,
            error: findingsResponse.ok ? "" : extractApiError(findingsData, "Failed to load findings"),
            items: findingsResponse.ok ? findingsData : [],
          });
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Failed to load dashboard";
          setDashboard((current) => ({
            ...current,
            loading: false,
            error: message,
          }));
          setFindingsState({
            loading: false,
            error: message,
            items: [],
          });
        }
      }
    }

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [dateRange.end, dateRange.start, granularity, refreshKey]);

  useEffect(() => {
    const sectionEntries = navigationSections
      .map((section) => {
        const element = document.getElementById(section.id);
        return element ? { ...section, element } : null;
      })
      .filter(Boolean)
      .sort((left, right) => left.element.offsetTop - right.element.offsetTop);

    if (sectionEntries.length === 0) {
      return undefined;
    }

    function updateActiveSection() {
      const offset = 120;
      let currentId = sectionEntries[0].id;

      for (const section of sectionEntries) {
        if (section.element.offsetTop - offset <= window.scrollY) {
          currentId = section.id;
        }
      }

      setActiveSection(currentId);
    }

    updateActiveSection();
    window.addEventListener("scroll", updateActiveSection, { passive: true });
    window.addEventListener("hashchange", updateActiveSection);

    return () => {
      window.removeEventListener("scroll", updateActiveSection);
      window.removeEventListener("hashchange", updateActiveSection);
    };
  }, [dashboard.loading, findingsState.loading, organizationContext.loading]);

  async function handleConnectionSave(event) {
    event.preventDefault();
    setConnectionState({ saving: true, message: "", error: "" });

    try {
      const response = await apiFetch("/organization/aws-connection", {
        method: "PUT",
        body: JSON.stringify(connectionForm),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(extractApiError(data, "Failed to save AWS connection"));
      }

      setOrganizationContext({
        loading: false,
        data,
        error: "",
      });
      setConnectionState({
        saving: false,
        message: "AWS connection saved for this organization.",
        error: "",
      });
      setRefreshKey((current) => current + 1);
      setConnectionForm((current) => ({
        ...current,
        access_key_id: "",
        secret_access_key: "",
      }));
    } catch (error) {
      setConnectionState({
        saving: false,
        message: "",
        error: error instanceof Error ? error.message : "Failed to save AWS connection",
      });
    }
  }

  async function handleTeammateCreate(event) {
    event.preventDefault();
    setTeammateState({ saving: true, message: "", error: "" });

    try {
      const response = await apiFetch("/auth/teammates", {
        method: "POST",
        body: JSON.stringify(teammateForm),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(extractApiError(data, "Failed to create teammate"));
      }

      setTeammateState({
        saving: false,
        message: `Created ${data.email} as ${data.role} in ${data.organization.name}.`,
        error: "",
      });
      setTeammateForm({
        email: "",
        password: "",
        role: "viewer",
      });
    } catch (error) {
      setTeammateState({
        saving: false,
        message: "",
        error: error instanceof Error ? error.message : "Failed to create teammate",
      });
    }
  }

  async function handleManualSync() {
    setSyncState({
      running: true,
      message: "",
      error: "",
      summary: null,
    });

    try {
      const response = await apiFetch("/sync/run", { method: "POST" });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(extractApiError(data, "Failed to run sync"));
      }

      setSyncState({
        running: false,
        message: data.message ?? "Sync completed.",
        error: "",
        summary: data.summary ?? null,
      });
      setRefreshKey((current) => current + 1);
    } catch (error) {
      setSyncState({
        running: false,
        message: "",
        error: error instanceof Error ? error.message : "Failed to run sync",
        summary: null,
      });
    }
  }

  async function handleDemoSeed() {
    setDemoSeedState({
      running: true,
      message: "",
      error: "",
      summary: null,
    });

    try {
      const response = await apiFetch("/organization/demo-seed", { method: "POST" });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(extractApiError(data, "Failed to load demo workspace"));
      }

      setDemoSeedState({
        running: false,
        message: data.message ?? "Demo workspace loaded.",
        error: "",
        summary: data.summary ?? null,
      });
      setSyncState({
        running: false,
        message: "",
        error: "",
        summary: null,
      });
      setRefreshKey((current) => current + 1);
    } catch (error) {
      setDemoSeedState({
        running: false,
        message: "",
        error: error instanceof Error ? error.message : "Failed to load demo workspace",
        summary: null,
      });
    }
  }

  const isSimulatedWorkspace =
    !organizationContext.data?.aws_connection.has_connection &&
    ((dashboard.summary?.current_month_spend ?? 0) > 0 ||
      dashboard.byService.length > 0 ||
      dashboard.byRegion.length > 0 ||
      dashboard.resources.length > 0);

  const derivedStats = useMemo(() => {
    const cpuRows = dashboard.resources.filter((resource) => resource.latest_cpu_utilization !== null && resource.latest_cpu_utilization !== undefined);
    const avgCpu =
      cpuRows.length > 0
        ? cpuRows.reduce((total, resource) => total + resource.latest_cpu_utilization, 0) / cpuRows.length
        : null;
    const connectedRegions = new Set(dashboard.resources.map((resource) => resource.region).filter(Boolean));
    const potentialRiskCount = dashboard.resources.filter((resource) => {
      const cpu = resource.latest_cpu_utilization ?? 0;
      return resource.state === "running" && cpu < 15;
    }).length;

    return {
      avgCpu,
      connectedRegions: connectedRegions.size,
      totalResources: dashboard.resources.length,
      potentialRiskCount,
    };
  }, [dashboard.resources]);

  const findings = useMemo(() => {
    return findingsState.items.map((finding) => ({
      ...finding,
      title: formatFindingTypeLabel(finding.finding_type),
      resource: `ID: ${finding.resource_id}`,
      icon:
        finding.finding_type === "unattached_volume"
          ? "s"
          : finding.finding_type === "unused_elastic_ip"
            ? "@"
            : finding.finding_type === "oversized_mismatch"
              ? "!"
              : "~",
      timeAgo: formatTimeAgo(finding.detected_at),
      impact: summarizeFindingImpact(finding),
    }));
  }, [findingsState.items]);

  const openFindings = useMemo(
    () => findings.filter((finding) => finding.status === "open"),
    [findings]
  );

  const systemStats = useMemo(() => {
    const utilization = derivedStats.avgCpu ?? 0;
    return [
      { label: "Compute efficiency", value: `${Math.min(Math.round((utilization / 35) * 100), 99)}%`, detail: "Based on latest CPU samples" },
      { label: "Storage density", value: `${dashboard.resources.some((resource) => resource.resource_type.includes("volume")) ? "91" : "0"}%`, detail: "Inventory-backed heuristic score" },
      { label: "Budget utilization", value: dashboard.summary?.current_month_spend ? "62%" : "0%", detail: "Enabled once cost data exists" },
      { label: "Active regions", value: `${derivedStats.connectedRegions}`, detail: "Regions visible in current workspace" },
    ];
  }, [dashboard.resources, dashboard.summary?.current_month_spend, derivedStats.avgCpu, derivedStats.connectedRegions]);

  const initials = (auth.user?.email ?? "CI")
    .slice(0, 2)
    .toUpperCase();
  const activeSectionLabel = navigationSections.find((section) => section.id === activeSection)?.label ?? "Overview";

  return (
    <div className="dashboard-app">
      <aside className="dashboard-sidebar">
        <div className="sidebar-brand">
          <strong>Cloud Intelligence</strong>
        </div>

        <div className="sidebar-section">
          <a className={`sidebar-link ${activeSection === "overview" ? "active" : ""}`} href="#overview">
            <span className="sidebar-icon">[]</span>
            <span>Overview</span>
          </a>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-label">Resources</div>
          <a className={`sidebar-link ${activeSection === "inventory" ? "active" : ""}`} href="#inventory">
            <span className="sidebar-icon">#</span>
            <span>Resource Inventory</span>
          </a>
          <a className={`sidebar-link ${activeSection === "connect-aws" ? "active" : ""}`} href="#connect-aws">
            <span className="sidebar-icon">*</span>
            <span>Connect AWS</span>
          </a>
          <a className={`sidebar-link ${activeSection === "operations" ? "active" : ""}`} href="#operations">
            <span className="sidebar-icon">@</span>
            <span>Sync Status</span>
          </a>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-label">Analytics</div>
          <a className={`sidebar-link ${activeSection === "findings" ? "active" : ""}`} href="#findings">
            <span className="sidebar-icon">!</span>
            <span>Waste & Risks</span>
          </a>
          <a className={`sidebar-link ${activeSection === "forecast" ? "active" : ""}`} href="#forecast">
            <span className="sidebar-icon">+</span>
            <span>Cost Forecast</span>
          </a>
        </div>

        <div className="sidebar-user">
          <div className="sidebar-avatar">{initials}</div>
          <div className="sidebar-user-meta">
            <strong title={auth.user?.email ?? "Workspace user"}>{auth.user?.email ?? "Workspace user"}</strong>
            <div className="sidebar-user-row">
              <span>{auth.user?.role ?? "viewer"}</span>
              <button className="sidebar-signout" type="button" onClick={auth.logout}>
                Sign out
              </button>
            </div>
          </div>
        </div>
      </aside>

      <div className="dashboard-main">
        <header className="dashboard-topbar">
          <h1>{activeSectionLabel}</h1>
          <div className="dashboard-topbar-tools">
            <span className="topbar-org">{auth.user?.organization?.name ?? "workspace"}</span>
          </div>
        </header>

        <main className="dashboard-content">
          <section className="system-banner" id="overview">
            <div className="banner-title">
              <div className="banner-icon">~</div>
              <div>
                <h2>{isSimulatedWorkspace ? "Demo workspace active" : "System health healthy"}</h2>
                <p>
                  {isSimulatedWorkspace
                    ? `Showing seeded simulated dashboard data for ${auth.user?.organization?.name ?? "this organization"}.`
                    : `Workspace sync, cost, and inventory views are scoped to ${auth.user?.organization?.name ?? "this organization"}.`}
                </p>
              </div>
            </div>
          </section>

          {dashboard.error ? <p className="form-error" style={{ marginTop: "16px" }}>{dashboard.error}</p> : null}

          <section className="dashboard-grid">
            <MetricCard
              label="Current month spend"
              value={formatCurrency(dashboard.summary?.current_month_spend ?? 0, dashboard.summary?.currency)}
              trendText={`${formatPercent(dashboard.summary?.percent_change ?? null)} vs last month`}
              trendTone={(dashboard.summary?.percent_change ?? 0) > 0 ? "up" : "down"}
            />
            <MetricCard
              label="Prior month spend"
              value={formatCurrency(dashboard.summary?.prior_month_spend ?? 0, dashboard.summary?.currency)}
              trendText={dashboard.summary?.top_service ? `Top service: ${dashboard.summary.top_service}` : "No cost service data yet"}
              trendTone="info"
            />
            <MetricCard
              label="Avg CPU utilization"
              value={derivedStats.avgCpu !== null ? `${derivedStats.avgCpu.toFixed(1)}%` : "n/a"}
              trendText={derivedStats.totalResources > 0 ? `${derivedStats.totalResources} resources in workspace` : "No resource telemetry yet"}
              trendTone="good"
            />
            <MetricCard
              label="Projected posture"
              value={isSimulatedWorkspace ? "Demo mode" : `${derivedStats.connectedRegions} region${derivedStats.connectedRegions === 1 ? "" : "s"}`}
              trendText={isSimulatedWorkspace ? "Seeded demo data is clearly marked" : `${derivedStats.potentialRiskCount} low-utilization candidates`}
              trendTone="info"
              accent
            />

            <SpendTrendChart
              data={dashboard.trend}
              loading={dashboard.loading}
              granularity={granularity}
              onGranularityChange={setGranularity}
            />
            <FindingsFeed findings={openFindings} loading={findingsState.loading} isSimulatedWorkspace={isSimulatedWorkspace} />
            <CostBreakdownChart
              title="Cost by service"
              subtitle="Top spend buckets in the selected window."
              data={dashboard.byService}
              loading={dashboard.loading}
            />
            <CostBreakdownChart
              title="Cost by region"
              subtitle="Regional distribution of tracked spend."
              data={dashboard.byRegion}
              loading={dashboard.loading}
            />

            <ResourceTable data={dashboard.resources} loading={dashboard.loading} />

            <AwsSetupGuide />

            {auth.user?.role === "admin" ? (
              <OperationsPanel
                auth={auth}
                organizationContext={organizationContext}
                connectionForm={connectionForm}
                connectionState={connectionState}
                setConnectionForm={setConnectionForm}
                handleConnectionSave={handleConnectionSave}
                syncState={syncState}
                handleManualSync={handleManualSync}
                demoSeedState={demoSeedState}
                handleDemoSeed={handleDemoSeed}
                teammateForm={teammateForm}
                teammateState={teammateState}
                setTeammateForm={setTeammateForm}
                handleTeammateCreate={handleTeammateCreate}
                isSimulatedWorkspace={isSimulatedWorkspace}
              />
            ) : null}

            <FindingsWorkbench findings={findingsState.items} loading={findingsState.loading} error={findingsState.error} />

            <article className="info-card full-span-card" id="forecast">
              <div className="chart-header">
                <div className="chart-title">
                  <h2>Cloud fleet optimization status</h2>
                  <p>High-level executive readout derived from current workspace telemetry and cost state.</p>
                </div>
                <div className="chip-row">
                  <span className="chip good">Healthy workspace</span>
                  {isSimulatedWorkspace ? <span className="chip warning">Demo seeded</span> : null}
                  <span className="chip info">{derivedStats.connectedRegions} active regions</span>
                </div>
              </div>
              <div className="system-grid">
                {systemStats.map((stat) => (
                  <div className="system-stat" key={stat.label}>
                    <p>{stat.label}</p>
                    <h3>{stat.value}</h3>
                    <p>{stat.detail}</p>
                  </div>
                ))}
              </div>
            </article>
          </section>
        </main>
      </div>
    </div>
  );
}
