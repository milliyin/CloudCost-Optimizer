import { useEffect, useState } from "react";

import { apiFetch } from "../api/client";
import { useAuth } from "../components/AuthProvider";

export default function DashboardPage() {
  const auth = useAuth();
  const [profile, setProfile] = useState({
    loading: true,
    data: null,
    error: "",
  });
  const [organizationContext, setOrganizationContext] = useState({
    loading: true,
    data: null,
    error: "",
  });
  const [adminCheck, setAdminCheck] = useState({
    loading: true,
    message: "",
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

  useEffect(() => {
    let cancelled = false;

    async function loadProtectedData() {
      try {
        const [meResponse, adminResponse, organizationResponse] = await Promise.all([
          apiFetch("/auth/me"),
          apiFetch("/auth/admin-check"),
          apiFetch("/organization/me"),
        ]);

        const meData = await meResponse.json();
        const adminData = await adminResponse.json();
        const organizationData = await organizationResponse.json();

        if (!cancelled) {
          auth.updateUser(meData);
          setProfile({
            loading: false,
            data: meData,
            error: meResponse.ok ? "" : meData.detail ?? "Failed to load profile",
          });
          setAdminCheck({
            loading: false,
            message: adminResponse.ok ? adminData.message : "",
            error: adminResponse.ok ? "" : adminData.detail ?? "Admin check failed",
          });
          setOrganizationContext({
            loading: false,
            data: organizationResponse.ok ? organizationData : null,
            error: organizationResponse.ok ? "" : organizationData.detail ?? "Failed to load organization",
          });
          if (organizationResponse.ok && organizationData.aws_connection?.region) {
            setConnectionForm((current) => ({
              ...current,
              region: organizationData.aws_connection.region,
            }));
          }
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Protected request failed";
          setProfile({
            loading: false,
            data: null,
            error: message,
          });
          setAdminCheck({
            loading: false,
            message: "",
            error: message,
          });
          setOrganizationContext({
            loading: false,
            data: null,
            error: message,
          });
        }
      }
    }

    loadProtectedData();

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleConnectionSave(event) {
    event.preventDefault();
    setConnectionState({
      saving: true,
      message: "",
      error: "",
    });

    try {
      const response = await apiFetch("/organization/aws-connection", {
        method: "PUT",
        body: JSON.stringify(connectionForm),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail ?? "Failed to save AWS connection");
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
    setTeammateState({
      saving: true,
      message: "",
      error: "",
    });

    try {
      const response = await apiFetch("/auth/teammates", {
        method: "POST",
        body: JSON.stringify(teammateForm),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail ?? "Failed to create teammate");
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

  return (
    <section className="dashboard-shell">
      <div className="dashboard-header">
        <div>
          <p className="eyebrow">Protected area</p>
          <h1>Dashboard shell</h1>
          <p className="lede">
            The app now keeps users in separate organization workspaces, each
            with its own AWS connection and isolated synced data.
          </p>
        </div>
        <button className="secondary-button" type="button" onClick={auth.logout}>
          Sign out
        </button>
      </div>

      <div className="dashboard-grid">
        <article className="info-card">
          <h2>Session</h2>
          {profile.loading ? <p>Loading profile...</p> : null}
          {profile.data ? (
            <dl className="facts-list">
              <div>
                <dt>Email</dt>
                <dd>{profile.data.email}</dd>
              </div>
              <div>
                <dt>Organization</dt>
                <dd>{profile.data.organization?.name}</dd>
              </div>
              <div>
                <dt>Role</dt>
                <dd>{profile.data.role}</dd>
              </div>
              <div>
                <dt>Created</dt>
                <dd>{new Date(profile.data.created_at).toLocaleString()}</dd>
              </div>
            </dl>
          ) : null}
          {profile.error ? <p className="form-error">{profile.error}</p> : null}
        </article>

        <article className="info-card">
          <h2>Admin-only route check</h2>
          {adminCheck.loading ? <p>Checking route permissions...</p> : null}
          {adminCheck.message ? <p className="form-success">{adminCheck.message}</p> : null}
          {adminCheck.error ? (
            <p>
              {auth.user?.role === "viewer"
                ? `Viewer access correctly blocked: ${adminCheck.error}`
                : adminCheck.error}
            </p>
          ) : null}
        </article>

        <article className="info-card">
          <h2>Organization workspace</h2>
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
            </dl>
          ) : null}
          {organizationContext.error ? <p className="form-error">{organizationContext.error}</p> : null}
        </article>

        {auth.user?.role === "admin" ? (
          <article className="info-card">
            <h2>AWS connection settings</h2>
            <p className="inline-note">
              Save organization-specific AWS credentials here so each client
              workspace syncs only its own AWS account.
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
            <h2>Create teammate</h2>
            <p className="inline-note">
              Add more users to this same organization workspace without going
              through public registration again.
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
