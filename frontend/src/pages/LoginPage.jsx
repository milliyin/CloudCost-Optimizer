import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../components/AuthProvider";

const initialForm = {
  email: "",
  password: "",
};

export default function LoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (auth.isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(form),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail ?? "Login failed");
      }

      auth.login(data);
      navigate(location.state?.from ?? "/dashboard", { replace: true });
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="auth-layout">
      <aside className="auth-hero">
        <div className="auth-brand">
          <strong>Cloud Intelligence</strong>
          <span>FinOps Management</span>
        </div>
        <div className="auth-hero-copy">
          <p className="eyebrow">Persistent workspace access</p>
          <h1>Executive visibility for every cloud client.</h1>
          <p className="lede">
            Sign in to review organization-scoped cost data, sync health, and
            optimization signals without losing your session on refresh.
          </p>
          <div className="auth-points">
            <div className="auth-point">
              <div className="auth-point-bullet" />
              <div>
                <strong>Organization isolation</strong>
                <span>Each client workspace keeps AWS settings and synced data separated.</span>
              </div>
            </div>
            <div className="auth-point">
              <div className="auth-point-bullet" />
              <div>
                <strong>Admin operations in-app</strong>
                <span>Run sync, seed demo data, and add teammates directly from the dashboard.</span>
              </div>
            </div>
          </div>
        </div>
        <div className="auth-note">Stage 3 dashboard and multitenant workspace controls are active.</div>
      </aside>

      <div className="auth-panel">
        <section className="auth-card">
          <p className="eyebrow">Stage 1 access</p>
          <h2>Sign in</h2>
          <p className="lede">Return to your organization workspace.</p>
          <form className="auth-form" onSubmit={handleSubmit}>
            <label>
              <span>Email</span>
              <input
                required
                type="email"
                value={form.email}
                onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
              />
            </label>
            <label>
              <span>Password</span>
              <input
                required
                type="password"
                minLength={8}
                value={form.password}
                onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
              />
            </label>
            {error ? <p className="form-error">{error}</p> : null}
            <button className="primary-button" type="submit" disabled={submitting}>
              {submitting ? "Signing in..." : "Sign in"}
            </button>
          </form>
          <p className="auth-footer">
            Need an account? <Link to="/register">Create one</Link>
          </p>
        </section>
      </div>
    </section>
  );
}
