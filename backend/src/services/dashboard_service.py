from __future__ import annotations

from datetime import datetime, timezone

from src.services.cache_service import CacheService
from src.services.comparison_service import ComparisonService
from src.services.grade_analytics_service import GradeAnalyticsService
from src.services.scraping_service import ScrapingService


class DashboardService:
    def __init__(self) -> None:
        self.scraping = ScrapingService()
        self.comparison = ComparisonService()
        self.cache = CacheService()
        self.grade_analytics = GradeAnalyticsService()

    def get_dashboard(self, force_refresh: bool = False) -> dict:
        if not force_refresh:
            cached = self.cache.load_dashboard()
            if cached:
                return cached

        return self.refresh_dashboard()

    def refresh_dashboard(self) -> dict:
        try:
            courses = self.scraping.get_courses()
            assignments_by_course = self.scraping.get_assignments_by_course(courses)
            assignment_groups_by_course = self.scraping.get_assignment_groups(courses)

            dashboard_assignments = []
            for assignments in assignments_by_course.values():
                dashboard_assignments.extend(self.scraping._filter_dashboard_assignments(assignments))

            groups = self.comparison.build_groups(dashboard_assignments)

            course_summaries = [
                self.grade_analytics.analyze_course(
                    course=course,
                    assignments=assignments_by_course.get(course["course_id"], []),
                    assignment_groups=assignment_groups_by_course.get(course["course_id"], []),
                )
                for course in courses
            ]

            payload = {
                "sync": {
                    "status": "healthy",
                    "source": "canvas_api",
                    "last_synced_at": datetime.now(timezone.utc).isoformat(),
                    "message": "Live data loaded successfully.",
                },
                "summary": {
                    "actionable": len(groups["act_now"]) + len(groups["this_week"]) + len(groups["next_week"]) + len(groups["third_week"]) + len(groups["no_due_date"]),
                    "urgent": len(groups["act_now"]),
                    "opens_soon": len(groups["opens_soon"]),
                    "projects": len(groups["urgent_projects"]),
                    "submitted": len(groups["submitted"]),
                    "courses_at_risk": len([c for c in course_summaries if c["risk_level"] in {"at_risk", "critical"}]),
                    "courses_watch": len([c for c in course_summaries if c["risk_level"] == "watch"]),
                    "courses_not_enough_data": len([c for c in course_summaries if c["risk_level"] == "not_enough_data"]),
                    "healthy_courses": len([c for c in course_summaries if c["risk_level"] == "healthy"]),
                    "courses_finished": len([c for c in course_summaries if c.get("course_finished")]),
                    "courses_passed": len([c for c in course_summaries if c.get("course_result") == "passed"]),
                    "courses_failed": len([c for c in course_summaries if c.get("course_result") == "failed"]),
                    "hidden_or_review": sum(int(c.get("hidden_or_review_count") or 0) for c in course_summaries),
                    "attendance_watch": len([c for c in course_summaries if (c.get("attendance") or {}).get("level") in {"watch", "at_risk", "critical"}]),
                },
                "groups": groups,
                "courses": course_summaries,
            }

            self.cache.save_dashboard(payload)
            self.cache.mark_success()
            return payload

        except Exception as exc:
            self.cache.mark_error(str(exc))
            cached = self.cache.load_dashboard()
            if cached:
                cached["sync"] = {
                    "status": "error",
                    "source": "cache_fallback",
                    "last_synced_at": cached.get("sync", {}).get("last_synced_at"),
                    "message": f"Live sync failed. Showing cached data. Error: {exc}",
                }
                return cached
            raise
