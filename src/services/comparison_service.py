from __future__ import annotations

from datetime import datetime
from dateutil import parser as date_parser
from config.settings import DAYS_AHEAD_WARNING

class ComparisonService:
    def compare(self, previous_snapshot: dict, current_snapshot: dict) -> dict:
        previous_assignments = {
            f"{item['course_name']}::{item['assignment_name']}": item
            for item in previous_snapshot.get("assignments", [])
        }

        current_assignments = {
            f"{item['course_name']}::{item['assignment_name']}": item
            for item in current_snapshot.get("assignments", [])
        }

        new_assignments = []
        changed_assignments = []
        new_grades = []

        for key, current in current_assignments.items():
            previous = previous_assignments.get(key)

            if previous is None:
                new_assignments.append(current)
                continue

            if previous.get("due_date_iso") != current.get("due_date_iso"):
                changed_assignments.append(
                    {
                        "type": "due_date_changed",
                        "before": previous,
                        "after": current,
                    }
                )

            if previous.get("score") != current.get("score") and current.get("score"):
                new_grades.append(
                    {
                        "type": "new_grade",
                        "before": previous,
                        "after": current,
                    }
                )

        upcoming = self._get_upcoming(current_snapshot.get("assignments", []))

        return {
            "new_assignments": new_assignments,
            "changed_assignments": changed_assignments,
            "new_grades": new_grades,
            "upcoming_assignments": upcoming,
        }

    def _get_upcoming(self, assignments: list[dict]) -> list[dict]:
        now = datetime.now().astimezone()
        results = []

        for assignment in assignments:
            due_date_iso = assignment.get("due_date_iso")
            if not due_date_iso:
                continue

            try:
                due_dt = date_parser.parse(due_date_iso)
            except Exception:
                continue

            delta_days = (due_dt - now).total_seconds() / 86400
            if 0 <= delta_days <= DAYS_AHEAD_WARNING:
                results.append(assignment)

        results.sort(key=lambda item: item.get("due_date_iso") or "")
        return results