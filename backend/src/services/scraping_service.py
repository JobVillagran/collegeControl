from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from dateutil import parser as date_parser

from src.services.canvas_api_service import CanvasAPIService


class ScrapingService:
    TERM_PATTERN = re.compile(r"\b([12])(\d{4})-\d{4}-\d{3}-[A-Z]\b")
    EXCLUDED_ASSIGNMENT_PATTERNS = [
        "roll call attendance",
        "asistencia",
        "attendance",
        "roll call",
    ]

    def __init__(self) -> None:
        self.canvas_api = CanvasAPIService()

    def get_courses(self) -> list[dict]:
        self.canvas_api.validate_connection()
        all_courses = self.canvas_api.get_courses()
        if not all_courses:
            raise RuntimeError("No courses returned by Canvas API.")

        filtered = self._filter_current_term_courses(all_courses)
        if not filtered:
            raise RuntimeError("No courses matched the current term.")

        return filtered

    def get_dashboard_assignments(self, courses: list[dict]) -> list[dict]:
        all_assignments: list[dict] = []

        for course in courses:
            assignments = self.canvas_api.get_assignments_for_course(
                course_id=course["course_id"],
                course_name=course["course_name"],
                course_url=course["course_url"],
            )
            normalized = [self._normalize_assignment_status(a) for a in assignments]
            all_assignments.extend(self._filter_dashboard_assignments(normalized))

        return all_assignments

    def get_course_progress_assignments(self, courses: list[dict]) -> dict[str, list[dict]]:
        assignments_by_course: dict[str, list[dict]] = {}

        for course in courses:
            assignments = self.canvas_api.get_assignments_for_course(
                course_id=course["course_id"],
                course_name=course["course_name"],
                course_url=course["course_url"],
            )
            normalized = [self._normalize_assignment_status(a) for a in assignments]
            progress_assignments = self._filter_progress_assignments(normalized)
            assignments_by_course[course["course_id"]] = progress_assignments

        return assignments_by_course

    def get_assignment_groups(self, courses: list[dict]) -> dict[str, list[dict]]:
        assignment_groups_by_course: dict[str, list[dict]] = {}

        for course in courses:
            assignment_groups_by_course[course["course_id"]] = self.canvas_api.get_assignment_groups_for_course(
                course_id=course["course_id"]
            )

        return assignment_groups_by_course

    def _filter_current_term_courses(self, courses: list[dict]) -> list[dict]:
        tagged: list[tuple[tuple[int, int], dict]] = []

        for course in courses:
            key = self._extract_term_key(course)
            if key:
                tagged.append((key, course))

        if not tagged:
            return []

        latest = max(term_key for term_key, _ in tagged)
        return [course for term_key, course in tagged if term_key == latest]

    def _extract_term_key(self, course: dict) -> Optional[tuple[int, int]]:
        for text in [course.get("course_name") or "", course.get("course_code") or ""]:
            match = self.TERM_PATTERN.search(text)
            if match:
                return (int(match.group(2)), int(match.group(1)))

        term = course.get("term") or {}
        term_name = term.get("name") or ""
        match = self.TERM_PATTERN.search(term_name)
        if match:
            return (int(match.group(2)), int(match.group(1)))

        return None

    def _normalize_assignment_status(self, assignment: dict) -> dict:
        now = datetime.now(timezone.utc)
        a = dict(assignment)

        name = (a.get("assignment_name") or "").lower()
        due_at = self._parse_dt(a.get("due_date_iso"))
        unlock_at = self._parse_dt(a.get("unlock_at"))
        lock_at = self._parse_dt(a.get("lock_at"))

        score = a.get("score")
        max_score = a.get("max_score")
        submitted_at = a.get("submitted_at")
        submission_state = (a.get("submission_workflow_state") or "").lower()
        missing = bool(a.get("missing"))
        late = bool(a.get("late"))
        published = bool(a.get("published", False))
        locked_for_user = bool(a.get("locked_for_user", False))

        a["is_excluded"] = any(pattern in name for pattern in self.EXCLUDED_ASSIGNMENT_PATTERNS)
        a["is_locked"] = bool(lock_at and lock_at <= now)
        a["is_future_locked"] = bool(unlock_at and unlock_at > now)
        a["is_due_future"] = bool(due_at and due_at > now)
        a["is_due_past"] = bool(due_at and due_at <= now)
        a["is_graded"] = score is not None and max_score is not None
        a["is_submitted"] = bool(submitted_at)
        a["is_submitted_pending"] = bool(
            submitted_at and score is None and submission_state not in {"unsubmitted", ""}
        )
        a["is_missing"] = bool(
            missing or (
                submission_state == "unsubmitted"
                and due_at
                and due_at <= now
                and not submitted_at
            )
        )
        a["is_late"] = late

        if not published:
            a["status"] = "hidden"
        elif a["is_missing"]:
            a["status"] = "missing"
        elif a["is_graded"]:
            a["status"] = "graded"
        elif a["is_submitted_pending"]:
            a["status"] = "submitted_pending"
        elif a["is_submitted"]:
            a["status"] = "submitted"
        elif a["is_future_locked"] or locked_for_user:
            a["status"] = "not_enabled_yet"
        elif a["is_due_future"]:
            a["status"] = "open"
        elif not due_at and not lock_at:
            a["status"] = "open_no_due_date"
        elif a["is_due_past"] and not a["is_submitted"] and not a["is_graded"]:
            a["status"] = "expired"
        elif a["is_locked"]:
            a["status"] = "closed"
        else:
            a["status"] = "open"

        return a

    def _filter_dashboard_assignments(self, assignments: list[dict]) -> list[dict]:
        now = datetime.now(timezone.utc)
        results = []

        for a in assignments:
            if a.get("is_excluded"):
                continue

            due_at = self._parse_dt(a.get("due_date_iso"))
            status = a.get("status")

            # Nunca mostrar en el dashboard operativo tareas cuya fecha ya pasó.
            if due_at and due_at <= now:
                continue

            # Nunca mostrar missing / faltante en paneles operativos.
            if status == "missing":
                continue

            if status in {
                "open",
                "not_enabled_yet",
                "submitted",
                "submitted_pending",
                "open_no_due_date",
            }:
                results.append(a)

        return results

    def _filter_progress_assignments(self, assignments: list[dict]) -> list[dict]:
        results = []

        for a in assignments:
            if a.get("is_excluded"):
                continue
            if a.get("status") == "hidden":
                continue
            results.append(a)

        return results

    def _parse_dt(self, value: str | None):
        if not value:
            return None
        try:
            return date_parser.parse(value).astimezone(timezone.utc)
        except Exception:
            return None