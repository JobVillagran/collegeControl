from __future__ import annotations

import re
from typing import Optional

from src.services.canvas_api_service import CanvasAPIService


class ScrapingService:
    TERM_PATTERN = re.compile(r"\b([12])(\d{4})-\d{4}-\d{3}-[A-Z]\b")

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
            all_assignments.extend(assignments)

        if not all_assignments:
            raise RuntimeError("No assignments were returned by Canvas API for the current term courses.")

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

        filtered = [
            course
            for term_key, course in tagged_courses
            if term_key == latest_term
        ]

        return filtered

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