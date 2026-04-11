from __future__ import annotations

from playwright.sync_api import Page
from src.pages.dashboard_page import DashboardPage
from src.pages.assignments_page import AssignmentsPage
from src.parsers.date_parser import extract_due_date_iso
from config.constants import STATUS_CLOSED, STATUS_GRADED, STATUS_UPCOMING, STATUS_UNKNOWN

class ScrapingService:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.dashboard_page = DashboardPage(page)
        self.assignments_page = AssignmentsPage(page)

    def get_courses(self) -> list[dict]:
        courses = self.dashboard_page.get_courses()
        return [course.to_dict() for course in courses]

    def get_assignments(self, courses: list[dict]) -> list[dict]:
        all_assignments: list[dict] = []

        for course in courses:
            assignments = self.assignments_page.get_assignments_for_course(
                course_name=course["course_name"],
                course_url=course["course_url"],
            )

            for assignment in assignments:
                assignment.due_date_iso = extract_due_date_iso(assignment.due_date_raw)
                assignment.status = self._infer_status(
                    raw_due=assignment.due_date_raw,
                    raw_score=assignment.score,
                )
                all_assignments.append(assignment.to_dict())

        return all_assignments

    def _infer_status(self, raw_due: str | None, raw_score: str | None) -> str:
        blob = f"{raw_due or ''} {raw_score or ''}".lower()

        if "/" in blob and any(ch.isdigit() for ch in blob):
            return STATUS_GRADED

        if "closed" in blob or "cerrad" in blob or "past" in blob:
            return STATUS_CLOSED

        if "due" in blob or "entrega" in blob:
            return STATUS_UPCOMING

        return STATUS_UNKNOWN