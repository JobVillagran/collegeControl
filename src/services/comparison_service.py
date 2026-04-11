from __future__ import annotations

from datetime import datetime, timezone
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
        now = datetime.now(timezone.utc)
        results = []

        for assignment in assignments:
            enriched = self._enrich_assignment(assignment, now)
            if enriched is None:
                continue

            candidate_hours = enriched.get("hours_until_due")
            candidate_unlock_hours = enriched.get("hours_until_unlock")

            include = False

            if enriched.get("status") == "not_enabled_yet":
                if candidate_unlock_hours is not None and 0 <= candidate_unlock_hours <= (DAYS_AHEAD_WARNING * 24):
                    include = True
            elif enriched.get("status") in {"open", "open_no_due_date"}:
                if candidate_hours is None:
                    include = True
                elif 0 <= candidate_hours <= (DAYS_AHEAD_WARNING * 24):
                    include = True

            if include:
                results.append(enriched)

        results.sort(key=self._sort_key)
        return results

    def _enrich_assignment(self, assignment: dict, now: datetime) -> dict | None:
        enriched = dict(assignment)

        due_dt = self._parse_dt(assignment.get("due_date_iso"))
        unlock_dt = self._parse_dt(assignment.get("unlock_at"))

        hours_until_due = None
        if due_dt is not None:
            hours_until_due = (due_dt - now).total_seconds() / 3600

        hours_until_unlock = None
        if unlock_dt is not None:
            hours_until_unlock = (unlock_dt - now).total_seconds() / 3600

        enriched["hours_until_due"] = hours_until_due
        enriched["hours_until_unlock"] = hours_until_unlock

        if assignment.get("status") == "not_enabled_yet":
            urgency_key, urgency_label = self._classify_unlock_urgency(hours_until_unlock)
            enriched["urgency_key"] = urgency_key
            enriched["urgency_label"] = urgency_label
            enriched["action_required"] = "Wait until it opens"
            return enriched

        if assignment.get("status") == "open_no_due_date":
            enriched["urgency_key"] = "no_due_date"
            enriched["urgency_label"] = "No due date"
            enriched["action_required"] = "Review manually"
            return enriched

        if hours_until_due is None:
            return None

        if hours_until_due < 0:
            return None

        urgency_key, urgency_label = self._classify_due_urgency(hours_until_due)
        enriched["urgency_key"] = urgency_key
        enriched["urgency_label"] = urgency_label
        enriched["action_required"] = self._action_required_label(urgency_key)

        return enriched

    def _classify_due_urgency(self, hours_until_due: float) -> tuple[str, str]:
        if hours_until_due <= 6:
            return "act_now", "Act now"
        if hours_until_due <= 24:
            return "less_than_24h", "Less than 24h"
        if hours_until_due <= 72:
            return "two_to_three_days", "2–3 days"
        if hours_until_due <= 168:
            return "this_week", "This week"
        return "later", "Later"

    def _classify_unlock_urgency(self, hours_until_unlock: float | None) -> tuple[str, str]:
        if hours_until_unlock is None:
            return "not_enabled_yet", "Not enabled yet"
        if hours_until_unlock <= 24:
            return "opens_soon", "Opens soon"
        return "not_enabled_yet", "Not enabled yet"

    def _action_required_label(self, urgency_key: str) -> str:
        mapping = {
            "act_now": "Take action immediately",
            "less_than_24h": "Finish today",
            "two_to_three_days": "Plan it soon",
            "this_week": "Organize this week",
            "later": "Keep it in view",
        }
        return mapping.get(urgency_key, "Review soon")

    def _parse_dt(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return date_parser.parse(value).astimezone(timezone.utc)
        except Exception:
            return None

    def _sort_key(self, item: dict) -> tuple[int, float]:
        urgency_order = {
            "act_now": 0,
            "less_than_24h": 1,
            "two_to_three_days": 2,
            "this_week": 3,
            "opens_soon": 4,
            "not_enabled_yet": 5,
            "no_due_date": 6,
            "later": 7,
        }

        if item.get("status") == "not_enabled_yet":
            metric = item.get("hours_until_unlock")
        else:
            metric = item.get("hours_until_due")

        if metric is None:
            metric = 999999

        return (urgency_order.get(item.get("urgency_key"), 99), metric)