import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  CheckSquare,
  ChevronDown,
  ChevronUp,
  CircleDashed,
  ClipboardList,
  Eye,
  FileText,
  Folder,
  GraduationCap,
  Lock,
  MessageCircle,
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
  translateComponent,
  translateStatus,
} from "./i18n";

import creatorPhoto from "./assets/job-villagran.png";
import brandLogoColor from "./assets/athena-desk-color.png";
import brandLogoWhite from "./assets/athena-desk-white.png";

const TIME_ZONE = "America/Guatemala";
const THEME_STORAGE_KEY = "athena_desk_theme";

const REFRESH_DURATION_STORAGE_KEY =
  "athena_desk_refresh_duration_ms";

const AUTH_DURATION_STORAGE_KEY =
  "athena_desk_auth_duration_ms";

const DEFAULT_REFRESH_DURATION_MS = 22000;
const DEFAULT_AUTH_DURATION_MS = 30000;
const MIN_REFRESH_DURATION_MS = 12000;
const MAX_REFRESH_DURATION_MS = 45000;

function normalizeTheme(value) {
  return value === "dark" ? "dark" : "light";
}

function getInitialTheme() {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);

    if (stored) {
      return normalizeTheme(stored);
    }
  } catch {
    // Ignore storage errors.
  }

  try {
    if (
      window.matchMedia?.(
        "(prefers-color-scheme: dark)"
      )?.matches
    ) {
      return "dark";
    }
  } catch {
    // Ignore browser preference errors.
  }

  return "light";
}

function saveTheme(theme) {
  try {
    localStorage.setItem(
      THEME_STORAGE_KEY,
      normalizeTheme(theme)
    );
  } catch {
    // Ignore storage errors.
  }
}

function clampRefreshDuration(value) {
  const numeric = Number(value);

  if (!Number.isFinite(numeric)) {
    return DEFAULT_REFRESH_DURATION_MS;
  }

  return Math.min(
    MAX_REFRESH_DURATION_MS,
    Math.max(
      MIN_REFRESH_DURATION_MS,
      numeric
    )
  );
}

function getExpectedDuration(
  storageKey,
  fallbackDurationMs
) {
  try {
    const stored = localStorage.getItem(
      storageKey
    );

    if (!stored) {
      return clampRefreshDuration(
        fallbackDurationMs
      );
    }

    return clampRefreshDuration(stored);
  } catch {
    return clampRefreshDuration(
      fallbackDurationMs
    );
  }
}

function saveObservedDuration(
  storageKey,
  durationMs,
  fallbackDurationMs
) {
  const observed =
    clampRefreshDuration(durationMs);

  try {
    const previous =
      getExpectedDuration(
        storageKey,
        fallbackDurationMs
      );

    const smoothed =
      previous * 0.7 +
      observed * 0.3;

    localStorage.setItem(
      storageKey,
      String(
        Math.round(
          clampRefreshDuration(smoothed)
        )
      )
    );
  } catch {
    // Ignore storage errors.
  }
}

function getExpectedRefreshDuration() {
  return getExpectedDuration(
    REFRESH_DURATION_STORAGE_KEY,
    DEFAULT_REFRESH_DURATION_MS
  );
}

function saveObservedRefreshDuration(durationMs) {
  saveObservedDuration(
    REFRESH_DURATION_STORAGE_KEY,
    durationMs,
    DEFAULT_REFRESH_DURATION_MS
  );
}

function getExpectedAuthDuration() {
  return getExpectedDuration(
    AUTH_DURATION_STORAGE_KEY,
    DEFAULT_AUTH_DURATION_MS
  );
}

function saveObservedAuthDuration(durationMs) {
  saveObservedDuration(
    AUTH_DURATION_STORAGE_KEY,
    durationMs,
    DEFAULT_AUTH_DURATION_MS
  );
}

function calculateRefreshProgress(
  elapsedMs,
  expectedDurationMs
) {
  const elapsed = Math.max(
    0,
    Number(elapsedMs) || 0
  );

  const expected =
    clampRefreshDuration(
      expectedDurationMs
    );

  const ratio = Math.min(
    1,
    elapsed / expected
  );

  if (ratio < 1) {
    const eased =
      1 -
      Math.pow(
        1 - ratio,
        1.35
      );

    return Math.min(
      96,
      Math.max(
        2,
        Math.round(
          2 + eased * 94
        )
      )
    );
  }

  const overtime =
    elapsed - expected;

  const slowCreep =
    96 +
    3 *
      (
        1 -
        Math.exp(
          -overtime / 12000
        )
      );

  return Math.min(
    99,
    Math.max(
      96,
      Math.floor(slowCreep)
    )
  );
}

function scrollToTop() {
  if (typeof window === "undefined") {
    return;
  }

  window.requestAnimationFrame(() => {
    window.scrollTo({
      top: 0,
      left: 0,
      behavior: "auto",
    });
  });
}

function getLocale(language) {
  return (
    LANGUAGES[language]?.locale ||
    LANGUAGES.es.locale
  );
}

function formatNumber(value) {
  const numeric = Number(value ?? 0);

  if (Number.isNaN(numeric)) {
    return "0";
  }

  if (Number.isInteger(numeric)) {
    return String(numeric);
  }

  return numeric
    .toFixed(2)
    .replace(/\.00$/, "")
    .replace(/(\.\d)0$/, "$1");
}

function formatDateTime(value, language) {
  if (!value) {
    return null;
  }

  try {
    const result = new Intl.DateTimeFormat(
      getLocale(language),
      {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
        timeZone: TIME_ZONE,
      }
    ).format(new Date(value));

    return result
      .replace(" am", " AM")
      .replace(" pm", " PM")
      .replace("a. m.", "AM")
      .replace("p. m.", "PM");
  } catch {
    return value;
  }
}

function formatShortDate(value, language) {
  if (!value) {
    return "--";
  }

  try {
    return new Intl.DateTimeFormat(
      getLocale(language),
      {
        month: "short",
        day: "2-digit",
        timeZone: TIME_ZONE,
      }
    ).format(new Date(value));
  } catch {
    return "--";
  }
}

function normalizeMeridiem(value) {
  return String(value)
    .replace(" am", " AM")
    .replace(" pm", " PM")
    .replace("a. m.", "AM")
    .replace("p. m.", "PM");
}

function getCalendarDateParts(
  value
) {
  const date =
    value instanceof Date
      ? value
      : new Date(value);

  if (Number.isNaN(date.getTime())) {
    return null;
  }

  const parts =
    new Intl.DateTimeFormat(
      "en-CA",
      {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        timeZone: TIME_ZONE,
      }
    ).formatToParts(date);

  const values = {};

  parts.forEach((part) => {
    if (
      part.type !== "literal"
    ) {
      values[part.type] =
        Number(part.value);
    }
  });

  return {
    year: values.year,
    month: values.month,
    day: values.day,
  };
}

function getCalendarDayNumber(
  parts
) {
  if (!parts) {
    return null;
  }

  return Math.floor(
    Date.UTC(
      parts.year,
      parts.month - 1,
      parts.day
    ) /
      86400000
  );
}

function formatSyncDateTime(
  value,
  language
) {
  if (!value) {
    return null;
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  const targetDateParts =
    getCalendarDateParts(date);

  const currentDateParts =
    getCalendarDateParts(
      new Date()
    );

  const targetDayNumber =
    getCalendarDayNumber(
      targetDateParts
    );

  const currentDayNumber =
    getCalendarDayNumber(
      currentDateParts
    );

  const differenceInDays =
    currentDayNumber -
    targetDayNumber;

  const formattedTime =
    normalizeMeridiem(
      new Intl.DateTimeFormat(
        getLocale(language),
        {
          hour: "numeric",
          minute: "2-digit",
          hour12: true,
          timeZone: TIME_ZONE,
        }
      ).format(date)
    );

  if (differenceInDays === 0) {
    const todayLabel =
      language === "es"
        ? "Hoy"
        : "Today";

    return `${todayLabel} ${formattedTime}`;
  }

  if (differenceInDays === 1) {
    const yesterdayLabel =
      language === "es"
        ? "Ayer"
        : "Yesterday";

    return `${yesterdayLabel} ${formattedTime}`;
  }

  const includeYear =
    targetDateParts?.year !==
    currentDateParts?.year;

  const formattedDate =
    new Intl.DateTimeFormat(
      getLocale(language),
      {
        month: "short",
        day: "numeric",
        ...(includeYear
          ? { year: "numeric" }
          : {}),
        timeZone: TIME_ZONE,
      }
    ).format(date);

  return `${formattedDate}, ${formattedTime}`;
}

function getStatusClass(value) {
  const normalized = String(
    value || ""
  ).toLowerCase();

  if (
    [
      "submitted",
      "graded",
      "healthy",
      "open",
      "published",
      "passed",
    ].includes(normalized)
  ) {
    return "success";
  }

  if (
    [
      "missing",
      "late",
      "at_risk",
      "critical",
      "failed",
    ].includes(normalized)
  ) {
    return "danger";
  }

  if (
    [
      "submitted_pending",
      "watch",
      "not_enabled_yet",
      "not_enough_data",
      "no_due_date",
      "needs_reply",
      "unread",
    ].includes(normalized)
  ) {
    return "warning";
  }

  return "neutral";
}

function LanguageToggle({
  language,
  onChange,
  compact = false,
}) {
  return (
    <div
      className={`language-toggle ${
        compact ? "compact" : ""
      }`}
      role="group"
      aria-label="Language selector"
    >
      <button
        type="button"
        className={
          language === "en" ? "active" : ""
        }
        onClick={() => onChange("en")}
        aria-pressed={language === "en"}
      >
        EN
      </button>

      <button
        type="button"
        className={
          language === "es" ? "active" : ""
        }
        onClick={() => onChange("es")}
        aria-pressed={language === "es"}
      >
        ES
      </button>
    </div>
  );
}

function ThemeToggle({
  theme,
  onChange,
  compact = false,
  t,
}) {
  const isDark = theme === "dark";
  const nextTheme = isDark
    ? "light"
    : "dark";

  const accessibleLabel = isDark
    ? t("theme.switchToLight")
    : t("theme.switchToDark");

  return (
    <button
      type="button"
      className={`theme-toggle ${
        compact ? "compact" : ""
      }`}
      onClick={() => onChange(nextTheme)}
      aria-label={accessibleLabel}
      title={accessibleLabel}
    >
      {isDark ? (
        <Sun size={17} />
      ) : (
        <Moon size={17} />
      )}

      <span>
        {isDark
          ? t("theme.light")
          : t("theme.dark")}
      </span>
    </button>
  );
}

function BrandLockup({
  compact = false,
  showSubtitle = false,
  t,
}) {
  return (
    <div
      className={`brand-lockup ${
        compact ? "compact" : ""
      }`}
    >
      <img
        src={brandLogoColor}
        alt="Athena Desk logo"
        className="brand-logo brand-logo-light"
      />

      <img
        src={brandLogoWhite}
        alt="Athena Desk logo"
        className="brand-logo brand-logo-dark"
      />

      <div className="brand-text-wrap">
        <div className="brand-name">
          Athena Desk
        </div>

        {showSubtitle ? (
          <div className="brand-subtitle">
            {t("brand.subtitle")}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function SyncChip({
  sync,
  language,
  t,
}) {
  if (!sync) {
    return null;
  }

  const lastSync = sync?.last_synced_at
    ? formatSyncDateTime(
        sync.last_synced_at,
        language
      )
    : null;

  const healthy =
    sync?.status === "healthy" ||
    !sync?.status;

  const guatemalaTimeLabel =
    language === "es"
      ? "Hora Guatemala"
      : "Guatemala Time";

  return (
    <div
      className={`sync-chip ${
        healthy ? "healthy" : "warning"
      }`}
    >
      <span className="sync-dot" />

      <div>
        <strong>
          {healthy
            ? t("ui.compactSync")
            : t("sync.issue")}
        </strong>

        <small>
          {lastSync
            ? `${lastSync} · ${guatemalaTimeLabel}`
            : guatemalaTimeLabel}
        </small>
      </div>
    </div>
  );
}

function LoadingOverlay({
  title,
  subtitle,
  compact = false,
}) {
  return (
    <div
      className={`refresh-overlay ${
        compact ? "compact-loader" : ""
      }`}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div
        className={`refresh-loader-card ${
          compact
            ? "compact-loader-card"
            : ""
        }`}
      >
        <div className="loading-spinner-shell">
          <div className="loading-spinner-ring" />

          <div className="loading-spinner-core">
            <RefreshCw
              size={compact ? 22 : 28}
            />
          </div>
        </div>

        <div className="refresh-loader-copy">
          <strong>{title}</strong>
          <span>{subtitle}</span>
        </div>
      </div>
    </div>
  );
}

function RefreshOverlay({
  progress,
  t,
  title,
  subtitle,
}) {
  const normalizedProgress = Math.max(
    0,
    Math.min(
      100,
      Math.round(
        Number(progress) || 0
      )
    )
  );

  const resolvedTitle =
    title ?? t("ui.refreshTitle");

  const resolvedSubtitle =
    subtitle ?? t("ui.refreshSubtitle");

  return (
    <div
      className="refresh-overlay"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="refresh-loader-card">
        <div
          className="refresh-orbit"
          style={{
            "--refresh-progress": `${normalizedProgress}%`,
          }}
        >
          <div className="refresh-orbit-inner">
            <span>
              {normalizedProgress}%
            </span>
          </div>
        </div>

        <div className="refresh-loader-copy">
          <strong>
            {resolvedTitle}
          </strong>

          <span>
            {resolvedSubtitle}
          </span>
        </div>

        <div className="refresh-loader-bar">
          <div
            style={{
              width: `${normalizedProgress}%`,
            }}
          />
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  tone = "default",
}) {
  return (
    <div className={`stat-card ${tone}`}>
      <div className="stat-icon">
        <Icon
          size={24}
          strokeWidth={1.85}
        />
      </div>

      <div className="stat-copy">
        <div className="stat-value">
          {formatNumber(value)}
        </div>

        <div className="stat-label">
          {label}
        </div>
      </div>
    </div>
  );
}

function StatsOverview({
  summary,
  t,
}) {
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
      label: t("stats.discussions"),
      value:
        summary?.discussions_actionable ??
        summary?.discussions_needs_action ??
        0,
      icon: MessageCircle,
      tone: "forum",
    },
    {
      label: t("stats.submitted"),
      value: summary?.submitted ?? 0,
      icon: Send,
      tone: "green",
    },
    {
      label: t("stats.atRisk"),
      value:
        summary?.courses_at_risk ?? 0,
      icon: AlertTriangle,
      tone: "red",
    },
    {
      label: t("stats.watch"),
      value:
        summary?.courses_watch ?? 0,
      icon: Eye,
      tone: "amber",
    },
    {
      label: t("stats.incomplete"),
      value:
        summary?.courses_not_enough_data ??
        0,
      icon: CircleDashed,
      tone: "slate",
    },
  ];

  return (
    <section
      className="stats-grid"
      aria-label="Dashboard summary"
    >
      {stats.map((stat) => (
        <StatCard
          key={stat.label}
          {...stat}
        />
      ))}
    </section>
  );
}

function StatusBadge({
  value,
  t,
}) {
  const statusClass =
    getStatusClass(value);

  return (
    <span
      className={`status-badge ${statusClass}`}
    >
      {translateStatus(value, t)}
    </span>
  );
}

function ScoreProgress({
  course,
  t,
}) {
  const earned = Number(
    course.earned_effective_points ??
      course.earned_points ??
      0
  );

  const total =
    Number(course.total_points ?? 100) ||
    100;

  const passing = Number(
    course.passing_score ?? 61
  );

  const earnedPercent = Math.max(
    0,
    Math.min(
      100,
      (earned / total) * 100
    )
  );

  const passPercent = Math.max(
    0,
    Math.min(
      100,
      (passing / total) * 100
    )
  );

  const tone = course.course_result
    ? getStatusClass(
        course.course_result
      )
    : getStatusClass(course.risk_level);

  return (
    <div className="progress-compact">
      <div className="progress-compact-top">
        <strong>
          {formatNumber(earned)} /{" "}
          {formatNumber(total)}
        </strong>

        <span>
          {t("course.passMark")}{" "}
          {formatNumber(passing)} /{" "}
          {formatNumber(total)}
        </span>
      </div>

      <div className="progress-track">
        <div
          className={`progress-fill ${tone}`}
          style={{
            width: `${earnedPercent}%`,
          }}
        />

        <div
          className="progress-marker"
          style={{
            left: `${passPercent}%`,
          }}
        />
      </div>
    </div>
  );
}

function ComponentRows({
  components,
  t,
}) {
  if (
    !components ||
    components.length === 0
  ) {
    return null;
  }

  return (
    <div className="component-list">
      {components
        .slice(0, 5)
        .map((component, index) => (
          <div
            className="component-item"
            key={`${
              component.type || "component"
            }-${index}`}
          >
            <span>
              {translateComponent(
                component,
                t
              )}
            </span>

            <strong>
              {formatNumber(
                component.earned_points
              )}{" "}
              /{" "}
              {formatNumber(
                component.published_points
              )}
            </strong>
          </div>
        ))}
    </div>
  );
}

function RecoverySummary({
  recoveryEvents,
  t,
}) {
  if (
    !recoveryEvents ||
    recoveryEvents.length === 0
  ) {
    return null;
  }

  return (
    <div className="recovery-summary">
      <div className="recovery-title">
        {t("course.recoveryRule")}
      </div>

      {recoveryEvents.map(
        (event, index) => (
          <div
            className="recovery-row"
            key={`${
              event.component ||
              "recovery"
            }-${index}`}
          >
            <span>
              {event.applied
                ? t("course.applied")
                : t(
                    "course.notApplied"
                  )}
            </span>

            <strong>
              {formatNumber(
                event.recovery_score
              )}{" "}
              /{" "}
              {formatNumber(
                event.recovery_points
              )}
            </strong>
          </div>
        )
      )}
    </div>
  );
}

function CourseCard({
  course,
  expanded,
  onToggle,
  t,
}) {
  const finishedStatus =
    course.course_finished
      ? course.course_result
      : course.risk_level;

  const statusClass =
    getStatusClass(finishedStatus);

  const earned = Number(
    course.earned_effective_points ??
      course.earned_points ??
      0
  );

  const total =
    Number(course.total_points ?? 100) ||
    100;

  const passing =
    Number(course.passing_score ?? 61) ||
    61;

  const available = Number(
    course.remaining_available_points ?? 0
  );

  const calculatedRemaining = Math.max(
    0,
    passing - earned
  );

  const remainingToPass = Number(
    course.remaining_to_pass ??
      calculatedRemaining
  );

  const attendance =
    course.attendance?.label || "N/A";

  const attendanceLevel =
    getStatusClass(
      course.attendance?.level ||
        "not_applicable"
    );

  const courseKey = String(
    course.course_id ||
      course.course_code ||
      course.course_name
  );

  const detailsId = `course-details-${courseKey.replace(
    /[^a-zA-Z0-9_-]/g,
    "-"
  )}`;

  const explanatoryText =
    useMemo(() => {
      const parts = [];

      parts.push(
        t("course.expl.realPoints", {
          earned: formatNumber(
            course.earned_effective_points ??
              course.earned_points ??
              0
          ),
          total: formatNumber(
            course.total_points ?? 100
          ),
        })
      );

      parts.push(
        t("course.expl.published", {
          published: formatNumber(
            course.effective_published_points ??
              course.published_points ??
              0
          ),
        })
      );

      if (
        Number(
          course.lost_points ?? 0
        ) > 0
      ) {
        parts.push(
          t("course.expl.lost", {
            points: formatNumber(
              course.lost_points
            ),
          })
        );
      }

      if (
        Number(
          course.pending_points ?? 0
        ) > 0
      ) {
        parts.push(
          t("course.expl.pending", {
            points: formatNumber(
              course.pending_points
            ),
          })
        );
      }

      if (
        Number(
          course.open_points ?? 0
        ) > 0
      ) {
        parts.push(
          t("course.expl.open", {
            points: formatNumber(
              course.open_points
            ),
          })
        );
      }

      if (
        Number(
          course.hidden_or_review_points ??
            0
        ) > 0
      ) {
        parts.push(
          t("course.expl.review", {
            points: formatNumber(
              course.hidden_or_review_points
            ),
          })
        );
      }

      if (
        Number(
          course.remaining_unpublished_points ??
            0
        ) > 0
      ) {
        parts.push(
          t("course.expl.unpublished", {
            points: formatNumber(
              course.remaining_unpublished_points
            ),
          })
        );
      }

      if (
        Number(
          course.remaining_to_pass ?? 0
        ) > 0
      ) {
        parts.push(
          t("course.expl.need", {
            points: formatNumber(
              course.remaining_to_pass
            ),
            passing: formatNumber(
              course.passing_score
            ),
          })
        );
      }

      if (
        course.required_percent_of_remaining !==
          null &&
        course.required_percent_of_remaining !==
          undefined
      ) {
        parts.push(
          t("course.expl.required", {
            percent: formatNumber(
              course.required_percent_of_remaining
            ),
          })
        );
      }

      return parts.join(" ");
    }, [course, t]);

  const resultText =
    course.course_result === "passed"
      ? t("course.finishedPassed", {
          earned:
            formatNumber(earned),
          passing:
            formatNumber(passing),
        })
      : course.course_result ===
          "failed"
        ? t("course.finishedFailed", {
            earned:
              formatNumber(earned),
            total:
              formatNumber(total),
            passing:
              formatNumber(passing),
          })
        : explanatoryText;

  const secondaryFactLabel =
    course.course_finished
      ? t("ui.result")
      : t("course.needToPass");

  const secondaryFactValue =
    course.course_finished
      ? translateStatus(
          course.course_result,
          t
        )
      : formatNumber(
          remainingToPass
        );

  return (
    <article
      className={[
        "course-tile",
        statusClass,
        expanded ? "expanded" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="course-tile-summary">
        <div className="course-tile-header">
          <div className="course-tile-identity">
            <div
              className={`course-tile-icon ${statusClass}`}
              aria-hidden="true"
            >
              <GraduationCap
                size={23}
                strokeWidth={1.75}
              />
            </div>

            <div className="course-tile-title">
              <h3
                title={
                  course.course_name
                }
              >
                {course.course_name}
              </h3>

              <p
                title={
                  course.course_code ||
                  t("course.current")
                }
              >
                {course.course_code ||
                  t("course.current")}
              </p>
            </div>
          </div>

          <StatusBadge
            value={finishedStatus}
            t={t}
          />
        </div>

        <ScoreProgress
          course={course}
          t={t}
        />

        <div className="course-tile-footer">
          <div className="course-quick-facts">
            <div
              className="course-quick-fact"
              title={t(
                "course.availableHelper"
              )}
            >
              <span>
                {t("course.available")}
              </span>

              <strong>
                {formatNumber(
                  available
                )}
              </strong>
            </div>

            <div className="course-quick-fact">
              <span>
                {secondaryFactLabel}
              </span>

              <strong>
                {secondaryFactValue}
              </strong>
            </div>
          </div>

          <button
            type="button"
            className={`course-tile-toggle ${
              expanded ? "open" : ""
            }`}
            onClick={onToggle}
            aria-expanded={expanded}
            aria-controls={detailsId}
            aria-label={`${
              expanded
                ? t(
                    "course.hideDetails"
                  )
                : t(
                    "course.viewDetails"
                  )
            }: ${course.course_name}`}
          >
            <span>
              {expanded
                ? t(
                    "course.hideDetails"
                  )
                : t(
                    "course.viewDetails"
                  )}
            </span>

            {expanded ? (
              <ChevronUp size={16} />
            ) : (
              <ChevronDown size={16} />
            )}
          </button>
        </div>
      </div>

      <div
        id={detailsId}
        className={`course-tile-details ${
          expanded ? "open" : ""
        }`}
        aria-hidden={!expanded}
      >
        <div className="course-detail-grid">
          <div>
            <span>
              {t("ui.points")}
            </span>

            <strong>
              {formatNumber(earned)} /{" "}
              {formatNumber(total)}
            </strong>
          </div>

          <div>
            <span>
              {t("ui.mark")}
            </span>

            <strong>
              {formatNumber(passing)} /{" "}
              {formatNumber(total)}
            </strong>
          </div>

          <div>
            <span>
              {t("ui.result")}
            </span>

            <strong>
              {course.course_finished
                ? translateStatus(
                    course.course_result,
                    t
                  )
                : translateStatus(
                    course.risk_level,
                    t
                  )}
            </strong>
          </div>

          <div>
            <span>
              {t(
                "course.attendance"
              )}
            </span>

            <strong
              className={`attendance-value ${attendanceLevel}`}
            >
              {attendance}
            </strong>
          </div>
        </div>

        <div className="course-detail-grid secondary">
          <div>
            <span>
              {t(
                "course.lostPoints"
              )}
            </span>

            <strong>
              {formatNumber(
                course.lost_points
              )}
            </strong>
          </div>

          <div>
            <span>
              {t("course.available")}
            </span>

            <strong>
              {formatNumber(
                course.remaining_available_points
              )}
            </strong>
          </div>

          <div>
            <span>
              {t("course.graded")}
            </span>

            <strong>
              {formatNumber(
                course.graded_count
              )}
            </strong>
          </div>

          <div>
            <span>
              {t("course.pending")}
            </span>

            <strong>
              {formatNumber(
                course.pending_grade_count ??
                  0
              )}
            </strong>
          </div>
        </div>

        <div className="course-detail-content">
          <ComponentRows
            components={
              course.components
            }
            t={t}
          />

          <RecoverySummary
            recoveryEvents={
              course.recovery_events
            }
            t={t}
          />
        </div>

        <div className="course-audit">
          <span>
            {t("course.published")}:{" "}
            {formatNumber(
              course.effective_published_points ??
                course.published_points
            )}
          </span>

          <span>
            {t("course.pending")}:{" "}
            {formatNumber(
              course.pending_points
            )}
          </span>

          <span>
            {t("course.review")}:{" "}
            {formatNumber(
              course.hidden_or_review_points
            )}
          </span>

          <span>
            {t(
              "course.unpublishedEst"
            )}
            :{" "}
            {formatNumber(
              course.remaining_unpublished_points
            )}
          </span>
        </div>

        <p className="course-note">
          {course.course_finished
            ? resultText
            : explanatoryText}
        </p>
      </div>
    </article>
  );
}

function CoursePanel({
  courses = [],
  t,
}) {
  const [
    expandedCourseId,
    setExpandedCourseId,
  ] = useState(null);

  const toggleCourse = (courseId) => {
    setExpandedCourseId(
      (current) =>
        current === courseId
          ? null
          : courseId
    );
  };

  return (
    <section className="courses-panel">
      <div className="section-header">
        <div>
          <h2>
            {t("ui.myCourses")}
          </h2>

          <p>
            {t("course.progress")}
          </p>
        </div>

        <span className="panel-count">
          {courses.length}
        </span>
      </div>

      <div className="course-tile-grid">
        {courses.map((course) => {
          const courseId = String(
            course.course_id ||
              course.course_code ||
              course.course_name
          );

          return (
            <CourseCard
              key={courseId}
              course={course}
              expanded={
                expandedCourseId ===
                courseId
              }
              onToggle={() =>
                toggleCourse(courseId)
              }
              t={t}
            />
          );
        })}
      </div>
    </section>
  );
}

function AssignmentMiniList({
  title,
  items,
  t,
  language,
}) {
  if (
    !items ||
    items.length === 0
  ) {
    return null;
  }

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
        {items
          .slice(0, 6)
          .map((item, index) => (
            <a
              className={`upcoming-item ${
                item.is_discussion
                  ? "discussion-task"
                  : ""
              }`}
              key={`${
                item.assignment_id ||
                item.assignment_name
              }-${index}`}
              href={
                item.assignment_url ||
                "#"
              }
              target={
                item.assignment_url
                  ? "_blank"
                  : undefined
              }
              rel={
                item.assignment_url
                  ? "noreferrer"
                  : undefined
              }
            >
              <div className="upcoming-date">
                <span>
                  {formatShortDate(
                    item.due_date_iso,
                    language
                  )}
                </span>
              </div>

              <div className="upcoming-copy">
                <strong className="upcoming-title-row">
                  {item.is_discussion ? (
                    <MessageCircle
                      size={14}
                      aria-hidden="true"
                    />
                  ) : null}

                  <span>
                    {item.assignment_name}
                  </span>
                </strong>

                <span>
                  {item.course_name}
                </span>

                <small>
                  {item.due_date_iso
                    ? formatDateTime(
                        item.due_date_iso,
                        language
                      )
                    : t(
                        "assignment.noDueDate"
                      )}
                </small>
              </div>

              <StatusBadge
                value={item.status}
                t={t}
              />
            </a>
          ))}
      </div>
    </section>
  );
}

function DiscussionPanel({
  discussions,
  t,
  language,
}) {
  const pending =
    discussions?.groups?.needs_action || [];

  const hasPending = pending.length > 0;

  const summaryText = hasPending
    ? pending.length === 1
      ? t("discussion.pendingSummaryOne")
      : t("discussion.pendingSummaryMany", {
          count: pending.length,
        })
    : t("discussion.emptySummary");

  return (
    <section
      className={`side-panel discussion-panel ${
        hasPending
          ? "has-pending"
          : "is-clear"
      }`}
    >
      <div className="side-panel-header discussion-panel-header">
        <div>
          <h2>{t("discussion.title")}</h2>
          <p>{summaryText}</p>
        </div>

        <div className="discussion-header-icon">
          {hasPending ? (
            <>
              <MessageCircle size={21} />

              <span className="discussion-header-count">
                {pending.length > 99
                  ? "99+"
                  : pending.length}
              </span>
            </>
          ) : (
            <CheckCircle2 size={21} />
          )}
        </div>
      </div>

      {hasPending ? (
        <div className="discussion-primary-content">
          <div className="discussion-list">
            {pending.map((item) => {
              const dueDate =
                item.due_date_iso ||
                item.lock_at;

              const metaText = dueDate
                ? t("discussion.replyBy", {
                    date: formatDateTime(
                      dueDate,
                      language
                    ),
                  })
                : t(
                    "discussion.replyNoDueDate"
                  );

              return (
                <a
                  className="discussion-item pending"
                  key={`${item.course_id}-${item.discussion_id}`}
                  href={
                    item.discussion_url || "#"
                  }
                  target={
                    item.discussion_url
                      ? "_blank"
                      : undefined
                  }
                  rel={
                    item.discussion_url
                      ? "noreferrer"
                      : undefined
                  }
                >
                  <div className="discussion-item-icon">
                    <MessageCircle size={18} />
                  </div>

                  <div className="discussion-item-copy">
                    <strong
                      title={
                        item.discussion_title
                      }
                    >
                      {item.discussion_title}
                    </strong>

                    <span
                      title={item.course_name}
                    >
                      {item.course_name}
                    </span>

                    <small>{metaText}</small>
                  </div>

                  <StatusBadge
                    value="needs_reply"
                    t={t}
                  />
                </a>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="discussion-clear-state">
          <div className="discussion-clear-icon">
            <CheckCircle2 size={20} />
          </div>

          <div>
            <strong>
              {t("discussion.emptyTitle")}
            </strong>

            <span>
              {t("discussion.emptyText")}
            </span>
          </div>
        </div>
      )}
    </section>
  );
}

function AssignmentsColumn({
  groups,
  discussions,
  t,
  language,
}) {
  const assignmentItemsOnly = (items) =>
    (items || []).filter(
      (item) => !item?.is_discussion
    );

  const actNowItems = assignmentItemsOnly(
    groups?.act_now
  );
  const thisWeekItems = assignmentItemsOnly(
    groups?.this_week
  );
  const nextWeekItems = assignmentItemsOnly(
    groups?.next_week
  );
  const opensSoonItems = assignmentItemsOnly(
    groups?.opens_soon
  );
  const noDueDateItems = assignmentItemsOnly(
    groups?.no_due_date
  );
  const submittedItems = assignmentItemsOnly(
    groups?.submitted
  );

  const hasAssignments =
    actNowItems.length +
      thisWeekItems.length +
      nextWeekItems.length +
      opensSoonItems.length +
      noDueDateItems.length +
      submittedItems.length >
    0;

  return (
    <aside className="right-column">
      <AssignmentMiniList
        title={t("groups.actNow")}
        items={actNowItems}
        t={t}
        language={language}
      />

      <AssignmentMiniList
        title={t("groups.thisWeek")}
        items={thisWeekItems}
        t={t}
        language={language}
      />

      <AssignmentMiniList
        title={t("groups.nextWeek")}
        items={nextWeekItems}
        t={t}
        language={language}
      />

      <AssignmentMiniList
        title={t("groups.opensSoon")}
        items={opensSoonItems}
        t={t}
        language={language}
      />

      <AssignmentMiniList
        title={t("groups.noDueDate")}
        items={noDueDateItems}
        t={t}
        language={language}
      />

      <DiscussionPanel
        discussions={discussions}
        t={t}
        language={language}
      />

      <AssignmentMiniList
        title={t("groups.submitted")}
        items={submittedItems}
        t={t}
        language={language}
      />

      {!hasAssignments ? (
        <section className="side-panel">
          <div className="empty-state">
            <CheckCircle2 size={24} />

            <strong>
              {t("ui.stableTitle")}
            </strong>

            <span>
              {t("ui.stableText")}
            </span>
          </div>
        </section>
      ) : null}
    </aside>
  );
}

function RemindersStrip({
  summary,
  courses,
  language,
  t,
}) {
  const atRisk = Number(
    summary?.courses_at_risk ?? 0
  );

  const pending = Number(
    courses?.reduce(
      (total, course) =>
        total +
        Number(
          course.pending_grade_count ??
            0
        ),
      0
    ) ?? 0
  );

  const discussionAttention =
    Number(
      summary?.discussions_actionable ??
        summary?.discussions_needs_action ??
        0
    );

  if (
    atRisk === 0 &&
    pending === 0 &&
    discussionAttention === 0
  ) {
    return (
      <section className="reminders-strip success">
        <ShieldCheck size={21} />

        <div>
          <strong>
            {t("ui.stableTitle")}
          </strong>

          <span>
            {t("ui.stableText")}
          </span>
        </div>
      </section>
    );
  }

  const title =
    language === "es"
      ? "Atención académica"
      : "Academic attention";

  let description = "";

  if (
    pending > 0 &&
    atRisk > 0
  ) {
    description =
      language === "es"
        ? `${pending} nota(s) pendiente(s) y ${atRisk} curso(s) en riesgo`
        : `${pending} pending grade(s) and ${atRisk} course(s) at risk`;
  } else if (pending > 0) {
    description =
      language === "es"
        ? `${pending} nota(s) pendiente(s) por confirmar`
        : `${pending} pending grade(s) to confirm`;
  } else if (atRisk > 0) {
    description =
      language === "es"
        ? `${atRisk} curso(s) en riesgo`
        : `${atRisk} course(s) at risk`;
  }

  if (discussionAttention > 0) {
    const discussionText = t(
      "reminders.discussions",
      { count: discussionAttention }
    );

    description = description
      ? `${description} · ${discussionText}`
      : discussionText;
  }

  return (
    <section className="reminders-strip alert">
      <div className="reminder-summary-icon">
        {atRisk > 0 ? (
          <AlertTriangle size={20} />
        ) : discussionAttention > 0 ? (
          <MessageCircle size={20} />
        ) : (
          <FileText size={20} />
        )}
      </div>

      <div className="reminder-summary-copy">
        <strong>{title}</strong>
        <span>{description}</span>
      </div>
    </section>
  );
}

function AccessGate({
  onUnlock,
  errorMessage,
  loading,
  language,
  setLanguage,
  theme,
  setTheme,
  t,
}) {
  const [
    accessKey,
    setAccessKey,
  ] = useState("");

  const submit = async (event) => {
    event.preventDefault();

    if (
      !accessKey.trim() ||
      loading
    ) {
      return;
    }

    await onUnlock(
      accessKey.trim()
    );
  };

  return (
    <div className="gate-shell">
      <div className="gate-card-wrap">
        <section className="gate-brand-panel">
          <div className="gate-top">
            <BrandLockup
              compact
              showSubtitle={false}
              t={t}
            />

            <div className="gate-top-actions">
              <LanguageToggle
                language={language}
                onChange={setLanguage}
                compact
              />

              <ThemeToggle
                theme={theme}
                onChange={setTheme}
                compact
                t={t}
              />
            </div>
          </div>

          <div className="gate-copy desktop-gate-copy">
            <h1>
              {t("gate.title")}
            </h1>

            <p>
              {t(
                "gate.description"
              )}
            </p>

            <div className="gate-brand-points">
              <div>
                <CheckSquare size={18} />

                {t(
                  "gate.point.currentTerm"
                )}
              </div>

              <div>
                <RefreshCw size={18} />

                {t(
                  "gate.point.canvasSync"
                )}
              </div>

              <div>
                <Lock size={18} />

                {t(
                  "gate.point.protected"
                )}
              </div>
            </div>
          </div>

          <div className="gate-mobile-hero">
            <h1>
              {t(
                "gate.mobileTitle"
              )}
            </h1>

            <p>
              {t(
                "gate.mobileSubtitle"
              )}
            </p>
          </div>
        </section>

        <section className="gate-form-card">
          <div className="creator-block desktop-creator-block">
            <img
              src={creatorPhoto}
              alt="Job Villagran"
              className="creator-avatar"
            />

            <div className="creator-meta">
              <span className="creator-label">
                {t(
                  "ui.creatorLabel"
                )}
              </span>

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

          <div className="gate-title">
            {t("gate.welcome")}
          </div>

          <div className="gate-subtitle">
            {t("gate.subtitle")}
          </div>

          <form
            onSubmit={submit}
            className="gate-form"
          >
            <label
              className="gate-label"
              htmlFor="accessKey"
            >
              {t(
                "gate.accessKey"
              )}
            </label>

            <input
              id="accessKey"
              type="password"
              className="gate-input"
              placeholder={t(
                "gate.placeholder"
              )}
              value={accessKey}
              onChange={(event) =>
                setAccessKey(
                  event.target.value
                )
              }
              autoComplete="off"
            />

            {errorMessage ? (
              <div className="gate-error">
                {errorMessage}
              </div>
            ) : null}

            <button
              type="submit"
              className="gate-button"
              disabled={loading}
            >
              {loading
                ? t(
                    "gate.validating"
                  )
                : t(
                    "gate.unlock"
                  )}
            </button>

            <div className="gate-mobile-security">
              <Lock size={15} />

              <span>
                {t(
                  "gate.mobileSecureNote"
                )}
              </span>
            </div>

          </form>
        </section>
      </div>

      <footer
        className="mobile-creator-credit"
        aria-label={`${t("ui.creatorLabel")} Job Villagran`}
      >
        <img
          src={creatorPhoto}
          alt="Job Villagran"
        />

        <div>
          <span>
            {t("ui.creatorLabel")}
          </span>

          <strong>
            Job Villagran
          </strong>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  const [
    language,
    setLanguageState,
  ] = useState(
    getInitialLanguage
  );

  const [
    theme,
    setThemeState,
  ] = useState(
    getInitialTheme
  );

  const t = useMemo(
    () =>
      createTranslator(language),
    [language]
  );

  const [data, setData] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  const [
    refreshing,
    setRefreshing,
  ] = useState(false);

  const [
    refreshProgress,
    setRefreshProgress,
  ] = useState(0);

  const [
    authProgress,
    setAuthProgress,
  ] = useState(0);

  const refreshStartedAtRef =
    useRef(null);

  const expectedRefreshDurationRef =
    useRef(
      DEFAULT_REFRESH_DURATION_MS
    );

  const authStartedAtRef =
    useRef(null);

  const expectedAuthDurationRef =
    useRef(
      DEFAULT_AUTH_DURATION_MS
    );

  const [error, setError] =
    useState("");

  const [
    authError,
    setAuthError,
  ] = useState("");

  const [
    isUnlocked,
    setIsUnlocked,
  ] = useState(false);

  const setLanguage = (
    nextLanguage
  ) => {
    setLanguageState(
      nextLanguage
    );

    saveLanguage(
      nextLanguage
    );
  };

  const setTheme = (
    nextTheme
  ) => {
    const normalizedTheme =
      normalizeTheme(nextTheme);

    setThemeState(
      normalizedTheme
    );

    saveTheme(
      normalizedTheme
    );
  };

  useEffect(() => {
    document.documentElement.lang =
      language;
  }, [language]);

  useEffect(() => {
    document.documentElement.dataset.theme =
      theme;
  }, [theme]);

  useEffect(() => {
    if (
      typeof window ===
        "undefined" ||
      !(
        "scrollRestoration" in
        window.history
      )
    ) {
      return undefined;
    }

    const previous =
      window.history.scrollRestoration;

    window.history.scrollRestoration =
      "manual";

    return () => {
      window.history.scrollRestoration =
        previous;
    };
  }, []);

  useEffect(() => {
    scrollToTop();
  }, []);

  useEffect(() => {
    const existingKey =
      getStoredAccessKey();

    if (!existingKey) {
      return undefined;
    }

    let cancelled = false;

    const bootstrap = async () => {
      const requestStartedAt =
        performance.now();

      let requestSucceeded = false;

      try {
        authStartedAtRef.current =
          requestStartedAt;

        expectedAuthDurationRef.current =
          getExpectedAuthDuration();

        setAuthProgress(2);
        setLoading(true);
        setError("");
        setAuthError("");

        const payload =
          await getDashboard(false);

        if (cancelled) {
          return;
        }

        setData(payload);
        requestSucceeded = true;

        saveObservedAuthDuration(
          performance.now() -
            requestStartedAt
        );

        setAuthProgress(100);

        await new Promise((resolve) => {
          window.setTimeout(
            resolve,
            350
          );
        });

        if (cancelled) {
          return;
        }

        setIsUnlocked(true);
        scrollToTop();
      } catch {
        if (cancelled) {
          return;
        }

        clearAccessKey();
        setIsUnlocked(false);
        setData(null);
        setAuthProgress(0);

        setAuthError(
          t(
            "error.savedKeyInvalid"
          )
        );
      } finally {
        if (!cancelled) {
          setLoading(false);

          if (!requestSucceeded) {
            setAuthProgress(0);
          }

          authStartedAtRef.current =
            null;
        }
      }
    };

    bootstrap();

    return () => {
      cancelled = true;
    };
  }, [t]);

  useEffect(() => {
    if (
      !loading ||
      isUnlocked ||
      authStartedAtRef.current ===
        null
    ) {
      return undefined;
    }

    let animationFrameId = 0;

    const updateProgress = (now) => {
      const elapsed =
        now -
        authStartedAtRef.current;

      const nextProgress =
        calculateRefreshProgress(
          elapsed,
          expectedAuthDurationRef.current
        );

      setAuthProgress(
        (current) =>
          Math.max(
            current,
            nextProgress
          )
      );

      animationFrameId =
        window.requestAnimationFrame(
          updateProgress
        );
    };

    setAuthProgress(2);

    animationFrameId =
      window.requestAnimationFrame(
        updateProgress
      );

    return () => {
      window.cancelAnimationFrame(
        animationFrameId
      );
    };
  }, [loading, isUnlocked]);

  useEffect(() => {
    if (!refreshing) {
      return undefined;
    }

    if (
      refreshStartedAtRef.current ===
      null
    ) {
      refreshStartedAtRef.current =
        performance.now();
    }

    let animationFrameId = 0;

    const updateProgress = (now) => {
      const elapsed =
        now -
        refreshStartedAtRef.current;

      const nextProgress =
        calculateRefreshProgress(
          elapsed,
          expectedRefreshDurationRef.current
        );

      setRefreshProgress(
        (current) =>
          Math.max(
            current,
            nextProgress
          )
      );

      animationFrameId =
        window.requestAnimationFrame(
          updateProgress
        );
    };

    setRefreshProgress(2);

    animationFrameId =
      window.requestAnimationFrame(
        updateProgress
      );

    return () => {
      window.cancelAnimationFrame(
        animationFrameId
      );
    };
  }, [refreshing]);

  const load = async (
    force = false
  ) => {
    const requestStartedAt =
      performance.now();

    let requestSucceeded = false;

    try {
      setError("");

      if (force) {
        refreshStartedAtRef.current =
          requestStartedAt;

        expectedRefreshDurationRef.current =
          getExpectedRefreshDuration();

        setRefreshProgress(2);
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const payload = force
        ? await refreshDashboard()
        : await getDashboard(false);

      setData(payload);
      requestSucceeded = true;
    } catch (err) {
      if (
        String(
          err.message
        ).includes("401")
      ) {
        clearAccessKey();
        setIsUnlocked(false);
        setData(null);

        setAuthError(
          t("error.invalidKey")
        );
      } else {
        setError(
          err.message ||
            t(
              "error.dashboardLoad"
            )
        );
      }
    } finally {
      setLoading(false);

      if (force) {
        const observedDuration =
          performance.now() -
          requestStartedAt;

        if (requestSucceeded) {
          saveObservedRefreshDuration(
            observedDuration
          );
        }

        setRefreshProgress(100);

        window.setTimeout(() => {
          setRefreshing(false);
          setRefreshProgress(0);

          refreshStartedAtRef.current =
            null;
        }, 450);
      } else {
        setRefreshing(false);
      }
    }
  };

  const unlock = async (
    key
  ) => {
    const requestStartedAt =
      performance.now();

    let requestSucceeded = false;

    try {
      authStartedAtRef.current =
        requestStartedAt;

      expectedAuthDurationRef.current =
        getExpectedAuthDuration();

      setAuthProgress(2);
      setLoading(true);
      setAuthError("");
      setError("");

      const payload =
        await validateAccessKey(
          key
        );

      storeAccessKey(key);
      setData(payload);
      requestSucceeded = true;

      saveObservedAuthDuration(
        performance.now() -
          requestStartedAt
      );

      setAuthProgress(100);

      await new Promise((resolve) => {
        window.setTimeout(
          resolve,
          350
        );
      });

      setIsUnlocked(true);
      scrollToTop();
    } catch (err) {
      clearAccessKey();
      setIsUnlocked(false);
      setData(null);
      setAuthProgress(0);

      if (
        err?.status === 401 ||
        err?.status === 403
      ) {
        setAuthError(
          t(
            "error.invalidKeyRetry"
          )
        );
      } else {
        setAuthError(
          t(
            "error.canvasUnavailable"
          )
        );
      }
    } finally {
      setLoading(false);

      if (!requestSucceeded) {
        setAuthProgress(0);
      }

      authStartedAtRef.current =
        null;
    }
  };

  const logout = () => {
    clearAccessKey();
    setData(null);
    setError("");
    setAuthError("");
    setIsUnlocked(false);
    scrollToTop();
  };

  if (!isUnlocked) {
    return (
      <>
        <AccessGate
          onUnlock={unlock}
          errorMessage={
            authError
          }
          loading={loading}
          language={language}
          setLanguage={
            setLanguage
          }
          theme={theme}
          setTheme={setTheme}
          t={t}
        />

        {loading ? (
          <RefreshOverlay
            progress={
              authProgress
            }
            title={t(
              "ui.validatingTitle"
            )}
            subtitle={t(
              "ui.validatingSubtitle"
            )}
            t={t}
          />
        ) : null}
      </>
    );
  }

  if (
    loading &&
    !data
  ) {
    return (
      <LoadingOverlay
        title={t(
          "ui.loadingTitle"
        )}
        subtitle={t(
          "ui.loadingSubtitle"
        )}
      />
    );
  }

  return (
    <>
      {refreshing ? (
        <RefreshOverlay
          progress={
            refreshProgress
          }
          t={t}
        />
      ) : null}

      <header className="topbar">
        <div className="topbar-brand">
          <BrandLockup
            compact
            showSubtitle={false}
            t={t}
          />
        </div>

        <div className="topbar-actions">
          <SyncChip
            sync={data?.sync}
            language={language}
            t={t}
          />

          <LanguageToggle
            language={language}
            onChange={
              setLanguage
            }
          />

          <ThemeToggle
            theme={theme}
            onChange={setTheme}
            t={t}
          />

          <button
            type="button"
            className="toolbar-button primary"
            onClick={() =>
              load(true)
            }
            disabled={refreshing}
          >
            <RefreshCw size={18} />

            <span>
              {refreshing
                ? t(
                    "actions.refreshing"
                  )
                : t(
                    "actions.refresh"
                  )}
            </span>
          </button>

          <button
            type="button"
            className="toolbar-button"
            onClick={logout}
          >
            <Lock size={17} />

            <span>
              {t("actions.lock")}
            </span>
          </button>
        </div>
      </header>

      <div className="dashboard-page">
        <main className="dashboard-main">
          <section className="page-intro">
            <div>
              <h1>
                {t(
                  "ui.overviewTitle"
                )}
              </h1>

              <p>
                {t(
                  "ui.overviewSubtitle"
                )}
              </p>
            </div>

            <RemindersStrip
              summary={
                data?.summary
              }
              courses={
                data?.courses || []
              }
              language={language}
              t={t}
            />
          </section>

          {error ? (
            <div className="error-banner">
              {error}
            </div>
          ) : null}

          <StatsOverview
            summary={
              data?.summary
            }
            t={t}
          />

          <div className="dashboard-content">
            <CoursePanel
              courses={
                data?.courses || []
              }
              t={t}
            />

            <AssignmentsColumn
              groups={
                data?.groups
              }
              discussions={
                data?.discussions
              }
              language={language}
              t={t}
            />
          </div>
        </main>
      </div>
    </>
  );
}