from __future__ import annotations

from config.settings import (
    COURSE_RULES_FILE,
    DEFAULT_FINAL_POINTS,
    DEFAULT_PASSING_SCORE,
    DEFAULT_PARTIAL_1_POINTS,
    DEFAULT_PARTIAL_2_POINTS,
    DEFAULT_TOTAL_POINTS,
    DEFAULT_ZONE_POINTS,
)
from src.utils.file_utils import read_json


class GradeAnalyticsService:
    def __init__(self) -> None:
        self.rules = read_json(COURSE_RULES_FILE, default=None) or {
            "default": {
                "passing_score": DEFAULT_PASSING_SCORE,
                "zone_points": DEFAULT_ZONE_POINTS,
                "partial_1_points": DEFAULT_PARTIAL_1_POINTS,
                "partial_2_points": DEFAULT_PARTIAL_2_POINTS,
                "final_points": DEFAULT_FINAL_POINTS,
                "total_points": DEFAULT_TOTAL_POINTS,
            },
            "overrides": {},
        }

    def analyze_course(self, course: dict, assignments: list[dict]) -> dict:
        rule = self._get_rule(course)

        graded = [a for a in assignments if a.get("score") is not None and a.get("max_score") is not None]
        submitted_pending = [a for a in assignments if a.get("submitted_at") and a.get("score") is None]
        open_assignments = [a for a in assignments if not a.get("submitted_at") and a.get("score") is None]

        earned_points = round(sum(float(a["score"]) for a in graded if a.get("score") is not None), 2)
        published_points = round(sum(float(a["max_score"]) for a in graded if a.get("max_score") is not None), 2)
        submitted_pending_points = round(
            sum(float(a["max_score"]) for a in submitted_pending if a.get("max_score") is not None),
            2,
        )

        total_points = float(rule["total_points"])
        passing_score = float(rule["passing_score"])
        remaining_to_pass = max(0.0, round(passing_score - earned_points, 2))
        known_progress_percent = round((earned_points / total_points) * 100, 2) if total_points else 0.0

        risk_level = self._risk_level(
            earned_points=earned_points,
            passing_score=passing_score,
            submitted_pending_points=submitted_pending_points,
        )

        return {
            "course_id": course["course_id"],
            "course_name": course["course_name"],
            "course_code": course.get("course_code"),
            "earned_points": earned_points,
            "published_points": published_points,
            "submitted_pending_points": submitted_pending_points,
            "remaining_to_pass": remaining_to_pass,
            "passing_score": passing_score,
            "total_points": total_points,
            "known_progress_percent": known_progress_percent,
            "graded_count": len(graded),
            "submitted_pending_count": len(submitted_pending),
            "open_count": len(open_assignments),
            "risk_level": risk_level,
            "rule": rule,
        }

    def _get_rule(self, course: dict) -> dict:
        overrides = self.rules.get("overrides", {})
        course_code = course.get("course_code")
        if course_code and course_code in overrides:
            return {**self.rules["default"], **overrides[course_code]}
        return self.rules["default"]

    def _risk_level(self, earned_points: float, passing_score: float, submitted_pending_points: float) -> str:
        if earned_points >= passing_score:
            return "healthy"
        if earned_points + submitted_pending_points >= passing_score:
            return "watch"
        return "at_risk"