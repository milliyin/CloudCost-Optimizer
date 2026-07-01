import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiFetch } from "../api/client";
import { extractApiError } from "../api/errors";
import { useAuth } from "../components/AuthProvider";

const chartPalette = ["#0b6e4f", "#1f4c73", "#d9822b", "#b83280", "#3d9970", "#8d6e63"];

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

function SpendSummaryCard({ summary, loading }) {
  if (loading) {
    return <article className="info-card summary-card"><p>Loading summary...</p></article>;
  }

  return (
    <article className="info-card summary-card">
      <p className="eyebrow">Spend overview</p>
      <h2>{formatCurrency(summary?.current_month_spend ?? 0, summary?.currency)}</h2>
      <dl className="facts-list">
        <div>
          <dt>Prior month</dt>
          <dd>{formatCurrency(summary?.prior_month_spend ?? 0, summary?.currency)}</dd>
        </div>
        <div>
          <dt>Change</dt>
          <dd>{formatPercent(summary?.percent_change ?? null)}</dd>
        </div>
        <div>
          <dt>Top service</dt>
          <dd>{summary?.top_service ?? "No cost data yet"}</dd>
        </div>
      </dl>
    </article>
  );
}

function CostBreakdownChart({ title, data, loading }) {
  if (loading) {
    return <article className="info-card chart-card"><p>Loading {title.toLowerCase()}...</p></article>;
  }

  if (!data || data.length === 0) {
    return (
      <article className="info-card chart-card">
        <h2>{title}</h2>
        <EmptyState title="No synced cost data yet" description="Run a sync after Cost Explorer is ready to populate this breakdown." />
      </article>
    );
  }

  return (
    <article className="info-card chart-card">
      <h2>{title}</h2>
      <div className="chart-shell">
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={data}
              dataKey="amount"
              nameKey="key"
              outerRadius={95}
              innerRadius={55}
              paddingAngle={2}
            >
              {data.map((entry, index) => (
                <Cell key={entry.key} fill={chartPalette[index % chartPalette.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(value, _name, item) => formatCurrency(Number(value), item.payload.currency)} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

function SpendTrendChart({ data, loading, granularity, onGranularityChange }) {
  if (loading) {
    return <article className="info-card chart-card chart-card-wide"><p>Loading trend...</p></article>;
  }

  return (
    <article className="info-card chart-card chart-card-wide">
      <div className="chart-header">
        <h2>Spend trend</h2>
        <select value={granularity} onChange={(event) => onGranularityChange(event.target.value)}>
          <option value="daily">daily</option>
          <option value="monthly">monthly</option>
        </select>
      </div>
      {!data || data.length === 0 ? (
        <EmptyState title="No trend data yet" description="Trend lines appear after cost records are synced for this organization." />
      ) : (
        <div className="chart-shell">
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#d9e7f2" />
              <XAxis dataKey="period_start" tick={{ fill: "#486581" }} />
              <YAxis tick={{ fill: "#486581" }} />
              <Tooltip formatter={(value, _name, item) => formatCurrency(Number(value), item.payload.currency)} />
              <Line type="monotone" dataKey="amount" stroke="#0b6e4f" strokeWidth={3} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
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
    <article className="info-card resource-card">
      <div className="chart-header">
        <h2>Resources</h2>
        <div className="resource-controls">
          <input
            className="resource-search"
            placeholder="Filter resources"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
          />
          <select value={sortKey} onChange={(event) => setSortKey(event.target.value)}>
            <option value="resource_type">type</option>
            <option value="region">region</option>
            <option value="state">state</option>
            <option value="resource_id">id</option>
          </select>
        </div>
      </div>
      {loading ? <p>Loading resources...</p> : null}
      {!loading && filteredRows.length === 0 ? (
        <EmptyState title="No synced resources yet" description="Run sync after connecting AWS to populate the resource inventory." />
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
                <th>CPU</th>
                <th>In</th>
                <th>Out</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row) => (
                <tr key={`${row.resource_type}:${row.resource_id}`}>
                  <td>{row.resource_id}</td>
                  <td>{row.resource_type}</td>
                  <td>{row.region || "n/a"}</td>
                  <td>{row.state || "n/a"}</td>
                  <td>{row.latest_cpu_utilization?.toFixed(1) ?? "n/a"}</td>
                  <td>{row.latest_network_in?.toFixed(1) ?? "n/a"}</td>
                  <td>{row.latest_network_out?.toFixed(1) ?? "n/a"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </article>
  );
}

export default function DashboardPage() {
  const auth = useAuth();
  const [dateRange, setDateRange] = useState(buildDefaultDateRange);
  const [granularity, setGranularity] = useState("daily");
  const [dashboard, setDashboard] = useState({
    loading: true,
    error: "",
    summary: null,
    byService: [],
    byRegion: [],
    trend: [],
    resources: [],
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

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      setDashboard((current) => ({ ...current, loading: true, error: "" }));

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
        ] = await Promise.all([
          apiFetch("/auth/me"),
          apiFetch("/organization/me"),
          apiFetch("/dashboard/summary"),
          apiFetch(`/dashboard/by-service?${params.toString()}`),
          apiFetch(`/dashboard/by-region?${params.toString()}`),
          apiFetch(`/dashboard/trend?${trendParams.toString()}`),
          apiFetch("/dashboard/resources"),
        ]);

        const [
          meData,
          organizationData,
          summaryData,
          serviceData,
          regionData,
          trendData,
          resourceData,
        ] = await Promise.all([
          meResponse.json(),
          organizationResponse.json(),
          summaryResponse.json(),
          serviceResponse.json(),
          regionResponse.json(),
          trendResponse.json(),
          resourceResponse.json(),
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
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Failed to load dashboard";
          setDashboard((current) => ({
            ...current,
            loading: false,
            error: message,
          }));
        }
      }
    }

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [auth, dateRange.end, dateRange.start, granularity]);

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
    } catch (error) {
      setSyncState({
        running: false,
        message: "",
        error: error instanceof Error ? error.message : "Failed to run sync",
        summary: null,
      });
    }
  }

  return (
    <section className="dashboard-shell dashboard-shell-wide">
      <div className="dashboard-header">
        <div>
          <p className="eyebrow">Organization dashboard</p>
          <h1>{auth.user?.organization?.name ?? "CloudCost Optimizer"}</h1>
          <p className="lede">
            Spend, inventory, and sync activity are all scoped to this organization workspace.
          </p>
        </div>
        <div className="dashboard-actions">
          <label className="date-input">
            <span>Start</span>
            <input
              type="date"
              value={dateRange.start}
              onChange={(event) => setDateRange((current) => ({ ...current, start: event.target.value }))}
            />
          </label>
          <label className="date-input">
            <span>End</span>
            <input
              type="date"
              value={dateRange.end}
              onChange={(event) => setDateRange((current) => ({ ...current, end: event.target.value }))}
            />
          </label>
          <button className="secondary-button" type="button" onClick={auth.logout}>
            Sign out
          </button>
        </div>
      </div>

      {dashboard.error ? <p className="form-error">{dashboard.error}</p> : null}

      <div className="dashboard-grid stage3-grid">
        <SpendSummaryCard summary={dashboard.summary} loading={dashboard.loading} />
        <CostBreakdownChart title="Cost by service" data={dashboard.byService} loading={dashboard.loading} />
        <CostBreakdownChart title="Cost by region" data={dashboard.byRegion} loading={dashboard.loading} />
        <SpendTrendChart
          data={dashboard.trend}
          loading={dashboard.loading}
          granularity={granularity}
          onGranularityChange={setGranularity}
        />
        <ResourceTable data={dashboard.resources} loading={dashboard.loading} />

        <article className="info-card">
          <h2>Workspace</h2>
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
                <dt>Role</dt>
                <dd>{auth.user?.role}</dd>
              </div>
            </dl>
          ) : null}
          {organizationContext.error ? <p className="form-error">{organizationContext.error}</p> : null}
        </article>

        {auth.user?.role === "admin" ? (
          <article className="info-card">
            <h2>AWS connection settings</h2>
            <p className="inline-note">
              Save organization-specific AWS credentials here so each client workspace syncs only its own AWS account.
            </p>
            <form className="auth-form" onSubmit={handleConnectionSave}>
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
          </article>
        ) : null}

        {auth.user?.role === "admin" ? (
          <article className="info-card">
            <h2>Manual sync</h2>
            <p className="inline-note">Run an organization-scoped AWS sync directly from the dashboard.</p>
            <button className="primary-button" type="button" onClick={handleManualSync} disabled={syncState.running}>
              {syncState.running ? "Running sync..." : "Run sync now"}
            </button>
            {syncState.error ? <p className="form-error">{syncState.error}</p> : null}
            {syncState.message ? <p className="form-success">{syncState.message}</p> : null}
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
                  <dt>Warnings</dt>
                  <dd>
                    {Array.isArray(syncState.summary.warnings) && syncState.summary.warnings.length > 0
                      ? syncState.summary.warnings.join(" | ")
                      : "none"}
                  </dd>
                </div>
              </dl>
            ) : null}
          </article>
        ) : null}

        {auth.user?.role === "admin" ? (
          <article className="info-card">
            <h2>Create teammate</h2>
            <p className="inline-note">
              Add more users to this same organization workspace without going through public registration again.
            </p>
            <form className="auth-form" onSubmit={handleTeammateCreate}>
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
          </article>
        ) : null}
      </div>
    </section>
  );
}
