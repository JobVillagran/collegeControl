from __future__ import annotations

from datetime import datetime, timezone
from dateutil import parser as date_parser


class ComparisonService:
    def _parse_dt(self, value: str | None):
        if not value:
            return None
        try:
            return date_parser.parse(value).astimezone(timezone.utc)
        except Exception:
            return None

    def build_groups(self, assignments: list[dict]) -> dict:
        now = datetime.now(timezone.utc)

        groups = {
            "act_now": [],
            "this_week": [],
            "next_week": [],
            "third_week": [],
            "urgent_projects": [],
            "opens_soon": [],
            "submitted": [],
            "no_due_date": [],
        }

        for a in assignments:
            enriched = dict(a)
            due_dt = self._parse_dt(a.get("due_date_iso"))
            unlock_dt = self._parse_dt(a.get("unlock_at"))

            if a.get("status") == "submitted":
                groups["submitted"].append(enriched)
                continue

            if a.get("status") == "not_enabled_yet":
                groups["opens_soon"].append(enriched)
                continue

            if a.get("status") == "open_no_due_date":
                groups["no_due_date"].append(enriched)
                continue

            if due_dt is None:
                continue

            hours = (due_dt - now).total_seconds() / 3600
            enriched["hours_until_due"] = hours

            is_project = self._is_project(a.get("assignment_name"))

            if hours <= 48:
                groups["act_now"].append(enriched)
                if is_project:
                    groups["urgent_projects"].append(enriched)
            elif hours <= 168:
                groups["this_week"].append(enriched)
                if is_project:
                    groups["urgent_projects"].append(enriched)
            elif hours <= 336:
                groups["next_week"].append(enriched)
                if is_project:
                    groups["urgent_projects"].append(enriched)
            elif hours <= 504:
                groups["third_week"].append(enriched)

        return groups

    def _is_project(self, name: str | None) -> bool:
        if not name:
            return False
        name = name.lower()
        keywords = ["proyecto", "project", "entrega final", "plan de trabajo", "proposal", "propuesta"]
        return any(k in name for k in keywords)