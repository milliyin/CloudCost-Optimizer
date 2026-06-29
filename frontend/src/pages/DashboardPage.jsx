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
  const [adminCheck, setAdminCheck] = useState({
    loading: true,
    message: "",
    error: "",
  });

  useEffect(() => {
    let cancelled = false;

    async function loadProtectedData() {
      try {
        const [meResponse, adminResponse] = await Promise.all([
          apiFetch("/auth/me"),
          apiFetch("/auth/admin-check"),
        ]);

        const meData = await meResponse.json();
        const adminData = await adminResponse.json();

        if (!cancelled) {
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
        }
      }
    }

    loadProtectedData();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="dashboard-shell">
      <div className="dashboard-header">
        <div>
          <p className="eyebrow">Protected area</p>
          <h1>Dashboard shell</h1>
          <p className="lede">
            Stage 1 confirms auth, bearer tokens, and role-aware route behavior
            before the real dashboard arrives in Stage 3.
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
      </div>
    </section>
  );
}
