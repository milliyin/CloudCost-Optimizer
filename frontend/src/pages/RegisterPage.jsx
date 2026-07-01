import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

const initialForm = {
  organization_name: "",
  email: "",
  password: "",
  role: "viewer",
};

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch("/auth/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(form),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail ?? "Registration failed");
      }

      setSuccess(`Account created for ${data.email}. You can sign in now.`);
      setForm(initialForm);
      window.setTimeout(() => navigate("/login"), 800);
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="auth-card">
      <p className="eyebrow">Role-based access</p>
      <h1>Create an account</h1>
      <p className="lede">
        Registration now creates a dedicated client workspace so each
        organization can connect its own AWS account and keep data isolated.
      </p>
      <form className="auth-form" onSubmit={handleSubmit}>
        <label>
          <span>Organization</span>
          <input
            required
            type="text"
            value={form.organization_name}
            onChange={(event) => setForm((current) => ({ ...current, organization_name: event.target.value }))}
          />
        </label>
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
        <label>
          <span>Role</span>
          <select
            value={form.role}
            onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))}
          >
            <option value="viewer">viewer</option>
            <option value="admin">admin</option>
          </select>
        </label>
        {error ? <p className="form-error">{error}</p> : null}
        {success ? <p className="form-success">{success}</p> : null}
        <button className="primary-button" type="submit" disabled={submitting}>
          {submitting ? "Creating..." : "Create account"}
        </button>
      </form>
      <p className="inline-note">
        Already registered? <Link to="/login">Sign in</Link>
      </p>
    </section>
  );
}
