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
        upcoming = changes.get("upcoming_assignments", [])

        open_assignments = [item for item in upcoming if item.get("status") in {"open", "open_no_due_date"}]
        not_enabled_yet = [item for item in upcoming if item.get("status") == "not_enabled_yet"]

        act_now = [self._decorate_card(item) for item in open_assignments if item.get("urgency_key") == "act_now"]
        less_than_24h = [self._decorate_card(item) for item in open_assignments if item.get("urgency_key") == "less_than_24h"]
        two_to_three_days = [self._decorate_card(item) for item in open_assignments if item.get("urgency_key") == "two_to_three_days"]
        this_week = [self._decorate_card(item) for item in open_assignments if item.get("urgency_key") == "this_week"]
        no_due_date = [self._decorate_card(item) for item in open_assignments if item.get("urgency_key") == "no_due_date"]
        opens_later = [self._decorate_card(item) for item in not_enabled_yet]

        new_grades = [self._decorate_grade_card(item) for item in changes.get("new_grades", [])]
        changed_assignments = [self._decorate_changed_card(item) for item in changes.get("changed_assignments", [])]
        new_assignments = [self._decorate_card(item) for item in changes.get("new_assignments", [])]

        total_actionable = len(open_assignments)
        total_urgent = len(act_now) + len(less_than_24h)

        return {
            "generated_at": self._format_now(),
            "summary_stats": {
                "total_actionable": total_actionable,
                "total_urgent": total_urgent,
                "not_enabled_yet": len(opens_later),
                "new_grades": len(new_grades),
            },
            "sections": {
                "act_now": act_now,
                "less_than_24h": less_than_24h,
                "two_to_three_days": two_to_three_days,
                "this_week": this_week,
                "no_due_date": no_due_date,
                "not_enabled_yet": opens_later,
                "new_assignments": new_assignments,
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

        lines.append("University Summary")
        lines.append(f"Generated at: {payload['generated_at']}")
        lines.append("")

        lines.append("Act now:")
        lines.extend(self._section_lines(sections["act_now"]))

        lines.append("")
        lines.append("Less than 24h:")
        lines.extend(self._section_lines(sections["less_than_24h"]))

        lines.append("")
        lines.append("2–3 days:")
        lines.extend(self._section_lines(sections["two_to_three_days"]))

        lines.append("")
        lines.append("This week:")
        lines.extend(self._section_lines(sections["this_week"]))

        lines.append("")
        lines.append("Not enabled yet:")
        lines.extend(self._section_lines(sections["not_enabled_yet"], use_unlock=True))

        lines.append("")
        lines.append("No due date:")
        lines.extend(self._section_lines(sections["no_due_date"]))

        lines.append("")
        lines.append("New grades:")
        if sections["new_grades"]:
            for item in sections["new_grades"]:
                lines.append(f"- {item['course_name']} | {item['assignment_name']} | Score: {item['score_display']}")
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
            if use_unlock:
                lines.append(
                    f"- {item['course_name']} | {item['assignment_name']} | Opens: {item.get('unlock_display', 'N/A')}"
                )
            else:
                lines.append(
                    f"- {item['course_name']} | {item['assignment_name']} | Due: {item.get('due_display', 'N/A')} | {item.get('relative_time', '')}"
                )
        return lines

    def _decorate_card(self, item: dict) -> dict:
        due_display = self._format_iso(item.get("due_date_iso"))
        unlock_display = self._format_iso(item.get("unlock_at"))

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
            "less_than_24h": "#FFEDD5",
            "two_to_three_days": "#FEF3C7",
            "this_week": "#DBEAFE",
            "not_enabled_yet": "#E0E7FF",
            "opens_soon": "#E0E7FF",
            "no_due_date": "#E5E7EB",
        }
        return mapping.get(urgency_key, "#E5E7EB")

    def _badge_color(self, urgency_key: str | None) -> str:
        mapping = {
            "act_now": "#B91C1C",
            "less_than_24h": "#C2410C",
            "two_to_three_days": "#A16207",
            "this_week": "#1D4ED8",
            "not_enabled_yet": "#4338CA",
            "opens_soon": "#4338CA",
            "no_due_date": "#374151",
        }
        return mapping.get(urgency_key, "#374151")

    def _border_color(self, urgency_key: str | None) -> str:
        mapping = {
            "act_now": "#EF4444",
            "less_than_24h": "#F97316",
            "two_to_three_days": "#F59E0B",
            "this_week": "#3B82F6",
            "not_enabled_yet": "#6366F1",
            "opens_soon": "#6366F1",
            "no_due_date": "#9CA3AF",
        }
        return mapping.get(urgency_key, "#D1D5DB")