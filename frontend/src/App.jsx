import { useEffect, useState } from "react";

const initialState = {
  loading: true,
  status: null,
  error: null,
};

export default function App() {
  const [health, setHealth] = useState(initialState);

  useEffect(() => {
    let cancelled = false;

    async function loadHealth() {
      try {
        const response = await fetch("/health");

        if (!response.ok) {
          throw new Error(`Backend returned ${response.status}`);
        }

        const data = await response.json();

        if (!cancelled) {
          setHealth({
            loading: false,
            status: data.status ?? "unknown",
            error: null,
          });
        }
      } catch (error) {
        if (!cancelled) {
          setHealth({
            loading: false,
            status: null,
            error: error instanceof Error ? error.message : "Unknown error",
          });
        }
      }
    }

    loadHealth();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="app-shell">
      <section className="hero-card">
        <p className="eyebrow">AWS cost visibility, safely staged</p>
        <h1>CloudCost Optimizer</h1>
        <p className="lede">
          Stage 0 bootstrap: the frontend is talking to the FastAPI backend and
          is ready for the next layer of the build.
        </p>
        <div className="status-panel">
          <span className="status-label">Backend health</span>
          {health.loading ? <strong>Checking...</strong> : null}
          {!health.loading && health.status ? (
            <strong className="status-ok">{health.status}</strong>
          ) : null}
          {!health.loading && health.error ? (
            <strong className="status-error">{health.error}</strong>
          ) : null}
        </div>
      </section>
    </main>
  );
}
