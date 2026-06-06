import { useEffect, useState } from "react";
import {
  clearAccessKey,
  getDashboard,
  getStoredAccessKey,
  refreshDashboard,
  storeAccessKey,
  validateAccessKey,
} from "./api";
import creatorPhoto from "./assets/job-villagran.png";
import brandLogoColor from "./assets/athena-desk-color.png";
import brandLogoWhite from "./assets/athena-desk-white.png";

function formatStatusLabel(value) {
  if (!value) return "Info";

  const dictionary = {
    not_enabled_yet: "Not enabled yet",
    submitted: "Submitted",
    missing: "Missing",
    late: "Late",
    unsubmitted: "Not submitted",
    open: "Open",
    closed: "Closed",
    published: "Published",
    healthy: "Healthy",
    watch: "Watch",
    at_risk: "At risk",
    not_enough_data: "Not enough data",
    no_due_date: "No due date",
  };

  if (dictionary[value]) {
    return dictionary[value];
  }

  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getStatusClass(value) {
  const normalized = (value || "").toLowerCase();

  if (["submitted", "healthy", "open", "published"].includes(normalized)) {
    return "submitted";
  }

  if (["missing", "late", "at_risk"].includes(normalized)) {
    return "danger";
  }

  if (["not_enabled_yet", "watch", "not_enough_data", "no_due_date"].includes(normalized)) {
    return "not_enabled_yet";
  }

  return "default";
}

function BrandLockup({ compact = false, theme = "light", showSubtitle = true }) {
  const logoSrc = theme === "dark" ? brandLogoWhite : brandLogoColor;

  return (
    <div className={`brand-lockup ${compact ? "compact" : ""} ${theme}`}>
      <img src={logoSrc} alt="Athena Desk logo" className="brand-logo" />
      <div className="brand-text-wrap">
        <div className="brand-name">Athena Desk</div>
        {showSubtitle ? (
          <div className="brand-subtitle">Secure academic workspace</div>
        ) : null}
      </div>
    </div>
  );
}

function StatCard({ label, value, tone = "default" }) {
  return (
    <div className={`stat-card ${tone}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function SyncBanner({ sync }) {
  if (!sync) return null;

  return (
    <div className={`sync-banner ${sync.status}`}>
      <div className="sync-banner-title">
        {sync.status === "healthy" ? "Sync healthy" : "Sync issue"}
      </div>
      <div className="sync-banner-text">{sync.message}</div>
      {sync.last_synced_at ? (
        <small>Last sync: {new Date(sync.last_synced_at).toLocaleString()}</small>
      ) : null}
    </div>
  );
}

function AssignmentList({ title, items }) {
  if (!items || items.length === 0) return null;

  return (
    <section className="panel panel-soft">
      <div className="panel-header">
        <h2>{title}</h2>
        <span className="panel-count">{items.length}</span>
      </div>

      <div className="assignment-list">
        {items.map((item, index) => (
          <div className="assignment-card" key={`${item.assignment_id || item.assignment_name}-${index}`}>
            <div className="assignment-card-top">
              <div className="assignment-course">{item.course_name}</div>
              <span className={`mini-tag ${getStatusClass(item.status)}`}>
                {formatStatusLabel(item.status)}
              </span>
            </div>

            <div className="assignment-title">{item.assignment_name}</div>

            <div className="assignment-meta">
              {item.due_date_iso ? `Due: ${new Date(item.due_date_iso).toLocaleString()}` : "No due date"}
            </div>

            {typeof item.hours_until_due === "number" ? (
              <div
                className={`urgency-line ${
                  item.hours_until_due <= 24
                    ? "critical"
                    : item.hours_until_due <= 48
                    ? "warning"
                    : "normal"
                }`}
              >
                {item.hours_until_due <= 24
                  ? `Act now • ${item.hours_until_due.toFixed(1)}h left`
                  : item.hours_until_due <= 48
                  ? `Soon • ${item.hours_until_due.toFixed(1)}h left`
                  : `Planned • ${item.hours_until_due.toFixed(1)}h left`}
              </div>
            ) : null}

            {item.submitted_at ? (
              <div className="submitted-note">Submitted • waiting for grading</div>
            ) : null}

            {item.assignment_url ? (
              <a className="action-link" href={item.assignment_url} target="_blank" rel="noreferrer">
                Open in Canvas
              </a>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}

function RiskPill({ level }) {
  const map = {
    healthy: "healthy",
    watch: "watch",
    at_risk: "at_risk",
    not_enough_data: "neutral",
  };

  return (
    <span className={`risk-pill ${map[level] || "neutral"}`}>
      {formatStatusLabel(level)}
    </span>
  );
}

function CourseCard({ course }) {
  return (
    <div className="course-card">
      <div className="course-top">
        <div>
          <div className="course-name">{course.course_name}</div>
          <div className="course-code">{course.course_code || "Current course"}</div>
        </div>
        <RiskPill level={course.risk_level} />
      </div>

      <div className="course-metrics">
        <div>
          <span>Earned</span>
          <strong>{course.earned_points}</strong>
        </div>
        <div>
          <span>Published</span>
          <strong>{course.published_points}</strong>
        </div>
        <div>
          <span>Pending grade</span>
          <strong>{course.submitted_pending_points}</strong>
        </div>
        <div>
          <span>To pass</span>
          <strong>{course.remaining_to_pass}</strong>
        </div>
      </div>

      <div className="progress-block">
        <div className="progress-label-row">
          <span>Progress to pass</span>
          <span>{course.pass_progress_percent}%</span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{
              width: `${Math.min(100, course.pass_progress_percent)}%`,
            }}
          />
        </div>
      </div>

      <div className="course-footer">
        <span>Graded: {course.graded_count}</span>
        <span>Submitted: {course.submitted_pending_count}</span>
        <span>Open: {course.open_count}</span>
      </div>

      <div className="risk-reason">{course.risk_reason}</div>
    </div>
  );
}

function AccessGate({ onUnlock, errorMessage, loading }) {
  const [accessKey, setAccessKey] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    if (!accessKey.trim() || loading) return;
    await onUnlock(accessKey.trim());
  };

  return (
    <div className="gate-shell">
      <div className="gate-layout">
        <div className="gate-brand-panel">
          <BrandLockup theme="dark" />

          <h1>Secure academic workspace</h1>

          <p>
            Enter your private access key to open your personal university dashboard,
            refresh tasks, and review course progress securely.
          </p>

          <div className="gate-brand-points">
            <div>Current-term courses only</div>
            <div>Canvas-backed live sync</div>
            <div>Protected refresh and dashboard access</div>
          </div>
        </div>

        <div className="gate-card">
          <div className="creator-block">
            <img
              src={creatorPhoto}
              alt="Job Villagran"
              className="creator-avatar"
            />

            <div className="creator-meta">
              <span className="creator-label">Created by</span>
              <a
                href="https://www.linkedin.com/in/jobvillagran/"
                target="_blank"
                rel="noreferrer"
                className="creator-link"
              >
                Job Villagran
              </a>
            </div>
          </div>

          <div className="gate-title">Welcome back</div>
          <div className="gate-subtitle">
            Enter your private access key to continue.
          </div>

          <form onSubmit={submit} className="gate-form">
            <label className="gate-label" htmlFor="accessKey">
              Access key
            </label>

            <input
              id="accessKey"
              type="password"
              className="gate-input"
              placeholder="Enter access key"
              value={accessKey}
              onChange={(e) => setAccessKey(e.target.value)}
              autoComplete="off"
            />

            {errorMessage ? <div className="gate-error">{errorMessage}</div> : null}

            <button type="submit" className="gate-button" disabled={loading}>
              {loading ? "Validating..." : "Unlock dashboard"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [authError, setAuthError] = useState("");
  const [isUnlocked, setIsUnlocked] = useState(false);

  useEffect(() => {
    const existingKey = getStoredAccessKey();
    if (!existingKey) return;

    const bootstrap = async () => {
      try {
        setLoading(true);
        setError("");
        setAuthError("");

        const payload = await getDashboard(false);
        setData(payload);
        setIsUnlocked(true);
      } catch (_) {
        clearAccessKey();
        setIsUnlocked(false);
        setData(null);
        setAuthError("Your saved key is no longer valid. Please enter it again.");
      } finally {
        setLoading(false);
      }
    };

    bootstrap();
  }, []);

  const load = async (force = false) => {
    try {
      setError("");
      if (force) setRefreshing(true);
      else setLoading(true);

      const payload = force ? await refreshDashboard() : await getDashboard(false);
      setData(payload);
    } catch (err) {
      if (String(err.message).includes("401")) {
        clearAccessKey();
        setIsUnlocked(false);
        setData(null);
        setAuthError("Invalid access key.");
      } else {
        setError(err.message || "Failed to load dashboard.");
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const unlock = async (key) => {
    try {
      setLoading(true);
      setAuthError("");
      setError("");

      const payload = await validateAccessKey(key);

      storeAccessKey(key);
      setData(payload);
      setIsUnlocked(true);
    } catch (_) {
      clearAccessKey();
      setIsUnlocked(false);
      setData(null);
      setAuthError("Invalid access key. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    clearAccessKey();
    setData(null);
    setError("");
    setAuthError("");
    setIsUnlocked(false);
  };

  if (!isUnlocked) {
    return (
      <AccessGate
        onUnlock={unlock}
        errorMessage={authError}
        loading={loading}
      />
    );
  }

  if (loading && !data) {
    return <div className="screen-state">Loading dashboard...</div>;
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero-main">
          <BrandLockup compact theme="light" showSubtitle={false} />
          <div className="hero-copy">
            <div className="hero-eyebrow">Private dashboard</div>
            <p>Current term, live sync, clearer priorities.</p>
          </div>
        </div>

        <div className="hero-actions">
          <button className="refresh-btn" onClick={() => load(true)} disabled={refreshing}>
            {refreshing ? "Refreshing..." : "Refresh now"}
          </button>

          <button className="logout-btn" onClick={logout}>
            Lock
          </button>
        </div>
      </header>

      <SyncBanner sync={data?.sync} />
      {error ? <div className="error-banner">{error}</div> : null}

      <section className="stats-grid">
        <StatCard label="Actionable" value={data?.summary?.actionable ?? 0} />
        <StatCard label="Urgent" value={data?.summary?.urgent ?? 0} tone="danger" />
        <StatCard label="Opens soon" value={data?.summary?.opens_soon ?? 0} tone="indigo" />
        <StatCard label="Projects" value={data?.summary?.projects ?? 0} tone="amber" />
        <StatCard label="Submitted" value={data?.summary?.submitted ?? 0} tone="green" />
        <StatCard label="At risk" value={data?.summary?.courses_at_risk ?? 0} tone="danger" />
        <StatCard label="Watch" value={data?.summary?.courses_watch ?? 0} tone="amber" />
        <StatCard label="Too early" value={data?.summary?.courses_not_enough_data ?? 0} tone="neutral" />
      </section>

      <AssignmentList title="Act now" items={data?.groups?.act_now} />
      <AssignmentList title="This week" items={data?.groups?.this_week} />
      <AssignmentList title="Next week" items={data?.groups?.next_week} />
      <AssignmentList title="Third week" items={data?.groups?.third_week} />
      <AssignmentList title="Opens soon" items={data?.groups?.opens_soon} />
      <AssignmentList title="Submitted" items={data?.groups?.submitted} />
      <AssignmentList title="No due date" items={data?.groups?.no_due_date} />

      <section className="panel panel-strong">
        <div className="panel-header">
          <h2>Course progress</h2>
          <span className="panel-count">{data?.courses?.length ?? 0}</span>
        </div>

        <div className="course-grid">
          {data?.courses?.map((course) => (
            <CourseCard key={course.course_id} course={course} />
          ))}
        </div>
      </section>
    </div>
  );
}