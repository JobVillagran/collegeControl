import { useEffect, useMemo, useState } from "react";
import {
  clearAccessKey,
  getDashboard,
  getStoredAccessKey,
  refreshDashboard,
  storeAccessKey,
  validateAccessKey,
} from "./api";
import {
  LANGUAGES,
  createTranslator,
  getInitialLanguage,
  saveLanguage,
  translateStatus,
  translateSyncMessage,
} from "./i18n";
import creatorPhoto from "./assets/job-villagran.png";
import brandLogoColor from "./assets/athena-desk-color.png";
import brandLogoWhite from "./assets/athena-desk-white.png";

const TIME_ZONE = "America/Guatemala";

function getLocale(language) {
  return LANGUAGES[language]?.locale || LANGUAGES.en.locale;
}

function formatNumber(value) {
  const numeric = Number(value ?? 0);
  if (Number.isNaN(numeric)) return "0";
  if (Number.isInteger(numeric)) return String(numeric);
  return numeric.toFixed(2).replace(/\.00$/, "").replace(/(\.\d)0$/, "$1");
}

function formatDateTime(value, language) {
  if (!value) return null;
  try {
    const result = new Intl.DateTimeFormat(getLocale(language), {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
      timeZone: TIME_ZONE,
    }).format(new Date(value));

    return result.replace(" am", " AM").replace(" pm", " PM").replace("a. m.", "AM").replace("p. m.", "PM");
  } catch {
    return value;
  }
}

function getStatusClass(value) {
  const normalized = (value || "").toLowerCase();
  if (["submitted", "graded", "healthy", "open", "published", "passed"].includes(normalized)) return "success";
  if (["missing", "late", "at_risk", "critical", "failed"].includes(normalized)) return "danger";
  if (["submitted_pending", "watch", "not_enabled_yet", "not_enough_data", "no_due_date"].includes(normalized)) return "warning";
  return "neutral";
}

function LanguageToggle({ language, onChange, compact = false }) {
  return (
    <div className={`language-toggle ${compact ? "compact" : ""}`} role="group" aria-label="Language selector">
      <button
        type="button"
        className={language === "en" ? "active" : ""}
        onClick={() => onChange("en")}
        aria-pressed={language === "en"}
      >
        EN
      </button>
      <button
        type="button"
        className={language === "es" ? "active" : ""}
        onClick={() => onChange("es")}
        aria-pressed={language === "es"}
      >
        ES
      </button>
    </div>
  );
}

function BrandLockup({ compact = false, theme = "light", showSubtitle = true, t }) {
  const logoSrc = theme === "dark" ? brandLogoWhite : brandLogoColor;
  return (
    <div className={`brand-lockup ${compact ? "compact" : ""} ${theme}`}>
      <img src={logoSrc} alt="Athena Desk logo" className="brand-logo" />
      <div className="brand-text-wrap">
        <div className="brand-name">Athena Desk</div>
        {showSubtitle ? <div className="brand-subtitle">{t("brand.subtitle")}</div> : null}
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

function SyncBanner({ sync, t, language }) {
  if (!sync) return null;
  return (
    <div className={`sync-banner ${sync.status || "healthy"}`}>
      <div className="sync-banner-title">{sync.status === "healthy" ? t("sync.healthy") : t("sync.issue")}</div>
      <div className="sync-banner-text">{translateSyncMessage(sync.message, t)}</div>
      {sync.last_synced_at ? <small>{t("sync.last")}: {formatDateTime(sync.last_synced_at, language)}</small> : null}
    </div>
  );
}

function AssignmentList({ title, items, t, language }) {
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
                <div className="assignment-meta">
                  {t("assignment.due")}: {item.due_date_iso ? formatDateTime(item.due_date_iso, language) : t("assignment.noDueDate")}
                </div>
              </div>
              <span className={`status-pill ${getStatusClass(item.status)}`}>{translateStatus(item.status, t)}</span>
            </div>
            <div className="assignment-card-actions">
              {typeof item.hours_until_due === "number" ? (
                <div className={`urgency-chip ${item.hours_until_due <= 24 ? "critical" : item.hours_until_due <= 48 ? "warning" : "normal"}`}>
                  {item.hours_until_due <= 24
                    ? t("assignment.urgency.actNow", { hours: formatNumber(item.hours_until_due) })
                    : item.hours_until_due <= 48
                    ? t("assignment.urgency.soon", { hours: formatNumber(item.hours_until_due) })
                    : t("assignment.urgency.upcoming", { hours: formatNumber(item.hours_until_due) })}
                </div>
              ) : null}
              {item.submitted_at ? <div className="submitted-note">{t("assignment.submittedWaiting")}</div> : null}
              {item.assignment_url ? <a className="action-link" href={item.assignment_url} target="_blank" rel="noreferrer">{t("actions.openCanvas")}</a> : null}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function RiskPill({ level, t }) {
  return <span className={`risk-pill ${getStatusClass(level)}`}>{translateStatus(level, t)}</span>;
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

function ScoreBar({ course, t }) {
  const earnedPercent = Math.max(0, Math.min(100, Number(course.earned_effective_points ?? course.earned_points ?? 0)));
  const riskTone = getStatusClass(course.risk_level);
  return (
    <div className="score-block">
      <div className="score-header-row">
        <div>
          <div className="score-block-label">{t("course.realPointsEarned")}</div>
          <div className="score-block-value">{`${formatNumber(course.earned_effective_points ?? course.earned_points ?? 0)} / ${formatNumber(course.total_points ?? 100)}`}</div>
        </div>
        <div className="score-threshold">
          {t("course.passMark")}
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
        <span className="score-pass-text">{formatNumber(course.passing_score)} {t("course.toPass")}</span>
        <span>{formatNumber(course.total_points ?? 100)}</span>
      </div>
    </div>
  );
}

function AttendanceBadge({ attendance, t }) {
  const level = attendance?.level || "not_applicable";
  return (
    <div className={`attendance-box ${getStatusClass(level)}`}>
      <div className="attendance-label">{t("course.attendance")}</div>
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

function RecoverySummary({ recoveryEvents, t }) {
  if (!recoveryEvents || recoveryEvents.length === 0) return null;
  return (
    <div className="recovery-summary">
      <div className="recovery-title">{t("course.recoveryRule")}</div>
      {recoveryEvents.map((event, index) => (
        <div className="recovery-row" key={`${event.component}-${index}`}>
          <span>{event.applied ? t("course.applied") : t("course.notApplied")}</span>
          <strong>{formatNumber(event.recovery_score)} / {formatNumber(event.recovery_points)}</strong>
        </div>
      ))}
    </div>
  );
}

function CourseCard({ course, t }) {
  const pendingReviewCount = Number(course.pending_grade_count ?? 0);

  const explanatoryText = useMemo(() => {
    const parts = [];
    parts.push(t("course.expl.realPoints", {
      earned: formatNumber(course.earned_effective_points ?? course.earned_points ?? 0),
      total: formatNumber(course.total_points ?? 100),
    }));
    parts.push(t("course.expl.published", {
      published: formatNumber(course.effective_published_points ?? course.published_points ?? 0),
    }));

    if (Number(course.lost_points ?? 0) > 0) parts.push(t("course.expl.lost", { points: formatNumber(course.lost_points) }));
    if (Number(course.pending_points ?? 0) > 0) parts.push(t("course.expl.pending", { points: formatNumber(course.pending_points) }));
    if (Number(course.open_points ?? 0) > 0) parts.push(t("course.expl.open", { points: formatNumber(course.open_points) }));
    if (Number(course.hidden_or_review_points ?? 0) > 0) parts.push(t("course.expl.review", { points: formatNumber(course.hidden_or_review_points) }));
    if (Number(course.remaining_unpublished_points ?? 0) > 0) parts.push(t("course.expl.unpublished", { points: formatNumber(course.remaining_unpublished_points) }));
    if (Number(course.remaining_to_pass ?? 0) > 0) parts.push(t("course.expl.need", {
      points: formatNumber(course.remaining_to_pass),
      passing: formatNumber(course.passing_score),
    }));
    if (course.required_percent_of_remaining !== null && course.required_percent_of_remaining !== undefined) {
      parts.push(t("course.expl.required", { percent: formatNumber(course.required_percent_of_remaining) }));
    }
    return parts.join(" ");
  }, [course, t]);

  const resultText = course.course_result === "passed"
    ? t("course.finishedPassed", {
        earned: formatNumber(course.earned_effective_points ?? course.earned_points ?? 0),
        passing: formatNumber(course.passing_score),
      })
    : course.course_result === "failed"
    ? t("course.finishedFailed", {
        earned: formatNumber(course.earned_effective_points ?? course.earned_points ?? 0),
        total: formatNumber(course.total_points ?? 100),
        passing: formatNumber(course.passing_score),
      })
    : explanatoryText;

  return (
    <div className="course-card">
      <div className="course-top">
        <div className="course-title-wrap">
          <div className="course-name">{course.course_name}</div>
          <div className="course-code">{course.course_code || t("course.current")}</div>
        </div>
        <RiskPill level={course.risk_level} t={t} />
      </div>

      <div className="course-metrics">
        <MetricTile label={t("course.earnedPoints")} value={`${formatNumber(course.earned_effective_points ?? course.earned_points)} / ${formatNumber(course.total_points)}`} helper={t("course.realConfirmedPoints")} tone="neutral" />
        {course.course_finished ? (
          <MetricTile label={t("course.finalResult")} value={translateStatus(course.course_result, t)} helper={t("course.finalFound")} tone={course.course_result === "passed" ? "success" : "danger"} />
        ) : (
          <MetricTile label={t("course.needToPass")} value={formatNumber(course.remaining_to_pass)} helper={`${t("course.passMark")}: ${formatNumber(course.passing_score)}`} tone={Number(course.remaining_to_pass ?? 0) > 0 ? "warning" : "success"} />
        )}
        <MetricTile label={t("course.lostPoints")} value={formatNumber(course.lost_points)} helper={t("course.lostPointsHelper")} tone={Number(course.lost_points ?? 0) > 0 ? "danger" : "success"} />
        <MetricTile label={t("course.available")} value={formatNumber(course.remaining_available_points)} helper={t("course.availableHelper")} tone="success" />
      </div>

      <div className="missing-strip">
        <div className="missing-strip-title">{t("course.pointAudit")}</div>
        <div className="missing-strip-values">
          <span>{t("course.published")}: {formatNumber(course.effective_published_points ?? course.published_points)}</span>
          <span>{t("course.pending")}: {formatNumber(course.pending_points)}</span>
          <span>{t("course.review")}: {formatNumber(course.hidden_or_review_points)}</span>
          <span>{t("course.unpublishedEst")}: {formatNumber(course.remaining_unpublished_points)}</span>
        </div>
      </div>

      <ScoreBar course={course} t={t} />

      <div className="course-status-row">
        <MicroStat label={t("course.graded")} value={formatNumber(course.graded_count)} />
        <MicroStat label={t("course.pending")} value={formatNumber(pendingReviewCount)} tone="warning" />
        <MicroStat label={t("course.missed")} value={formatNumber(course.missing_count)} tone="danger" />
        <AttendanceBadge attendance={course.attendance} t={t} />
      </div>

      <ComponentsSummary components={course.components} />
      <RecoverySummary recoveryEvents={course.recovery_events} t={t} />

      <div className="risk-reason">{course.course_finished ? resultText : explanatoryText}</div>
      <div className="risk-reason secondary">{explanatoryText}</div>
    </div>
  );
}

function AccessGate({ onUnlock, errorMessage, loading, language, setLanguage, t }) {
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
          <div className="gate-language-position">
            <LanguageToggle language={language} onChange={setLanguage} compact />
          </div>
          <BrandLockup theme="dark" t={t} />
          <h1>{t("gate.title")}</h1>
          <p>{t("gate.description")}</p>
          <div className="gate-brand-points">
            <div>{t("gate.point.currentTerm")}</div>
            <div>{t("gate.point.canvasSync")}</div>
            <div>{t("gate.point.protected")}</div>
          </div>
        </div>
        <div className="gate-card">
          <div className="creator-block">
            <img src={creatorPhoto} alt="Job Villagran" className="creator-avatar" />
            <div className="creator-meta">
              <span className="creator-label">{t("creator.label")}</span>
              <a href="https://www.linkedin.com/in/jobvillagran/" target="_blank" rel="noreferrer" className="creator-link">Job Villagran</a>
            </div>
          </div>
          <div className="gate-title">{t("gate.welcome")}</div>
          <div className="gate-subtitle">{t("gate.subtitle")}</div>
          <form onSubmit={submit} className="gate-form">
            <label className="gate-label" htmlFor="accessKey">{t("gate.accessKey")}</label>
            <input id="accessKey" type="password" className="gate-input" placeholder={t("gate.placeholder")} value={accessKey} onChange={(e) => setAccessKey(e.target.value)} autoComplete="off" />
            {errorMessage ? <div className="gate-error">{errorMessage}</div> : null}
            <button type="submit" className="gate-button" disabled={loading}>{loading ? t("gate.validating") : t("gate.unlock")}</button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [language, setLanguageState] = useState(getInitialLanguage);
  const t = useMemo(() => createTranslator(language), [language]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [authError, setAuthError] = useState("");
  const [isUnlocked, setIsUnlocked] = useState(false);

  const setLanguage = (nextLanguage) => {
    setLanguageState(nextLanguage);
    saveLanguage(nextLanguage);
  };

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

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
        setAuthError(t("error.savedKeyInvalid"));
      } finally {
        setLoading(false);
      }
    };
    bootstrap();
  }, [t]);

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
        setAuthError(t("error.invalidKey"));
      } else {
        setError(err.message || t("error.dashboardLoad"));
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
      setAuthError(t("error.invalidKeyRetry"));
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
    return <AccessGate onUnlock={unlock} errorMessage={authError} loading={loading} language={language} setLanguage={setLanguage} t={t} />;
  }

  if (loading && !data) return <div className="screen-state">{t("screen.loading")}</div>;

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero-main"><BrandLockup compact theme="light" showSubtitle={false} t={t} /></div>
        <div className="hero-actions">
          <LanguageToggle language={language} onChange={setLanguage} />
          <button className="refresh-btn" onClick={() => load(true)} disabled={refreshing}>{refreshing ? t("actions.refreshing") : t("actions.refresh")}</button>
          <button className="logout-btn" onClick={logout}>{t("actions.lock")}</button>
        </div>
      </header>

      <SyncBanner sync={data?.sync} t={t} language={language} />
      {error ? <div className="error-banner">{error}</div> : null}

      <section className="stats-grid">
        <StatCard label={t("stats.actionable")} value={data?.summary?.actionable ?? 0} />
        <StatCard label={t("stats.urgent")} value={data?.summary?.urgent ?? 0} tone="danger" />
        <StatCard label={t("stats.opensSoon")} value={data?.summary?.opens_soon ?? 0} tone="indigo" />
        <StatCard label={t("stats.projects")} value={data?.summary?.projects ?? 0} tone="amber" />
        <StatCard label={t("stats.submitted")} value={data?.summary?.submitted ?? 0} tone="green" />
        <StatCard label={t("stats.atRisk")} value={data?.summary?.courses_at_risk ?? 0} tone="danger" />
        <StatCard label={t("stats.watch")} value={data?.summary?.courses_watch ?? 0} tone="amber" />
        <StatCard label={t("stats.incomplete")} value={data?.summary?.courses_not_enough_data ?? 0} tone="neutral" />
      </section>

      <AssignmentList title={t("groups.actNow")} items={data?.groups?.act_now} t={t} language={language} />
      <AssignmentList title={t("groups.thisWeek")} items={data?.groups?.this_week} t={t} language={language} />
      <AssignmentList title={t("groups.nextWeek")} items={data?.groups?.next_week} t={t} language={language} />
      <AssignmentList title={t("groups.thirdWeek")} items={data?.groups?.third_week} t={t} language={language} />
      <AssignmentList title={t("groups.opensSoon")} items={data?.groups?.opens_soon} t={t} language={language} />
      <AssignmentList title={t("groups.submitted")} items={data?.groups?.submitted} t={t} language={language} />
      <AssignmentList title={t("groups.noDueDate")} items={data?.groups?.no_due_date} t={t} language={language} />

      <section className="panel panel-strong">
        <div className="panel-header">
          <h2>{t("course.progress")}</h2>
          <span className="panel-count">{data?.courses?.length ?? 0}</span>
        </div>
        <div className="course-grid">
          {data?.courses?.map((course) => <CourseCard key={course.course_id} course={course} t={t} />)}
        </div>
      </section>
    </div>
  );
}
