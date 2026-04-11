from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from config.settings import APP_TIMEZONE, NOTIFICATION_STATE_FILE
from src.utils.file_utils import read_json, write_json


class NotificationDecisionService:
    def __init__(self) -> None:
        self.timezone = ZoneInfo(APP_TIMEZONE)
        self.state = read_json(
            NOTIFICATION_STATE_FILE,
            default={
                "sent_slots": {},
                "alerts": {},
            },
        )

    def should_send_email(self, payload: dict) -> tuple[bool, str]:
        now = datetime.now(self.timezone)
        slot = self._get_time_slot(now)
        local_date = now.strftime("%Y-%m-%d")

        if slot is None:
            return False, "Current run is outside configured notification slots."

        if slot == "morning":
            reason = "Morning summary is always sent."
            return True, reason

        if slot == "midday":
            has_new_critical = self._has_new_critical_alert(payload)
            if has_new_critical:
                return True, "Midday alert triggered by new critical change."
            return False, "No new critical alerts for midday run."

        if slot == "evening":
            if self._has_actionable_content(payload) or self._has_relevant_changes(payload):
                if not self._already_sent_slot(local_date, slot):
                    return True, "Evening summary triggered by actionable content or relevant changes."
                return False, "Evening summary already sent for this date."
            return False, "No actionable content for evening run."

        return False, "No matching notification rule."

    def mark_email_sent(self, payload: dict) -> None:
        now = datetime.now(self.timezone)
        slot = self._get_time_slot(now)
        local_date = now.strftime("%Y-%m-%d")

        if slot is not None:
            sent_slots = self.state.setdefault("sent_slots", {})
            sent_slots[f"{local_date}:{slot}"] = now.isoformat()

        self._store_alert_levels(payload)
        self._save()

    def _get_time_slot(self, now: datetime) -> str | None:
        hour = now.hour

        if hour == 7:
            return "morning"
        if hour == 13:
            return "midday"
        if hour == 19:
            return "evening"

        return None

    def _already_sent_slot(self, local_date: str, slot: str) -> bool:
        sent_slots = self.state.get("sent_slots", {})
        return f"{local_date}:{slot}" in sent_slots

    def _has_actionable_content(self, payload: dict) -> bool:
        sections = payload.get("sections", {})
        return any(
            len(sections.get(key, [])) > 0
            for key in [
                "act_now",
                "this_week",
                "next_week",
                "third_week",
                "urgent_projects",
                "opens_same_day",
                "no_due_date",
            ]
        )

    def _has_relevant_changes(self, payload: dict) -> bool:
        sections = payload.get("sections", {})
        return any(
            len(sections.get(key, [])) > 0
            for key in [
                "changed_assignments",
                "new_grades",
            ]
        )

    def _has_new_critical_alert(self, payload: dict) -> bool:
        sections = payload.get("sections", {})
        current_critical_items = []

        for key in ["act_now", "urgent_projects", "opens_same_day", "changed_assignments"]:
            for item in sections.get(key, []):
                alert_key, level = self._build_alert_identity(key, item)
                current_critical_items.append((alert_key, level))

        if not current_critical_items:
            return False

        saved_alerts = self.state.get("alerts", {})

        for alert_key, level in current_critical_items:
            previous_level = saved_alerts.get(alert_key)
            if previous_level != level:
                return True

        return False

    def _store_alert_levels(self, payload: dict) -> None:
        sections = payload.get("sections", {})
        alerts = self.state.setdefault("alerts", {})

        tracked_sections = {
            "act_now": "act_now",
            "urgent_projects": "urgent_project",
            "opens_same_day": "opens_same_day",
            "changed_assignments": "deadline_changed",
        }

        for section_name, level in tracked_sections.items():
            for item in sections.get(section_name, []):
                alert_key, _ = self._build_alert_identity(section_name, item)
                alerts[alert_key] = level

    def _build_alert_identity(self, section_name: str, item: dict) -> tuple[str, str]:
        course_name = item.get("course_name", "")
        assignment_name = item.get("assignment_name", "")
        base_key = f"{section_name}::{course_name}::{assignment_name}"

        if section_name == "changed_assignments":
            return base_key, "deadline_changed"
        if section_name == "urgent_projects":
            return base_key, "urgent_project"
        if section_name == "opens_same_day":
            return base_key, "opens_same_day"
        return base_key, "act_now"

    def _save(self) -> None:
        write_json(NOTIFICATION_STATE_FILE, self.state)