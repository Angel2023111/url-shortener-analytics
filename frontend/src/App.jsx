
import { useMemo, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  Check,
  ChevronRight,
  CircleAlert,
  Copy,
  ExternalLink,
  Link2,
  LoaderCircle,
  LogOut,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Unplug,
  Zap,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./App.css";

const API = "/api";

async function request(path, apiKey, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey.trim(),
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message =
      typeof data.detail === "string"
        ? data.detail
        : data.detail?.message || `Request failed (${response.status})`;
    throw new Error(message);
  }

  return data;
}

function shortCodeFrom(data) {
  if (data.short_code) return data.short_code;
  if (data.shortCode) return data.shortCode;
  if (data.short_url) return data.short_url.split("/").filter(Boolean).pop();
  if (data.shortened_url) {
    return data.shortened_url.split("/").filter(Boolean).pop();
  }
  return null;
}

function App() {
  const [apiKey, setApiKey] = useState("");
  const [connected, setConnected] = useState(false);
  const [url, setUrl] = useState("");
  const [urls, setUrls] = useState([]);
  const [loading, setLoading] = useState(false);
  const [analyticsLoading, setAnalyticsLoading] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [copied, setCopied] = useState("");
  const [filter, setFilter] = useState("all");

  const totalClicks = urls.reduce(
    (sum, item) => sum + (item.clicks ?? 0),
    0
  );
  const measuredUrls = urls.filter((item) => item.clicks !== null).length;

  const chartData = useMemo(
    () =>
      urls
        .filter((item) => item.clicks !== null)
        .slice(0, 8)
        .reverse()
        .map((item) => ({
          name: item.shortCode,
          clicks: item.clicks,
        })),
    [urls]
  );

  const visibleUrls = urls.filter((item) => {
    if (filter === "measured") return item.clicks !== null;
    if (filter === "unmeasured") return item.clicks === null;
    return true;
  });

  
  
  function connect(event) {
    event.preventDefault();
    setError("");
    setNotice("");

    if (!apiKey.trim()) {
      setError("Enter your API key to continue.");
      return;
    }

    setConnected(true);
    setNotice("API key entered. It will be validated when you create a short URL.");
  }



  async function createUrl(event) {
    event.preventDefault();
    setError("");
    setNotice("");

    if (!connected) {
      setError("Enter your API key first.");
      return;
    }

    let parsed;
    try {
      parsed = new URL(url.trim());
      if (!["http:", "https:"].includes(parsed.protocol)) throw new Error();
    } catch {
      setError("Enter a valid URL starting with http:// or https://.");
      return;
    }

    setLoading(true);
    try {
      const data = await request("/urls", apiKey, {
        method: "POST",
        body: JSON.stringify({ original_url: parsed.href }),
      });

      const shortCode = shortCodeFrom(data);
      if (!shortCode) {
        throw new Error(
          "The API response did not contain a short_code. Check the URL response schema."
        );
      }

      const item = {
        id: data.id ?? `${shortCode}-${Date.now()}`,
        shortCode,
        originalUrl: data.original_url ?? parsed.href,
        createdAt: data.created_at ?? new Date().toISOString(),
        clicks: null,
        taskId: null,
        analyticsStatus: "Not measured",
      };

      setUrls((previous) => [item, ...previous]);
      setUrl("");
      setNotice("Short URL created successfully.");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function refreshAnalytics(item) {
    setError("");
    setNotice("");
    setAnalyticsLoading(item.shortCode);

    try {
      const task = await request(
        `/urls/${encodeURIComponent(item.shortCode)}/analytics/refresh`,
        apiKey,
        { method: "POST" }
      );

      const taskId = task.task_id;
      if (!taskId) throw new Error("The API did not return a task ID.");

      setUrls((previous) =>
        previous.map((row) =>
          row.id === item.id
            ? { ...row, taskId, analyticsStatus: "Processing" }
            : row
        )
      );

      let finished = false;
      for (let attempt = 0; attempt < 20; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 1000));

        const status = await request(
          `/tasks/${encodeURIComponent(taskId)}`,
          apiKey
        );

        if (status.status === "SUCCESS") {
          const result = status.result ?? {};
          setUrls((previous) =>
            previous.map((row) =>
              row.id === item.id
                ? {
                    ...row,
                    taskId,
                    clicks: Number(result.total_clicks ?? 0),
                    analyticsStatus: "Measured",
                  }
                : row
            )
          );
          setNotice(`Analytics refreshed for ${item.shortCode}.`);
          finished = true;
          break;
        }

        if (status.status === "FAILURE" || status.status === "REVOKED") {
          throw new Error(status.error || "Analytics task failed.");
        }
      }

      if (!finished) {
        setNotice(`Task ${taskId} is still processing. Try refreshing analytics again shortly.`);
      }
    } catch (err) {
      setError(err.message);
      setUrls((previous) =>
        previous.map((row) =>
          row.id === item.id
            ? { ...row, analyticsStatus: "Refresh failed" }
            : row
        )
      );
    } finally {
      setAnalyticsLoading("");
    }
  }

  async function copyUrl(shortCode) {
    const shortUrl = `http://localhost:8000/${shortCode}`;
    try {
      await navigator.clipboard.writeText(shortUrl);
      setCopied(shortCode);
      setNotice("Short link copied.");
      setTimeout(() => setCopied(""), 1800);
    } catch {
      setError(`Copy failed. Select and copy this link: ${shortUrl}`);
    }
  }

  function disconnect() {
    setConnected(false);
    setApiKey("");
    setNotice("");
    setError("");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" aria-label="Shortly home">
          <span className="brand-mark"><Link2 size={22} /></span>
          <span>shortly<span className="brand-dot">.</span></span>
        </a>

        <div className="workspace-label">WORKSPACE</div>
        <button className="nav-item active">
          <BarChart3 size={18} /> Overview
        </button>
        <button
          className="nav-item"
          onClick={() => document.getElementById("url-manager")?.scrollIntoView({ behavior: "smooth" })}
        >
          <Link2 size={18} /> My links
        </button>
        <button
          className="nav-item"
          onClick={() => document.getElementById("analytics")?.scrollIntoView({ behavior: "smooth" })}
        >
          <Activity size={18} /> Analytics
        </button>

        <div className="sidebar-bottom">
          <div className="secure-card">
            <ShieldCheck size={20} />
            <strong>Secure by design</strong>
            <p>API-key protected requests and isolated task access.</p>
          </div>
          <div className="profile-row">
            <div className="avatar">S</div>
            <div className="profile-copy">
              <strong>Developer workspace</strong>
              <span>{connected ? "Connected" : "Not connected"}</span>
            </div>
            {connected && (
              <button className="icon-button" onClick={disconnect} title="Disconnect API key">
                <LogOut size={16} />
              </button>
            )}
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumbs">Workspace <ChevronRight size={15} /> Overview</div>
          <div className="topbar-right">
            <span className={`connection-pill ${connected ? "online" : ""}`}>
              <span className="status-dot" />
              {connected ? "API connected" : "API disconnected"}
            </span>
            <div className="top-avatar">S</div>
          </div>
        </header>

        <div className="page">
          <section className="welcome-row">
            <div>
              <div className="eyebrow"><Sparkles size={14} /> LINK MANAGEMENT</div>
              <h1>Your links, <span>at a glance.</span></h1>
              <p className="subtitle">Create short links and track their performance in one place.</p>
            </div>
            <div className="date-chip"><Activity size={15} /> Live workspace</div>
          </section>

          {(error || notice) && (
            <div className={`alert ${error ? "alert-error" : "alert-success"}`} role="status">
              {error ? <CircleAlert size={18} /> : <Check size={18} />}
              <span>{error || notice}</span>
              <button className="alert-close" onClick={() => { setError(""); setNotice(""); }}>×</button>
            </div>
          )}

          {!connected && (
            <section className="connect-banner">
              <div className="connect-icon"><ShieldCheck size={23} /></div>
              <div className="connect-copy">
                <strong>Connect your API key</strong>
                <p>Use the key generated by your backend. It stays in this page's memory and isn't saved to storage.</p>
              </div>
              <form className="connect-form" onSubmit={connect}>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(event) => setApiKey(event.target.value)}
                  placeholder="Paste API key"
                  aria-label="API key"
                  autoComplete="off"
                />
                <button className="button button-primary" type="submit">
                  Connect <ArrowUpRight size={16} />
                </button>
              </form>
            </section>
          )}

          <section className="stats-grid">
            <article className="stat-card">
              <div className="stat-top"><span>Total short links</span><span className="stat-icon purple"><Link2 size={19} /></span></div>
              <div className="stat-value">{urls.length}</div>
              <div className="stat-foot"><span className="stat-neutral">This session</span><span>Created links</span></div>
            </article>
            <article className="stat-card">
              <div className="stat-top"><span>Total measured clicks</span><span className="stat-icon green"><Activity size={19} /></span></div>
              <div className="stat-value">{totalClicks.toLocaleString()}</div>
              <div className="stat-foot"><span className="stat-neutral">{measuredUrls} measured</span><span>From refreshed analytics</span></div>
            </article>
            <article className="stat-card">
              <div className="stat-top"><span>Analytics coverage</span><span className="stat-icon orange"><BarChart3 size={19} /></span></div>
              <div className="stat-value">{urls.length ? Math.round((measuredUrls / urls.length) * 100) : 0}<span className="value-unit">%</span></div>
              <div className="stat-foot"><span className="stat-neutral">Measured links</span><span>Of session links</span></div>
            </article>
          </section>

          <section className="create-card">
            <div className="section-heading">
              <div className="heading-icon"><Zap size={19} /></div>
              <div><h2>Shorten a new link</h2><p>Turn a long URL into a compact, shareable link.</p></div>
            </div>
            <form className="create-form" onSubmit={createUrl}>
              <div className="url-input-wrap">
                <Link2 size={19} />
                <input
                  type="url"
                  value={url}
                  onChange={(event) => setUrl(event.target.value)}
                  placeholder="https://example.com/your-long-url"
                  aria-label="URL to shorten"
                  required
                />
              </div>
              <button className="button button-primary create-button" disabled={!connected || loading}>
                {loading ? <LoaderCircle className="spin" size={17} /> : <Plus size={18} />}
                {loading ? "Creating..." : "Create short link"}
              </button>
            </form>
            {!connected && <p className="helper-text">Connect your API key above to create links.</p>}
          </section>

          <section className="analytics-card" id="analytics">
            <div className="section-heading chart-heading">
              <div className="heading-icon green-icon"><BarChart3 size={19} /></div>
              <div><h2>Click analytics</h2><p>Click counts returned by your background analytics tasks.</p></div>
            </div>
            {chartData.length ? (
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height={230}>
                  <BarChart data={chartData} margin={{ top: 12, right: 12, left: -16, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e9edf4" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "#8791a5", fontSize: 12 }} />
                    <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: "#8791a5", fontSize: 12 }} />
                    <Tooltip cursor={{ fill: "#f3f5ff" }} contentStyle={{ borderRadius: 12, border: "1px solid #e7eaf1" }} />
                    <Bar dataKey="clicks" name="Clicks" fill="#6558e8" radius={[6, 6, 0, 0]} maxBarSize={48} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="empty-chart">
                <div className="empty-chart-icon"><BarChart3 size={25} /></div>
                <strong>No analytics data yet</strong>
                <p>Create a short link, then select <b>Refresh analytics</b> to load its click count.</p>
              </div>
            )}
          </section>

          <section className="table-card" id="url-manager">
            <div className="table-header">
              <div className="section-heading">
                <div className="heading-icon"><Link2 size={19} /></div>
                <div><h2>Your short links</h2><p>Links created during this dashboard session.</p></div>
              </div>
              <div className="filter-tabs">
                {[
                  ["all", "All links"],
                  ["measured", "Measured"],
                  ["unmeasured", "Unmeasured"],
                ].map(([value, label]) => (
                  <button key={value} className={filter === value ? "filter-tab selected" : "filter-tab"} onClick={() => setFilter(value)}>
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {visibleUrls.length ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr><th>SHORT LINK</th><th>DESTINATION</th><th>CLICKS</th><th>STATUS</th><th>CREATED</th><th>ACTIONS</th></tr>
                  </thead>
                  <tbody>
                    {visibleUrls.map((item) => (
                      <tr key={item.id}>
                        <td>
                          <div className="short-link-cell">
                            <span className="link-symbol"><Link2 size={15} /></span>
                            <div>
                              <a href={`http://localhost:8000/${item.shortCode}`} target="_blank" rel="noreferrer" className="short-link-text">{item.shortCode}</a>
                              <span className="short-link-domain">localhost:8000</span>
                            </div>
                          </div>
                        </td>
                        <td><span className="destination" title={item.originalUrl}>{item.originalUrl}</span></td>
                        <td><span className="click-count">{item.clicks === null ? "—" : item.clicks.toLocaleString()}</span></td>
                        <td><span className={`row-status ${item.clicks === null ? "status-pending" : "status-done"}`}><span />{item.analyticsStatus}</span></td>
                        <td><span className="created-date">{new Date(item.createdAt).toLocaleDateString()}</span></td>
                        <td>
                          <div className="action-buttons">
                            <button className="icon-button" title="Copy short URL" onClick={() => copyUrl(item.shortCode)}>
                              {copied === item.shortCode ? <Check size={16} /> : <Copy size={16} />}
                            </button>
                            <button
                              className="icon-button refresh-button"
                              title="Refresh analytics"
                              disabled={analyticsLoading === item.shortCode || !connected}
                              onClick={() => refreshAnalytics(item)}
                            >
                              {analyticsLoading === item.shortCode ? <LoaderCircle className="spin" size={16} /> : <RefreshCw size={16} />}
                            </button>
                            <a className="icon-button" title="Open destination" href={item.originalUrl} target="_blank" rel="noreferrer"><ExternalLink size={16} /></a>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-table">
                <div className="empty-table-icon"><Unplug size={24} /></div>
                <strong>{urls.length ? "No links match this filter" : "Your first short link starts here"}</strong>
                <p>{urls.length ? "Try another filter." : "Paste a destination URL above to create your first short link."}</p>
                {!urls.length && <button className="button button-secondary" onClick={() => document.querySelector('input[aria-label="URL to shorten"]')?.focus()}>Create a link <ChevronRight size={16} /></button>}
              </div>
            )}
            <div className="table-footer">
              <span>Showing {visibleUrls.length} of {urls.length} session links</span>
              <span><ShieldCheck size={14} /> Protected by API-key authentication</span>
            </div>
          </section>

          <footer className="footer">
            <span>shortly<span className="brand-dot">.</span> <span className="footer-muted">URL Shortener & Analytics Platform</span></span>
            <span>Built with FastAPI · PostgreSQL · Redis · Celery · React</span>
          </footer>
        </div>
      </main>
    </div>
  );
}

export default App;

