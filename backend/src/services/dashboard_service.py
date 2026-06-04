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
            assignments = self.scraping.get_assignments(courses)

            groups = self.comparison.build_groups(assignments)

            assignments_by_course = {}
            for a in assignments:
                assignments_by_course.setdefault(a["course_id"], []).append(a)

            course_summaries = [
                self.grade_analytics.analyze_course(course, assignments_by_course.get(course["course_id"], []))
                for course in courses
            ]

            payload = {
                "sync": {
                    "status": "healthy",
                    "source": "canvas_api",
                    "last_synced_at": datetime.now(timezone.utc).isoformat(),
                    "message": "Live data loaded successfully."
                },
                "summary": {
                    "actionable": len(groups["act_now"]) + len(groups["this_week"]) + len(groups["next_week"]) + len(groups["third_week"]) + len(groups["no_due_date"]),
                    "urgent": len(groups["act_now"]),
                    "opens_soon": len(groups["opens_soon"]),
                    "projects": len(groups["urgent_projects"]),
                    "submitted": len(groups["submitted"]),
                    "courses_at_risk": len([c for c in course_summaries if c["risk_level"] == "at_risk"]),
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