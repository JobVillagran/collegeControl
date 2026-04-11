from __future__ import annotations

from jinja2 import Environment, FileSystemLoader

from config.settings import (
    TEMPLATES_DIR,
    SUMMARY_HTML_FILE,
    SUMMARY_PAYLOAD_FILE,
    SUMMARY_TXT_FILE,
)
from src.utils.file_utils import write_json, write_text


class SummaryService:
    def build_payload(self, changes: dict) -> dict:
        upcoming = changes.get("upcoming_assignments", [])

        open_now = [item for item in upcoming if item.get("status") in {"open", "open_no_due_date"}]
        not_enabled_yet = [item for item in upcoming if item.get("status") == "not_enabled_yet"]

        return {
            "new_assignments": changes.get("new_assignments", []),
            "changed_assignments": changes.get("changed_assignments", []),
            "new_grades": changes.get("new_grades", []),
            "upcoming_assignments": upcoming,
            "open_assignments": open_now,
            "not_enabled_yet_assignments": not_enabled_yet,
        }

    def render_html(self, payload: dict) -> str:
        env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
        template = env.get_template("summary_template.html")
        return template.render(payload=payload)

    def render_text(self, payload: dict) -> str:
        lines: list[str] = []
        lines.append("University Summary")
        lines.append("")

        lines.append("Open Assignments:")
        if payload["open_assignments"]:
            for item in payload["open_assignments"]:
                lines.append(
                    f"- {item['course_name']} | {item['assignment_name']} | Due: {item.get('due_date_iso')}"
                )
        else:
            lines.append("- None")

        lines.append("")
        lines.append("Not Enabled Yet:")
        if payload["not_enabled_yet_assignments"]:
            for item in payload["not_enabled_yet_assignments"]:
                lines.append(
                    f"- {item['course_name']} | {item['assignment_name']} | Unlocks: {item.get('unlock_at')}"
                )
        else:
            lines.append("- None")

        lines.append("")
        lines.append("New Grades:")
        if payload["new_grades"]:
            for item in payload["new_grades"]:
                lines.append(
                    f"- {item['after']['course_name']} | {item['after']['assignment_name']}"
                )
        else:
            lines.append("- None")

        return "\n".join(lines)

    def save_outputs(self, payload: dict, html: str, text: str) -> None:
        write_json(SUMMARY_PAYLOAD_FILE, payload)
        write_text(SUMMARY_HTML_FILE, html)
        write_text(SUMMARY_TXT_FILE, text)