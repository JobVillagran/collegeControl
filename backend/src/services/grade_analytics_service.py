from __future__ import annotations

from config.settings import DEFAULT_PASSING_SCORE, DEFAULT_TOTAL_POINTS


class GradeAnalyticsService:
    def analyze_course(
        self,
        course: dict,
        assignments: list[dict],
        assignment_groups: list[dict],
    ) -> dict:
        graded = [a for a in assignments if a.get("is_graded")]
        missing_assignments = [a for a in assignments if a.get("is_missing")]
        submitted_pending = [a for a in assignments if a.get("is_submitted_pending")]
        submitted_done_ungraded = [
            a
            for a in assignments
            if a.get("is_submitted") and not a.get("is_graded") and not a.get("is_submitted_pending")
        ]
        submitted_ungraded = [a for a in assignments if a.get("is_submitted") and not a.get("is_graded")]
        open_assignments = [
            a for a in assignments if a.get("status") in {"open", "not_enabled_yet", "open_no_due_date"}
        ]

        grading_mode = self._detect_grading_mode(assignment_groups)

        earned_points = round(
            sum(float(a["score"]) for a in graded if a.get("score") is not None),
            2,
        )

        settled_assignments = graded + missing_assignments
        published_points = round(
            sum(float(a["max_score"]) for a in settled_assignments if a.get("max_score") is not None),
            2,
        )

        submitted_pending_points = round(
            sum(float(a["max_score"]) for a in submitted_ungraded if a.get("max_score") is not None),
            2,
        )

        missing_points = round(
            sum(float(a["max_score"]) for a in missing_assignments if a.get("max_score") is not None),
            2,
        )

        open_points = round(
            sum(float(a["max_score"]) for a in open_assignments if a.get("max_score") is not None),
            2,
        )

        canvas_current_total_percent = self._resolve_current_total_percent(course, graded)

        impact = self._build_course_impact_over_100(
            assignments=assignments,
            assignment_groups=assignment_groups,
            grading_mode=grading_mode,
        )

        passing_score = float(DEFAULT_PASSING_SCORE)
        total_points = float(DEFAULT_TOTAL_POINTS)

        secured_over_100 = impact["secured_over_100"]
        pending_over_100 = impact["pending_over_100"]
        missing_over_100 = impact["missing_over_100"]
        open_over_100 = impact["open_over_100"]
        resolved_over_100 = impact["resolved_over_100"]
        known_total_points = impact["known_total_points"]

        remaining_to_pass = max(0.0, round(passing_score - secured_over_100, 2))
        pass_progress_percent = round(min((secured_over_100 / passing_score) * 100.0, 100.0), 2)

        group_summaries = self._build_group_summaries(
            assignment_groups=assignment_groups,
            assignments=assignments,
            grading_mode=grading_mode,
        )

        risk_level, risk_reason = self._risk_level(
            secured_over_100=secured_over_100,
            pending_over_100=pending_over_100,
            open_over_100=open_over_100,
            missing_over_100=missing_over_100,
        )

        pending_grade_count = len(submitted_ungraded)

        return {
            "course_id": course["course_id"],
            "course_name": course["course_name"],
            "course_code": course.get("course_code"),
            "grading_mode": grading_mode,
            "canvas_current_total_percent": canvas_current_total_percent,
            "current_total_percent": canvas_current_total_percent,
            "earned_points": earned_points,
            "published_points": published_points,
            "submitted_pending_points": submitted_pending_points,
            "open_points": open_points,
            "missing_points": missing_points,
            "remaining_to_pass": remaining_to_pass,
            "passing_score": passing_score,
            "total_points": total_points,
            "known_total_points": known_total_points,
            "secured_over_100": secured_over_100,
            "pending_over_100": pending_over_100,
            "missing_over_100": missing_over_100,
            "open_over_100": open_over_100,
            "resolved_over_100": resolved_over_100,
            "known_progress_percent": round(secured_over_100, 2),
            "published_progress_percent": round(canvas_current_total_percent or 0.0, 2),
            "pass_progress_percent": pass_progress_percent,
            "score_bar_percent": round(min(max(secured_over_100, 0.0), 100.0), 2),
            "pass_threshold_percent": passing_score,
            "graded_count": len(graded),
            "submitted_pending_count": len(submitted_pending),
            "submitted_done_ungraded_count": len(submitted_done_ungraded),
            "pending_grade_count": pending_grade_count,
            "missing_count": len(missing_assignments),
            "open_count": len(open_assignments),
            "risk_level": risk_level,
            "risk_reason": risk_reason,
            "groups": group_summaries,
        }

    def _resolve_current_total_percent(self, course: dict, graded: list[dict]) -> float | None:
        if course.get("current_score") is not None:
            return round(float(course["current_score"]), 2)

        if not graded:
            return None

        earned = sum(float(a["score"]) for a in graded if a.get("score") is not None)
        possible = sum(float(a["max_score"]) for a in graded if a.get("max_score") is not None)

        if possible <= 0:
            return None

        return round((earned / possible) * 100, 2)

    def _detect_grading_mode(self, assignment_groups: list[dict]) -> str:
        total_weight = round(sum(float(group.get("group_weight") or 0.0) for group in assignment_groups), 2)
        return "weighted" if total_weight > 0 else "unweighted"

    def _build_course_impact_over_100(
        self,
        assignments: list[dict],
        assignment_groups: list[dict],
        grading_mode: str,
    ) -> dict:
        if grading_mode == "weighted":
            return self._build_weighted_course_impact(assignments, assignment_groups)

        return self._build_unweighted_course_impact(assignments)

    def _build_weighted_course_impact(
        self,
        assignments: list[dict],
        assignment_groups: list[dict],
    ) -> dict:
        assignments_by_group: dict[str, list[dict]] = {}

        for assignment in assignments:
            group_id = assignment.get("assignment_group_id")
            if not group_id:
                continue
            assignments_by_group.setdefault(group_id, []).append(assignment)

        secured = 0.0
        pending = 0.0
        missing = 0.0
        open_value = 0.0
        known_total_points = 0.0

        for group in assignment_groups:
            weight = float(group.get("group_weight") or 0.0)
            group_id = group.get("group_id")

            if weight <= 0 or not group_id:
                continue

            group_assignments = assignments_by_group.get(group_id, [])
            countable = [a for a in group_assignments if a.get("max_score") is not None]

            if not countable:
                continue

            group_known_total = sum(float(a["max_score"]) for a in countable if a.get("max_score") is not None)
            if group_known_total <= 0:
                continue

            known_total_points += group_known_total
            factor = weight / group_known_total

            for assignment in countable:
                max_score = float(assignment["max_score"])

                if assignment.get("is_graded") and assignment.get("score") is not None:
                    secured += float(assignment["score"]) * factor
                elif assignment.get("is_missing"):
                    missing += max_score * factor
                elif assignment.get("is_submitted") and not assignment.get("is_graded"):
                    pending += max_score * factor
                elif assignment.get("status") in {"open", "not_enabled_yet", "open_no_due_date"}:
                    open_value += max_score * factor

        resolved = secured + missing

        return {
            "secured_over_100": round(secured, 2),
            "pending_over_100": round(pending, 2),
            "missing_over_100": round(missing, 2),
            "open_over_100": round(open_value, 2),
            "resolved_over_100": round(resolved, 2),
            "known_total_points": round(known_total_points, 2),
        }

    def _build_unweighted_course_impact(self, assignments: list[dict]) -> dict:
        countable = [a for a in assignments if a.get("max_score") is not None]

        total_known = sum(float(a["max_score"]) for a in countable if a.get("max_score") is not None)
        if total_known <= 0:
            return {
                "secured_over_100": 0.0,
                "pending_over_100": 0.0,
                "missing_over_100": 0.0,
                "open_over_100": 0.0,
                "resolved_over_100": 0.0,
                "known_total_points": 0.0,
            }

        factor = 100.0 / total_known

        secured = 0.0
        pending = 0.0
        missing = 0.0
        open_value = 0.0

        for assignment in countable:
            max_score = float(assignment["max_score"])

            if assignment.get("is_graded") and assignment.get("score") is not None:
                secured += float(assignment["score"]) * factor
            elif assignment.get("is_missing"):
                missing += max_score * factor
            elif assignment.get("is_submitted") and not assignment.get("is_graded"):
                pending += max_score * factor
            elif assignment.get("status") in {"open", "not_enabled_yet", "open_no_due_date"}:
                open_value += max_score * factor

        resolved = secured + missing

        return {
            "secured_over_100": round(secured, 2),
            "pending_over_100": round(pending, 2),
            "missing_over_100": round(missing, 2),
            "open_over_100": round(open_value, 2),
            "resolved_over_100": round(resolved, 2),
            "known_total_points": round(total_known, 2),
        }

    def _build_group_summaries(
        self,
        assignment_groups: list[dict],
        assignments: list[dict],
        grading_mode: str,
    ) -> list[dict]:
        assignments_by_group: dict[str, list[dict]] = {}

        for assignment in assignments:
            group_id = assignment.get("assignment_group_id")
            if not group_id:
                continue
            assignments_by_group.setdefault(group_id, []).append(assignment)

        summaries: list[dict] = []

        for group in assignment_groups:
            group_id = group.get("group_id")
            group_assignments = assignments_by_group.get(group_id, [])

            graded = [a for a in group_assignments if a.get("is_graded")]
            missing = [a for a in group_assignments if a.get("is_missing")]
            submitted_pending = [a for a in group_assignments if a.get("is_submitted_pending")]
            submitted_done_ungraded = [
                a
                for a in group_assignments
                if a.get("is_submitted") and not a.get("is_graded") and not a.get("is_submitted_pending")
            ]
            submitted_ungraded = [a for a in group_assignments if a.get("is_submitted") and not a.get("is_graded")]
            open_items = [
                a for a in group_assignments if a.get("status") in {"open", "not_enabled_yet", "open_no_due_date"}
            ]

            earned = sum(float(a["score"]) for a in graded if a.get("score") is not None)
            settled_possible = sum(
                float(a["max_score"])
                for a in (graded + missing)
                if a.get("max_score") is not None
            )

            score_percent = None
            if settled_possible > 0:
                score_percent = round((earned / settled_possible) * 100, 2)

            summaries.append(
                {
                    "group_id": group_id,
                    "name": group.get("name") or "Unnamed group",
                    "weight": round(float(group.get("group_weight") or 0.0), 2) if grading_mode == "weighted" else 0.0,
                    "score_percent": score_percent,
                    "earned_points": round(earned, 2),
                    "published_points": round(settled_possible, 2),
                    "submitted_pending_points": round(
                        sum(float(a["max_score"]) for a in submitted_ungraded if a.get("max_score") is not None),
                        2,
                    ),
                    "missing_points": round(
                        sum(float(a["max_score"]) for a in missing if a.get("max_score") is not None),
                        2,
                    ),
                    "graded_count": len(graded),
                    "submitted_pending_count": len(submitted_pending),
                    "submitted_done_ungraded_count": len(submitted_done_ungraded),
                    "pending_grade_count": len(submitted_ungraded),
                    "missing_count": len(missing),
                    "open_count": len(open_items),
                    "assignment_count": len(group_assignments),
                }
            )

        return summaries

    def _risk_level(
        self,
        secured_over_100: float,
        pending_over_100: float,
        open_over_100: float,
        missing_over_100: float,
    ) -> tuple[str, str]:
        if secured_over_100 <= 0 and pending_over_100 <= 0 and open_over_100 <= 0 and missing_over_100 <= 0:
            return "not_enough_data", "No countable grade data yet."

        if secured_over_100 < 61:
            recoverable = pending_over_100 + open_over_100

            if recoverable <= 0:
                return "at_risk", (
                    f"Secured progress is {secured_over_100:.2f}/100 and there is no remaining recoverable work."
                )

            return "at_risk", (
                f"Secured progress is {secured_over_100:.2f}/100. "
                f"There is still {recoverable:.2f}/100 recoverable through pending or open work."
            )

        if missing_over_100 > 0 or pending_over_100 > 0 or open_over_100 > 0:
            return "watch", (
                f"Secured progress is {secured_over_100:.2f}/100, but there are still pending, open, or missed impacts."
            )

        return "healthy", f"Secured progress is {secured_over_100:.2f}/100."