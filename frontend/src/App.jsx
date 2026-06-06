import { useEffect, useState } from "react";
import {
  clearAccessKey,
  getDashboard,
  getStoredAccessKey,
  refreshDashboard,
  storeAccessKey,
} from "./api";

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
      <strong>{sync.status === "healthy" ? "Sync healthy" : "Sync issue"}</strong>
      <span>{sync.message}</span>
      {sync.last_synced_at ? (
        <small>Last sync: {new Date(sync.last_synced_at).toLocaleString()}</small>
      ) : null}
    </div>
  );
}

function AssignmentList({ title, items }) {
  if (!items || items.length === 0) return null;

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>{title}</h2>
      </div>

      <div className="assignment-list">
        {items.map((item, index) => (
          <div className="assignment-card" key={`${item.assignment_id || item.assignment_name}-${index}`}>
            <div className="assignment-top">
              <div className="assignment-course">{item.course_name}</div>
              <span className={`mini-tag ${item.status || "default"}`}>
                {item.status || "info"}
              </span>
            </div>

            <div className="assignment-title">{item.assignment_name}</div>

            <div className="assignment-meta">
              {item.due_date_iso ? `Due: ${new Date(item.due_date_iso).toLocaleString()}` : "No due date"}
            </div>

            {item.submitted_at ? (
              <div className="submitted-note">Submitted • waiting for grading</div>
            ) : null}

            {typeof item.hours_until_due === "number" ? (
              <div className="time-note">
                {item.hours_until_due <= 48
                  ? `Due in ${item.hours_until_due.toFixed(1)}h`
                  : `Remaining: ${item.hours_until_due.toFixed(1)}h`}
              </div>
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

  return <span className={`risk-pill ${map[level] || "neutral"}`}>{level.replaceAll("_", " ")}</span>;
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

function AccessGate({ onUnlock, errorMessage }) {
  const [accessKey, setAccessKey] = useState("");

  const submit = (event) => {
    event.preventDefault();
    if (!accessKey.trim()) return;
    onUnlock(accessKey.trim());
  };

  return (
    <div className="gate-shell">
      <div className="gate-card">
        <div className="gate-title">College Control</div>
        <div className="gate-subtitle">
          Enter your private access key to open the dashboard.
        </div>

        <form onSubmit={submit} className="gate-form">
          <input
            type="password"
            className="gate-input"
            placeholder="Access key"
            value={accessKey}
            onChange={(e) => setAccessKey(e.target.value)}
          />

          <button type="submit" className="gate-button">
            Unlock
          </button>
        </form>

        {errorMessage ? <div className="gate-error">{errorMessage}</div> : null}
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
  const [isUnlocked, setIsUnlocked] = useState(Boolean(getStoredAccessKey()));

  const load = async (force = false) => {
    try {
      setError("");
      if (force) setRefreshing(true);
      else setLoading(true);

      const payload = force ? await refreshDashboard() : await getDashboard(false);
      setData(payload);
      setAuthError("");
      setIsUnlocked(true);
    } catch (err) {
      if (String(err.message).includes("401")) {
        clearAccessKey();
        setIsUnlocked(false);
        setAuthError("Invalid access key.");
        setData(null);
      } else {
        setError(err.message || "Failed to load dashboard.");
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (!isUnlocked) return;
    load(false);
  }, [isUnlocked]);

  const unlock = async (key) => {
    storeAccessKey(key);
    setIsUnlocked(true);
    setAuthError("");
    await load(false);
  };

  const logout = () => {
    clearAccessKey();
    setData(null);
    setError("");
    setAuthError("");
    setIsUnlocked(false);
  };

  if (!isUnlocked) {
    return <AccessGate onUnlock={unlock} errorMessage={authError} />;
  }

  if (loading && !data) {
    return <div className="screen-state">Loading dashboard...</div>;
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <h1>College Control</h1>
          <p>Clear view of your courses, tasks, and progress.</p>
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

      <section className="panel">
        <div className="panel-header">
          <h2>Course progress</h2>
        </div>

        <div className="course-grid">
          {data?.courses?.map((course) => (
            <CourseCard key={course.course_id} course={course} />
          ))}
        </div>
      </section>

      <AssignmentList title="Act now" items={data?.groups?.act_now} />
      <AssignmentList title="This week" items={data?.groups?.this_week} />
      <AssignmentList title="Next week" items={data?.groups?.next_week} />
      <AssignmentList title="Third week" items={data?.groups?.third_week} />
      <AssignmentList title="Opens soon" items={data?.groups?.opens_soon} />
      <AssignmentList title="Submitted" items={data?.groups?.submitted} />
      <AssignmentList title="No due date" items={data?.groups?.no_due_date} />
    </div>
  );
}