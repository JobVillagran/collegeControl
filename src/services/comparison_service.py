from __future__ import annotations

from datetime import datetime, timezone
from dateutil import parser as date_parser


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

        actionable = self._build_actionable_groups(current_snapshot.get("assignments", []))

        return {
            "new_assignments": new_assignments,
            "changed_assignments": changed_assignments,
            "new_grades": new_grades,
            "actionable_groups": actionable,
        }

    def _build_actionable_groups(self, assignments: list[dict]) -> dict:
        now = datetime.now(timezone.utc)

        groups = {
            "act_now": [],
            "this_week": [],
            "next_week": [],
            "third_week": [],
            "urgent_projects": [],
            "opens_same_day": [],
            "no_due_date": [],
        }

        for assignment in assignments:
            enriched = self._enrich_assignment(assignment, now)
            if enriched is None:
                continue

            status = enriched.get("status")
            urgency = enriched.get("urgency_key")
            is_project = enriched.get("is_project", False)

            if status == "not_enabled_yet":
                groups["opens_same_day"].append(enriched)
                continue

            if urgency == "act_now":
                groups["act_now"].append(enriched)
            elif urgency == "this_week":
                groups["this_week"].append(enriched)
            elif urgency == "next_week":
                groups["next_week"].append(enriched)
            elif urgency == "third_week":
                groups["third_week"].append(enriched)
            elif urgency == "no_due_date":
                groups["no_due_date"].append(enriched)

            if is_project and urgency in {"act_now", "this_week", "next_week"}:
                groups["urgent_projects"].append(enriched)

        for key in groups:
            groups[key].sort(key=self._sort_key)

        return groups

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
        enriched["is_project"] = self._is_project(assignment.get("assignment_name"))

        if assignment.get("status") == "not_enabled_yet":
            if hours_until_unlock is None:
                return None

            if hours_until_unlock < 0 or hours_until_unlock > (24 * 7):
                return None

            enriched["urgency_key"] = "opens_same_day"
            enriched["urgency_label"] = "Opens soon"
            enriched["action_required"] = "Be ready when it opens"
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
        if urgency_key == "later":
            return None

        enriched["urgency_key"] = urgency_key
        enriched["urgency_label"] = urgency_label
        enriched["action_required"] = self._action_required_label(urgency_key)

        return enriched

    def _classify_due_urgency(self, hours_until_due: float) -> tuple[str, str]:
        if hours_until_due <= 6:
            return "act_now", "Act now"
        if hours_until_due <= 48:
            return "act_now", "1–2 days"
        if hours_until_due <= 168:
            return "this_week", "This week"
        if hours_until_due <= 336:
            return "next_week", "Next week"
        if hours_until_due <= 504:
            return "third_week", "Third week"
        return "later", "Later"

    def _action_required_label(self, urgency_key: str) -> str:
        mapping = {
            "act_now": "Take action as soon as possible",
            "this_week": "Plan and start this week",
            "next_week": "Prepare next week",
            "third_week": "Keep it on your radar",
            "no_due_date": "Review manually",
        }
        return mapping.get(urgency_key, "Review soon")

    def _is_project(self, assignment_name: str | None) -> bool:
        if not assignment_name:
            return False

        normalized = assignment_name.lower()
        keywords = [
            "proyecto",
            "project",
            "entrega final",
            "final delivery",
            "plan de trabajo",
            "proposal",
            "propuesta",
        ]
        return any(keyword in normalized for keyword in keywords)

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
            "this_week": 1,
            "next_week": 2,
            "third_week": 3,
            "opens_same_day": 4,
            "no_due_date": 5,
        }

        if item.get("status") == "not_enabled_yet":
            metric = item.get("hours_until_unlock")
        else:
            metric = item.get("hours_until_due")

        if metric is None:
            metric = 999999

        return (urgency_order.get(item.get("urgency_key"), 99), metric)
