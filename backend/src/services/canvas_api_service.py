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
            raise RuntimeError("Canvas API returned 401 Unauthorized. Token invalid or expired.")

        if response.status_code == 404:
            raise RuntimeError(
                f"Canvas API returned 404 for {url}. Check CANVAS_BASE_URL."
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
            course_code = item.get("course_code")
            if not course_id or not name:
                continue

            courses.append(
                {
                    "course_id": str(course_id),
                    "course_name": name,
                    "course_code": course_code,
                    "course_url": f"{self.base_url}/courses/{course_id}",
                    "workflow_state": item.get("workflow_state"),
                    "start_at": item.get("start_at"),
                    "end_at": item.get("end_at"),
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
            submission = item.get("submission") or {}

            assignments.append(
                {
                    "course_id": str(course_id),
                    "course_name": course_name,
                    "course_url": course_url,
                    "assignment_id": str(item.get("id")) if item.get("id") else None,
                    "assignment_name": item.get("name") or "Untitled assignment",
                    "assignment_url": item.get("html_url"),
                    "due_date_iso": item.get("due_at"),
                    "unlock_at": item.get("unlock_at"),
                    "lock_at": item.get("lock_at"),
                    "published": bool(item.get("published", False)),
                    "locked_for_user": bool(item.get("locked_for_user", False)),
                    "workflow_state": item.get("workflow_state"),
                    "score": submission.get("score"),
                    "max_score": item.get("points_possible"),
                    "submitted_at": submission.get("submitted_at"),
                    "submission_workflow_state": submission.get("workflow_state"),
                    "missing": submission.get("missing"),
                    "late": submission.get("late"),
                    "excused": submission.get("excused"),
                    "status": "unknown",
                }
            )

        return assignments