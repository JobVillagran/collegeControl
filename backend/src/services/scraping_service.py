from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from dateutil import parser as date_parser

from src.services.canvas_api_service import CanvasAPIService


class ScrapingService:
    TERM_PATTERN = re.compile(r"\b([12])(\d{4})-\d{4}-\d{3}-[A-Z]\b")
    ATTENDANCE_PATTERNS = [
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
            raise RuntimeError("No courses returned by Canvas API.")

        filtered = self._filter_current_term_courses(all_courses)
        if not filtered:
            raise RuntimeError("No courses matched the current term.")

        return filtered

    def get_assignments_by_course(self, courses: list[dict]) -> dict[str, list[dict]]:
        assignments_by_course: dict[str, list[dict]] = {}

        for course in courses:
            grade_page_payload = self.canvas_api.get_grade_page_payload_for_course(course_id=course["course_id"])
            raw_assignments = self.canvas_api.get_assignments_for_course(
                course_id=course["course_id"],
                course_name=course["course_name"],
                course_url=course["course_url"],
            )
            normalized = []

            for assignment in raw_assignments:
                assignment = self._merge_grade_page_data(assignment, grade_page_payload)
                item = self._normalize_assignment_status(assignment)

                if self._should_deep_check(item):
                    try:
                        detail = self.canvas_api.get_assignment_detail_for_course(
                            course_id=course["course_id"],
                            course_name=course["course_name"],
                            course_url=course["course_url"],
                            assignment_id=item["assignment_id"],
                        )
                        detail = self._merge_grade_page_data(detail, grade_page_payload)
                        detail = self._normalize_assignment_status(detail)
                        detail["detail_checked"] = True
                        item = detail
                    except Exception as exc:
                        item["detail_checked"] = False
                        item["detail_check_error"] = str(exc)

                    if item.get("score") is None and item.get("max_score") is not None:
                        item = self._recover_grade_from_submission_detail(course, item)

                normalized.append(item)

            assignments_by_course[course["course_id"]] = normalized

        return assignments_by_course

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

    def get_assignment_groups(self, courses: list[dict]) -> dict[str, list[dict]]:
        assignment_groups_by_course: dict[str, list[dict]] = {}

        for course in courses:
            groups = self.canvas_api.get_assignment_groups_for_course(course_id=course["course_id"])
            grade_payload = self.canvas_api.get_grade_page_payload_for_course(course_id=course["course_id"])
            if grade_payload.get("assignment_groups"):
                groups = self._merge_grade_page_groups(groups, grade_payload.get("assignment_groups") or [])
            assignment_groups_by_course[course["course_id"]] = groups

        return assignment_groups_by_course

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
        Goal:
        Keep only courses from the current semester.

        Priority:
        1. Use semester/year inferred from course_name/course_code
        2. If that fails, use Canvas term.id
        3. If that fails, use available courses only
        """
        available_courses = [
            course for course in courses
            if (course.get("workflow_state") or "").lower() in {"available", "unpublished", "completed"}
        ]

        if not available_courses:
            return courses

        # 1) Best source for your case: infer semester/year from course code or name
        tagged_by_regex: list[tuple[tuple[int, int], dict]] = []
        for course in available_courses:
            key = self._extract_term_key(course)
            if key:
                tagged_by_regex.append((key, course))

        if tagged_by_regex:
            latest_key = max(term_key for term_key, _ in tagged_by_regex)
            regex_filtered = [course for term_key, course in tagged_by_regex if term_key == latest_key]
            if regex_filtered:
                return regex_filtered

        # 2) Fallback: use Canvas term.id groups
        buckets_by_term_id: dict[str, list[dict]] = {}
        for course in available_courses:
            term = course.get("term") or {}
            term_id = term.get("id")
            if term_id is not None:
                buckets_by_term_id.setdefault(str(term_id), []).append(course)

        if buckets_by_term_id:
            # Prefer the group with the most recent course dates, then largest size
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

        # 3) Final fallback
        return available_courses

    def _best_course_date_key(self, grouped_courses: list[dict]) -> str:
        values = []
        for course in grouped_courses:
            for value in [course.get("start_at"), course.get("end_at")]:
                if value:
                    values.append(str(value))
        return max(values) if values else ""

    def _extract_term_key(self, course: dict) -> Optional[tuple[int, int]]:
        """
        Returns (year, semester)
        Example:
        12026-1900-032-B -> (2026, 1)
        22026-1900-038-A -> (2026, 2)
        """
        for text in [course.get("course_name") or "", course.get("course_code") or ""]:
            match = self.TERM_PATTERN.search(text)
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