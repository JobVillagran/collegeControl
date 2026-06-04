import { useEffect, useState } from "react";
import { getDashboard, refreshDashboard } from "./api";

function StatCard({ label, value, tone = "default" }) {
  return (
    <div className={`stat-card ${tone}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function AssignmentList({ title, items, badge }) {
  if (!items || items.length === 0) return null;

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>{title}</h2>
        {badge ? <span className="section-badge">{badge}</span> : null}
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

function CourseCard({ course }) {
  return (
    <div className="course-card">
      <div className="course-top">
        <div>
          <div className="course-name">{course.course_name}</div>
          <div className="course-code">{course.course_code || "Current course"}</div>
        </div>
        <span className={`risk-pill ${course.risk_level}`}>{course.risk_level.replace("_", " ")}</span>
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
          <span>Progress to pass ({course.passing_score})</span>
          <span>{course.known_progress_percent}%</span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{
              width: `${Math.min(100, (course.earned_points / course.passing_score) * 100)}%`,
            }}
          />
        </div>
      </div>

      <div className="course-footer">
        <span>Graded: {course.graded_count}</span>
        <span>Submitted: {course.submitted_pending_count}</span>
        <span>Open: {course.open_count}</span>
      </div>
    </div>
  );
}

export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = async (force = false) => {
    try {
      setError("");
      if (force) setRefreshing(true);
      else setLoading(true);

      const payload = force ? await refreshDashboard() : await getDashboard(false);
      setData(payload);
    } catch (err) {
      setError(err.message || "Failed to load dashboard.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    load(false);
  }, []);

  if (loading) {
    return <div className="screen-state">Loading dashboard...</div>;
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <h1>College Control</h1>
          <p>Direct, clear, and always current.</p>
        </div>

        <button className="refresh-btn" onClick={() => load(true)} disabled={refreshing}>
          {refreshing ? "Refreshing..." : "Refresh now"}
        </button>
      </header>

      {data?.sync ? (
        <div className={`sync-banner ${data.sync.status}`}>
          <strong>{data.sync.status === "healthy" ? "Sync healthy" : "Sync issue"}</strong>
          <span>{data.sync.message}</span>
        </div>
      ) : null}

      {error ? <div className="error-banner">{error}</div> : null}

      <section className="stats-grid">
        <StatCard label="Actionable" value={data?.summary?.actionable ?? 0} />
        <StatCard label="Urgent" value={data?.summary?.urgent ?? 0} tone="danger" />
        <StatCard label="Opens soon" value={data?.summary?.opens_soon ?? 0} tone="indigo" />
        <StatCard label="Projects" value={data?.summary?.projects ?? 0} tone="amber" />
        <StatCard label="Submitted" value={data?.summary?.submitted ?? 0} tone="green" />
        <StatCard label="Courses at risk" value={data?.summary?.courses_at_risk ?? 0} tone="danger" />
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

      <AssignmentList title="Act now" items={data?.groups?.act_now} badge="urgent" />
      <AssignmentList title="This week" items={data?.groups?.this_week} />
      <AssignmentList title="Next week" items={data?.groups?.next_week} />
      <AssignmentList title="Third week" items={data?.groups?.third_week} />
      <AssignmentList title="Opens soon" items={data?.groups?.opens_soon} />
      <AssignmentList title="Submitted" items={data?.groups?.submitted} badge="waiting for grading" />
    </div>
  );
}