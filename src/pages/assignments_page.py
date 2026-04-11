from __future__ import annotations

from src.pages.base_page import BasePage
from src.models.assignment import Assignment
from config.constants import STATUS_UNKNOWN

class AssignmentsPage(BasePage):
    def get_assignments_for_course(self, course_name: str, course_url: str) -> list[Assignment]:
        assignments_url = f"{course_url.rstrip('/')}/assignments"
        self.goto(assignments_url)

        items = self.page.locator("a").all()
        results: list[Assignment] = []
        seen: set[str] = set()

        for item in items:
            href = item.get_attribute("href") or ""
            title = (item.inner_text() or "").strip()

            if "/assignments/" not in href:
                continue

            if not title:
                continue

            key = f"{course_name}::{title}"
            if key in seen:
                continue
            seen.add(key)

            due_text = None
            score_text = None

            try:
                parent_text = item.locator("xpath=ancestor::*[self::li or self::div][1]").inner_text()
            except Exception:
                parent_text = title

            lower_parent = parent_text.lower()

            if "due" in lower_parent or "entrega" in lower_parent or "abr" in lower_parent or "mar" in lower_parent:
                due_text = parent_text

            if "/" in parent_text and any(char.isdigit() for char in parent_text):
                score_text = parent_text

            results.append(
                Assignment(
                    course_name=course_name,
                    course_url=course_url,
                    assignment_name=title,
                    due_date_raw=due_text,
                    due_date_iso=None,
                    status=STATUS_UNKNOWN,
                    score=score_text,
                    assignment_url=href,
                )
            )

        return results