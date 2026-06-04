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

    def get_assignments(self, courses: list[dict]) -> list[dict]:
        all_assignments: list[dict] = []
        for course in courses:
            assignments = self.canvas_api.get_assignments_for_course(
                course_id=course["course_id"],
                course_name=course["course_name"],
                course_url=course["course_url"],
            )
            all_assignments.extend(self._filter_assignments(assignments))

        return all_assignments

    def _filter_current_term_courses(self, courses: list[dict]) -> list[dict]:
        tagged: list[tuple[tuple[int, int], dict]] = []
        for course in courses:
            key = self._extract_term_key(course)
            if key:
                tagged.append((key, course))

        latest = max(term_key for term_key, _ in tagged)
        return [course for term_key, course in tagged if term_key == latest]

    def _extract_term_key(self, course: dict) -> Optional[tuple[int, int]]:
        for text in [course.get("course_name") or "", course.get("course_code") or ""]:
            match = self.TERM_PATTERN.search(text)
            if match:
                return (int(match.group(2)), int(match.group(1)))
        return None

    def _filter_assignments(self, assignments: list[dict]) -> list[dict]:
        now = datetime.now(timezone.utc)
        results = []

        for a in assignments:
            name = (a.get("assignment_name") or "").lower()
            if any(p in name for p in self.EXCLUDED_ASSIGNMENT_PATTERNS):
                continue

            due_at = self._parse_dt(a.get("due_date_iso"))
            unlock_at = self._parse_dt(a.get("unlock_at"))
            lock_at = self._parse_dt(a.get("lock_at"))

            if not a.get("published"):
                continue
            if lock_at and lock_at <= now:
                continue

            if a.get("submitted_at"):
                a["status"] = "submitted"
            elif unlock_at and unlock_at > now:
                a["status"] = "not_enabled_yet"
            elif due_at and due_at > now:
                a["status"] = "open"
            elif not due_at and not lock_at:
                a["status"] = "open_no_due_date"
            else:
                a["status"] = "open"

            results.append(a)

        return results

    def _parse_dt(self, value: str | None):
        if not value:
            return None
        try:
            return date_parser.parse(value).astimezone(timezone.utc)
        except Exception:
            return None