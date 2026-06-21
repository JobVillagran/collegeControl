import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  CheckSquare,
  CircleDashed,
  ClipboardList,
  Eye,
  FileText,
  Folder,
  GraduationCap,
  Lock,
  Moon,
  RefreshCw,
  Send,
  ShieldCheck,
  Sun,
} from "lucide-react";
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
  translateComponent,
} from "./i18n";
import creatorPhoto from "./assets/job-villagran.png";
import brandLogoColor from "./assets/athena-desk-color.png";
import brandLogoWhite from "./assets/athena-desk-white.png";

const TIME_ZONE = "America/Guatemala";

const THEME_STORAGE_KEY = "athena_desk_theme";

function normalizeTheme(value) {
  return value === "dark" ? "dark" : "light";
}

function getInitialTheme() {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored) return normalizeTheme(stored);
  } catch {
    // ignore
  }

  try {
    if (window.matchMedia?.("(prefers-color-scheme: dark)")?.matches) return "dark";
  } catch {
    // ignore
  }

  return "light";
}

function saveTheme(theme) {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, normalizeTheme(theme));
  } catch {
    // ignore
  }
}

function getLocale(language) {
  return LANGUAGES[language]?.locale || LANGUAGES.es.locale;
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

    return result
      .replace(" am", " AM")
      .replace(" pm", " PM")
      .replace("a. m.", "AM")
      .replace("p. m.", "PM")
      .replace("a. m.", "AM")
      .replace("p. m.", "PM");
  } catch {
    return value;
  }
}

function formatShortDate(value, language) {
  if (!value) return "--";

  try {
    return new Intl.DateTimeFormat(getLocale(language), {
      month: "short",
      day: "2-digit",
      timeZone: TIME_ZONE,
    }).format(new Date(value));
  } catch {
    return "--";
  }
}

function getStatusClass(value) {
  const normalized = String(value || "").toLowerCase();

  if (["submitted", "graded", "healthy", "open", "published", "passed"].includes(normalized)) {
    return "success";
  }

  if (["missing", "late", "at_risk", "critical", "failed"].includes(normalized)) {
    return "danger";
  }

  if (["submitted_pending", "watch", "not_enabled_yet", "not_enough_data", "no_due_date"].includes(normalized)) {
    return "warning";
  }

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

function ThemeToggle({ theme, onChange, compact = false, t }) {
  const isDark = theme === "dark";
  const nextTheme = isDark ? "light" : "dark";

  return (
    <button
      type="button"
      className={`theme-toggle ${compact ? "compact" : ""}`}
      onClick={() => onChange(nextTheme)}
      aria-label={isDark ? t("theme.switchToLight") : t("theme.switchToDark")}
      title={isDark ? t("theme.switchToLight") : t("theme.switchToDark")}
    >
      {isDark ? <Sun size={17} /> : <Moon size={17} />}
      <span>{isDark ? t("theme.light") : t("theme.dark")}</span>
    </button>
  );
}

function BrandLockup({ compact = false, showSubtitle = false, t }) {
  return (
    <div className={`brand-lockup ${compact ? "compact" : ""}`}>
      <img src={brandLogoColor} alt="Athena Desk logo" className="brand-logo brand-logo-light" />
      <img src={brandLogoWhite} alt="Athena Desk logo" className="brand-logo brand-logo-dark" />
      <div className="brand-text-wrap">
        <div className="brand-name">Athena Desk</div>
        {showSubtitle ? <div className="brand-subtitle">{t("brand.subtitle")}</div> : null}
      </div>
    </div>
  );
}

function SyncChip({ sync, language, t }) {
  if (!sync) return null;

  const lastSync = sync?.last_synced_at ? formatDateTime(sync.last_synced_at, language) : null;
  const healthy = sync?.status === "healthy" || !sync?.status;

  return (
    <div className={`sync-chip ${healthy ? "healthy" : "warning"}`}>
      <span className="sync-dot" />
      <div>
        <strong>{healthy ? t("ui.compactSync") : t("sync.issue")}</strong>
        {lastSync ? <small>{lastSync}</small> : null}
      </div>
    </div>
  );
}

function RefreshOverlay({ progress, t }) {
  return (
    <div className="refresh-overlay" role="status" aria-live="polite" aria-busy="true">
      <div className="refresh-loader-card">
        <div className="refresh-orbit" style={{ "--refresh-progress": `${progress}%` }}>
          <div className="refresh-orbit-inner">
            <span>{progress}%</span>
          </div>
        </div>

        <div className="refresh-loader-copy">
          <strong>{t("ui.refreshTitle")}</strong>
          <span>{t("ui.refreshSubtitle")}</span>
        </div>

        <div className="refresh-loader-bar">
          <div style={{ width: `${progress}%` }} />
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon: Icon, tone = "default" }) {
  return (
    <div className={`stat-card ${tone}`}>
      <div className="stat-icon">
        <Icon size={24} strokeWidth={1.85} />
      </div>
      <div className="stat-copy">
        <div className="stat-value">{formatNumber(value)}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );
}

function StatsOverview({ summary, t }) {
  const stats = [
    {
      label: t("stats.actionable"),
      value: summary?.actionable ?? 0,
      icon: CheckSquare,
      tone: "blue",
    },
    {
      label: t("stats.urgent"),
      value: summary?.urgent ?? 0,
      icon: AlertTriangle,
      tone: "red",
    },
    {
      label: t("stats.opensSoon"),
      value: summary?.opens_soon ?? 0,
      icon: CalendarDays,
      tone: "indigo",
    },
    {
      label: t("stats.projects"),
      value: summary?.projects ?? 0,
      icon: Folder,
      tone: "amber",
    },
    {
      label: t("stats.submitted"),
      value: summary?.submitted ?? 0,
      icon: Send,
      tone: "green",
    },
    {
      label: t("stats.atRisk"),
      value: summary?.courses_at_risk ?? 0,
      icon: AlertTriangle,
      tone: "red",
    },
    {
      label: t("stats.watch"),
      value: summary?.courses_watch ?? 0,
      icon: Eye,
      tone: "amber",
    },
    {
      label: t("stats.incomplete"),
      value: summary?.courses_not_enough_data ?? 0,
      icon: CircleDashed,
      tone: "slate",
    },
  ];

  return (
    <section className="stats-grid" aria-label="Dashboard summary">
      {stats.map((stat) => (
        <StatCard key={stat.label} {...stat} />
      ))}
    </section>
  );
}

function StatusBadge({ value, t }) {
  const statusClass = getStatusClass(value);
  return <span className={`status-badge ${statusClass}`}>{translateStatus(value, t)}</span>;
}

function ScoreProgress({ course, t }) {
  const earned = Number(course.earned_effective_points ?? course.earned_points ?? 0);
  const total = Number(course.total_points ?? 100) || 100;
  const passing = Number(course.passing_score ?? 61);
  const earnedPercent = Math.max(0, Math.min(100, (earned / total) * 100));
  const passPercent = Math.max(0, Math.min(100, (passing / total) * 100));
  const tone = course.course_result ? getStatusClass(course.course_result) : getStatusClass(course.risk_level);

  return (
    <div className="progress-compact">
      <div className="progress-compact-top">
        <strong>{formatNumber(earned)} / {formatNumber(total)}</strong>
        <span>
          {t("course.passMark")} {formatNumber(passing)} / {formatNumber(total)}
        </span>
      </div>

      <div className="progress-track">
        <div className={`progress-fill ${tone}`} style={{ width: `${earnedPercent}%` }} />
        <div className="progress-marker" style={{ left: `${passPercent}%` }} />
      </div>
    </div>
  );
}

function ComponentRows({ components, t }) {
  if (!components || components.length === 0) return null;

  return (
    <div className="component-list">
      {components.slice(0, 5).map((component) => (
        <div className="component-item" key={component.type}>
          <span>{translateComponent(component, t)}</span>
          <strong>
            {formatNumber(component.earned_points)} / {formatNumber(component.published_points)}
          </strong>
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
          <strong>
            {formatNumber(event.recovery_score)} / {formatNumber(event.recovery_points)}
          </strong>
        </div>
      ))}
    </div>
  );
}

function CourseCard({ course, language, t }) {
  const finishedStatus = course.course_finished ? course.course_result : course.risk_level;
  const attendance = course.attendance?.label || "N/A";
  const attendanceLevel = getStatusClass(course.attendance?.level || "not_applicable");

  const explanatoryText = useMemo(() => {
    const parts = [];

    parts.push(
      t("course.expl.realPoints", {
        earned: formatNumber(course.earned_effective_points ?? course.earned_points ?? 0),
        total: formatNumber(course.total_points ?? 100),
      })
    );

    parts.push(
      t("course.expl.published", {
        published: formatNumber(course.effective_published_points ?? course.published_points ?? 0),
      })
    );

    if (Number(course.lost_points ?? 0) > 0) {
      parts.push(t("course.expl.lost", { points: formatNumber(course.lost_points) }));
    }

    if (Number(course.pending_points ?? 0) > 0) {
      parts.push(t("course.expl.pending", { points: formatNumber(course.pending_points) }));
    }

    if (Number(course.open_points ?? 0) > 0) {
      parts.push(t("course.expl.open", { points: formatNumber(course.open_points) }));
    }

    if (Number(course.hidden_or_review_points ?? 0) > 0) {
      parts.push(t("course.expl.review", { points: formatNumber(course.hidden_or_review_points) }));
    }

    if (Number(course.remaining_unpublished_points ?? 0) > 0) {
      parts.push(t("course.expl.unpublished", { points: formatNumber(course.remaining_unpublished_points) }));
    }

    if (Number(course.remaining_to_pass ?? 0) > 0) {
      parts.push(
        t("course.expl.need", {
          points: formatNumber(course.remaining_to_pass),
          passing: formatNumber(course.passing_score),
        })
      );
    }

    if (course.required_percent_of_remaining !== null && course.required_percent_of_remaining !== undefined) {
      parts.push(
        t("course.expl.required", {
          percent: formatNumber(course.required_percent_of_remaining),
        })
      );
    }

    return parts.join(" ");
  }, [course, t]);

  const resultText =
    course.course_result === "passed"
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
    <article className={`course-card ${getStatusClass(finishedStatus)}`}>
      <div className="course-art">
        <GraduationCap size={31} strokeWidth={1.6} />
      </div>

      <div className="course-body">
        <div className="course-heading">
          <div>
            <h3>{course.course_name}</h3>
            <p>{course.course_code || t("course.current")}</p>
          </div>
          <StatusBadge value={finishedStatus} t={t} />
        </div>

        <div className="course-key-grid">
          <div>
            <span>{t("ui.points")}</span>
            <strong>
              {formatNumber(course.earned_effective_points ?? course.earned_points)} /{" "}
              {formatNumber(course.total_points ?? 100)}
            </strong>
          </div>

          <div>
            <span>{t("ui.mark")}</span>
            <strong>
              {formatNumber(course.passing_score)} / {formatNumber(course.total_points ?? 100)}
            </strong>
          </div>

          <div>
            <span>{t("ui.result")}</span>
            <strong>
              {course.course_finished
                ? translateStatus(course.course_result, t)
                : translateStatus(course.risk_level, t)}
            </strong>
          </div>

          <div>
            <span>{t("course.attendance")}</span>
            <strong className={`attendance-value ${attendanceLevel}`}>{attendance}</strong>
          </div>
        </div>

        <ScoreProgress course={course} t={t} />

        <div className="course-mini-grid">
          <div>
            <span>{t("course.lostPoints")}</span>
            <strong>{formatNumber(course.lost_points)}</strong>
          </div>
          <div>
            <span>{t("course.available")}</span>
            <strong>{formatNumber(course.remaining_available_points)}</strong>
          </div>
          <div>
            <span>{t("course.graded")}</span>
            <strong>{formatNumber(course.graded_count)}</strong>
          </div>
          <div>
            <span>{t("course.pending")}</span>
            <strong>{formatNumber(course.pending_grade_count ?? 0)}</strong>
          </div>
        </div>

        <ComponentRows components={course.components} t={t} />

        <RecoverySummary recoveryEvents={course.recovery_events} t={t} />

        <div className="course-audit">
          <span>
            {t("course.published")}:{" "}
            {formatNumber(course.effective_published_points ?? course.published_points)}
          </span>
          <span>{t("course.pending")}: {formatNumber(course.pending_points)}</span>
          <span>{t("course.review")}: {formatNumber(course.hidden_or_review_points)}</span>
          <span>{t("course.unpublishedEst")}: {formatNumber(course.remaining_unpublished_points)}</span>
        </div>

        <p className="course-note">{course.course_finished ? resultText : explanatoryText}</p>
      </div>
    </article>
  );
}

function CoursePanel({ courses = [], language, t }) {
  return (
    <section className="courses-panel">
      <div className="section-header">
        <div>
          <h2>{t("ui.myCourses")}</h2>
          <p>{t("course.progress")}</p>
        </div>
        <span className="panel-count">{courses.length}</span>
      </div>

      <div className="course-list">
        {courses.map((course) => (
          <CourseCard key={course.course_id} course={course} language={language} t={t} />
        ))}
      </div>
    </section>
  );
}

function AssignmentMiniList({ title, items, t, language }) {
  if (!items || items.length === 0) return null;

  return (
    <section className="side-panel">
      <div className="side-panel-header">
        <div>
          <h2>{title}</h2>
          <p>{items.length}</p>
        </div>
        <ClipboardList size={20} />
      </div>

      <div className="upcoming-list">
        {items.slice(0, 6).map((item, index) => (
          <a
            className="upcoming-item"
            key={`${item.assignment_id || item.assignment_name}-${index}`}
            href={item.assignment_url || "#"}
            target={item.assignment_url ? "_blank" : undefined}
            rel={item.assignment_url ? "noreferrer" : undefined}
          >
            <div className="upcoming-date">
              <span>{formatShortDate(item.due_date_iso, language)}</span>
            </div>

            <div className="upcoming-copy">
              <strong>{item.assignment_name}</strong>
              <span>{item.course_name}</span>
              <small>
                {item.due_date_iso
                  ? formatDateTime(item.due_date_iso, language)
                  : t("assignment.noDueDate")}
              </small>
            </div>

            <StatusBadge value={item.status} t={t} />
          </a>
        ))}
      </div>
    </section>
  );
}

function AssignmentsColumn({ groups, t, language }) {
  const hasAssignments =
    (groups?.act_now?.length || 0) +
      (groups?.this_week?.length || 0) +
      (groups?.next_week?.length || 0) +
      (groups?.opens_soon?.length || 0) +
      (groups?.submitted?.length || 0) >
    0;

  return (
    <aside className="right-column">
      <AssignmentMiniList title={t("groups.actNow")} items={groups?.act_now} t={t} language={language} />
      <AssignmentMiniList title={t("groups.thisWeek")} items={groups?.this_week} t={t} language={language} />
      <AssignmentMiniList title={t("groups.nextWeek")} items={groups?.next_week} t={t} language={language} />
      <AssignmentMiniList title={t("groups.opensSoon")} items={groups?.opens_soon} t={t} language={language} />
      <AssignmentMiniList title={t("groups.submitted")} items={groups?.submitted} t={t} language={language} />

      {!hasAssignments ? (
        <section className="side-panel">
          <div className="empty-state">
            <CheckCircle2 size={24} />
            <strong>{t("ui.stableTitle")}</strong>
            <span>{t("ui.stableText")}</span>
          </div>
        </section>
      ) : null}
    </aside>
  );
}

function RemindersStrip({ summary, courses, language, t }) {
  const atRisk = Number(summary?.courses_at_risk ?? 0);
  const pending = Number(courses?.reduce((total, course) => total + Number(course.pending_grade_count ?? 0), 0) ?? 0);

  if (atRisk === 0 && pending === 0) {
    return (
      <section className="reminders-strip success">
        <ShieldCheck size={21} />
        <div>
          <strong>{t("ui.stableTitle")}</strong>
          <span>{t("ui.stableText")}</span>
        </div>
      </section>
    );
  }

  const title = language === "es" ? "Atención académica" : "Academic attention";

  let description = "";
  if (pending > 0 && atRisk > 0) {
    description =
      language === "es"
        ? `${pending} nota(s) pendiente(s) y ${atRisk} curso(s) en riesgo`
        : `${pending} pending grade(s) and ${atRisk} course(s) at risk`;
  } else if (pending > 0) {
    description =
      language === "es"
        ? `${pending} nota(s) pendiente(s) por confirmar`
        : `${pending} pending grade(s) to confirm`;
  } else {
    description =
      language === "es"
        ? `${atRisk} curso(s) en riesgo`
        : `${atRisk} course(s) at risk`;
  }

  return (
    <section className="reminders-strip alert">
      <div className="reminder-summary-icon">
        {atRisk > 0 ? <AlertTriangle size={20} /> : <FileText size={20} />}
      </div>

      <div className="reminder-summary-copy">
        <strong>{title}</strong>
        <span>{description}</span>
      </div>
    </section>
  );
}

function AccessGate({ onUnlock, errorMessage, loading, language, setLanguage, theme, setTheme, t }) {
  const [accessKey, setAccessKey] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    if (!accessKey.trim() || loading) return;
    await onUnlock(accessKey.trim());
  };

  return (
    <div className="gate-shell">
      <div className="gate-card-wrap">
        <section className="gate-brand-panel">
          <div className="gate-top">
            <BrandLockup compact showSubtitle={false} t={t} />
            <LanguageToggle language={language} onChange={setLanguage} compact />
            <ThemeToggle theme={theme} onChange={setTheme} compact t={t} />
          </div>

          <div className="gate-copy">
            <h1>{t("gate.title")}</h1>
            <p>{t("gate.description")}</p>

            <div className="gate-brand-points">
              <div>
                <CheckSquare size={18} />
                {t("gate.point.currentTerm")}
              </div>
              <div>
                <RefreshCw size={18} />
                {t("gate.point.canvasSync")}
              </div>
              <div>
                <Lock size={18} />
                {t("gate.point.protected")}
              </div>
            </div>
          </div>
        </section>

        <section className="gate-form-card">
          <div className="creator-block">
            <img src={creatorPhoto} alt="Job Villagran" className="creator-avatar" />
            <div className="creator-meta">
              <span className="creator-label">{t("ui.creatorLabel")}</span>
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

          <div className="gate-title">{t("gate.welcome")}</div>
          <div className="gate-subtitle">{t("gate.subtitle")}</div>

          <form onSubmit={submit} className="gate-form">
            <label className="gate-label" htmlFor="accessKey">
              {t("gate.accessKey")}
            </label>
            <input
              id="accessKey"
              type="password"
              className="gate-input"
              placeholder={t("gate.placeholder")}
              value={accessKey}
              onChange={(event) => setAccessKey(event.target.value)}
              autoComplete="off"
            />

            {errorMessage ? <div className="gate-error">{errorMessage}</div> : null}

            <button type="submit" className="gate-button" disabled={loading}>
              {loading ? t("gate.validating") : t("gate.unlock")}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}

export default function App() {
  const [language, setLanguageState] = useState(getInitialLanguage);
  const [theme, setThemeState] = useState(getInitialTheme);
  const t = useMemo(() => createTranslator(language), [language]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshProgress, setRefreshProgress] = useState(0);
  const [error, setError] = useState("");
  const [authError, setAuthError] = useState("");
  const [isUnlocked, setIsUnlocked] = useState(false);

  const setLanguage = (nextLanguage) => {
    setLanguageState(nextLanguage);
    saveLanguage(nextLanguage);
  };

  const setTheme = (nextTheme) => {
    const normalizedTheme = normalizeTheme(nextTheme);
    setThemeState(normalizedTheme);
    saveTheme(normalizedTheme);
  };

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

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

  useEffect(() => {
    if (!refreshing) return;

    setRefreshProgress(8);

    const interval = window.setInterval(() => {
      setRefreshProgress((current) => {
        if (current >= 92) return current;
        const distance = 92 - current;
        const step = Math.max(1, Math.round(distance * 0.12));
        return Math.min(92, current + step);
      });
    }, 220);

    return () => window.clearInterval(interval);
  }, [refreshing]);

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

      if (force) {
        setRefreshProgress(100);

        window.setTimeout(() => {
          setRefreshing(false);
          setRefreshProgress(0);
        }, 450);
      } else {
        setRefreshing(false);
      }
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
    return (
      <AccessGate
        onUnlock={unlock}
        errorMessage={authError}
        loading={loading}
        language={language}
        setLanguage={setLanguage}
        theme={theme}
        setTheme={setTheme}
        t={t}
      />
    );
  }

  if (loading && !data) {
    return <div className="screen-state">{t("screen.loading")}</div>;
  }

  return (
    <>
    {refreshing ? <RefreshOverlay progress={refreshProgress} t={t} /> : null}

    <div className="dashboard-page">
      <main className="dashboard-main">
        <header className="topbar">
          <div className="topbar-brand">
            <BrandLockup compact showSubtitle={false} t={t} />
          </div>

          <div className="topbar-actions">
            <SyncChip sync={data?.sync} language={language} t={t} />
            <LanguageToggle language={language} onChange={setLanguage} />
            <ThemeToggle theme={theme} onChange={setTheme} t={t} />

            <button className="toolbar-button primary" onClick={() => load(true)} disabled={refreshing}>
              <RefreshCw size={18} />
              <span>{refreshing ? t("actions.refreshing") : t("actions.refresh")}</span>
            </button>

            <button className="toolbar-button" onClick={logout}>
              <Lock size={17} />
              <span>{t("actions.lock")}</span>
            </button>
          </div>
        </header>

        <section className="page-intro">
          <div>
            <h1>{t("ui.overviewTitle")}</h1>
            <p>{t("ui.overviewSubtitle")}</p>
          </div>

          <RemindersStrip summary={data?.summary} courses={data?.courses || []} language={language} t={t} />
        </section>

        {error ? <div className="error-banner">{error}</div> : null}

        <StatsOverview summary={data?.summary} t={t} />

        <div className="dashboard-content">
          <CoursePanel courses={data?.courses || []} language={language} t={t} />
          <AssignmentsColumn groups={data?.groups} language={language} t={t} />
        </div>
      </main>
    </div>
  </>
);
}
