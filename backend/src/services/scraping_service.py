from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from dateutil import parser as date_parser

from src.services.canvas_api_service import CanvasAPIService


class ScrapingService:
    # Canvas course identifiers are not completely uniform. Both of these
    # examples belong to the same semester:
    #   22026-1900-040-A
    #   22026-090-037-3
    # The middle campus/program block may contain three or four digits and
    # the section may be either a letter or a number.
    TERM_PATTERN = re.compile(
        r"\b([12])(\d{4})-\d{3,4}-\d{3}-[A-Z0-9]\b",
        re.IGNORECASE,
    )
    COMPACT_TERM_PATTERN = re.compile(
        r"\b([12])(\d{4})\d{3,4}\d{3}[A-Z0-9]\b",
        re.IGNORECASE,
    )
    ATTENDANCE_PATTERNS = [
        "roll call attendance",
        "asistencia",
        "attendance",
        "roll call",
    ]

    def __init__(self, canvas_api: CanvasAPIService | None = None) -> None:
        self.canvas_api = canvas_api or CanvasAPIService()
        self.last_discussion_errors: dict[str, str] = {}

    def close(self) -> None:
        close = getattr(self.canvas_api, "close", None)
        if callable(close):
            close()

    def get_courses(self) -> list[dict]:
        # Do not perform a separate /users/self request before /courses.
        # The courses request already validates the token and connectivity.
        # Removing the duplicate call reduces cold-start latency and avoids
        # failing the entire refresh before course discovery begins.
        all_courses = self.canvas_api.get_courses()
        if not all_courses:
            raise RuntimeError("No courses returned by Canvas API.")

        filtered = self._filter_current_term_courses(all_courses)
        if not filtered:
            raise RuntimeError("No courses matched the current term.")

        return filtered

    def get_assignments_for_course(
        self,
        course: dict,
        *,
        grade_page_payload: dict | None = None,
    ) -> list[dict]:
        """Load and normalize one course without sharing mutable worker state."""
        if grade_page_payload is None:
            grade_page_payload = self.canvas_api.get_grade_page_payload_for_course(
                course_id=course["course_id"]
            )

        raw_assignments = self.canvas_api.get_assignments_for_course(
            course_id=course["course_id"],
            course_name=course["course_name"],
            course_url=course["course_url"],
        )
        normalized: list[dict] = []

        for assignment in raw_assignments:
            assignment = self._merge_grade_page_data(
                assignment,
                grade_page_payload,
            )
            item = self._normalize_assignment_status(assignment)

            if self._should_deep_check(item):
                try:
                    detail = self.canvas_api.get_assignment_detail_for_course(
                        course_id=course["course_id"],
                        course_name=course["course_name"],
                        course_url=course["course_url"],
                        assignment_id=item["assignment_id"],
                    )
                    detail = self._merge_grade_page_data(
                        detail,
                        grade_page_payload,
                    )
                    detail = self._normalize_assignment_status(detail)
                    detail["detail_checked"] = True
                    item = detail
                except Exception as exc:
                    item["detail_checked"] = False
                    item["detail_check_error"] = str(exc)

                if item.get("score") is None and item.get("max_score") is not None:
                    item = self._recover_grade_from_submission_detail(course, item)

            normalized.append(item)

        return normalized

    def get_assignments_by_course(
        self,
        courses: list[dict],
    ) -> dict[str, list[dict]]:
        return {
            str(course["course_id"]): self.get_assignments_for_course(course)
            for course in courses
        }

    def get_discussions_for_course(
        self,
        course: dict,
        assignments: list[dict],
        *,
        current_user: dict | None = None,
    ) -> list[dict]:
        current_user = (
            self.canvas_api.get_current_user_profile()
            if current_user is None
            else current_user
        )
        current_user_id = current_user.get("id")
        current_user_name = current_user.get("name")
        course_id = str(course["course_id"])
        assignments_by_id = {
            str(item.get("assignment_id")): item
            for item in assignments
            if item.get("assignment_id") is not None
        }

        raw_topics = self.canvas_api.get_discussion_topics_for_course(
            course_id=course_id,
            course_name=course["course_name"],
            course_url=course["course_url"],
        )

        normalized_topics: list[dict] = []
        for topic in raw_topics:
            assignment = assignments_by_id.get(str(topic.get("assignment_id")))
            item = self._normalize_discussion_status(
                topic=topic,
                assignment=assignment,
                current_user_id=current_user_id,
                current_user_name=current_user_name,
            )

            if assignment is not None:
                self._attach_discussion_metadata_to_assignment(assignment, item)

            normalized_topics.append(item)

        return normalized_topics

    def get_discussions_by_course(
        self,
        courses: list[dict],
        assignments_by_course: dict[str, list[dict]] | None = None,
    ) -> dict[str, list[dict]]:
        discussions_by_course: dict[str, list[dict]] = {}
        assignments_by_course = assignments_by_course or {}
        current_user = self.canvas_api.get_current_user_profile()
        self.last_discussion_errors = {}

        for course in courses:
            course_id = str(course["course_id"])
            try:
                discussions_by_course[course_id] = self.get_discussions_for_course(
                    course,
                    assignments_by_course.get(course_id, []),
                    current_user=current_user,
                )
            except Exception as exc:
                self.last_discussion_errors[course_id] = str(exc)
                discussions_by_course[course_id] = []

        return discussions_by_course

    def collect_course_data(
        self,
        course: dict,
        *,
        current_user: dict | None = None,
    ) -> dict:
        """Fetch all expensive data for one course using one grade-page read."""
        course_id = str(course["course_id"])
        grade_page_payload = self.canvas_api.get_grade_page_payload_for_course(
            course_id=course_id
        )
        assignments = self.get_assignments_for_course(
            course,
            grade_page_payload=grade_page_payload,
        )

        discussion_error: str | None = None
        try:
            discussions = self.get_discussions_for_course(
                course,
                assignments,
                current_user=current_user,
            )
        except Exception as exc:
            discussion_error = str(exc)
            discussions = []

        assignment_groups = self.get_assignment_groups_for_course(
            course,
            grade_page_payload=grade_page_payload,
        )

        return {
            "course_id": course_id,
            "assignments": assignments,
            "discussions": discussions,
            "assignment_groups": assignment_groups,
            "discussion_error": discussion_error,
            "grade_page_available": bool(grade_page_payload.get("available")),
        }

    def _normalize_discussion_status(
        self,
        topic: dict,
        assignment: dict | None,
        current_user_id: str | None,
        current_user_name: str | None,
    ) -> dict:
        now = datetime.now(timezone.utc)
        item = dict(topic)

        item["assignment_name"] = item.get("discussion_title")
        item["assignment_url"] = item.get("discussion_url")
        item["is_graded_discussion"] = bool(
            assignment is not None or item.get("assignment_id")
        )
        item["requires_post"] = bool(
            item.get("published") and not item.get("is_announcement")
        )
        item["participation_checked"] = False
        item["participation_check_error"] = None
        item["participation_source"] = None
        item["user_has_posted"] = False
        item["own_entry_id"] = None
        item["own_posted_at"] = None
        item["own_author_name"] = None

        if assignment is not None:
            item["due_date_iso"] = (
                assignment.get("due_date_iso") or item.get("due_date_iso")
            )
            item["unlock_at"] = assignment.get("unlock_at") or item.get("unlock_at")
            item["lock_at"] = assignment.get("lock_at") or item.get("lock_at")
            item["points_possible"] = assignment.get("max_score")

        assignment_proves_submission = bool(
            assignment
            and (
                assignment.get("is_submitted")
                or assignment.get("is_submitted_pending")
                or assignment.get("submitted_at")
            )
        )

        if assignment_proves_submission:
            item["user_has_posted"] = True
            item["participation_checked"] = True
            item["participation_source"] = "assignment_submission"
            item["own_posted_at"] = assignment.get("submitted_at")
        elif item.get("requires_post"):
            if not current_user_id and not current_user_name:
                item["participation_check_error"] = (
                    "Canvas current user could not be identified."
                )
            else:
                try:
                    view = self.canvas_api.get_discussion_topic_view(
                        course_id=str(item["course_id"]),
                        topic_id=str(item["discussion_id"]),
                    )
                    evidence = self._find_user_discussion_entry(
                        payload=view,
                        user_id=current_user_id,
                        user_name=current_user_name,
                    )
                    item["participation_checked"] = True

                    if evidence:
                        item["user_has_posted"] = True
                        item["participation_source"] = evidence.get("source")
                        item["own_entry_id"] = evidence.get("entry_id")
                        item["own_posted_at"] = evidence.get("posted_at")
                        item["own_author_name"] = evidence.get("author_name")
                except Exception as exc:
                    item["participation_check_error"] = str(exc)

        unlock_at = self._parse_dt(item.get("unlock_at"))
        lock_at = self._parse_dt(item.get("lock_at"))
        due_at = self._parse_dt(item.get("due_date_iso"))
        unread_count = int(item.get("unread_count") or 0)
        read_state = str(item.get("read_state") or "read").lower()
        has_unread_activity = unread_count > 0 or read_state == "unread"
        assignment_status = str((assignment or {}).get("status") or "").lower()

        if not item.get("published"):
            status = "hidden"
        elif item.get("is_announcement"):
            status = "info"
        elif unlock_at and unlock_at > now:
            status = "not_enabled_yet"
        elif assignment_status == "not_enabled_yet" and not item.get("user_has_posted"):
            status = "not_enabled_yet"
        elif item.get("user_has_posted"):
            status = "submitted"
        elif item.get("participation_check_error"):
            status = "verification_needed"
        elif (
            (lock_at and lock_at <= now)
            or item.get("locked")
            or item.get("locked_for_user")
        ):
            status = "missing"
        elif item.get("requires_post"):
            status = "needs_reply"
        else:
            status = "info"

        item["status"] = status
        item["has_unread_activity"] = has_unread_activity
        item["has_updates"] = bool(
            item.get("user_has_posted") and has_unread_activity
        )
        item["needs_action"] = status == "needs_reply"
        item["is_missed"] = status == "missing"
        item["needs_attention"] = item["needs_action"]

        if status == "needs_reply":
            attention_kind = "reply"
        elif status == "not_enabled_yet":
            attention_kind = "opens_soon"
        elif status == "missing":
            attention_kind = "missed"
        elif status == "verification_needed":
            attention_kind = "verification"
        elif item["has_updates"]:
            attention_kind = "new_activity"
        else:
            attention_kind = "none"
        item["attention_kind"] = attention_kind

        item["display_date_iso"] = (
            item.get("due_date_iso")
            or item.get("lock_at")
            or item.get("own_posted_at")
            or item.get("last_reply_at")
            or item.get("posted_at")
        )

        item["priority_rank"] = self._discussion_priority_rank(
            item=item,
            due_at=due_at or lock_at,
            now=now,
        )

        return item

    def _find_user_discussion_entry(
        self,
        payload: dict,
        user_id: str | None,
        user_name: str | None,
    ) -> dict | None:
        target_user_id = str(user_id) if user_id else None
        target_user_name = self._normalize_person_name(user_name)
        stack = list(payload.get("view") or [])

        while stack:
            entry = stack.pop()
            if not isinstance(entry, dict):
                continue

            entry_user_id = entry.get("user_id") or entry.get("author_id")
            author_name = (
                entry.get("user_name")
                or entry.get("display_name")
                or entry.get("author_name")
                or entry.get("name")
            )

            id_matches = bool(
                target_user_id
                and entry_user_id is not None
                and str(entry_user_id) == target_user_id
            )
            name_matches = bool(
                target_user_name
                and author_name
                and self._normalize_person_name(author_name) == target_user_name
            )

            if id_matches or name_matches:
                return {
                    "entry_id": (
                        str(entry.get("id"))
                        if entry.get("id") is not None
                        else None
                    ),
                    "user_id": (
                        str(entry_user_id)
                        if entry_user_id is not None
                        else None
                    ),
                    "author_name": author_name,
                    "posted_at": entry.get("created_at") or entry.get("updated_at"),
                    "source": (
                        "discussion_view_user_id"
                        if id_matches
                        else "discussion_view_user_name"
                    ),
                }

            replies = entry.get("replies") or entry.get("recent_replies") or []
            if isinstance(replies, list):
                stack.extend(replies)

        return None

    def _normalize_person_name(self, value: str | None) -> str:
        if not value:
            return ""
        return " ".join(str(value).casefold().split())

    def _discussion_priority_rank(
        self,
        item: dict,
        due_at,
        now: datetime,
    ) -> int:
        if item.get("needs_action") and due_at:
            hours = (due_at - now).total_seconds() / 3600
            if hours <= 48:
                return 0
            if hours <= 168:
                return 1
            return 2

        if item.get("needs_action"):
            return 3

        if item.get("status") == "not_enabled_yet":
            return 4

        if item.get("has_updates"):
            return 5

        if item.get("status") == "missing":
            return 6

        if item.get("status") == "verification_needed":
            return 7

        if item.get("user_has_posted"):
            return 8

        return 9

    def _attach_discussion_metadata_to_assignment(
        self,
        assignment: dict,
        discussion: dict,
    ) -> None:
        assignment.update(
            {
                "item_type": "discussion",
                "is_discussion": True,
                "discussion_id": discussion.get("discussion_id"),
                "discussion_title": discussion.get("discussion_title"),
                "discussion_url": discussion.get("discussion_url"),
                "discussion_read_state": discussion.get("read_state"),
                "discussion_unread_count": discussion.get("unread_count", 0),
                "discussion_reply_count": discussion.get("reply_count", 0),
                "discussion_require_initial_post": discussion.get(
                    "require_initial_post",
                    False,
                ),
                "discussion_user_has_posted": discussion.get("user_has_posted"),
                "discussion_own_entry_id": discussion.get("own_entry_id"),
                "discussion_has_updates": discussion.get("has_updates"),
            }
        )

    def discussion_to_dashboard_assignment(self, discussion: dict) -> dict | None:
        if discussion.get("is_graded_discussion"):
            return None

        discussion_status = discussion.get("status")
        if discussion_status not in {"needs_reply", "not_enabled_yet"}:
            return None

        due_date_iso = discussion.get("due_date_iso") or discussion.get("lock_at")
        if discussion_status == "not_enabled_yet":
            dashboard_status = "not_enabled_yet"
        elif due_date_iso:
            dashboard_status = "open"
        else:
            dashboard_status = "open_no_due_date"

        return {
            "course_id": str(discussion.get("course_id") or ""),
            "course_name": discussion.get("course_name"),
            "course_url": discussion.get("course_url"),
            "assignment_id": (
                f"discussion-{discussion.get('course_id')}-{discussion.get('discussion_id')}"
            ),
            "assignment_name": discussion.get("discussion_title"),
            "assignment_url": discussion.get("discussion_url"),
            "assignment_group_id": None,
            "due_date_iso": due_date_iso,
            "unlock_at": discussion.get("unlock_at"),
            "lock_at": discussion.get("lock_at"),
            "published": bool(discussion.get("published")),
            "locked_for_user": bool(discussion.get("locked_for_user")),
            "workflow_state": "published",
            "score": None,
            "entered_score": None,
            "grade": None,
            "entered_grade": None,
            "max_score": discussion.get("points_possible"),
            "submitted_at": None,
            "submission_workflow_state": "unsubmitted",
            "missing": False,
            "late": False,
            "excused": False,
            "muted": False,
            "omit_from_final_grade": False,
            "status": dashboard_status,
            "item_type": "discussion",
            "is_discussion": True,
            "discussion_id": discussion.get("discussion_id"),
            "discussion_title": discussion.get("discussion_title"),
            "discussion_url": discussion.get("discussion_url"),
            "discussion_status": discussion_status,
            "discussion_user_has_posted": False,
            "discussion_unread_count": discussion.get("unread_count", 0),
        }

    def get_dashboard_assignments(self, courses: list[dict]) -> list[dict]:
        assignments_by_course = self.get_assignments_by_course(courses)
        all_assignments = []
        for assignments in assignments_by_course.values():
            all_assignments.extend(self._filter_dashboard_assignments(assignments))
        return all_assignments

    def get_course_progress_assignments(self, courses: list[dict]) -> dict[str, list[dict]]:
        assignments_by_course = self.get_assignments_by_course(courses)
        return {
            course_id: self._filter_progress_assignments(assignments)
            for course_id, assignments in assignments_by_course.items()
        }

    def get_assignment_groups_for_course(
        self,
        course: dict,
        *,
        grade_page_payload: dict | None = None,
    ) -> list[dict]:
        groups = self.canvas_api.get_assignment_groups_for_course(
            course_id=course["course_id"]
        )
        if grade_page_payload is None:
            grade_page_payload = self.canvas_api.get_grade_page_payload_for_course(
                course_id=course["course_id"]
            )
        if grade_page_payload.get("assignment_groups"):
            groups = self._merge_grade_page_groups(
                groups,
                grade_page_payload.get("assignment_groups") or [],
            )
        return groups

    def get_assignment_groups(
        self,
        courses: list[dict],
    ) -> dict[str, list[dict]]:
        return {
            str(course["course_id"]): self.get_assignment_groups_for_course(course)
            for course in courses
        }

    def _recover_grade_from_submission_detail(self, course: dict, assignment: dict) -> dict:
        item = dict(assignment)
        assignment_id = item.get("assignment_id")
        if not assignment_id:
            return item

        detail_grade = self.canvas_api.get_assignment_submission_detail_grade(
            course_id=course["course_id"],
            assignment_id=str(assignment_id),
        )

        score = detail_grade.get("score")
        detail_max_score = detail_grade.get("max_score")
        current_max_score = item.get("max_score")

        if score is None or detail_max_score is None:
            item["submission_detail_checked"] = True
            item["submission_detail_grade_found"] = False
            if detail_grade.get("error"):
                item["submission_detail_error"] = detail_grade.get("error")
            return item

        if current_max_score is not None:
            try:
                current_max = float(current_max_score)
                detail_max = float(detail_max_score)
                if current_max > 0 and abs(current_max - detail_max) > max(0.25, current_max * 0.05):
                    item["submission_detail_checked"] = True
                    item["submission_detail_grade_found"] = False
                    item["submission_detail_error"] = (
                        f"Detail score max mismatch. Canvas max={current_max}; detail max={detail_max}."
                    )
                    return item
            except Exception:
                pass

        item["score"] = score
        item["entered_score"] = detail_grade.get("entered_score") or score
        item["max_score"] = current_max_score if current_max_score is not None else detail_max_score
        item["hidden_grade_recovered"] = True
        item["submission_detail_checked"] = True
        item["submission_detail_grade_found"] = True
        item["grade_source"] = detail_grade.get("source") or "submission_detail_html"
        item["submission_detail_url"] = detail_grade.get("detail_url")
        item["submission_workflow_state"] = item.get("submission_workflow_state") or "graded"
        item["missing"] = False
        item["status"] = "graded"
        return self._normalize_assignment_status(item)

    def _merge_grade_page_data(self, assignment: dict, grade_page_payload: dict) -> dict:
        item = dict(assignment)
        assignment_id = str(item.get("assignment_id") or "")
        if not assignment_id:
            return item

        grade_assignment = (grade_page_payload.get("assignments_by_id") or {}).get(assignment_id) or {}
        grade_submission = (grade_page_payload.get("submissions_by_assignment_id") or {}).get(assignment_id) or {}

        if grade_assignment:
            if item.get("max_score") is None and grade_assignment.get("max_score") is not None:
                item["max_score"] = grade_assignment.get("max_score")
            if not item.get("due_date_iso") and grade_assignment.get("due_date_iso"):
                item["due_date_iso"] = grade_assignment.get("due_date_iso")
            if not item.get("assignment_group_id") and grade_assignment.get("assignment_group_id"):
                item["assignment_group_id"] = grade_assignment.get("assignment_group_id")
            item["muted"] = bool(item.get("muted") or grade_assignment.get("muted"))
            item["omit_from_final_grade"] = bool(item.get("omit_from_final_grade") or grade_assignment.get("omit_from_final_grade"))
            item["grade_page_assignment_found"] = True

        if grade_submission:
            recovered_score = grade_submission.get("score")
            recovered_entered_score = grade_submission.get("entered_score")
            if item.get("score") is None and recovered_score is not None:
                item["score"] = recovered_score
                item["hidden_grade_recovered"] = True
                item["grade_source"] = grade_submission.get("source") or "grade_page_env"
            if item.get("entered_score") is None and recovered_entered_score is not None:
                item["entered_score"] = recovered_entered_score
            if not item.get("grade") and grade_submission.get("grade") is not None:
                item["grade"] = grade_submission.get("grade")
            if not item.get("entered_grade") and grade_submission.get("entered_grade") is not None:
                item["entered_grade"] = grade_submission.get("entered_grade")
            if not item.get("submission_workflow_state") and grade_submission.get("workflow_state"):
                item["submission_workflow_state"] = grade_submission.get("workflow_state")
            if item.get("excused") is None and grade_submission.get("excused") is not None:
                item["excused"] = grade_submission.get("excused")
            if not item.get("assignment_url") and grade_submission.get("assignment_url"):
                item["assignment_url"] = self.canvas_api._build_url(grade_submission.get("assignment_url"))
            item["grade_page_submission_found"] = True

        return item

    def _merge_grade_page_groups(self, api_groups: list[dict], grade_page_groups: list[dict]) -> list[dict]:
        by_id = {str(group.get("group_id")): dict(group) for group in api_groups if group.get("group_id") is not None}
        for group in grade_page_groups:
            group_id = str(group.get("group_id")) if group.get("group_id") is not None else None
            if not group_id:
                continue
            if group_id not in by_id:
                by_id[group_id] = dict(group)
            else:
                if not by_id[group_id].get("name") and group.get("name"):
                    by_id[group_id]["name"] = group.get("name")
                if float(by_id[group_id].get("group_weight") or 0.0) == 0.0 and group.get("group_weight") is not None:
                    by_id[group_id]["group_weight"] = group.get("group_weight")
        return list(by_id.values())

    def _filter_current_term_courses(self, courses: list[dict]) -> list[dict]:
        """
        Keep only courses from the latest semester while preserving every
        course that Canvas places in that same term.

        Priority:
        1. Infer the latest semester/year from course_name or course_code.
        2. Expand that selection to every course sharing the matching
           Canvas ``term.id``. This prevents one irregular course code from
           disappearing while its classmates remain visible.
        3. If no semester/year can be inferred, choose the most recent
           Canvas term bucket.
        4. If Canvas provides no term metadata, return all available courses.
        """
        available_courses = [
            course
            for course in courses
            if (course.get("workflow_state") or "").lower()
            in {"available", "unpublished", "completed"}
        ]

        if not available_courses:
            return courses

        tagged_courses: list[tuple[tuple[int, int], dict]] = []
        for course in available_courses:
            key = self._extract_term_key(course)
            if key is not None:
                tagged_courses.append((key, course))

        if tagged_courses:
            latest_key = max(term_key for term_key, _ in tagged_courses)
            latest_tagged_courses = [
                course
                for term_key, course in tagged_courses
                if term_key == latest_key
            ]

            # Canvas already tells us which academic term owns each course.
            # Once the latest semester has been identified, include every
            # available course from those term IDs, even when one course has
            # a malformed or nonstandard code.
            latest_term_ids = {
                str(term_id)
                for course in latest_tagged_courses
                for term_id in [self._get_canvas_term_id(course)]
                if term_id is not None
            }

            if latest_term_ids:
                expanded_courses = [
                    course
                    for course in available_courses
                    if (
                        self._get_canvas_term_id(course) is not None
                        and str(self._get_canvas_term_id(course))
                        in latest_term_ids
                    )
                ]

                # Keep parsed courses that have no Canvas term ID so that a
                # missing metadata field does not make a valid course vanish.
                expanded_ids = {
                    str(course.get("course_id") or course.get("id") or "")
                    for course in expanded_courses
                }
                for course in latest_tagged_courses:
                    course_id = str(
                        course.get("course_id")
                        or course.get("id")
                        or ""
                    )
                    if course_id not in expanded_ids:
                        expanded_courses.append(course)
                        expanded_ids.add(course_id)

                if expanded_courses:
                    return expanded_courses

            if latest_tagged_courses:
                return latest_tagged_courses

        buckets_by_term_id: dict[str, list[dict]] = {}
        for course in available_courses:
            term_id = self._get_canvas_term_id(course)
            if term_id is not None:
                buckets_by_term_id.setdefault(str(term_id), []).append(course)

        if buckets_by_term_id:
            ranked = []
            for term_id, grouped_courses in buckets_by_term_id.items():
                ranked.append(
                    (
                        self._best_course_date_key(grouped_courses),
                        len(grouped_courses),
                        term_id,
                        grouped_courses,
                    )
                )
            ranked.sort(reverse=True)
            return ranked[0][3]

        return available_courses

    @staticmethod
    def _get_canvas_term_id(course: dict) -> object | None:
        term = course.get("term") or {}
        if not isinstance(term, dict):
            return None
        return term.get("id")

    def _best_course_date_key(self, grouped_courses: list[dict]) -> str:
        values = []
        for course in grouped_courses:
            for value in [course.get("start_at"), course.get("end_at")]:
                if value:
                    values.append(str(value))
        return max(values) if values else ""

    def _extract_term_key(self, course: dict) -> Optional[tuple[int, int]]:
        """
        Return ``(year, semester)`` from either the display name or the
        compact Canvas course code.

        Supported examples:
        - ``12026-1900-032-B`` -> ``(2026, 1)``
        - ``22026-1900-038-A`` -> ``(2026, 2)``
        - ``22026-090-037-3``  -> ``(2026, 2)``
        - ``220260900373``     -> ``(2026, 2)``
        """
        values = [
            course.get("course_name") or "",
            course.get("course_code") or "",
        ]

        for text in values:
            normalized = str(text).strip().upper()
            for pattern in (
                self.TERM_PATTERN,
                self.COMPACT_TERM_PATTERN,
            ):
                match = pattern.search(normalized)
                if match:
                    semester = int(match.group(1))
                    year = int(match.group(2))
                    return (year, semester)

        return None

    def _normalize_assignment_status(self, assignment: dict) -> dict:
        now = datetime.now(timezone.utc)
        a = dict(assignment)

        name = (a.get("assignment_name") or "").lower()
        due_at = self._parse_dt(a.get("due_date_iso"))
        unlock_at = self._parse_dt(a.get("unlock_at"))
        lock_at = self._parse_dt(a.get("lock_at"))

        score = a.get("score")
        entered_score = a.get("entered_score")
        if score is None and entered_score is not None:
            score = entered_score
            a["score"] = entered_score

        max_score = a.get("max_score")
        submitted_at = a.get("submitted_at")
        submission_state = (a.get("submission_workflow_state") or "").lower()
        missing = bool(a.get("missing"))
        late = bool(a.get("late"))
        published = bool(a.get("published", False))
        locked_for_user = bool(a.get("locked_for_user", False))

        a["is_attendance"] = any(pattern in name for pattern in self.ATTENDANCE_PATTERNS)
        a["is_locked"] = bool(lock_at and lock_at <= now)
        a["is_future_locked"] = bool(unlock_at and unlock_at > now)
        a["is_due_future"] = bool(due_at and due_at > now)
        a["is_due_past"] = bool(due_at and due_at <= now)
        a["is_graded"] = score is not None and max_score is not None
        a["is_submitted"] = bool(submitted_at)
        a["is_submitted_pending"] = bool(
            submitted_at and score is None and submission_state not in {"unsubmitted", ""}
        )
        a["is_missing"] = bool(
            missing or (
                submission_state == "unsubmitted"
                and due_at
                and due_at <= now
                and not submitted_at
                and score is None
            )
        )
        a["is_late"] = late

        if not published:
            a["status"] = "hidden"
        elif a["is_missing"]:
            a["status"] = "missing"
        elif a["is_graded"]:
            a["status"] = "graded"
        elif a["is_submitted_pending"]:
            a["status"] = "submitted_pending"
        elif a["is_submitted"]:
            a["status"] = "submitted"
        elif a["is_future_locked"] or locked_for_user:
            a["status"] = "not_enabled_yet"
        elif a["is_due_future"]:
            a["status"] = "open"
        elif not due_at and not lock_at:
            a["status"] = "open_no_due_date"
        elif a["is_due_past"] and not a["is_submitted"] and not a["is_graded"]:
            a["status"] = "expired"
        elif a["is_locked"]:
            a["status"] = "closed"
        else:
            a["status"] = "open"

        return a

    def _should_deep_check(self, item: dict) -> bool:
        if item.get("is_graded"):
            return False
        if item.get("is_missing"):
            return False
        if item.get("status") == "hidden":
            return False
        if item.get("assignment_id") is None:
            return False
        return True

    def _filter_dashboard_assignments(self, assignments: list[dict]) -> list[dict]:
        now = datetime.now(timezone.utc)
        results = []

        for item in assignments:
            due_at = self._parse_dt(item.get("due_date_iso"))

            if due_at and due_at <= now and not item.get("is_submitted_pending"):
                continue

            if item.get("status") in {
                "open",
                "not_enabled_yet",
                "submitted",
                "submitted_pending",
                "open_no_due_date",
            }:
                results.append(item)

        return results

    def _filter_progress_assignments(self, assignments: list[dict]) -> list[dict]:
        return [item for item in assignments if item.get("status") != "hidden"]

    def _parse_dt(self, value: str | None):
        if not value:
            return None
        try:
            return date_parser.parse(value).astimezone(timezone.utc)
        except Exception:
            return None