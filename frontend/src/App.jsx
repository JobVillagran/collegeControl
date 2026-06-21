import { useEffect, useMemo, useState } from "react";
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

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
  timeZone: "America/Guatemala",
});

function formatNumber(value) {
  const numeric = Number(value ?? 0);
  if (Number.isNaN(numeric)) return "0";
  if (Number.isInteger(numeric)) return String(numeric);
  return numeric.toFixed(2).replace(/\.00$/, "").replace(/(\.\d)0$/, "$1");
}

function formatDateTime(value) {
  if (!value) return "No due date";
  try {
    const result = DATE_TIME_FORMATTER.format(new Date(value));
    return result.replace(" am", " AM").replace(" pm", " PM");
  } catch {
    return value;
  }
}

function formatStatusLabel(value) {
  if (!value) return "Info";
  const dictionary = {
    not_enabled_yet: "Not enabled yet",
    submitted: "Submitted",
    submitted_pending: "Pending review",
    graded: "Graded",
    missing: "Missed",
    late: "Late",
    unsubmitted: "Not submitted",
    open: "Open",
    open_no_due_date: "Open",
    closed: "Closed",
    published: "Published",
    healthy: "Healthy",
    watch: "Watch",
    at_risk: "At risk",
    critical: "Critical",
    not_enough_data: "Incomplete data",
    no_due_date: "No due date",
    not_applicable: "N/A",
    passed: "Passed",
    failed: "Failed",
    in_progress: "In progress",
  };
  if (dictionary[value]) return dictionary[value];
  return value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function getStatusClass(value) {
  const normalized = (value || "").toLowerCase();
  if (["submitted", "graded", "healthy", "open", "published", "passed"].includes(normalized)) return "success";
  if (["missing", "late", "at_risk", "critical", "failed"].includes(normalized)) return "danger";
  if (["submitted_pending", "watch", "not_enabled_yet", "not_enough_data", "no_due_date"].includes(normalized)) return "warning";
  return "neutral";
}

function BrandLockup({ compact = false, theme = "light", showSubtitle = true }) {
  const logoSrc = theme === "dark" ? brandLogoWhite : brandLogoColor;
  return (
    <div className={`brand-lockup ${compact ? "compact" : ""} ${theme}`}>
      <img src={logoSrc} alt="Athena Desk logo" className="brand-logo" />
      <div className="brand-text-wrap">
        <div className="brand-name">Athena Desk</div>
        {showSubtitle ? <div className="brand-subtitle">Secure academic workspace</div> : null}
      </div>
    </div>
  );
}

function StatCard({ label, value, tone = "default" }) {
  return (
    <div className={`stat-card ${tone}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{formatNumber(value)}</div>
    </div>
  );
}

function SyncBanner({ sync }) {
  if (!sync) return null;
  return (
    <div className={`sync-banner ${sync.status || "healthy"}`}>
      <div className="sync-banner-title">{sync.status === "healthy" ? "Sync healthy" : "Sync issue"}</div>
      <div className="sync-banner-text">{sync.message}</div>
      {sync.last_synced_at ? <small>Last sync: {formatDateTime(sync.last_synced_at)}</small> : null}
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
            <div className="assignment-card-header">
              <div className="assignment-card-copy">
                <div className="assignment-course">{item.course_name}</div>
                <div className="assignment-title">{item.assignment_name}</div>
                <div className="assignment-meta">Due: {item.due_date_iso ? formatDateTime(item.due_date_iso) : "No due date"}</div>
              </div>
              <span className={`status-pill ${getStatusClass(item.status)}`}>{formatStatusLabel(item.status)}</span>
            </div>
            <div className="assignment-card-actions">
              {typeof item.hours_until_due === "number" ? (
                <div className={`urgency-chip ${item.hours_until_due <= 24 ? "critical" : item.hours_until_due <= 48 ? "warning" : "normal"}`}>
                  {item.hours_until_due <= 24
                    ? `Act now • ${formatNumber(item.hours_until_due)}h left`
                    : item.hours_until_due <= 48
                    ? `Soon • ${formatNumber(item.hours_until_due)}h left`
                    : `Upcoming • ${formatNumber(item.hours_until_due)}h left`}
                </div>
              ) : null}
              {item.submitted_at ? <div className="submitted-note">Submitted • waiting for grading</div> : null}
              {item.assignment_url ? <a className="action-link" href={item.assignment_url} target="_blank" rel="noreferrer">Open in Canvas</a> : null}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function RiskPill({ level }) {
  return <span className={`risk-pill ${getStatusClass(level)}`}>{formatStatusLabel(level)}</span>;
}

function MetricTile({ label, value, helper = "", tone = "neutral" }) {
  return (
    <div className={`metric-tile ${tone}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {helper ? <div className="metric-helper">{helper}</div> : null}
    </div>
  );
}

function MicroStat({ label, value, tone = "neutral" }) {
  return (
    <div className={`micro-stat ${tone}`}>
      <div className="micro-stat-label">{label}</div>
      <div className="micro-stat-value">{value}</div>
    </div>
  );
}

function ScoreBar({ course }) {
  const earnedPercent = Math.max(0, Math.min(100, Number(course.earned_effective_points ?? course.earned_points ?? 0)));
  const riskTone = getStatusClass(course.risk_level);
  return (
    <div className="score-block">
      <div className="score-header-row">
        <div>
          <div className="score-block-label">Real points earned</div>
          <div className="score-block-value">{`${formatNumber(course.earned_effective_points ?? course.earned_points ?? 0)} / ${formatNumber(course.total_points ?? 100)}`}</div>
        </div>
        <div className="score-threshold">
          Pass mark
          <strong>{formatNumber(course.passing_score)} / {formatNumber(course.total_points ?? 100)}</strong>
        </div>
      </div>
      <div className="score-bar-shell">
        <div className="score-bar-track">
          <div className={`score-bar-fill ${riskTone}`} style={{ width: `${earnedPercent}%` }} />
          <div className="score-pass-marker" style={{ left: `${Math.min(Number(course.pass_threshold_percent ?? 61), 100)}%` }} />
        </div>
      </div>
      <div className="score-bar-scale">
        <span>0</span>
        <span className="score-pass-text">{formatNumber(course.passing_score)} to pass</span>
        <span>{formatNumber(course.total_points ?? 100)}</span>
      </div>
    </div>
  );
}

function AttendanceBadge({ attendance }) {
  const level = attendance?.level || "not_applicable";
  return (
    <div className={`attendance-box ${getStatusClass(level)}`}>
      <div className="attendance-label">Attendance</div>
      <div className="attendance-value">{attendance?.label || "N/A"}</div>
    </div>
  );
}

function ComponentsSummary({ components }) {
  if (!components || components.length === 0) return null;
  return (
    <div className="component-summary">
      {components.slice(0, 6).map((component) => (
        <div className="component-row" key={component.type}>
          <span>{component.label}</span>
          <strong>{formatNumber(component.earned_points)} / {formatNumber(component.published_points)}</strong>
        </div>
      ))}
    </div>
  );
}

function RecoverySummary({ recoveryEvents }) {
  if (!recoveryEvents || recoveryEvents.length === 0) return null;
  return (
    <div className="recovery-summary">
      <div className="recovery-title">Recovery rule</div>
      {recoveryEvents.map((event, index) => (
        <div className="recovery-row" key={`${event.component}-${index}`}>
          <span>{event.applied ? "Applied" : "Not applied"}</span>
          <strong>{formatNumber(event.recovery_score)} / {formatNumber(event.recovery_points)}</strong>
        </div>
      ))}
    </div>
  );
}

function CourseCard({ course }) {
  const pendingReviewCount = Number(course.pending_grade_count ?? 0);

  const explanatoryText = useMemo(() => {
    const parts = [];
    parts.push(`Real points: ${formatNumber(course.earned_effective_points ?? course.earned_points ?? 0)} / ${formatNumber(course.total_points ?? 100)}.`);
    parts.push(`Effective published points: ${formatNumber(course.effective_published_points ?? course.published_points ?? 0)}.`);

    if (Number(course.lost_points ?? 0) > 0) parts.push(`${formatNumber(course.lost_points)} point(s) are already lost.`);
    if (Number(course.pending_points ?? 0) > 0) parts.push(`${formatNumber(course.pending_points)} point(s) are submitted but pending grade.`);
    if (Number(course.open_points ?? 0) > 0) parts.push(`${formatNumber(course.open_points)} point(s) are still open.`);
    if (Number(course.hidden_or_review_points ?? 0) > 0) parts.push(`${formatNumber(course.hidden_or_review_points)} point(s) need manual/detail review.`);
    if (Number(course.remaining_unpublished_points ?? 0) > 0) parts.push(`${formatNumber(course.remaining_unpublished_points)} point(s) are estimated as not published yet.`);
    if (Number(course.remaining_to_pass ?? 0) > 0) parts.push(`Need ${formatNumber(course.remaining_to_pass)} more point(s) to reach ${formatNumber(course.passing_score)}.`);
    if (course.required_percent_of_remaining !== null && course.required_percent_of_remaining !== undefined) {
      parts.push(`Required from remaining: ${formatNumber(course.required_percent_of_remaining)}%.`);
    }
    return parts.join(" ");
  }, [course]);

  return (
    <div className="course-card">
      <div className="course-top">
        <div className="course-title-wrap">
          <div className="course-name">{course.course_name}</div>
          <div className="course-code">{course.course_code || "Current course"}</div>
        </div>
        <RiskPill level={course.risk_level} />
      </div>

      <div className="course-metrics">
        <MetricTile label="Earned points" value={`${formatNumber(course.earned_effective_points ?? course.earned_points)} / ${formatNumber(course.total_points)}`} helper="Real confirmed points" tone="neutral" />
        {course.course_finished ? (
          <MetricTile label="Final result" value={formatStatusLabel(course.course_result)} helper="Final/Recovery grade found" tone={course.course_result === "passed" ? "success" : "danger"} />
        ) : (
          <MetricTile label="Need to pass" value={formatNumber(course.remaining_to_pass)} helper={`Pass mark: ${formatNumber(course.passing_score)}`} tone={Number(course.remaining_to_pass ?? 0) > 0 ? "warning" : "success"} />
        )}
        <MetricTile label="Lost points" value={formatNumber(course.lost_points)} helper="Missed + points lost in grades" tone={Number(course.lost_points ?? 0) > 0 ? "danger" : "success"} />
        <MetricTile label="Available" value={formatNumber(course.remaining_available_points)} helper="Open + pending + unpublished" tone="success" />
      </div>

      <div className="missing-strip">
        <div className="missing-strip-title">Point audit</div>
        <div className="missing-strip-values">
          <span>Published: {formatNumber(course.effective_published_points ?? course.published_points)}</span>
          <span>Pending: {formatNumber(course.pending_points)}</span>
          <span>Review: {formatNumber(course.hidden_or_review_points)}</span>
          <span>Unpublished est.: {formatNumber(course.remaining_unpublished_points)}</span>
        </div>
      </div>

      <ScoreBar course={course} />

      <div className="course-status-row">
        <MicroStat label="Graded" value={formatNumber(course.graded_count)} />
        <MicroStat label="Pending" value={formatNumber(pendingReviewCount)} tone="warning" />
        <MicroStat label="Missed" value={formatNumber(course.missing_count)} tone="danger" />
        <AttendanceBadge attendance={course.attendance} />
      </div>

      <ComponentsSummary components={course.components} />
      <RecoverySummary recoveryEvents={course.recovery_events} />

      <div className="risk-reason">{course.risk_reason || explanatoryText}</div>
      <div className="risk-reason secondary">{explanatoryText}</div>
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
          <p>Enter your private access key to open your personal university dashboard, refresh tasks, and review course progress securely.</p>
          <div className="gate-brand-points">
            <div>Current-term courses only</div>
            <div>Canvas-backed live sync</div>
            <div>Protected refresh and dashboard access</div>
          </div>
        </div>
        <div className="gate-card">
          <div className="creator-block">
            <img src={creatorPhoto} alt="Job Villagran" className="creator-avatar" />
            <div className="creator-meta">
              <span className="creator-label">Created by</span>
              <a href="https://www.linkedin.com/in/jobvillagran/" target="_blank" rel="noreferrer" className="creator-link">Job Villagran</a>
            </div>
          </div>
          <div className="gate-title">Welcome back</div>
          <div className="gate-subtitle">Enter your private access key to continue.</div>
          <form onSubmit={submit} className="gate-form">
            <label className="gate-label" htmlFor="accessKey">Access key</label>
            <input id="accessKey" type="password" className="gate-input" placeholder="Enter access key" value={accessKey} onChange={(e) => setAccessKey(e.target.value)} autoComplete="off" />
            {errorMessage ? <div className="gate-error">{errorMessage}</div> : null}
            <button type="submit" className="gate-button" disabled={loading}>{loading ? "Validating..." : "Unlock dashboard"}</button>
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
      } catch {
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
    } catch {
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

  if (!isUnlocked) return <AccessGate onUnlock={unlock} errorMessage={authError} loading={loading} />;
  if (loading && !data) return <div className="screen-state">Loading dashboard...</div>;

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero-main"><BrandLockup compact theme="light" showSubtitle={false} /></div>
        <div className="hero-actions">
          <button className="refresh-btn" onClick={() => load(true)} disabled={refreshing}>{refreshing ? "Refreshing..." : "Refresh now"}</button>
          <button className="logout-btn" onClick={logout}>Lock</button>
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
        <StatCard label="Incomplete" value={data?.summary?.courses_not_enough_data ?? 0} tone="neutral" />
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
          {data?.courses?.map((course) => <CourseCard key={course.course_id} course={course} />)}
        </div>
      </section>
    </div>
  );
}
