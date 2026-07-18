from __future__ import annotations

import html as html_lib
import json
import re
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import (
    CANVAS_API_TOKEN,
    CANVAS_BASE_URL,
    CANVAS_CONNECT_TIMEOUT_SECONDS,
    CANVAS_PROFILE_READ_TIMEOUT_SECONDS,
    CANVAS_READ_TIMEOUT_SECONDS,
)


class CanvasAPIService:
    def __init__(self) -> None:
        self.base_url = CANVAS_BASE_URL.rstrip("/")
        self.session = requests.Session()
        self._current_user_cache: dict | None = None
        self._current_user_id_cache: str | None = None
        self._current_user_name_cache: str | None = None

        retry_policy = Retry(
            total=2,
            connect=2,
            read=0,
            status=2,
            backoff_factor=0.35,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(
            max_retries=retry_policy,
            pool_connections=4,
            pool_maxsize=4,
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update(
            {
                "Authorization": f"Bearer {CANVAS_API_TOKEN}",
                "Accept": "application/json",
            }
        )
        self.request_timeout = (
            CANVAS_CONNECT_TIMEOUT_SECONDS,
            CANVAS_READ_TIMEOUT_SECONDS,
        )
        self.profile_timeout = (
            CANVAS_CONNECT_TIMEOUT_SECONDS,
            min(
                CANVAS_READ_TIMEOUT_SECONDS,
                CANVAS_PROFILE_READ_TIMEOUT_SECONDS,
            ),
        )

    def _build_url(self, path: str) -> str:
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    def _get(
        self,
        path: str,
        params: dict | None = None,
        *,
        timeout: tuple[int, int] | int | float | None = None,
    ) -> list | dict:
        url = self._build_url(path)
        response = self.session.get(
            url,
            params=params,
            timeout=timeout or self.request_timeout,
        )
        self._raise_canvas_errors(response, url)
        return response.json()

    def _get_text(self, path: str, params: dict | None = None) -> str:
        url = self._build_url(path)
        headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
        response = self.session.get(
            url,
            params=params,
            headers=headers,
            timeout=self.request_timeout,
        )
        self._raise_canvas_errors(response, url)
        return response.text

    def _get_paginated(self, path: str, params: dict | None = None) -> list[dict]:
        url = self._build_url(path)
        next_url: str | None = url
        next_params = dict(params or {})
        results: list[dict] = []

        while next_url:
            response = self.session.get(
                next_url,
                params=next_params,
                timeout=self.request_timeout,
            )
            self._raise_canvas_errors(response, next_url)
            data = response.json()

            if isinstance(data, list):
                results.extend(data)
            elif isinstance(data, dict):
                results.append(data)

            next_url = response.links.get("next", {}).get("url")
            next_params = None

        return results

    def _raise_canvas_errors(self, response: requests.Response, url: str) -> None:
        if response.status_code == 401:
            raise RuntimeError("Canvas returned 401 Unauthorized. Token/session invalid or expired.")

        if response.status_code == 404:
            raise RuntimeError(f"Canvas returned 404 for {url}. Check CANVAS_BASE_URL.")

        response.raise_for_status()


    def get_current_user_profile(self) -> dict:
        if self._current_user_cache is not None:
            return dict(self._current_user_cache)

        try:
            user = self.validate_connection(timeout=self.profile_timeout)
        except Exception:
            return {}

        if not isinstance(user, dict):
            return {}

        self._cache_current_user(user)
        return dict(self._current_user_cache or {})

    def get_current_user_id(self) -> str | None:
        if self._current_user_id_cache:
            return self._current_user_id_cache

        profile = self.get_current_user_profile()
        user_id = profile.get("id")
        if user_id:
            self._current_user_id_cache = str(user_id)
        return self._current_user_id_cache

    def get_current_user_name(self) -> str | None:
        if self._current_user_name_cache:
            return self._current_user_name_cache

        profile = self.get_current_user_profile()
        display_name = profile.get("name")
        if display_name:
            self._current_user_name_cache = str(display_name)
        return self._current_user_name_cache

    def get_assignment_submission_detail_grade(self, course_id: str, assignment_id: str) -> dict:
        """
        Some Canvas/External Tool quizzes are muted/unposted in the grades table and
        in the Assignments API, but the student's submission detail page renders the
        real result, e.g. "Resultados ... 5 De 10 puntos".

        This method fetches the submission detail page and extracts that visible
        score pair. It is intentionally conservative: it only returns a grade when
        it can read both score and max_score from the detail page.
        """
        candidates: list[str] = []
        current_user_id = self.get_current_user_id()
        if current_user_id:
            candidates.append(f"/courses/{course_id}/assignments/{assignment_id}/submissions/{current_user_id}")
        candidates.append(f"/courses/{course_id}/assignments/{assignment_id}")

        errors: list[str] = []
        for path in candidates:
            try:
                html = self._get_text(path)
                extracted = self._extract_submission_detail_score(html)
                if extracted:
                    return {
                        **extracted,
                        "assignment_id": str(assignment_id),
                        "source": "submission_detail_html",
                        "detail_url": self._build_url(path),
                    }
            except Exception as exc:
                errors.append(f"{path}: {exc}")

        return {
            "assignment_id": str(assignment_id),
            "source": "submission_detail_html",
            "score": None,
            "max_score": None,
            "error": " | ".join(errors) if errors else "No detail score found.",
        }

    def _extract_submission_detail_score(self, html: str) -> dict | None:
        if not html:
            return None

        decoded = html_lib.unescape(html)
        decoded = decoded.replace("\\u003c", "<").replace("\\u003e", ">")
        decoded = decoded.replace("\\u0026nbsp;", " ").replace("&nbsp;", " ")
        text = re.sub(r"<[^>]+>", " ", decoded)
        text = re.sub(r"\s+", " ", text).strip()

        result_index = text.lower().find("resultados")
        search_windows = []
        if result_index >= 0:
            search_windows.append(text[result_index : result_index + 1200])
        search_windows.append(text[:5000])
        search_windows.append(decoded[:10000])

        patterns = [
            r"(?i)resultados.{0,900}?(\d+(?:[\.,]\d+)?)\s*(?:de|/)\s*(\d+(?:[\.,]\d+)?)\s*puntos?",
            r"(?i)(\d+(?:[\.,]\d+)?)\s*(?:de|/)\s*(\d+(?:[\.,]\d+)?)\s*puntos?",
            r"(?i)score[^0-9]{0,40}(\d+(?:[\.,]\d+)?)[^0-9]{0,40}(?:out of|de|/)\s*(\d+(?:[\.,]\d+)?)",
        ]

        for window in search_windows:
            for pattern in patterns:
                match = re.search(pattern, window)
                if not match:
                    continue
                score = self._safe_float(str(match.group(1)).replace(",", "."))
                max_score = self._safe_float(str(match.group(2)).replace(",", "."))
                if score is None or max_score is None or max_score <= 0:
                    continue
                if score < 0 or score > max_score * 1.5:
                    continue
                return {
                    "score": score,
                    "entered_score": score,
                    "max_score": max_score,
                    "raw_match": match.group(0)[:180],
                }

        return None

    def validate_connection(
        self,
        *,
        timeout: tuple[int, int] | int | float | None = None,
    ) -> dict:
        user = self._get(
            "/api/v1/users/self",
            timeout=timeout,
        )
        if isinstance(user, dict):
            self._cache_current_user(user)
        return user

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "CanvasAPIService":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def _cache_current_user(self, user: dict) -> None:
        user_id = user.get("id")
        display_name = (
            user.get("name")
            or user.get("short_name")
            or user.get("sortable_name")
        )
        profile = {
            "id": str(user_id) if user_id is not None else None,
            "name": str(display_name).strip() if display_name else None,
        }
        self._current_user_cache = profile
        self._current_user_id_cache = profile.get("id")
        self._current_user_name_cache = profile.get("name")

    def get_courses(self) -> list[dict]:
        data = self._get_paginated(
            "/api/v1/courses",
            params={
                "enrollment_state": "active",
                "state[]": ["available", "completed", "unpublished"],
                "include[]": ["term", "total_scores"],
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

            student_enrollment = self._extract_student_enrollment(item.get("enrollments") or [])

            courses.append(
                {
                    "course_id": str(course_id),
                    "course_name": name,
                    "course_code": course_code,
                    "course_url": f"{self.base_url}/courses/{course_id}",
                    "workflow_state": item.get("workflow_state"),
                    "start_at": item.get("start_at"),
                    "end_at": item.get("end_at"),
                    "term": item.get("term") or {},
                    "current_score": self._safe_float(student_enrollment.get("computed_current_score")),
                    "final_score": self._safe_float(student_enrollment.get("computed_final_score")),
                    "current_grade": student_enrollment.get("computed_current_grade"),
                    "final_grade": student_enrollment.get("computed_final_grade"),
                    "has_grading_periods": item.get("has_grading_periods"),
                }
            )
        return courses

    def get_assignments_for_course(self, course_id: str, course_name: str, course_url: str) -> list[dict]:
        data = self._get_paginated(
            f"/api/v1/courses/{course_id}/assignments",
            params={
                "include[]": ["submission"],
                "order_by": "due_at",
                "per_page": 100,
            },
        )

        return [self._normalize_assignment_payload(course_id, course_name, course_url, item) for item in data]

    def get_assignment_detail_for_course(
        self,
        course_id: str,
        course_name: str,
        course_url: str,
        assignment_id: str,
    ) -> dict:
        item = self._get(
            f"/api/v1/courses/{course_id}/assignments/{assignment_id}",
            params={"include[]": ["submission"]},
        )
        return self._normalize_assignment_payload(course_id, course_name, course_url, item)

    def get_discussion_topics_for_course(
        self,
        course_id: str,
        course_name: str,
        course_url: str,
    ) -> list[dict]:
        data = self._get_paginated(
            f"/api/v1/courses/{course_id}/discussion_topics",
            params={
                "include_assignment": "true",
                "include[]": ["all_dates", "overrides"],
                "exclude_assignment_descriptions": "true",
                "plain_messages": "true",
                "per_page": 100,
            },
        )

        return [
            self._normalize_discussion_topic_payload(
                course_id=course_id,
                course_name=course_name,
                course_url=course_url,
                item=item,
            )
            for item in data
            if isinstance(item, dict)
        ]

    def get_discussion_topic_view(self, course_id: str, topic_id: str) -> dict:
        data = self._get(
            f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/view"
        )
        return data if isinstance(data, dict) else {}

    def get_grade_page_payload_for_course(self, course_id: str) -> dict:
        """
        Canvas sometimes hides/mutes grades in the normal assignments API while the
        student grades page still embeds the real submission score inside ENV.submissions.
        This method reads /courses/:id/grades and extracts that embedded ENV payload.

        If Canvas does not allow the API token to fetch the HTML page in a specific
        institution, this method returns an empty payload and the API path still works.
        """
        try:
            html = self._get_text(f"/courses/{course_id}/grades")
            env = self._extract_canvas_env(html)
            if not isinstance(env, dict):
                return self._empty_grade_page_payload()
            return self._normalize_grade_page_payload(env)
        except Exception as exc:
            return {
                **self._empty_grade_page_payload(),
                "available": False,
                "error": str(exc),
            }

    def _normalize_assignment_payload(self, course_id: str, course_name: str, course_url: str, item: dict) -> dict:
        submission = item.get("submission") or {}
        return {
            "course_id": str(course_id),
            "course_name": course_name,
            "course_url": course_url,
            "assignment_id": str(item.get("id")) if item.get("id") else None,
            "assignment_name": item.get("name") or "Untitled assignment",
            "assignment_url": item.get("html_url"),
            "assignment_group_id": str(item.get("assignment_group_id")) if item.get("assignment_group_id") else None,
            "due_date_iso": item.get("due_at"),
            "unlock_at": item.get("unlock_at"),
            "lock_at": item.get("lock_at"),
            "published": bool(item.get("published", False)),
            "locked_for_user": bool(item.get("locked_for_user", False)),
            "workflow_state": item.get("workflow_state"),
            "score": self._safe_float(submission.get("score")),
            "entered_score": self._safe_float(submission.get("entered_score")),
            "grade": submission.get("grade"),
            "entered_grade": submission.get("entered_grade"),
            "max_score": self._safe_float(item.get("points_possible")),
            "submitted_at": submission.get("submitted_at"),
            "submission_workflow_state": submission.get("workflow_state"),
            "missing": submission.get("missing"),
            "late": submission.get("late"),
            "excused": submission.get("excused"),
            "muted": bool(item.get("muted", False)),
            "omit_from_final_grade": bool(item.get("omit_from_final_grade", False)),
            "status": "unknown",
        }

    def _normalize_discussion_topic_payload(
        self,
        course_id: str,
        course_name: str,
        course_url: str,
        item: dict,
    ) -> dict:
        assignment = item.get("assignment") or {}
        discussion_id = item.get("id")
        assignment_id = item.get("assignment_id") or assignment.get("id")
        unread_count = item.get("unread_count")
        reply_count = item.get("discussion_subentry_count")

        try:
            normalized_unread_count = max(0, int(unread_count or 0))
        except (TypeError, ValueError):
            normalized_unread_count = 0

        try:
            normalized_reply_count = max(0, int(reply_count or 0))
        except (TypeError, ValueError):
            normalized_reply_count = 0

        discussion_url = item.get("html_url")
        if not discussion_url and discussion_id is not None:
            discussion_url = (
                f"{self.base_url}/courses/{course_id}/discussion_topics/{discussion_id}"
            )

        return {
            "course_id": str(course_id),
            "course_name": course_name,
            "course_url": course_url,
            "discussion_id": str(discussion_id) if discussion_id is not None else None,
            "discussion_title": item.get("title") or "Untitled discussion",
            "discussion_url": discussion_url,
            "assignment_id": str(assignment_id) if assignment_id is not None else None,
            "due_date_iso": assignment.get("due_at") or item.get("lock_at"),
            "unlock_at": assignment.get("unlock_at") or item.get("delayed_post_at"),
            "lock_at": assignment.get("lock_at") or item.get("lock_at"),
            "posted_at": item.get("posted_at"),
            "last_reply_at": item.get("last_reply_at"),
            "published": bool(item.get("published", False)),
            "locked": bool(item.get("locked", False)),
            "locked_for_user": bool(item.get("locked_for_user", False)),
            "lock_explanation": item.get("lock_explanation"),
            "read_state": item.get("read_state") or "read",
            "unread_count": normalized_unread_count,
            "reply_count": normalized_reply_count,
            "require_initial_post": bool(item.get("require_initial_post", False)),
            "user_can_see_posts": item.get("user_can_see_posts"),
            "pinned": bool(item.get("pinned", False)),
            "is_announcement": bool(item.get("is_announcement", False)),
            "discussion_type": item.get("discussion_type"),
            "group_category_id": (
                str(item.get("group_category_id"))
                if item.get("group_category_id") is not None
                else None
            ),
            "root_topic_id": (
                str(item.get("root_topic_id"))
                if item.get("root_topic_id") is not None
                else None
            ),
            "group_topic_children": item.get("group_topic_children") or [],
            "points_possible": self._safe_float(assignment.get("points_possible")),
            "assignment_published": bool(assignment.get("published", False)),
            "assignment_workflow_state": assignment.get("workflow_state"),
            "assignment_has_submitted_submissions": bool(
                assignment.get("has_submitted_submissions", False)
            ),
            "submission_types": assignment.get("submission_types") or [],
            "status": "unknown",
            "item_type": "discussion",
            "is_discussion": True,
        }

    def get_assignment_groups_for_course(self, course_id: str) -> list[dict]:
        data = self._get_paginated(
            f"/api/v1/courses/{course_id}/assignment_groups",
            params={"per_page": 100},
        )

        groups: list[dict] = []
        for item in data:
            groups.append(
                {
                    "group_id": str(item.get("id")) if item.get("id") else None,
                    "name": item.get("name") or "Unnamed group",
                    "group_weight": self._safe_float(item.get("group_weight")) or 0.0,
                    "rules": item.get("rules") or {},
                }
            )
        return groups

    def _extract_canvas_env(self, html: str) -> dict | None:
        marker = "ENV ="
        start = html.find(marker)
        if start == -1:
            marker = "ENV="
            start = html.find(marker)
        if start == -1:
            return None

        brace_start = html.find("{", start)
        if brace_start == -1:
            return None

        brace_count = 0
        in_string = False
        quote = ""
        escaped = False

        for index in range(brace_start, len(html)):
            char = html[index]

            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    in_string = False
                continue

            if char in {'"', "'"}:
                in_string = True
                quote = char
                continue

            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    raw_json = html[brace_start : index + 1]
                    try:
                        return json.loads(raw_json)
                    except json.JSONDecodeError:
                        return None

        return None

    def _normalize_grade_page_payload(self, env: dict) -> dict:
        submissions_by_assignment_id: dict[str, dict] = {}
        for submission in env.get("submissions") or []:
            assignment_id = submission.get("assignment_id")
            if assignment_id is None:
                continue
            assignment_id = str(assignment_id)
            submissions_by_assignment_id[assignment_id] = {
                "assignment_id": assignment_id,
                "score": self._safe_float(submission.get("score")),
                "entered_score": self._safe_float(submission.get("entered_score")),
                "grade": submission.get("grade"),
                "entered_grade": submission.get("entered_grade"),
                "workflow_state": submission.get("workflow_state"),
                "submission_type": submission.get("submission_type"),
                "excused": submission.get("excused"),
                "assignment_url": submission.get("assignment_url"),
                "source": "grade_page_env_submissions",
            }

        assignments_by_id: dict[str, dict] = {}
        normalized_groups: list[dict] = []
        for group in env.get("assignment_groups") or []:
            group_id = str(group.get("id")) if group.get("id") is not None else None
            normalized_groups.append(
                {
                    "group_id": group_id,
                    "name": group.get("name") or "Unnamed group",
                    "group_weight": self._safe_float(group.get("group_weight")) or 0.0,
                    "rules": group.get("rules") or {},
                }
            )
            for assignment in group.get("assignments") or []:
                assignment_id = assignment.get("id")
                if assignment_id is None:
                    continue
                assignment_id = str(assignment_id)
                assignments_by_id[assignment_id] = {
                    "assignment_id": assignment_id,
                    "assignment_group_id": group_id,
                    "max_score": self._safe_float(assignment.get("points_possible")),
                    "due_date_iso": assignment.get("due_at"),
                    "muted": bool(assignment.get("muted", False)),
                    "omit_from_final_grade": bool(assignment.get("omit_from_final_grade", False)),
                    "submission_types": assignment.get("submission_types") or [],
                    "source": "grade_page_env_assignment_groups",
                }

        return {
            "available": True,
            "submissions_by_assignment_id": submissions_by_assignment_id,
            "assignments_by_id": assignments_by_id,
            "assignment_groups": normalized_groups,
            "group_weighting_scheme": env.get("group_weighting_scheme"),
            "show_total_grade_as_points": env.get("show_total_grade_as_points"),
            "hide_final_grades": env.get("hide_final_grades"),
            "current_user_id": str(env.get("current_user_id")) if env.get("current_user_id") is not None else None,
        }

    def _empty_grade_page_payload(self) -> dict:
        return {
            "available": False,
            "submissions_by_assignment_id": {},
            "assignments_by_id": {},
            "assignment_groups": [],
        }

    def _extract_student_enrollment(self, enrollments: list[dict]) -> dict:
        for enrollment in enrollments:
            enrollment_type = (enrollment.get("type") or "").lower()
            role = (enrollment.get("role") or "").lower()

            if "student" in enrollment_type or "student" in role:
                return enrollment

        return enrollments[0] if enrollments else {}

    def _safe_float(self, value):
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None
