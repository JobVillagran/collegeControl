export const LANGUAGE_STORAGE_KEY = "athena_desk_language";

export const LANGUAGES = {
  en: {
    short: "EN",
    label: "English",
    locale: "en-GB",
  },
  es: {
    short: "ES",
    label: "Español",
    locale: "es-GT",
  },
};

export const DEFAULT_LANGUAGE = "es";

const DICTIONARY = {
  en: {
    "brand.subtitle": "Secure academic workspace",

    "creator.label": "Created by",

    "ui.overviewTitle": "Academic overview",
    "ui.overviewSubtitle": "Here is what matters most in your courses today.",
    "ui.myCourses": "My Courses",
    "ui.upcomingWork": "Upcoming work",
    "ui.stableTitle": "Everything looks stable",
    "ui.stableText": "No urgent assignment or course alert was found.",
    "ui.compactSync": "Synced",
    "ui.points": "Points",
    "ui.mark": "Pass mark",
    "ui.result": "Result",
    "ui.creatorLabel": "Created by",
    "ui.refreshTitle": "Refreshing your courses",
    "ui.refreshSubtitle":
      "We are syncing Canvas and recalculating your points.",
    "ui.validatingTitle": "Unlocking your workspace",
    "ui.validatingSubtitle":
      "Checking your private access key and preparing your dashboard.",
    "ui.loadingTitle": "Loading your dashboard",
    "ui.loadingSubtitle":
      "Bringing your latest academic data into view.",

    "theme.light": "Light",
    "theme.dark": "Dark",
    "theme.switchToLight": "Switch to light mode",
    "theme.switchToDark": "Switch to dark mode",

    "components.partial_1": "First partial",
    "components.partial_2": "Second partial",
    "components.final_exam": "Final exam",
    "components.recovery_exam": "Recovery exam",
    "components.final_project": "Final project",
    "components.project": "Projects",
    "components.task": "Assignments",
    "components.exam": "Exams",
    "components.attendance": "Attendance",
    "components.other": "Other",

    "gate.title": "Academic workspace",
    "gate.description":
      "Enter your private access key to open your personal university dashboard, refresh tasks, and review course progress securely.",
    "gate.mobileTitle": "Secure academic access",
    "gate.mobileSubtitle":
      "Enter your key to view courses, grades, and pending work.",
    "gate.mobileSecureNote": "Protected student workspace",
    "gate.point.currentTerm": "Current-term courses only",
    "gate.point.canvasSync": "Canvas-backed live sync",
    "gate.point.protected": "Protected refresh and dashboard access",
    "gate.welcome": "Welcome",
    "gate.subtitle": "Enter your private access key to continue.",
    "gate.accessKey": "Access key",
    "gate.placeholder": "Enter access key",
    "gate.validating": "Validating...",
    "gate.unlock": "Unlock dashboard",

    "language.switchLabel": "Language",
    "language.english": "English",
    "language.spanish": "Spanish",

    "actions.refresh": "Refresh now",
    "actions.refreshing": "Refreshing...",
    "actions.lock": "Lock",
    "actions.openCanvas": "Open in Canvas",

    "screen.loading": "Loading dashboard...",

    "error.savedKeyInvalid":
      "Your saved key is no longer valid. Please enter it again.",
    "error.invalidKey": "Invalid access key.",
    "error.invalidKeyRetry": "Invalid access key. Please try again.",
    "error.dashboardLoad": "Failed to load dashboard.",

    "sync.healthy": "Sync healthy",
    "sync.issue": "Sync issue",
    "sync.last": "Last sync",
    "sync.message.loaded": "Live data loaded successfully.",
    "sync.message.cached": "Cached data loaded.",
    "sync.message.refreshing": "Refreshing Canvas data...",

    "stats.actionable": "Actionable",
    "stats.urgent": "Urgent",
    "stats.opensSoon": "Opens soon",
    "stats.projects": "Projects",
    "stats.discussions": "Pending forums",
    "stats.submitted": "Submitted",
    "stats.atRisk": "At risk",
    "stats.watch": "Watch",
    "stats.incomplete": "Incomplete",

    "discussion.title": "Pending forums",
    "discussion.pendingSummaryOne": "1 forum still needs your participation",
    "discussion.pendingSummaryMany": "{count} forums still need your participation",
    "discussion.completeSummaryOne": "1 active forum · participation found",
    "discussion.completeSummaryMany": "{count} active forums · participation found",
    "discussion.submittedSummaryOne": "Your participation was found in the active forum.",
    "discussion.submittedSummaryMany": "Your participation was found in all {count} active forums.",
    "discussion.noActiveSummary": "No active forums found",
    "discussion.noActiveTitle": "No active forums",
    "discussion.noActiveText": "Canvas is not currently reporting discussion forums for your active courses.",
    "discussion.emptySummary": "No forums require action",
    "discussion.emptyTitle": "No pending forum actions",
    "discussion.emptyText": "No forum requires a reply or participation right now.",
    "discussion.sectionPending": "To reply",
    "discussion.sectionUpdates": "New activity",
    "discussion.sectionMissed": "Closed without participation",
    "discussion.sectionVerification": "Needs verification",
    "discussion.replyBy": "Reply by {date}",
    "discussion.replyNoDueDate": "No due date · Reply in Canvas",
    "discussion.submittedWithOneUpdate": "Submitted · 1 new reply",
    "discussion.submittedWithManyUpdates": "Submitted · {count} new replies",
    "discussion.submittedWithActivity": "Submitted · new activity",
    "discussion.unreadMessageOne": "1 unread message",
    "discussion.unreadMessageMany": "{count} unread messages",
    "discussion.updatedForumOne": "1 submitted forum",
    "discussion.updatedForumMany": "{count} submitted forums",
    "discussion.viewActivity": "View activity",
    "discussion.hideActivity": "Hide activity",
    "discussion.moreUpdates": "{count} more forum(s) with activity",
    "discussion.missedText": "The forum closed without finding your participation",
    "discussion.verificationText": "Canvas did not allow participation to be verified",
    "discussion.openInCanvas": "Open forum in Canvas",

    "groups.actNow": "Act now",
    "groups.thisWeek": "This week",
    "groups.nextWeek": "Next week",
    "groups.thirdWeek": "Third week",
    "groups.opensSoon": "Opens soon",
    "groups.submitted": "Submitted",
    "groups.noDueDate": "No due date",

    "assignment.due": "Due",
    "assignment.noDueDate": "No due date",
    "assignment.submittedWaiting": "Submitted • waiting for grading",
    "assignment.urgency.actNow": "Act now • {hours}h left",
    "assignment.urgency.soon": "Soon • {hours}h left",
    "assignment.urgency.upcoming": "Upcoming • {hours}h left",

    "reminders.discussions": "{count} discussion forum(s) still need your reply",

    "course.current": "Current course",
    "course.progress": "Course progress",
    "course.earnedPoints": "Earned points",
    "course.realConfirmedPoints": "Real confirmed points",
    "course.finalResult": "Final result",
    "course.finalFound": "Final/Recovery grade found",
    "course.needToPass": "Need to pass",
    "course.passMark": "Pass mark",
    "course.lostPoints": "Lost points",
    "course.lostPointsHelper": "Missed + points lost in grades",
    "course.available": "Available",
    "course.availableHelper": "Open + pending + unpublished",
    "course.pointAudit": "Point audit",
    "course.published": "Published",
    "course.pending": "Pending",
    "course.review": "Review",
    "course.unpublishedEst": "Unpublished est.",
    "course.realPointsEarned": "Real points earned",
    "course.toPass": "to pass",
    "course.graded": "Graded",
    "course.missed": "Missed",
    "course.attendance": "Attendance",
    "course.recoveryRule": "Recovery rule",
    "course.applied": "Applied",
    "course.notApplied": "Not applied",
    "course.viewDetails": "View details",
    "course.hideDetails": "Hide details",
    "course.finishedPassed":
      "Course finished. You passed with {earned} point(s). The passing mark is {passing}.",
    "course.finishedFailed":
      "Course finished. You did not reach the passing mark. Current confirmed total is {earned}/{total}; passing mark is {passing}.",
    "course.expl.realPoints": "Real points: {earned} / {total}.",
    "course.expl.published": "Effective published points: {published}.",
    "course.expl.lost": "{points} point(s) are already lost.",
    "course.expl.pending":
      "{points} point(s) are submitted but pending grade.",
    "course.expl.open": "{points} point(s) are still open.",
    "course.expl.review":
      "{points} point(s) need manual/detail review.",
    "course.expl.unpublished":
      "{points} point(s) are estimated as not published yet.",
    "course.expl.need":
      "Need {points} more point(s) to reach {passing}.",
    "course.expl.required": "Required from remaining: {percent}%.",

    "status.info": "Info",
    "status.not_enabled_yet": "Not enabled yet",
    "status.submitted": "Submitted",
    "status.submitted_pending": "Pending review",
    "status.graded": "Graded",
    "status.missing": "Missed",
    "status.late": "Late",
    "status.unsubmitted": "Not submitted",
    "status.open": "Open",
    "status.open_no_due_date": "Open",
    "status.closed": "Closed",
    "status.published": "Published",
    "status.healthy": "Healthy",
    "status.watch": "Watch",
    "status.at_risk": "At risk",
    "status.critical": "Critical",
    "status.not_enough_data": "Incomplete data",
    "status.no_due_date": "No due date",
    "status.needs_reply": "Reply needed",
    "status.verification_needed": "Verify",
    "status.unread": "New activity",
    "status.not_applicable": "N/A",
    "status.passed": "Passed",
    "status.failed": "Failed",
    "status.in_progress": "In progress",
    "status.success": "Success",
    "status.warning": "Warning",
    "status.danger": "Danger",
    "status.neutral": "Neutral",
  },

  es: {
    "brand.subtitle": "Espacio académico seguro",

    "creator.label": "Creado por",

    "ui.overviewTitle": "Resumen académico",
    "ui.overviewSubtitle":
      "Esto es lo más importante de tus cursos hoy.",
    "ui.myCourses": "Mis cursos",
    "ui.upcomingWork": "Próximas entregas",
    "ui.stableTitle": "Todo se ve estable",
    "ui.stableText":
      "No se encontró una alerta urgente de tarea o curso.",
    "ui.compactSync": "Sincronizado",
    "ui.points": "Puntos",
    "ui.mark": "Mínimo",
    "ui.result": "Resultado",
    "ui.creatorLabel": "Creado por",
    "ui.refreshTitle": "Actualizando tus cursos",
    "ui.refreshSubtitle":
      "Estamos consultando Canvas y recalculando tus puntos.",
    "ui.validatingTitle": "Abriendo tu espacio",
    "ui.validatingSubtitle":
      "Estamos validando tu llave privada y preparando el dashboard.",
    "ui.loadingTitle": "Cargando tu dashboard",
    "ui.loadingSubtitle":
      "Estamos trayendo tu información académica más reciente.",

    "theme.light": "Claro",
    "theme.dark": "Oscuro",
    "theme.switchToLight": "Cambiar a modo claro",
    "theme.switchToDark": "Cambiar a modo oscuro",

    "components.partial_1": "Primer parcial",
    "components.partial_2": "Segundo parcial",
    "components.final_exam": "Examen final",
    "components.recovery_exam": "Examen recuperación",
    "components.final_project": "Proyecto final",
    "components.project": "Proyectos",
    "components.task": "Tareas",
    "components.exam": "Exámenes",
    "components.attendance": "Asistencia",
    "components.other": "Otros",

    "gate.title": "Espacio académico",
    "gate.description":
      "Ingresa tu llave privada para abrir tu dashboard universitario, actualizar tareas y revisar tu progreso académico de forma segura.",
    "gate.mobileTitle": "Acceso académico seguro",
    "gate.mobileSubtitle":
      "Ingresa tu llave para ver cursos, notas y pendientes.",
    "gate.mobileSecureNote": "Espacio estudiantil protegido",
    "gate.point.currentTerm": "Solo cursos del semestre actual",
    "gate.point.canvasSync": "Sincronización en vivo con Canvas",
    "gate.point.protected":
      "Acceso protegido al dashboard y actualización",
    "gate.welcome": "Bienvenido",
    "gate.subtitle": "Ingresa tu llave privada para continuar.",
    "gate.accessKey": "Llave de acceso",
    "gate.placeholder": "Ingresa la llave de acceso",
    "gate.validating": "Validando...",
    "gate.unlock": "Abrir dashboard",

    "language.switchLabel": "Idioma",
    "language.english": "Inglés",
    "language.spanish": "Español",

    "actions.refresh": "Actualizar",
    "actions.refreshing": "Actualizando...",
    "actions.lock": "Bloquear",
    "actions.openCanvas": "Abrir en Canvas",

    "screen.loading": "Cargando dashboard...",

    "error.savedKeyInvalid":
      "Tu llave guardada ya no es válida. Ingrésala nuevamente.",
    "error.invalidKey": "Llave de acceso inválida.",
    "error.invalidKeyRetry":
      "Llave de acceso inválida. Intenta nuevamente.",
    "error.dashboardLoad": "No se pudo cargar el dashboard.",

    "sync.healthy": "Sincronización correcta",
    "sync.issue": "Problema de sincronización",
    "sync.last": "Última sincronización",
    "sync.message.loaded": "Datos cargados correctamente.",
    "sync.message.cached": "Datos guardados cargados.",
    "sync.message.refreshing": "Actualizando datos desde Canvas...",

    "stats.actionable": "Accionables",
    "stats.urgent": "Urgentes",
    "stats.opensSoon": "Abren pronto",
    "stats.projects": "Proyectos",
    "stats.discussions": "Foros pendientes",
    "stats.submitted": "Entregadas",
    "stats.atRisk": "En riesgo",
    "stats.watch": "Vigilar",
    "stats.incomplete": "Incompleto",

    "discussion.title": "Foros pendientes",
    "discussion.pendingSummaryOne": "1 foro todavía requiere tu participación",
    "discussion.pendingSummaryMany": "{count} foros todavía requieren tu participación",
    "discussion.completeSummaryOne": "1 foro activo · participación encontrada",
    "discussion.completeSummaryMany": "{count} foros activos · participación encontrada",
    "discussion.submittedSummaryOne": "Tu participación fue encontrada en el foro activo.",
    "discussion.submittedSummaryMany": "Tu participación fue encontrada en los {count} foros activos.",
    "discussion.noActiveSummary": "No se encontraron foros activos",
    "discussion.noActiveTitle": "No hay foros activos",
    "discussion.noActiveText": "Canvas no está reportando foros de discusión en tus cursos activos.",
    "discussion.emptySummary": "No hay foros que requieran acción",
    "discussion.emptyTitle": "No hay foros pendientes de accionar",
    "discussion.emptyText": "No tienes que responder ni entregar participación en ningún foro en este momento.",
    "discussion.sectionPending": "Por responder",
    "discussion.sectionUpdates": "Actividad nueva",
    "discussion.sectionMissed": "Cerrados sin participación",
    "discussion.sectionVerification": "Requieren verificación",
    "discussion.replyBy": "Responder antes de {date}",
    "discussion.replyNoDueDate": "Sin fecha límite · Responder en Canvas",
    "discussion.submittedWithOneUpdate": "Entregado · 1 respuesta nueva",
    "discussion.submittedWithManyUpdates": "Entregado · {count} respuestas nuevas",
    "discussion.submittedWithActivity": "Entregado · actividad nueva",
    "discussion.unreadMessageOne": "1 mensaje sin leer",
    "discussion.unreadMessageMany": "{count} mensajes sin leer",
    "discussion.updatedForumOne": "1 foro entregado",
    "discussion.updatedForumMany": "{count} foros entregados",
    "discussion.viewActivity": "Ver actividad",
    "discussion.hideActivity": "Ocultar actividad",
    "discussion.moreUpdates": "{count} foro(s) más con actividad",
    "discussion.missedText": "El foro cerró sin encontrar tu participación",
    "discussion.verificationText": "Canvas no permitió verificar tu participación",
    "discussion.openInCanvas": "Abrir foro en Canvas",

    "groups.actNow": "Accionar ahora",
    "groups.thisWeek": "Esta semana",
    "groups.nextWeek": "Próxima semana",
    "groups.thirdWeek": "Tercera semana",
    "groups.opensSoon": "Abren pronto",
    "groups.submitted": "Entregadas",
    "groups.noDueDate": "Sin fecha de entrega",

    "assignment.due": "Entrega",
    "assignment.noDueDate": "Sin fecha de entrega",
    "assignment.submittedWaiting":
      "Entregada • esperando calificación",
    "assignment.urgency.actNow":
      "Acciona ahora • faltan {hours}h",
    "assignment.urgency.soon": "Pronto • faltan {hours}h",
    "assignment.urgency.upcoming":
      "Próxima • faltan {hours}h",

    "reminders.discussions":
      "{count} foro(s) de discusión todavía requieren tu respuesta",

    "course.current": "Curso actual",
    "course.progress": "Progreso de cursos",
    "course.earnedPoints": "Puntos ganados",
    "course.realConfirmedPoints": "Puntos reales confirmados",
    "course.finalResult": "Resultado final",
    "course.finalFound":
      "Nota final/recuperación encontrada",
    "course.needToPass": "Faltan para ganar",
    "course.passMark": "Mínimo para ganar",
    "course.lostPoints": "Puntos perdidos",
    "course.lostPointsHelper":
      "Faltantes + puntos perdidos en notas",
    "course.available": "Disponibles",
    "course.availableHelper":
      "Abiertos + pendientes + no publicados",
    "course.pointAudit": "Auditoría de puntos",
    "course.published": "Publicados",
    "course.pending": "Pendientes",
    "course.review": "Revisar",
    "course.unpublishedEst": "No publicados est.",
    "course.realPointsEarned": "Puntos reales ganados",
    "course.toPass": "para ganar",
    "course.graded": "Calificadas",
    "course.missed": "Perdidas",
    "course.attendance": "Asistencia",
    "course.recoveryRule": "Regla de recuperación",
    "course.applied": "Aplicada",
    "course.notApplied": "No aplicada",
    "course.viewDetails": "Ver detalles",
    "course.hideDetails": "Ocultar detalles",
    "course.finishedPassed":
      "Curso finalizado. Ganaste con {earned} punto(s). El mínimo para ganar es {passing}.",
    "course.finishedFailed":
      "Curso finalizado. No llegaste al mínimo para ganar. Total confirmado actual: {earned}/{total}; mínimo requerido: {passing}.",
    "course.expl.realPoints":
      "Puntos reales: {earned} / {total}.",
    "course.expl.published":
      "Puntos publicados efectivos: {published}.",
    "course.expl.lost":
      "{points} punto(s) ya están perdidos.",
    "course.expl.pending":
      "{points} punto(s) fueron entregados pero siguen pendientes de nota.",
    "course.expl.open":
      "{points} punto(s) siguen abiertos.",
    "course.expl.review":
      "{points} punto(s) necesitan revisión manual/detalle.",
    "course.expl.unpublished":
      "{points} punto(s) se estiman como no publicados todavía.",
    "course.expl.need":
      "Necesitas {points} punto(s) más para llegar a {passing}.",
    "course.expl.required":
      "Requerido sobre lo restante: {percent}%.",

    "status.info": "Info",
    "status.not_enabled_yet": "No habilitada todavía",
    "status.submitted": "Entregada",
    "status.submitted_pending": "Pendiente de revisión",
    "status.graded": "Calificada",
    "status.missing": "Faltante",
    "status.late": "Tarde",
    "status.unsubmitted": "No entregada",
    "status.open": "Abierta",
    "status.open_no_due_date": "Abierta",
    "status.closed": "Cerrada",
    "status.published": "Publicada",
    "status.healthy": "Bien",
    "status.watch": "Vigilar",
    "status.at_risk": "En riesgo",
    "status.critical": "Crítico",
    "status.not_enough_data": "Datos incompletos",
    "status.no_due_date": "Sin fecha",
    "status.needs_reply": "Debes responder",
    "status.verification_needed": "Verificar",
    "status.unread": "Actividad nueva",
    "status.not_applicable": "N/A",
    "status.passed": "Ganado",
    "status.failed": "Perdido",
    "status.in_progress": "En progreso",
    "status.success": "Correcto",
    "status.warning": "Advertencia",
    "status.danger": "Peligro",
    "status.neutral": "Neutral",
  },
};

function readStorage(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Ignore storage errors.
  }
}

function interpolate(template, params = {}) {
  return String(template).replace(/\{(\w+)\}/g, (_, key) => {
    if (params[key] === undefined || params[key] === null) {
      return `{${key}}`;
    }

    return String(params[key]);
  });
}

function humanizeKey(key) {
  return String(key)
    .split(".")
    .pop()
    .replaceAll("_", " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function normalizeLanguage(value) {
  return Object.keys(LANGUAGES).includes(value)
    ? value
    : DEFAULT_LANGUAGE;
}

export function getInitialLanguage() {
  const stored = readStorage(LANGUAGE_STORAGE_KEY);

  if (stored) {
    return normalizeLanguage(stored);
  }

  const browserLanguage =
    navigator.language?.toLowerCase() || "";

  if (browserLanguage.startsWith("en")) {
    return "en";
  }

  return DEFAULT_LANGUAGE;
}

export function saveLanguage(language) {
  writeStorage(
    LANGUAGE_STORAGE_KEY,
    normalizeLanguage(language)
  );
}

export function createTranslator(language) {
  const currentLanguage = normalizeLanguage(language);

  return function translate(
    key,
    params = {},
    fallback = null
  ) {
    const currentDictionary =
      DICTIONARY[currentLanguage] || {};

    const defaultDictionary =
      DICTIONARY[DEFAULT_LANGUAGE] || {};

    const value =
      currentDictionary[key] ??
      defaultDictionary[key] ??
      DICTIONARY.en?.[key] ??
      fallback ??
      humanizeKey(key);

    return interpolate(value, params);
  };
}

export function translateStatus(value, t) {
  if (!value) {
    return t("status.info");
  }

  const normalized = String(value)
    .trim()
    .toLowerCase();

  return t(
    `status.${normalized}`,
    {},
    normalized
      .replaceAll("_", " ")
      .replace(/\b\w/g, (char) => char.toUpperCase())
  );
}

export function translateComponent(component, t) {
  if (!component) {
    return "";
  }

  const type = String(
    component.type ||
      component.label ||
      "other"
  )
    .trim()
    .toLowerCase();

  return t(
    `components.${type}`,
    {},
    component.label || type
  );
}

export function translateSyncMessage(message, t) {
  if (!message) {
    return "";
  }

  const normalized = String(message)
    .trim()
    .toLowerCase();

  const knownMessages = {
    "live data loaded successfully.":
      "sync.message.loaded",
    "live data loaded successfully":
      "sync.message.loaded",
    "cached data loaded.":
      "sync.message.cached",
    "cached data loaded":
      "sync.message.cached",
    "refreshing canvas data...":
      "sync.message.refreshing",
    "refreshing canvas data":
      "sync.message.refreshing",
  };

  const key = knownMessages[normalized];

  if (key) {
    return t(key);
  }

  return message;
}