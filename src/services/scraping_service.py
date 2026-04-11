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
            raise RuntimeError("Canvas API connection worked, but no courses were returned.")

        filtered_courses = self._filter_current_term_courses(all_courses)
        if not filtered_courses:
            raise RuntimeError("No courses matched the detected current term.")

        return filtered_courses

    def get_assignments(self, courses: list[dict]) -> list[dict]:
        all_assignments: list[dict] = []

        for course in courses:
            course_id = course.get("course_id")
            course_name = course.get("course_name")
            course_url = course.get("course_url")

            if not course_id:
                continue

            assignments = self.canvas_api.get_assignments_for_course(
                course_id=course_id,
                course_name=course_name,
                course_url=course_url,
            )

            filtered_assignments = self._filter_actionable_assignments(assignments)
            all_assignments.extend(filtered_assignments)

        if not all_assignments:
            raise RuntimeError(
                "No actionable assignments were returned by Canvas API for the current term courses."
            )

        return all_assignments

    def _filter_current_term_courses(self, courses: list[dict]) -> list[dict]:
        tagged_courses: list[tuple[tuple[int, int], dict]] = []

        for course in courses:
            term_key = self._extract_term_key(course)
            if term_key is not None:
                tagged_courses.append((term_key, course))

        if not tagged_courses:
            raise RuntimeError(
                "Could not detect semester code from any course name/course code. "
                "Expected something like 12026-1900-032-B or 22026-1900-008-A."
            )

        latest_term = max(term_key for term_key, _ in tagged_courses)

        return [
            course
            for term_key, course in tagged_courses
            if term_key == latest_term
        ]

    def _extract_term_key(self, course: dict) -> Optional[tuple[int, int]]:
        candidates = [
            course.get("course_name") or "",
            course.get("course_code") or "",
        ]

        for text in candidates:
            match = self.TERM_PATTERN.search(text)
            if not match:
                continue

            semester_str = match.group(1)
            year_str = match.group(2)

            try:
                semester = int(semester_str)
                year = int(year_str)
                return (year, semester)
            except ValueError:
                continue

        return None

    def _filter_actionable_assignments(self, assignments: list[dict]) -> list[dict]:
        now = datetime.now(timezone.utc)
        results: list[dict] = []

        for assignment in assignments:
            assignment_name = (assignment.get("assignment_name") or "").strip()
            if self._should_exclude_assignment(assignment_name):
                continue

            published = bool(assignment.get("published"))
            due_at = self._parse_dt(assignment.get("due_date_iso"))
            unlock_at = self._parse_dt(assignment.get("unlock_at"))
            lock_at = self._parse_dt(assignment.get("lock_at"))
            score = assignment.get("score")
            submitted_at = assignment.get("submitted_at")

            if not published:
                continue

            if lock_at and lock_at <= now:
                continue

            if due_at and due_at <= now and not lock_at and not unlock_at:
                continue

            if unlock_at and unlock_at > now:
                assignment["status"] = "not_enabled_yet"
            elif due_at and due_at > now:
                assignment["status"] = "open"
            elif not due_at and not lock_at:
                assignment["status"] = "open_no_due_date"
            else:
                assignment["status"] = "open"

            assignment["is_submitted"] = bool(submitted_at)
            assignment["is_graded"] = score is not None

            results.append(assignment)

        return results

    def _should_exclude_assignment(self, assignment_name: str) -> bool:
        normalized = assignment_name.lower()
        return any(pattern in normalized for pattern in self.EXCLUDED_ASSIGNMENT_PATTERNS)

    def _parse_dt(self, value: str | None) -> Optional[datetime]:
        if not value:
            return None
        try:
            return date_parser.parse(value).astimezone(timezone.utc)
        except Exception:
            return None
