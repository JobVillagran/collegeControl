from __future__ import annotations

from src.pages.base_page import BasePage
from src.models.course import Course

class DashboardPage(BasePage):
    def get_courses(self) -> list[Course]:
        links = self.page.locator("a").all()
        courses: list[Course] = []
        seen_urls: set[str] = set()

        for link in links:
            href = link.get_attribute("href") or ""
            text = (link.inner_text() or "").strip()

            if "/courses/" not in href:
                continue

            if not text:
                continue

            if href in seen_urls:
                continue

            seen_urls.add(href)
            course_id = href.rstrip("/").split("/")[-1] if href.rstrip("/").split("/")[-1].isdigit() else None
            courses.append(
                Course(
                    course_name=text,
                    course_url=href,
                    course_id=course_id,
                )
            )

        return courses