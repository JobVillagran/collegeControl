from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from config.settings import (
    COURSE_RULES_FILE,
    DEFAULT_FINAL_POINTS,
    DEFAULT_PARTIAL_1_POINTS,
    DEFAULT_PARTIAL_2_POINTS,
    DEFAULT_PASSING_SCORE,
    DEFAULT_TOTAL_POINTS,
)
from src.utils.file_utils import read_json


@dataclass
class CourseRules:
    total_points: float
    passing_score: float
    partial_1_points: float
    partial_2_points: float
    final_points: float


class GradeAnalyticsService:
    """
    Academic points engine.

    This service intentionally avoids using Canvas percentage as the source of truth.
    Canvas percentages can be misleading when instructors hide grades, publish partial
    structures, duplicate ordinary/recovery exams, or weight assignment groups.

    The main source of truth here is: score / points_possible per assignment.
    """

    PASSING_SCORE = float(DEFAULT_PASSING_SCORE)
    TOTAL_POINTS = float(DEFAULT_TOTAL_POINTS)

    def __init__(self) -> None:
        self.course_rules_payload = read_json(COURSE_RULES_FILE, default={}) or {}

    ATTENDANCE_GREEN = 92.0
    ATTENDANCE_WATCH = 85.0
    ATTENDANCE_DANGER = 80.0

    RECOVERY_WORDS = [
        "recuperacion",
        "recuperación",
        "extraordinario",
        "extraordinaria",
        "reposicion",
        "reposición",
        "replacement",
        "make up",
        "makeup",
    ]

    def analyze_course(
        self,
        course: dict,
        assignments: list[dict],
        assignment_groups: list[dict],
    ) -> dict:
        rules = self._rules_for_course(course)
        groups_by_id = {
            str(group.get("group_id")): group
            for group in assignment_groups
            if group.get("group_id") is not None
        }

        enriched = [self._enrich_assignment(a, groups_by_id, rules) for a in assignments]
        attendance_items = [a for a in enriched if a["component_type"] == "attendance"]
        academic_items = [a for a in enriched if a["component_type"] != "attendance"]

        resolved_items, recovery_events = self._resolve_recoveries(academic_items)

        graded_items = [a for a in resolved_items if a["count_state"] == "graded"]
        missing_items = [a for a in resolved_items if a["count_state"] == "missing"]
        pending_items = [a for a in resolved_items if a["count_state"] == "pending_grade"]
        open_items = [a for a in resolved_items if a["count_state"] == "open"]
        hidden_items = [a for a in resolved_items if a["count_state"] == "hidden_or_review"]
        closed_ungraded_items = [a for a in resolved_items if a["count_state"] == "closed_ungraded"]

        earned_points = self._sum_scores(graded_items)
        published_points = self._sum_possible(resolved_items)
        graded_possible_points = self._sum_possible(graded_items)
        lost_points = self._sum_lost(graded_items) + self._sum_possible(missing_items)
        pending_points = self._sum_possible(pending_items)
        open_points = self._sum_possible(open_items)
        hidden_or_review_points = self._sum_possible(hidden_items + closed_ungraded_items)
        published_unresolved_points = pending_points + open_points + hidden_or_review_points
        remaining_unpublished_points = max(0.0, round(rules.total_points - published_points, 2))
        remaining_available_points = round(
            pending_points + open_points + hidden_or_review_points + remaining_unpublished_points,
            2,
        )
        remaining_to_pass = max(0.0, round(rules.passing_score - earned_points, 2))
        maximum_possible_points = round(earned_points + remaining_available_points, 2)
        required_percent_of_remaining = None
        if remaining_to_pass > 0 and remaining_available_points > 0:
            required_percent_of_remaining = round((remaining_to_pass / remaining_available_points) * 100.0, 2)

        effective_percent = round((earned_points / rules.total_points) * 100.0, 2) if rules.total_points else 0.0
        published_percent = round((earned_points / published_points) * 100.0, 2) if published_points else None
        canvas_current_total_percent = self._resolve_current_total_percent(course, graded_items)

        attendance_summary = self._build_attendance_summary(attendance_items)
        component_summaries = self._build_component_summaries(resolved_items)
        group_summaries = self._build_group_summaries(assignment_groups, enriched)

        course_finished = self._course_finished(resolved_items, recovery_events)
        course_result = self._course_result(
            course_finished=course_finished,
            earned_points=earned_points,
            passing_score=rules.passing_score,
        )

        risk_level, risk_reason = self._risk_level(
            earned_points=earned_points,
            passing_score=rules.passing_score,
            maximum_possible_points=maximum_possible_points,
            remaining_to_pass=remaining_to_pass,
            remaining_available_points=remaining_available_points,
            required_percent_of_remaining=required_percent_of_remaining,
            published_points=published_points,
            hidden_or_review_points=hidden_or_review_points,
        )

        if course_finished:
            if course_result == "passed":
                risk_level = "passed"
                risk_reason = (
                    f"Course finished. You passed with {earned_points:.2f} point(s). "
                    f"The passing mark is {rules.passing_score:.2f}."
                )
            else:
                risk_level = "failed"
                risk_reason = (
                    f"Course finished. You did not reach the passing mark. "
                    f"Current confirmed total is {earned_points:.2f}/{rules.total_points:.2f}; "
                    f"passing mark is {rules.passing_score:.2f}."
                )

        return {
            "course_id": course["course_id"],
            "course_name": course["course_name"],
            "course_code": course.get("course_code"),
            "course_url": course.get("course_url"),
            "term": course.get("term") or {},
            "grading_mode": self._detect_grading_mode(assignment_groups),
            "calculation_mode": "effective_points",
            "course_finished": course_finished,
            "course_result": course_result,
            "course_result_label": self._course_result_label(course_result),
            "canvas_current_total_percent": canvas_current_total_percent,
            "current_total_percent": effective_percent,
            "published_score_percent": published_percent,
            "earned_points": earned_points,
            "earned_effective_points": earned_points,
            "graded_possible_points": graded_possible_points,
            "published_points": published_points,
            "effective_published_points": published_points,
            "lost_points": lost_points,
            "missing_points": self._sum_possible(missing_items),
            "pending_points": pending_points,
            "submitted_pending_points": pending_points,
            "open_points": open_points,
            "hidden_or_review_points": hidden_or_review_points,
            "remaining_unpublished_points": remaining_unpublished_points,
            "remaining_available_points": remaining_available_points,
            "remaining_to_pass": remaining_to_pass,
            "maximum_possible_points": maximum_possible_points,
            "required_percent_of_remaining": required_percent_of_remaining,
            "passing_score": rules.passing_score,
            "total_points": rules.total_points,
            "known_total_points": published_points,
            "secured_over_100": earned_points,
            "pending_over_100": pending_points,
            "missing_over_100": lost_points,
            "open_over_100": round(open_points + remaining_unpublished_points, 2),
            "resolved_over_100": round(earned_points + lost_points, 2),
            "known_progress_percent": effective_percent,
            "published_progress_percent": published_percent or 0.0,
            "pass_progress_percent": round(min((earned_points / rules.passing_score) * 100.0, 100.0), 2),
            "score_bar_percent": round(min(max(effective_percent, 0.0), 100.0), 2),
            "pass_threshold_percent": rules.passing_score,
            "graded_count": len(graded_items),
            "submitted_pending_count": len(pending_items),
            "submitted_done_ungraded_count": len(pending_items),
            "pending_grade_count": len(pending_items),
            "missing_count": len(missing_items),
            "open_count": len(open_items),
            "hidden_or_review_count": len(hidden_items) + len(closed_ungraded_items),
            "risk_level": risk_level,
            "risk_reason": risk_reason,
            "attendance": attendance_summary,
            "recovery_events": recovery_events,
            "components": component_summaries,
            "groups": group_summaries,
        }

    def _rules_for_course(self, course: dict) -> CourseRules:
        default_rules = dict(self.course_rules_payload.get("default") or {})
        overrides = self.course_rules_payload.get("overrides") or {}

        course_id = str(course.get("course_id") or "")
        course_code = str(course.get("course_code") or "")
        course_name = str(course.get("course_name") or "")

        override_rules = {}
        for key in [course_id, course_code, course_name]:
            if key and isinstance(overrides.get(key), dict):
                override_rules.update(overrides[key])

        rules = {**default_rules, **override_rules}

        return CourseRules(
            total_points=self._safe_float(rules.get("total_points")) or float(DEFAULT_TOTAL_POINTS),
            passing_score=self._safe_float(rules.get("passing_score")) or float(DEFAULT_PASSING_SCORE),
            partial_1_points=self._safe_float(rules.get("partial_1_points")) or float(DEFAULT_PARTIAL_1_POINTS),
            partial_2_points=self._safe_float(rules.get("partial_2_points")) or float(DEFAULT_PARTIAL_2_POINTS),
            final_points=self._safe_float(rules.get("final_points")) or float(DEFAULT_FINAL_POINTS),
        )

    def _enrich_assignment(self, assignment: dict, groups_by_id: dict[str, dict], rules: CourseRules) -> dict:
        item = dict(assignment)
        group = groups_by_id.get(str(item.get("assignment_group_id"))) or {}
        item["assignment_group_name"] = group.get("name") or "Ungrouped"
        item["component_type"] = self._classify_component(item, rules)
        item["recovered_component_type"] = self._infer_recovered_component(item, rules)
        item["count_state"] = self._count_state(item)
        return item

    def _classify_component(self, assignment: dict, rules: CourseRules) -> str:
        text = self._norm(" ".join([
            assignment.get("assignment_name") or "",
            assignment.get("assignment_group_name") or "",
        ]))
        points = self._safe_float(assignment.get("max_score"))

        if self._has_any(text, ["roll call", "attendance", "asistencia"]):
            return "attendance"

        if self._has_any(text, self.RECOVERY_WORDS):
            return "recovery_exam"

        if self._has_any(text, ["proyecto final", "final project", "entrega final proyecto", "project final"]):
            return "final_project"

        if self._has_any(text, ["segundo parcial", "parcial 2", "partial 2", "p2"]):
            return "partial_2"

        if self._has_any(text, ["primer parcial", "parcial 1", "partial 1", "p1"]):
            return "partial_1"

        if self._has_any(text, ["examen final", "final ordinario", "ordinario final", "final"]):
            return "final_exam"

        group_text = self._norm(assignment.get("assignment_group_name") or "")
        if self._has_any(group_text, ["final"]):
            return "final_exam" if (points or 0) >= 20 else "final_project"

        if self._has_any(group_text, ["parcial", "parciales"]):
            if points is not None:
                if abs(points - rules.partial_1_points) <= 1:
                    return "partial_1"
                if abs(points - rules.partial_2_points) <= 2:
                    return "partial_2"
            return "exam"

        if self._has_any(text, ["proyecto", "project", "plan de trabajo", "avance", "coeval", "documentacion", "documentación"]):
            return "project"

        return "task"

    def _infer_recovered_component(self, assignment: dict, rules: CourseRules) -> str | None:
        if not self._has_any(self._norm(assignment.get("assignment_name") or ""), self.RECOVERY_WORDS):
            return None

        text = self._norm(" ".join([
            assignment.get("assignment_name") or "",
            assignment.get("assignment_group_name") or "",
        ]))
        points = self._safe_float(assignment.get("max_score")) or 0.0

        if self._has_any(text, ["final"]):
            return "final_exam"
        if self._has_any(text, ["segundo", "parcial 2", "p2"]):
            return "partial_2"
        if self._has_any(text, ["primer", "parcial 1", "p1"]):
            return "partial_1"
        if abs(points - rules.final_points) <= 5 or points >= 25:
            return "final_exam"
        if abs(points - rules.partial_2_points) <= 3:
            return "partial_2"
        if abs(points - rules.partial_1_points) <= 2:
            return "partial_1"
        return "exam"

    def _count_state(self, assignment: dict) -> str:
        max_score = self._safe_float(assignment.get("max_score"))
        score = self._safe_float(assignment.get("score"))
        status = assignment.get("status")

        if max_score is None or max_score <= 0:
            return "not_countable"
        if assignment.get("excused"):
            return "excused"
        if score is not None:
            return "graded"
        if assignment.get("is_missing") or status == "missing":
            return "missing"
        if assignment.get("is_submitted") or assignment.get("is_submitted_pending") or status in {"submitted", "submitted_pending"}:
            return "pending_grade"
        if status in {"hidden", "locked", "closed"} or assignment.get("locked_for_user"):
            return "hidden_or_review"
        if status in {"open", "not_enabled_yet", "open_no_due_date"}:
            return "open"
        if status in {"expired", "closed"}:
            return "closed_ungraded"
        return "open"

    def _resolve_recoveries(self, items: list[dict]) -> tuple[list[dict], list[dict]]:
        regulars: list[dict] = []
        recoveries_by_component: dict[str, list[dict]] = {}

        for item in items:
            if item["component_type"] == "recovery_exam":
                target = item.get("recovered_component_type") or "exam"
                recoveries_by_component.setdefault(target, []).append(item)
            else:
                regulars.append(item)

        resolved = list(regulars)
        events: list[dict] = []

        for target, recovery_items in recoveries_by_component.items():
            target_regulars = [r for r in regulars if r["component_type"] == target]

            if not target_regulars:
                chosen = self._best_attempt(recovery_items)
                chosen = dict(chosen)
                chosen["component_type"] = target
                chosen["was_recovery_used"] = chosen.get("count_state") == "graded"
                resolved.append(chosen)
                events.append(self._recovery_event(target, None, chosen, chosen.get("count_state") == "graded"))
                continue

            # Pick the most exam-like regular for the same component. If there are multiple,
            # prefer the one with the highest possible points and latest due date already in Canvas order.
            regular = sorted(
                target_regulars,
                key=lambda x: (self._safe_float(x.get("max_score")) or 0.0, x.get("due_date_iso") or ""),
                reverse=True,
            )[0]
            best_recovery = self._best_attempt(recovery_items)
            use_recovery = self._should_use_recovery(regular, best_recovery)

            if use_recovery:
                regular_id = regular.get("assignment_id")
                if regular_id is not None:
                    resolved = [x for x in resolved if x.get("assignment_id") != regular_id]
                else:
                    resolved = [x for x in resolved if x is not regular]
                replacement = dict(best_recovery)
                replacement["component_type"] = target
                replacement["was_recovery_used"] = True
                replacement["replaces_assignment_id"] = regular.get("assignment_id")
                replacement["replaces_assignment_name"] = regular.get("assignment_name")
                resolved.append(replacement)

            events.append(self._recovery_event(target, regular, best_recovery, use_recovery))

        return resolved, events

    def _best_attempt(self, items: list[dict]) -> dict:
        def key(item: dict):
            score = self._safe_float(item.get("score"))
            max_score = self._safe_float(item.get("max_score")) or 0.0
            state_rank = {
                "graded": 4,
                "pending_grade": 3,
                "open": 2,
                "hidden_or_review": 1,
                "missing": 0,
            }.get(item.get("count_state"), 0)
            return (score if score is not None else -1.0, state_rank, max_score)

        return sorted(items, key=key, reverse=True)[0]

    def _should_use_recovery(self, regular: dict, recovery: dict) -> bool:
        regular_score = self._safe_float(regular.get("score"))
        recovery_score = self._safe_float(recovery.get("score"))

        if recovery_score is None:
            return False
        if regular_score is None:
            return True
        return recovery_score >= regular_score

    def _recovery_event(self, component: str, regular: dict | None, recovery: dict, applied: bool) -> dict:
        return {
            "component": component,
            "applied": bool(applied),
            "regular_assignment": regular.get("assignment_name") if regular else None,
            "regular_score": self._safe_float(regular.get("score")) if regular else None,
            "regular_points": self._safe_float(regular.get("max_score")) if regular else None,
            "recovery_assignment": recovery.get("assignment_name"),
            "recovery_score": self._safe_float(recovery.get("score")),
            "recovery_points": self._safe_float(recovery.get("max_score")),
        }

    def _course_finished(self, items: list[dict], recovery_events: list[dict]) -> bool:
        for item in items:
            if item.get("component_type") == "final_exam" and item.get("count_state") == "graded":
                return True

        for event in recovery_events:
            if event.get("component") == "final_exam" and self._safe_float(event.get("recovery_score")) is not None:
                return True

        return False

    def _course_result(self, course_finished: bool, earned_points: float, passing_score: float) -> str:
        if not course_finished:
            return "in_progress"
        return "passed" if earned_points >= passing_score else "failed"

    def _course_result_label(self, course_result: str) -> str:
        labels = {
            "in_progress": "In progress",
            "passed": "Passed",
            "failed": "Failed",
        }
        return labels.get(course_result, course_result)

    def _build_attendance_summary(self, attendance_items: list[dict]) -> dict:
        if not attendance_items:
            return {
                "available": False,
                "label": "N/A",
                "percent": None,
                "level": "not_applicable",
                "message": "Attendance is not published for this course.",
            }

        best = self._best_attempt(attendance_items)
        score = self._safe_float(best.get("score"))
        max_score = self._safe_float(best.get("max_score"))
        percent = None

        if score is not None and max_score and max_score > 0:
            percent = round((score / max_score) * 100.0, 2)
        elif score is not None:
            percent = round(score, 2)

        if percent is None:
            return {
                "available": True,
                "label": "Pending",
                "percent": None,
                "level": "not_enough_data",
                "message": "Attendance exists, but Canvas has not published a percentage yet.",
            }

        if percent >= self.ATTENDANCE_GREEN:
            level = "healthy"
            message = f"Attendance is {percent:.2f}%. Minimum target is 92%."
        elif percent >= self.ATTENDANCE_WATCH:
            level = "watch"
            message = f"Attendance is {percent:.2f}%. It is below the 92% target."
        elif percent >= self.ATTENDANCE_DANGER:
            level = "at_risk"
            message = f"Attendance is {percent:.2f}%. It is close to the danger zone."
        else:
            level = "critical"
            message = f"Attendance is {percent:.2f}%. It is under 80%."

        return {
            "available": True,
            "label": f"{percent:.2f}%",
            "percent": percent,
            "level": level,
            "message": message,
            "assignment_name": best.get("assignment_name"),
        }

    def _build_component_summaries(self, items: list[dict]) -> list[dict]:
        order = ["partial_1", "partial_2", "final_exam", "final_project", "project", "task", "exam"]
        labels = {
            "partial_1": "Primer parcial",
            "partial_2": "Segundo parcial",
            "final_exam": "Examen final",
            "final_project": "Proyecto final",
            "project": "Proyectos",
            "task": "Tareas",
            "exam": "Exámenes",
        }
        summaries = []
        for component in order:
            component_items = [i for i in items if i.get("component_type") == component]
            if not component_items:
                continue
            graded = [i for i in component_items if i.get("count_state") == "graded"]
            missing = [i for i in component_items if i.get("count_state") == "missing"]
            pending = [i for i in component_items if i.get("count_state") == "pending_grade"]
            open_items = [i for i in component_items if i.get("count_state") == "open"]
            hidden = [i for i in component_items if i.get("count_state") in {"hidden_or_review", "closed_ungraded"}]
            possible = self._sum_possible(component_items)
            earned = self._sum_scores(graded)
            summaries.append({
                "type": component,
                "label": labels.get(component, component),
                "earned_points": earned,
                "published_points": possible,
                "lost_points": self._sum_lost(graded) + self._sum_possible(missing),
                "pending_points": self._sum_possible(pending),
                "open_points": self._sum_possible(open_items),
                "hidden_or_review_points": self._sum_possible(hidden),
                "count": len(component_items),
            })
        return summaries

    def _build_group_summaries(self, assignment_groups: list[dict], assignments: list[dict]) -> list[dict]:
        assignments_by_group: dict[str, list[dict]] = {}
        for assignment in assignments:
            group_id = assignment.get("assignment_group_id")
            if not group_id:
                continue
            assignments_by_group.setdefault(str(group_id), []).append(assignment)

        summaries = []
        for group in assignment_groups:
            group_id = str(group.get("group_id")) if group.get("group_id") is not None else None
            group_assignments = assignments_by_group.get(group_id, [])
            academic = [a for a in group_assignments if a.get("component_type") != "attendance"]
            graded = [a for a in academic if a.get("count_state") == "graded"]
            missing = [a for a in academic if a.get("count_state") == "missing"]
            possible = self._sum_possible(academic)
            earned = self._sum_scores(graded)
            summaries.append({
                "group_id": group_id,
                "name": group.get("name") or "Unnamed group",
                "weight": round(float(group.get("group_weight") or 0.0), 2),
                "score_percent": round((earned / possible) * 100.0, 2) if possible else None,
                "earned_points": earned,
                "published_points": possible,
                "missing_points": self._sum_possible(missing),
                "assignment_count": len(group_assignments),
            })
        return summaries

    def _risk_level(
        self,
        earned_points: float,
        passing_score: float,
        maximum_possible_points: float,
        remaining_to_pass: float,
        remaining_available_points: float,
        required_percent_of_remaining: float | None,
        published_points: float,
        hidden_or_review_points: float,
    ) -> tuple[str, str]:
        if published_points <= 0:
            return "not_enough_data", "Canvas has not published enough countable grade data yet."

        if earned_points >= passing_score:
            if hidden_or_review_points > 0:
                return "healthy", (
                    f"You have {earned_points:.2f} points, enough to pass, but {hidden_or_review_points:.2f} point(s) still need review."
                )
            return "healthy", f"You have {earned_points:.2f} points. The passing mark is {passing_score:.2f}."

        if maximum_possible_points < passing_score:
            return "critical", (
                f"You have {earned_points:.2f} points. Even with all remaining known/estimated points, "
                f"the maximum possible is {maximum_possible_points:.2f}, below {passing_score:.2f}."
            )

        if remaining_available_points <= 0:
            return "at_risk", (
                f"You need {remaining_to_pass:.2f} more point(s), but there are no remaining published or estimated points."
            )

        if required_percent_of_remaining is None:
            return "not_enough_data", "There are remaining points, but the required percentage cannot be calculated yet."

        if required_percent_of_remaining >= 85:
            return "at_risk", (
                f"You need {remaining_to_pass:.2f} point(s). That requires {required_percent_of_remaining:.2f}% "
                f"of the remaining {remaining_available_points:.2f} point(s)."
            )

        if required_percent_of_remaining >= 60:
            return "watch", (
                f"You need {remaining_to_pass:.2f} point(s). That requires {required_percent_of_remaining:.2f}% "
                f"of the remaining {remaining_available_points:.2f} point(s)."
            )

        return "watch", (
            f"You need {remaining_to_pass:.2f} point(s) from {remaining_available_points:.2f} remaining point(s)."
        )

    def _resolve_current_total_percent(self, course: dict, graded: list[dict]) -> float | None:
        if course.get("current_score") is not None:
            return round(float(course["current_score"]), 2)
        earned = self._sum_scores(graded)
        possible = self._sum_possible(graded)
        if possible <= 0:
            return None
        return round((earned / possible) * 100.0, 2)

    def _detect_grading_mode(self, assignment_groups: list[dict]) -> str:
        total_weight = round(sum(float(group.get("group_weight") or 0.0) for group in assignment_groups), 2)
        return "weighted" if total_weight > 0 else "points"

    def _sum_possible(self, items: list[dict]) -> float:
        return round(sum(self._safe_float(a.get("max_score")) or 0.0 for a in items if a.get("count_state") not in {"not_countable", "excused"}), 2)

    def _sum_scores(self, items: list[dict]) -> float:
        return round(sum(self._safe_float(a.get("score")) or 0.0 for a in items), 2)

    def _sum_lost(self, items: list[dict]) -> float:
        total = 0.0
        for item in items:
            score = self._safe_float(item.get("score")) or 0.0
            possible = self._safe_float(item.get("max_score")) or 0.0
            total += max(0.0, possible - score)
        return round(total, 2)

    def _safe_float(self, value) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _norm(self, value: str) -> str:
        value = unicodedata.normalize("NFKD", value or "")
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = value.lower()
        value = re.sub(r"\s+", " ", value).strip()
        return value

    def _has_any(self, text: str, patterns: list[str]) -> bool:
        normalized_patterns = [self._norm(pattern) for pattern in patterns]
        return any(pattern in text for pattern in normalized_patterns)
