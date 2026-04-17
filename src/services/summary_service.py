from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from jinja2 import Environment, FileSystemLoader

from config.settings import (
    APP_TIMEZONE,
    SUMMARY_HTML_FILE,
    SUMMARY_PAYLOAD_FILE,
    SUMMARY_TXT_FILE,
    TEMPLATES_DIR,
)
from src.utils.file_utils import write_json, write_text


class SummaryService:
    def build_payload(self, changes: dict) -> dict:
        groups = changes.get("actionable_groups", {})

        act_now = [self._decorate_card(item) for item in groups.get("act_now", [])]
        this_week = [self._decorate_card(item) for item in groups.get("this_week", [])]
        next_week = [self._decorate_card(item) for item in groups.get("next_week", [])]
        third_week = [self._decorate_card(item) for item in groups.get("third_week", [])]
        urgent_projects = [self._decorate_card(item) for item in groups.get("urgent_projects", [])]
        opens_same_day = [self._decorate_card(item) for item in groups.get("opens_same_day", [])]
        no_due_date = [self._decorate_card(item) for item in groups.get("no_due_date", [])]

        new_grades = [self._decorate_grade_card(item) for item in changes.get("new_grades", [])]
        changed_assignments = [self._decorate_changed_card(item) for item in changes.get("changed_assignments", [])]

        total_actionable = (
            len(act_now)
            + len(this_week)
            + len(next_week)
            + len(third_week)
            + len(no_due_date)
        )

        total_urgent = len(act_now)
        total_opens_soon = len(opens_same_day)

        return {
            "generated_at": self._format_now(),
            "summary_stats": {
                "total_actionable": total_actionable,
                "total_urgent": total_urgent,
                "opens_soon": total_opens_soon,
                "urgent_projects": len(urgent_projects),
                "new_grades": len(new_grades),
            },
            "sections": {
                "act_now": act_now,
                "this_week": this_week,
                "next_week": next_week,
                "third_week": third_week,
                "urgent_projects": urgent_projects,
                "opens_same_day": opens_same_day,
                "no_due_date": no_due_date,
                "changed_assignments": changed_assignments,
                "new_grades": new_grades,
            },
        }

    def render_html(self, payload: dict) -> str:
        env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
        template = env.get_template("summary_template.html")
        return template.render(payload=payload)

    def render_text(self, payload: dict) -> str:
        sections = payload["sections"]
        lines: list[str] = []

        lines.append("College Control")
        lines.append(f"Generated at: {payload['generated_at']}")
        lines.append("")

        lines.append("Act now:")
        lines.extend(self._section_lines(sections["act_now"]))

        lines.append("")
        lines.append("This week:")
        lines.extend(self._section_lines(sections["this_week"]))

        lines.append("")
        lines.append("Next week:")
        lines.extend(self._section_lines(sections["next_week"]))

        lines.append("")
        lines.append("Third week:")
        lines.extend(self._section_lines(sections["third_week"]))

        lines.append("")
        lines.append("Urgent projects:")
        lines.extend(self._section_lines(sections["urgent_projects"]))

        lines.append("")
        lines.append("Opens soon:")
        lines.extend(self._section_lines(sections["opens_same_day"], use_unlock=True))

        lines.append("")
        lines.append("No due date:")
        lines.extend(self._section_lines(sections["no_due_date"]))

        lines.append("")
        lines.append("Changed deadlines:")
        if sections["changed_assignments"]:
            for item in sections["changed_assignments"]:
                lines.append(
                    f"- {item['course_name']} | {item['assignment_name']} | Before: {item['before_due_display']} | Now: {item['after_due_display']}"
                )
        else:
            lines.append("- None")

        lines.append("")
        lines.append("New grades:")
        if sections["new_grades"]:
            for item in sections["new_grades"]:
                lines.append(
                    f"- {item['course_name']} | {item['assignment_name']} | Score: {item['score_display']}"
                )
        else:
            lines.append("- None")

        return "\n".join(lines)

    def save_outputs(self, payload: dict, html: str, text: str) -> None:
        write_json(SUMMARY_PAYLOAD_FILE, payload)
        write_text(SUMMARY_HTML_FILE, html)
        write_text(SUMMARY_TXT_FILE, text)

    def _section_lines(self, items: list[dict], use_unlock: bool = False) -> list[str]:
        if not items:
            return ["- None"]

        lines = []
        for item in items:
            submitted_suffix = " | Submitted" if item.get("is_submitted") else ""
            if use_unlock:
                lines.append(
                    f"- {item['course_name']} | {item['assignment_name']} | Opens: {item.get('unlock_display', 'N/A')} | {item.get('relative_time', '')}{submitted_suffix}"
                )
            else:
                lines.append(
                    f"- {item['course_name']} | {item['assignment_name']} | Due: {item.get('due_display', 'N/A')} | {item.get('relative_time', '')}{submitted_suffix}"
                )
        return lines

    def _decorate_card(self, item: dict) -> dict:
        due_display = self._format_iso(item.get("due_date_iso"))
        unlock_display = self._format_iso(item.get("unlock_at"))

        is_submitted = bool(item.get("submitted_at"))
        is_graded = bool(item.get("score") is not None)

        return {
            "course_name": item.get("course_name"),
            "assignment_name": item.get("assignment_name"),
            "assignment_url": item.get("assignment_url"),
            "status": item.get("status"),
            "urgency_key": item.get("urgency_key"),
            "urgency_label": item.get("urgency_label"),
            "action_required": item.get("action_required"),
            "due_display": due_display,
            "unlock_display": unlock_display,
            "relative_time": self._relative_time(item),
            "badge_bg": self._badge_bg(item.get("urgency_key")),
            "badge_color": self._badge_color(item.get("urgency_key")),
            "border_color": self._border_color(item.get("urgency_key")),
            "meta_line": self._meta_line(item, due_display, unlock_display),
            "is_submitted": is_submitted,
            "submission_label": "Submitted" if is_submitted else None,
            "submission_bg": "#DCFCE7" if is_submitted else None,
            "submission_color": "#166534" if is_submitted else None,
            "is_graded": is_graded,
        }

    def _decorate_grade_card(self, item: dict) -> dict:
        after = item.get("after", {})
        score = after.get("score")
        max_score = after.get("max_score")

        score_display = str(score) if score is not None else "Graded"
        if score is not None and max_score is not None:
            score_display = f"{score}/{max_score}"

        return {
            "course_name": after.get("course_name"),
            "assignment_name": after.get("assignment_name"),
            "score_display": score_display,
            "assignment_url": after.get("assignment_url"),
        }

    def _decorate_changed_card(self, item: dict) -> dict:
        before = item.get("before", {})
        after = item.get("after", {})

        return {
            "course_name": after.get("course_name"),
            "assignment_name": after.get("assignment_name"),
            "before_due_display": self._format_iso(before.get("due_date_iso")),
            "after_due_display": self._format_iso(after.get("due_date_iso")),
            "assignment_url": after.get("assignment_url"),
        }

    def _meta_line(self, item: dict, due_display: str, unlock_display: str) -> str:
        if item.get("status") == "not_enabled_yet":
            return f"Opens: {unlock_display}"
        if item.get("status") == "open_no_due_date":
            return "Published with no due date"
        return f"Due: {due_display}"

    def _relative_time(self, item: dict) -> str:
        if item.get("status") == "not_enabled_yet":
            hours = item.get("hours_until_unlock")
            if hours is None:
                return "Will open later"
            return self._format_remaining(hours, prefix="Opens in ")

        hours = item.get("hours_until_due")
        if hours is None:
            return "No due date"
        return self._format_remaining(hours, prefix="Due in ")

    def _format_remaining(self, hours: float, prefix: str) -> str:
        if hours < 1:
            minutes = max(1, round(hours * 60))
            return f"{prefix}{minutes} min"

        if hours < 24:
            rounded_hours = round(hours, 1)
            return f"{prefix}{rounded_hours} h"

        days = int(hours // 24)
        remaining_hours = int(round(hours % 24))
        if remaining_hours == 0:
            return f"{prefix}{days} day(s)"
        return f"{prefix}{days}d {remaining_hours}h"

    def _format_iso(self, value: str | None) -> str:
        if not value:
            return "N/A"

        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            local_dt = dt.astimezone(ZoneInfo(APP_TIMEZONE))
            return local_dt.strftime("%a %d %b %Y • %I:%M %p")
        except Exception:
            return value

    def _format_now(self) -> str:
        return datetime.now(ZoneInfo(APP_TIMEZONE)).strftime("%a %d %b %Y • %I:%M %p")

    def _badge_bg(self, urgency_key: str | None) -> str:
        mapping = {
            "act_now": "#FEE2E2",
            "this_week": "#FEF3C7",
            "next_week": "#DBEAFE",
            "third_week": "#E0E7FF",
            "opens_same_day": "#EDE9FE",
            "no_due_date": "#E5E7EB",
        }
        return mapping.get(urgency_key, "#E5E7EB")

    def _badge_color(self, urgency_key: str | None) -> str:
        mapping = {
            "act_now": "#B91C1C",
            "this_week": "#A16207",
            "next_week": "#1D4ED8",
            "third_week": "#4338CA",
            "opens_same_day": "#6D28D9",
            "no_due_date": "#374151",
        }
        return mapping.get(urgency_key, "#374151")

    def _border_color(self, urgency_key: str | None) -> str:
        mapping = {
            "act_now": "#EF4444",
            "this_week": "#F59E0B",
            "next_week": "#3B82F6",
            "third_week": "#6366F1",
            "opens_same_day": "#8B5CF6",
            "no_due_date": "#9CA3AF",
        }
        return mapping.get(urgency_key, "#D1D5DB")