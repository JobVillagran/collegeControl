from __future__ import annotations

from urllib.parse import urljoin

import requests

from config.settings import CANVAS_BASE_URL, CANVAS_API_TOKEN


class CanvasAPIService:
    def __init__(self) -> None:
        self.base_url = CANVAS_BASE_URL.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {CANVAS_API_TOKEN}",
                "Accept": "application/json",
            }
        )

    def _build_url(self, path: str) -> str:
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    def _get(self, path: str, params: dict | None = None) -> list | dict:
        url = self._build_url(path)
        response = self.session.get(url, params=params, timeout=30)

        if response.status_code == 401:
            raise RuntimeError(
                "Canvas API returned 401 Unauthorized. The token is invalid, expired, or does not have access."
            )

        if response.status_code == 404:
            raise RuntimeError(
                f"Canvas API returned 404 Not Found for URL: {url}. "
                "Check that CANVAS_BASE_URL is the root Canvas domain only, for example: https://your-school.instructure.com"
            )

        response.raise_for_status()
        return response.json()

    def validate_connection(self) -> dict:
        return self._get("/api/v1/users/self")

    def get_courses(self) -> list[dict]:
        data = self._get(
            "/api/v1/courses",
            params={
                "enrollment_state": "active",
                "state[]": ["available", "completed", "unpublished"],
                "per_page": 100,
            },
        )

        courses: list[dict] = []
        for item in data:
            course_id = item.get("id")
            name = item.get("name")
            if not course_id or not name:
                continue

            courses.append(
                {
                    "course_id": str(course_id),
                    "course_name": name,
                    "course_url": f"{self.base_url}/courses/{course_id}",
                }
            )

        return courses

    def get_assignments_for_course(self, course_id: str, course_name: str, course_url: str) -> list[dict]:
        data = self._get(
            f"/api/v1/courses/{course_id}/assignments",
            params={
                "include[]": ["submission"],
                "order_by": "due_at",
                "per_page": 100,
            },
        )

        assignments: list[dict] = []

        for item in data:
            assignment_id = item.get("id")
            assignment_name = item.get("name")
            due_at = item.get("due_at")
            points_possible = item.get("points_possible")
            html_url = item.get("html_url")

            submission = item.get("submission") or {}
            score = submission.get("score")
            workflow_state = item.get("workflow_state")

            status = "unknown"
            if score is not None:
                status = "graded"
            elif due_at:
                status = "upcoming"
            elif workflow_state == "published":
                status = "published"

            assignments.append(
                {
                    "course_name": course_name,
                    "course_url": course_url,
                    "assignment_name": assignment_name or f"Assignment {assignment_id}",
                    "due_date_raw": due_at,
                    "due_date_iso": due_at,
                    "status": status,
                    "score": str(score) if score is not None else None,
                    "max_score": points_possible,
                    "assignment_url": html_url,
                }
            )

        return assignments