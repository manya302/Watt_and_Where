import { useEffect, useState } from "react";
import Dashboard from "./pages/Dashboard.jsx";
import AdminPage from "./pages/AdminPage.jsx";
import TextSizeControl from "./components/TextSizeControl.jsx";
import { loadDashboardData } from "./api.js";

const tabs = [
  { id: "overview", label: "Overview" },
  { id: "trends", label: "Bill trends" },
  { id: "breakdown", label: "Breakdown" },
  { id: "actions", label: "Recommendations" },
  { id: "summary", label: "Summary" },
  { id: "admin", label: "Admin login" },
];

function readRoute() {
  const route = window.location.hash.replace(/^#\/?/, "");
  return tabs.some((tab) => tab.id === route) ? route : "overview";
}

export default function App() {
  const [activeTab, setActiveTab] = useState(readRoute);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function refreshData() {
    setLoading(true);
    setError("");

    try {
      const result = await loadDashboardData();
      setData(result);
    } catch (err) {
      setError(err?.message || "Unable to load the dashboard.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshData();

    const handleHashChange = () => setActiveTab(readRoute());
    window.addEventListener("hashchange", handleHashChange);

    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  function navigate(tabId) {
    window.location.hash = `/${tabId}`;
    setActiveTab(tabId);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <a
          className="brand"
          href="#/overview"
          onClick={() => setActiveTab("overview")}
        >
          <span className="brand-mark" aria-hidden="true">⚡</span>
          <span>
            <strong>Watt & Where</strong>
            <small>Understand your energy</small>
          </span>
        </a>

        <div className="header-tools">
          <TextSizeControl />
        </div>
      </header>

      <nav className="tab-navigation" aria-label="Main navigation">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`nav-tab ${activeTab === tab.id ? "active" : ""}`}
            aria-current={activeTab === tab.id ? "page" : undefined}
            onClick={() => navigate(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div className="page-content">
        {activeTab === "admin" ? (
          <AdminPage />
        ) : loading ? (
          <section className="status-panel" aria-live="polite">
            <div className="loading-dot" />
            <h2>Preparing your dashboard</h2>
            <p>Loading your energy data…</p>
          </section>
        ) : error ? (
          <section className="status-panel">
            <h2>We couldn't load your dashboard</h2>
            <p>{error}</p>
            <button className="primary-button" onClick={refreshData}>
              Try again
            </button>
          </section>
        ) : (
          <Dashboard
            data={data}
            onDataChange={setData}
            onRetry={refreshData}
            activeTab={activeTab}
          />
        )}
      </div>

      <footer className="app-footer">
        <span>Watt & Where</span>
        <span>Energy insights, made easier.</span>
      </footer>
    </div>
  );
}