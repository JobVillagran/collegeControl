from __future__ import annotations

from src.services.canvas_api_service import CanvasAPIService


class ScrapingService:
    def __init__(self) -> None:
        self.canvas_api = CanvasAPIService()

    def get_courses(self) -> list[dict]:
        courses = self.canvas_api.get_courses()
        if not courses:
            raise RuntimeError("No courses were returned by Canvas API.")
        return courses

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
            raise RuntimeError("No assignments were returned by Canvas API.")
        return all_assignments
