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
  { id: "recommendations", label: "Recommendations" },
  { id: "budgets", label: "Budgets & Alerts" },
  { id: "reports", label: "Reports" },
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
  const numericAmount = Number(amount ?? 0);

  if (numericAmount !== 0 && Math.abs(numericAmount) < 0.01) {
    return numericAmount > 0 ? "<$0.01" : ">-$0.01";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(numericAmount);
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

function formatBudgetScope(scope, scopeValue) {
  if (scope === "total") {
    return "Total spend";
  }
  return `${scope}: ${scopeValue}`;
}

function getPresetDateRange(days) {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - (days - 1));
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
}

function buildDefaultDateRange() {
  return getPresetDateRange(90);
}

function EmptyState({ title, description, action }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{description}</p>
      {action ? <div style={{ marginTop: "12px" }}>{action}</div> : null}
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

function RecommendationsSection({ recommendations, loading, error, canManage, actionState, onApprove, onReject }) {
  const [statusFilter, setStatusFilter] = useState("pending");
  const filteredRecommendations = useMemo(() => {
    if (statusFilter === "all") {
      return recommendations;
    }
    return recommendations.filter((recommendation) => recommendation.status === statusFilter);
  }, [recommendations, statusFilter]);

  const pendingCount = recommendations.filter((recommendation) => recommendation.status === "pending").length;
  const approvedCount = recommendations.filter((recommendation) => recommendation.status === "approved").length;
  const potentialSavings = recommendations
    .filter((recommendation) => recommendation.status === "pending")
    .reduce((total, recommendation) => total + (recommendation.estimated_monthly_savings ?? 0), 0);

  return (
    <article className="info-card full-span-card" id="recommendations">
      <div className="chart-header">
        <div className="chart-title">
          <h2>Recommendations</h2>
          <p>Human-reviewed action drafts linked to findings. Approving only records intent; nothing is executed in AWS by this app.</p>
        </div>
        <div className="chip-row">
          <span className="chip info">{pendingCount} pending</span>
          <span className="chip good">{approvedCount} approved</span>
          <span className="chip warning">{formatCurrency(potentialSavings)} potential monthly savings</span>
        </div>
      </div>
      <div className="findings-toolbar">
        <div className="segmented-control">
          {["pending", "approved", "rejected", "all"].map((status) => (
            <button
              key={status}
              className={`segmented-pill ${statusFilter === status ? "active" : ""}`}
              type="button"
              onClick={() => setStatusFilter(status)}
            >
              {status[0].toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>
      </div>
      {loading ? <p>Loading recommendations...</p> : null}
      {error ? <p className="form-error">{error}</p> : null}
      {actionState.message ? <p className="form-success">{actionState.message}</p> : null}
      {actionState.error ? <p className="form-error">{actionState.error}</p> : null}
      {!loading && !error && filteredRecommendations.length === 0 ? (
        <EmptyState
          title="No recommendations yet"
          description="Run a sync after findings exist, or wait for current findings to hydrate into recommendation drafts."
        />
      ) : null}
      {!loading && !error && filteredRecommendations.length > 0 ? (
        <div className="recommendation-list">
          {filteredRecommendations.map((recommendation) => (
            <div className="recommendation-card" key={recommendation.id}>
              <div className="recommendation-header">
                <div>
                  <div className="finding-row-main">
                    <span className={`chip ${recommendation.severity}`}>{recommendation.severity.toUpperCase()}</span>
                    <span className={`chip ${recommendation.status === "approved" ? "good" : recommendation.status === "rejected" ? "warning" : "info"}`}>
                      {recommendation.status}
                    </span>
                    <span className={`chip ${recommendation.finding_status === "resolved" ? "good" : "info"}`}>
                      finding {recommendation.finding_status}
                    </span>
                  </div>
                  <h3>{recommendation.description}</h3>
                  <p className="finding-resource">{recommendation.resource_type} / {recommendation.resource_id}</p>
                </div>
                <div className="recommendation-side">
                  <strong>{recommendation.estimated_monthly_savings !== null ? `${formatCurrency(recommendation.estimated_monthly_savings)}/mo` : "Review only"}</strong>
                  <span className="finding-meta">{formatFindingTypeLabel(recommendation.finding_type)}</span>
                </div>
              </div>
              <p className="data-note">{recommendation.explanation}</p>
              {recommendation.decision_reason ? <p className="inline-note"><strong>Decision note:</strong> {recommendation.decision_reason}</p> : null}
              {canManage && recommendation.status === "pending" ? (
                <div className="recommendation-actions">
                  <button
                    className="primary-button"
                    type="button"
                    disabled={actionState.runningId === recommendation.id}
                    onClick={() => onApprove(recommendation)}
                  >
                    {actionState.runningId === recommendation.id ? "Saving..." : "Approve"}
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={actionState.runningId === recommendation.id}
                    onClick={() => onReject(recommendation)}
                  >
                    Reject
                  </button>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function RecommendationDecisionModal({ modalState, actionState, onClose, onReasonChange, onConfirm }) {
  if (!modalState.open || !modalState.recommendation) {
    return null;
  }

  const { mode, recommendation, reason } = modalState;
  const isReject = mode === "reject";
  const title = isReject ? "Reject recommendation" : "Approve recommendation";
  const buttonLabel = actionState.runningId === recommendation.id ? "Saving..." : isReject ? "Reject recommendation" : "Approve recommendation";

  return (
    <div className="app-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="app-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="recommendation-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="app-modal-header">
          <div>
            <p className="eyebrow">{isReject ? "Review outcome" : "Approval check"}</p>
            <h3 id="recommendation-modal-title">{title}</h3>
            <p className="lede">
              {recommendation.resource_type} / {recommendation.resource_id}
            </p>
          </div>
          <button className="ghost-button app-modal-close" type="button" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="app-modal-body">
          <div className="guide-callout">
            <strong>{recommendation.description}</strong>
            <p>
              {isReject
                ? "Rejecting keeps the recommendation in history and records your reason for the team."
                : "Approving only records review intent in the app. Nothing is executed in AWS automatically."}
            </p>
          </div>

          {isReject ? (
            <label className="modal-field">
              <span>Why are you rejecting this?</span>
              <textarea
                rows={4}
                value={reason}
                onChange={(event) => onReasonChange(event.target.value)}
                placeholder="Example: not a priority this month, already planned elsewhere, or required for production."
              />
            </label>
          ) : (
            <div className="modal-copy-block">
              <p className="inline-note">
                You can still act on this later in AWS manually. This workflow is only for internal review tracking and audit history.
              </p>
            </div>
          )}
        </div>

        <div className="app-modal-actions">
          <button className="secondary-button" type="button" onClick={onClose} disabled={actionState.runningId === recommendation.id}>
            Cancel
          </button>
          <button
            className="primary-button"
            type="button"
            disabled={actionState.runningId === recommendation.id || (isReject && !reason.trim())}
            onClick={onConfirm}
          >
            {buttonLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

function BudgetsSection({
  budgetsState,
  budgetForm,
  setBudgetForm,
  serviceOptions,
  budgetActionState,
  editingBudgetId,
  setEditingBudgetId,
  onSubmitBudget,
  canManage,
}) {
  const visibleAlerts = budgetsState.alerts.slice(0, 3);

  return (
    <article className="info-card full-span-card" id="budgets">
      <div className="chart-header">
        <div className="chart-title">
          <h2>Budgets & alerts</h2>
          <p>Create monthly budget thresholds for total spend, a service, or a region. Alert generation is real; email delivery remains log-only for now.</p>
        </div>
        <div className="chip-row">
          <span className="chip warning">{budgetsState.alerts.length} alerts</span>
          <span className="chip info">{budgetsState.items.length} budgets</span>
        </div>
      </div>
      {budgetsState.loading ? <p>Loading budgets and alerts...</p> : null}
      {budgetsState.error ? <p className="form-error">{budgetsState.error}</p> : null}
      {budgetActionState.message ? <p className="form-success">{budgetActionState.message}</p> : null}
      {budgetActionState.error ? <p className="form-error">{budgetActionState.error}</p> : null}
      <div className="budget-layout">
        <section className="budget-panel">
          <h3>Active alerts</h3>
          {budgetsState.alerts.length === 0 ? (
            <EmptyState title="No alerts yet" description="Create a low threshold or wait for synced spend to cross an active budget." />
          ) : (
            <div className="budget-list">
              {visibleAlerts.map((alert) => (
                <div className="budget-card" key={alert.id}>
                  <div className="recommendation-header">
                    <div>
                      <strong>{formatBudgetScope(alert.budget_scope, alert.budget_scope_value)}</strong>
                      <p className="finding-resource">Triggered for {alert.period_start}</p>
                    </div>
                    <div className="recommendation-side">
                      <strong>{formatCurrency(alert.spend_at_trigger)}</strong>
                      <span className="finding-meta">threshold {formatCurrency(alert.budget_threshold_amount)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
        <section className="budget-panel">
          <h3>Budgets</h3>
          {budgetsState.items.length === 0 ? (
            <EmptyState title="No budgets yet" description="Admins can create a monthly total, service, or region budget here." />
          ) : (
            <div className="budget-list">
              {budgetsState.items.map((budget) => (
                <div className="budget-card" key={budget.id}>
                  <div className="recommendation-header">
                    <div>
                      <strong>{formatBudgetScope(budget.scope, budget.scope_value)}</strong>
                      <p className="finding-resource">{budget.period} budget created {formatTimeAgo(budget.created_at)}</p>
                    </div>
                    <div className="recommendation-side">
                      <strong>{formatCurrency(budget.threshold_amount)}</strong>
                      <span className={`chip ${budget.is_active ? "good" : "warning"}`}>{budget.is_active ? "active" : "inactive"}</span>
                    </div>
                  </div>
                  {canManage ? (
                    <div className="recommendation-actions">
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => {
                          setEditingBudgetId(budget.id);
                          setBudgetForm({
                            scope: budget.scope,
                            scope_value: budget.scope_value,
                            threshold_amount: String(budget.threshold_amount),
                            period: budget.period,
                          });
                        }}
                      >
                        Edit
                      </button>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
      {canManage ? (
        <form className="budget-form" onSubmit={onSubmitBudget}>
          <div className="chart-header">
            <div className="chart-title">
              <h3>{editingBudgetId ? "Edit budget" : "Create budget"}</h3>
              <p>Budget checks are evaluated against the latest synced PostgreSQL cost data, not directly against AWS in the browser.</p>
            </div>
          </div>
          <div className="budget-scope-switch" role="tablist" aria-label="Budget scope">
            {[
              { value: "total", label: "Total spend" },
              { value: "service", label: "Service budget" },
            ].map((option) => (
              <button
                key={option.value}
                className={`budget-scope-pill ${budgetForm.scope === option.value ? "active" : ""}`}
                type="button"
                onClick={() =>
                  setBudgetForm((current) => ({
                    ...current,
                    scope: option.value,
                    scope_value: option.value === "total" ? "" : current.scope_value || serviceOptions[0]?.value || "",
                  }))
                }
              >
                {option.label}
              </button>
            ))}
          </div>
          <div className="budget-form-grid">
            <label className="budget-field-card budget-amount-card">
              <span>Threshold amount</span>
              <div className="budget-input-shell">
                <span className="budget-prefix">$</span>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  placeholder="5.00"
                  value={budgetForm.threshold_amount}
                  onChange={(event) => setBudgetForm((current) => ({ ...current, threshold_amount: event.target.value }))}
                />
              </div>
              <small>Monthly alert threshold for this workspace slice.</small>
            </label>

            {budgetForm.scope === "total" ? (
              <div className="budget-field-card budget-helper-card">
                <span>Scope coverage</span>
                <strong>Entire organization workspace</strong>
                <p>This budget watches total synced spend across all services in the current organization.</p>
                <div className="chip-row">
                  <span className="chip info">Monthly</span>
                  <span className="chip good">No extra filter needed</span>
                </div>
              </div>
            ) : (
              <label className="budget-field-card budget-helper-card">
                <span>Service name</span>
                <div className="budget-input-shell">
                  <select
                    value={budgetForm.scope_value}
                    onChange={(event) => setBudgetForm((current) => ({ ...current, scope_value: event.target.value }))}
                    disabled={serviceOptions.length === 0}
                  >
                    <option value="" disabled>
                      {serviceOptions.length === 0 ? "No services available yet" : "Choose a service"}
                    </option>
                    {serviceOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <small>Choose one of the synced AWS service names from the current dashboard data.</small>
              </label>
            )}
          </div>
          <div className="budget-form-actions">
            <button className="primary-button" type="submit" disabled={budgetActionState.saving}>
              {budgetActionState.saving ? "Saving..." : editingBudgetId ? "Update budget" : "Create budget"}
            </button>
            {editingBudgetId ? (
              <button
                className="secondary-button"
                type="button"
                onClick={() => {
                  setEditingBudgetId(null);
                  setBudgetForm({
                    scope: "total",
                    scope_value: "",
                    threshold_amount: "",
                    period: "monthly",
                  });
                }}
              >
                Cancel
              </button>
            ) : null}
          </div>
        </form>
      ) : null}
    </article>
  );
}

function ReportsSection({ reportState, onDownload }) {
  return (
    <article className="info-card full-span-card" id="reports">
      <div className="chart-header">
        <div className="chart-title">
          <h2>Reports</h2>
          <p>Export a point-in-time report covering spend summary, findings, and recommendation history for the current organization.</p>
        </div>
      </div>
      {reportState.error ? <p className="form-error">{reportState.error}</p> : null}
      <div className="reports-actions">
        <button className="primary-button" type="button" disabled={reportState.downloading === "csv"} onClick={() => onDownload("csv")}>
          {reportState.downloading === "csv" ? "Preparing CSV..." : "Download CSV"}
        </button>
        <button className="secondary-button" type="button" disabled={reportState.downloading === "pdf"} onClick={() => onDownload("pdf")}>
          {reportState.downloading === "pdf" ? "Preparing PDF..." : "Download PDF"}
        </button>
      </div>
      <p className="inline-note">
        PDF export uses ReportLab in the backend. This was chosen over WeasyPrint here because it keeps the Docker image lighter and avoids extra system dependencies such as Pango.
      </p>
    </article>
  );
}

function CostForecastWorkbench({
  forecastState,
  selectedService,
  setSelectedService,
  horizonDays,
  setHorizonDays,
  onRetrain,
  retrainState,
  canManage,
  serviceOptions,
  selectedScenario,
  onScenarioChange,
  demoSeedState,
}) {
  const { data, loading, error } = forecastState;

  const combinedChartData = useMemo(() => {
    if (!data) return [];
    const hist = (data.historical || []).map((h) => ({
      date: h.date,
      actual: h.amount,
      forecast: null,
      lower_bound: null,
      upper_bound: null,
    }));
    const fore = (data.forecast || []).map((f) => ({
      date: f.date,
      actual: null,
      forecast: f.amount,
      lower_bound: f.lower_bound,
      upper_bound: f.upper_bound,
    }));

    if (hist.length > 0 && fore.length > 0) {
      fore[0].actual = hist[hist.length - 1].actual;
    }
    return [...hist, ...fore];
  }, [data]);

  return (
    <article className="info-card full-span-card" id="forecast">
      <div className="chart-header">
        <div className="chart-title">
          <h2>Machine Learning Cost Forecast</h2>
          <p>Supervised regression time-series forecasting with time-aware split validation and 95% confidence interval bounds.</p>
        </div>
        <div className="chip-row">
          <span className="chip info">{data?.model_name || "Ridge Autoregressive"}</span>
          <span className="chip good">Time-Aware Train/Test Split</span>
        </div>
      </div>

      <div className="forecast-controls-row">
        <label className="filter-label">
          <span>Service Slice</span>
          <select value={selectedService} onChange={(e) => setSelectedService(e.target.value)}>
            <option value="total">Total Organization Spend</option>
            {serviceOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>

        <label className="filter-label">
          <span>Horizon</span>
          <select value={horizonDays} onChange={(e) => setHorizonDays(Number(e.target.value))}>
            <option value={14}>14 Days</option>
            <option value={30}>30 Days</option>
            <option value={60}>60 Days</option>
            <option value={90}>90 Days</option>
          </select>
        </label>

        {canManage ? (
          <button className="primary-button" type="button" onClick={onRetrain} disabled={retrainState?.running}>
            {retrainState?.running ? "Retraining..." : "Retrain ML Models"}
          </button>
        ) : null}
      </div>

      {retrainState?.message ? <p className="form-success">{retrainState.message}</p> : null}
      {retrainState?.error ? <p className="form-error">{retrainState.error}</p> : null}

      {data?.proactive_warnings && data.proactive_warnings.length > 0 ? (
        <div className="warning-banner-box">
          <div className="warning-banner-title">
            <span className="chip warning">PROACTIVE BUDGET BREACH WARNING</span>
            <strong>{data.proactive_warnings[0].message}</strong>
          </div>
          <p>
            Our ML model projected cumulative monthly spend will exceed your threshold of{" "}
            <strong>${data.proactive_warnings[0].threshold_amount.toFixed(2)}</strong> before month end.
          </p>
        </div>
      ) : null}

      {data ? (
        <div className="metrics-summary-grid">
          <div className="metric-pill-card highlight-metric">
            <span>Next Month Expected Total</span>
            <strong>${data.projected_next_month_total?.toFixed(2) ?? "0.00"}</strong>
            <small>30-Day ML Forecast Prediction</small>
          </div>
          <div className="metric-pill-card">
            <span>Current Month Projected Total</span>
            <strong>${data.projected_current_month_total?.toFixed(2) ?? "0.00"}</strong>
            <small>Actuals + Remaining Forecast</small>
          </div>
          <div className="metric-pill-card">
            <span>ML Model MAE</span>
            <strong>${data.mae?.toFixed(2) ?? "0.00"}</strong>
            <small>Mean Absolute Error</small>
          </div>
          <div className="metric-pill-card">
            <span>ML Model RMSE</span>
            <strong>${data.rmse?.toFixed(2) ?? "0.00"}</strong>
            <small>Root Mean Squared Error</small>
          </div>
          <div className="metric-pill-card">
            <span>Baseline Naive MAE</span>
            <strong>${data.baseline_mae?.toFixed(2) ?? "0.00"}</strong>
            <small>7-Day Moving Avg Baseline</small>
          </div>
          <div className="metric-pill-card">
            <span>Training Data Points</span>
            <strong>{data.data_points ?? 0} days</strong>
            <small>Chronological samples</small>
          </div>
        </div>
      ) : null}

      {loading ? <p>Training & running forecast model...</p> : null}
      {error ? <p className="form-error">{error}</p> : null}

      {!loading && combinedChartData.length > 0 ? (
        <div className="chart-shell" style={{ height: "360px", marginTop: "16px" }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={combinedChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e1ee" />
              <XAxis dataKey="date" tick={{ fill: "#777587", fontSize: 11 }} />
              <YAxis tick={{ fill: "#777587", fontSize: 11 }} />
              <Tooltip
                formatter={(val, _name, item) => [
                  val !== null ? formatCurrency(Number(val)) : "-",
                  item.dataKey === "actual"
                    ? "Historical Spend"
                    : item.dataKey === "forecast"
                    ? "Predicted Forecast"
                    : item.dataKey === "upper_bound"
                    ? "95% Upper Bound"
                    : "95% Lower Bound",
                ]}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="actual"
                stroke="#3525cd"
                strokeWidth={3}
                dot={{ r: 2 }}
                name="Historical Spend"
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="forecast"
                stroke="#8b5cf6"
                strokeWidth={3}
                strokeDasharray="6 6"
                dot={{ r: 3, fill: "#8b5cf6" }}
                name="Predicted Forecast"
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="upper_bound"
                stroke="#d8b4fe"
                strokeWidth={1}
                strokeDasharray="2 2"
                dot={false}
                name="95% Upper Bound"
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="lower_bound"
                stroke="#d8b4fe"
                strokeWidth={1}
                strokeDasharray="2 2"
                dot={false}
                name="95% Lower Bound"
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
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
  demoClearState,
  handleDemoClear,
  teammateForm,
  teammateState,
  setTeammateForm,
  handleTeammateCreate,
  isSimulatedWorkspace,
  selectedScenario,
  setSelectedScenario,
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
            <select
              style={{
                padding: "8px 12px",
                borderRadius: "8px",
                border: "1px solid var(--border)",
                background: "#ffffff",
                fontSize: "0.85rem",
                fontWeight: "600",
                color: "var(--text-main)",
              }}
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              disabled={demoSeedState.running || demoClearState?.running}
            >
              <option value="organic">📈 Organic Growth Pattern</option>
              <option value="volatile">⚡ High Volatility & Heavy Spikes</option>
              <option value="escalating">🚀 Rapid Cost Escalation</option>
              <option value="seasonal">🔄 Strict 7-Day Seasonal Cycles</option>
            </select>
            <button className="secondary-button" type="button" onClick={() => handleDemoSeed(selectedScenario)} disabled={demoSeedState.running || demoClearState?.running}>
              {demoSeedState.running ? "Loading demo..." : "Load demo data"}
            </button>
            <button className="secondary-button danger-tone" type="button" onClick={handleDemoClear} disabled={demoSeedState.running || demoClearState?.running}>
              {demoClearState?.running ? "Removing demo..." : "Remove demo data"}
            </button>
          </div>

          {syncState.error ? <p className="form-error">{syncState.error}</p> : null}
          {syncState.message ? <p className="form-success">{syncState.message}</p> : null}
          {demoSeedState.error ? <p className="form-error">{demoSeedState.error}</p> : null}
          {demoSeedState.message ? <p className="form-success">{demoSeedState.message}</p> : null}
          {demoClearState?.error ? <p className="form-error">{demoClearState.error}</p> : null}
          {demoClearState?.message ? <p className="form-success">{demoClearState.message}</p> : null}

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
                <dt>Recommendations</dt>
                <dd>{syncState.summary.recommendations_synced ?? 0}</dd>
              </div>
              <div>
                <dt>Alerts</dt>
                <dd>{syncState.summary.alerts_triggered ?? 0}</dd>
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
  const [activePreset, setActivePreset] = useState(90);
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
  const [recommendationsState, setRecommendationsState] = useState({
    loading: true,
    error: "",
    items: [],
  });
  const [budgetsState, setBudgetsState] = useState({
    loading: true,
    error: "",
    items: [],
    alerts: [],
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
  const [demoClearState, setDemoClearState] = useState({
    running: false,
    message: "",
    error: "",
  });
  const [recommendationActionState, setRecommendationActionState] = useState({
    runningId: null,
    message: "",
    error: "",
  });
  const [budgetForm, setBudgetForm] = useState({
    scope: "total",
    scope_value: "",
    threshold_amount: "",
    period: "monthly",
  });
  const [editingBudgetId, setEditingBudgetId] = useState(null);
  const [budgetActionState, setBudgetActionState] = useState({
    saving: false,
    message: "",
    error: "",
  });
  const [reportState, setReportState] = useState({
    downloading: "",
    error: "",
  });
  const [selectedScenario, setSelectedScenario] = useState("organic");
  const [selectedForecastService, setSelectedForecastService] = useState("total");
  const [forecastHorizonDays, setForecastHorizonDays] = useState(30);
  const [forecastState, setForecastState] = useState({
    loading: true,
    error: "",
    data: null,
  });
  const [retrainState, setRetrainState] = useState({
    running: false,
    message: "",
    error: "",
  });
  const [recommendationModal, setRecommendationModal] = useState({
    open: false,
    mode: "approve",
    recommendation: null,
    reason: "",
  });

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      setDashboard((current) => ({ ...current, loading: true, error: "" }));
      setFindingsState((current) => ({ ...current, loading: true, error: "" }));
      setRecommendationsState((current) => ({ ...current, loading: true, error: "" }));
      setBudgetsState((current) => ({ ...current, loading: true, error: "" }));

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
          recommendationsResponse,
          budgetsResponse,
          alertsResponse,
        ] = await Promise.all([
          apiFetch("/auth/me"),
          apiFetch("/organization/me"),
          apiFetch("/dashboard/summary"),
          apiFetch(`/dashboard/by-service?${params.toString()}`),
          apiFetch(`/dashboard/by-region?${params.toString()}`),
          apiFetch(`/dashboard/trend?${trendParams.toString()}`),
          apiFetch("/dashboard/resources"),
          apiFetch("/findings?status=all"),
          apiFetch("/recommendations?status=all"),
          apiFetch("/budgets"),
          apiFetch("/budgets/alerts"),
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
          recommendationsData,
          budgetsData,
          alertsData,
        ] = await Promise.all([
          meResponse.json(),
          organizationResponse.json(),
          summaryResponse.json(),
          serviceResponse.json(),
          regionResponse.json(),
          trendResponse.json(),
          resourceResponse.json(),
          findingsResponse.json(),
          recommendationsResponse.json(),
          budgetsResponse.json(),
          alertsResponse.json(),
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
          setRecommendationsState({
            loading: false,
            error: recommendationsResponse.ok ? "" : extractApiError(recommendationsData, "Failed to load recommendations"),
            items: recommendationsResponse.ok ? recommendationsData : [],
          });
          setBudgetsState({
            loading: false,
            error: budgetsResponse.ok && alertsResponse.ok
              ? ""
              : [
                  !budgetsResponse.ok ? extractApiError(budgetsData, "Failed to load budgets") : "",
                  !alertsResponse.ok ? extractApiError(alertsData, "Failed to load alerts") : "",
                ].filter(Boolean).join(" | "),
            items: budgetsResponse.ok ? budgetsData : [],
            alerts: alertsResponse.ok ? alertsData : [],
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
          setRecommendationsState({
            loading: false,
            error: message,
            items: [],
          });
          setBudgetsState({
            loading: false,
            error: message,
            items: [],
            alerts: [],
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
    let cancelled = false;
    async function loadForecast() {
      setForecastState((current) => ({ ...current, loading: true, error: "" }));
      setRetrainState({ running: false, message: "", error: "" });
      try {
        const response = await apiFetch(`/forecast/service?service_name=${selectedForecastService}&horizon_days=${forecastHorizonDays}`);
        const data = await response.json();
        if (!cancelled) {
          if (response.ok) {
            setForecastState({ loading: false, error: "", data });
          } else {
            setForecastState({ loading: false, error: extractApiError(data, "Failed to load forecast"), data: null });
          }
        }
      } catch (error) {
        if (!cancelled) {
          setForecastState({ loading: false, error: error instanceof Error ? error.message : "Failed to load forecast", data: null });
        }
      }
    }

    loadForecast();
    return () => {
      cancelled = true;
    };
  }, [selectedForecastService, forecastHorizonDays, refreshKey]);

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

  async function handleDemoSeed(scenarioToUse) {
    const scenario = typeof scenarioToUse === "string" ? scenarioToUse : selectedScenario;
    setDemoSeedState({
      running: true,
      message: "",
      error: "",
      summary: null,
    });

    try {
      const response = await apiFetch(`/organization/demo-seed?scenario=${scenario}`, { method: "POST" });
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
      setSelectedScenario(scenario);
      setDemoClearState({ running: false, message: "", error: "" });
      setSyncState({ running: false, message: "", error: "", summary: null });
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

  function handleApplyPreset(days) {
    setActivePreset(days);
    setDateRange(getPresetDateRange(days));
  }

  function handleGranularityChange(newGranularity) {
    setGranularity(newGranularity);
    if (newGranularity === "monthly") {
      const startMs = new Date(dateRange.start).getTime();
      const endMs = new Date(dateRange.end).getTime();
      const dayDiff = Math.round((endMs - startMs) / (1000 * 60 * 60 * 24));
      if (dayDiff < 85) {
        setDateRange(getPresetDateRange(90));
        setActivePreset(90);
      }
    }
  }

  async function handleDemoClear() {
    setDemoClearState({
      running: true,
      message: "",
      error: "",
    });

    try {
      const response = await apiFetch("/organization/demo-clear", { method: "POST" });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(extractApiError(data, "Failed to remove demo data"));
      }

      setDemoClearState({
        running: false,
        message: data.message ?? "Demo data removed successfully.",
        error: "",
      });
      setDemoSeedState({
        running: false,
        message: "",
        error: "",
        summary: null,
      });
      setRefreshKey((current) => current + 1);
    } catch (error) {
      setDemoClearState({
        running: false,
        message: "",
        error: error instanceof Error ? error.message : "Failed to remove demo data",
      });
    }
  }

  async function handleRetrainForecast() {
    setRetrainState({ running: true, message: "", error: "" });
    try {
      const response = await apiFetch("/forecast/retrain", { method: "POST" });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(extractApiError(data, "Failed to retrain models"));
      }
      setRetrainState({
        running: false,
        message: `Models retrained successfully! (ML MAE: $${data.mae?.toFixed(2)}, Baseline MAE: $${data.baseline_mae?.toFixed(2)})`,
        error: "",
      });
      setRefreshKey((current) => current + 1);
    } catch (error) {
      setRetrainState({
        running: false,
        message: "",
        error: error instanceof Error ? error.message : "Failed to retrain models",
      });
    }
  }

  function openRecommendationModal(mode, recommendation) {
    setRecommendationModal({
      open: true,
      mode,
      recommendation,
      reason: mode === "reject" ? "Not a priority right now" : "",
    });
  }

  function closeRecommendationModal() {
    if (recommendationActionState.runningId) {
      return;
    }
    setRecommendationModal({
      open: false,
      mode: "approve",
      recommendation: null,
      reason: "",
    });
  }

  async function submitRecommendationDecision() {
    const recommendation = recommendationModal.recommendation;
    if (!recommendation) {
      return;
    }

    const isReject = recommendationModal.mode === "reject";
    const reason = recommendationModal.reason.trim();
    setRecommendationActionState({ runningId: recommendation.id, message: "", error: "" });
    try {
      const response = await apiFetch(`/recommendations/${recommendation.id}/${isReject ? "reject" : "approve"}`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(extractApiError(data, `Failed to ${isReject ? "reject" : "approve"} recommendation`));
      }
      setRecommendationActionState({
        runningId: null,
        message: `${isReject ? "Rejected" : "Approved"} recommendation for ${recommendation.resource_id}.`,
        error: "",
      });
      closeRecommendationModal();
      setRefreshKey((current) => current + 1);
    } catch (error) {
      setRecommendationActionState({
        runningId: null,
        message: "",
        error: error instanceof Error ? error.message : `Failed to ${isReject ? "reject" : "approve"} recommendation`,
      });
    }
  }

  function handleRecommendationApprove(recommendation) {
    openRecommendationModal("approve", recommendation);
  }

  function handleRecommendationReject(recommendation) {
    openRecommendationModal("reject", recommendation);
  }

  async function handleBudgetSubmit(event) {
    event.preventDefault();
    setBudgetActionState({ saving: true, message: "", error: "" });

    try {
      const path = editingBudgetId ? `/budgets/${editingBudgetId}` : "/budgets";
      const method = editingBudgetId ? "PUT" : "POST";
      const response = await apiFetch(path, {
        method,
        body: JSON.stringify({
          scope: budgetForm.scope,
          scope_value: budgetForm.scope_value,
          threshold_amount: Number(budgetForm.threshold_amount),
          period: budgetForm.period,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(extractApiError(data, "Failed to save budget"));
      }
      setBudgetActionState({
        saving: false,
        message: editingBudgetId ? "Budget updated." : "Budget created.",
        error: "",
      });
      setEditingBudgetId(null);
      setBudgetForm({
        scope: "total",
        scope_value: "",
        threshold_amount: "",
        period: "monthly",
      });
      setRefreshKey((current) => current + 1);
    } catch (error) {
      setBudgetActionState({
        saving: false,
        message: "",
        error: error instanceof Error ? error.message : "Failed to save budget",
      });
    }
  }

  async function handleReportDownload(format) {
    setReportState({ downloading: format, error: "" });
    try {
      const response = await apiFetch(`/reports/export?format=${format}`);
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(extractApiError(payload, `Failed to export ${format.toUpperCase()} report`));
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `cloudcost-report.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setReportState({ downloading: "", error: "" });
    } catch (error) {
      setReportState({
        downloading: "",
        error: error instanceof Error ? error.message : `Failed to export ${format.toUpperCase()} report`,
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
  const budgetServiceOptions = useMemo(() => {
    const uniqueServices = new Set();
    const options = [];

    for (const row of dashboard.byService) {
      if (!row.key || uniqueServices.has(row.key)) {
        continue;
      }
      uniqueServices.add(row.key);
      options.push({ value: row.key, label: row.key });
    }

    return options;
  }, [dashboard.byService]);
  const recommendations = recommendationsState.items;

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
          {auth.user?.role === "admin" ? (
            <>
              <a className={`sidebar-link ${activeSection === "connect-aws" ? "active" : ""}`} href="#connect-aws">
                <span className="sidebar-icon">*</span>
                <span>Connect AWS</span>
              </a>
              <a className={`sidebar-link ${activeSection === "operations" ? "active" : ""}`} href="#operations">
                <span className="sidebar-icon">@</span>
                <span>Sync Status</span>
              </a>
            </>
          ) : null}
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-label">Analytics</div>
          <a className={`sidebar-link ${activeSection === "findings" ? "active" : ""}`} href="#findings">
            <span className="sidebar-icon">!</span>
            <span>Waste & Risks</span>
          </a>
          <a className={`sidebar-link ${activeSection === "recommendations" ? "active" : ""}`} href="#recommendations">
            <span className="sidebar-icon">=</span>
            <span>Recommendations</span>
          </a>
          <a className={`sidebar-link ${activeSection === "budgets" ? "active" : ""}`} href="#budgets">
            <span className="sidebar-icon">$</span>
            <span>Budgets & Alerts</span>
          </a>
          <a className={`sidebar-link ${activeSection === "reports" ? "active" : ""}`} href="#reports">
            <span className="sidebar-icon">%</span>
            <span>Reports</span>
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
            <div className="topbar-date-picker">
              <button
                className={activePreset === 30 ? "active" : ""}
                type="button"
                onClick={() => handleApplyPreset(30)}
              >
                30D
              </button>
              <button
                className={activePreset === 90 ? "active" : ""}
                type="button"
                onClick={() => handleApplyPreset(90)}
              >
                90D
              </button>
              <button
                className={activePreset === 180 ? "active" : ""}
                type="button"
                onClick={() => handleApplyPreset(180)}
              >
                6M
              </button>
              <button
                className={activePreset === 365 ? "active" : ""}
                type="button"
                onClick={() => handleApplyPreset(365)}
              >
                1Y
              </button>
            </div>
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

          <RecommendationDecisionModal
            modalState={recommendationModal}
            actionState={recommendationActionState}
            onClose={closeRecommendationModal}
            onReasonChange={(reason) => setRecommendationModal((current) => ({ ...current, reason }))}
            onConfirm={submitRecommendationDecision}
          />

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
              onGranularityChange={handleGranularityChange}
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

            {auth.user?.role === "admin" ? <AwsSetupGuide /> : null}

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
                demoClearState={demoClearState}
                handleDemoClear={handleDemoClear}
                teammateForm={teammateForm}
                teammateState={teammateState}
                setTeammateForm={setTeammateForm}
                handleTeammateCreate={handleTeammateCreate}
                isSimulatedWorkspace={isSimulatedWorkspace}
                selectedScenario={selectedScenario}
                setSelectedScenario={setSelectedScenario}
              />
            ) : null}

            <FindingsWorkbench findings={findingsState.items} loading={findingsState.loading} error={findingsState.error} />

            <RecommendationsSection
              recommendations={recommendations}
              loading={recommendationsState.loading}
              error={recommendationsState.error}
              canManage={auth.user?.role === "admin"}
              actionState={recommendationActionState}
              onApprove={handleRecommendationApprove}
              onReject={handleRecommendationReject}
            />

            <BudgetsSection
              budgetsState={budgetsState}
              budgetForm={budgetForm}
              setBudgetForm={setBudgetForm}
              serviceOptions={budgetServiceOptions}
              budgetActionState={budgetActionState}
              editingBudgetId={editingBudgetId}
              setEditingBudgetId={setEditingBudgetId}
              onSubmitBudget={handleBudgetSubmit}
              canManage={auth.user?.role === "admin"}
            />

            <ReportsSection reportState={reportState} onDownload={handleReportDownload} />

            <CostForecastWorkbench
              forecastState={forecastState}
              selectedService={selectedForecastService}
              setSelectedService={setSelectedForecastService}
              horizonDays={forecastHorizonDays}
              setHorizonDays={setForecastHorizonDays}
              onRetrain={handleRetrainForecast}
              retrainState={retrainState}
              canManage={auth.user?.role === "admin"}
              serviceOptions={budgetServiceOptions}
              selectedScenario={selectedScenario}
              onScenarioChange={handleDemoSeed}
              demoSeedState={demoSeedState}
            />

            <article className="info-card full-span-card" id="executive-summary">
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
