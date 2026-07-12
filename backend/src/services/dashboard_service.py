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
            discussions_by_course = self.scraping.get_discussions_by_course(
                courses,
                assignments_by_course=assignments_by_course,
            )
            assignment_groups_by_course = self.scraping.get_assignment_groups(courses)

            dashboard_assignments: list[dict] = []
            for assignments in assignments_by_course.values():
                dashboard_assignments.extend(
                    self.scraping._filter_dashboard_assignments(assignments)
                )

            discussion_items: list[dict] = []
            for discussions in discussions_by_course.values():
                discussion_items.extend(discussions)

            # Ungraded forums do not exist in Canvas' assignments endpoint. Convert only
            # pending/opening forums into assignment-shaped items so they participate in
            # the existing scheduling groups without duplicating graded forums.
            for discussion in discussion_items:
                dashboard_item = self.scraping.discussion_to_dashboard_assignment(
                    discussion
                )
                if dashboard_item is not None:
                    dashboard_assignments.append(dashboard_item)

            groups = self.comparison.build_groups(dashboard_assignments)
            discussion_groups = self.comparison.build_discussion_groups(
                discussion_items
            )

            discussion_panel_items = (
                discussion_groups["needs_action"]
                + discussion_groups["updates"]
                + discussion_groups["missed"]
                + discussion_groups["verification_needed"]
            )

            visible_discussions = [
                item
                for item in discussion_items
                if item.get("status") != "hidden"
                and not item.get("is_announcement")
            ]

            discussion_submitted_count = (
                len(discussion_groups["submitted"])
                + len(discussion_groups["updates"])
            )
            discussion_unread_messages = sum(
                int(item.get("unread_count") or 0)
                for item in visible_discussions
            )

            course_summaries = [
                self.grade_analytics.analyze_course(
                    course=course,
                    assignments=assignments_by_course.get(course["course_id"], []),
                    assignment_groups=assignment_groups_by_course.get(
                        course["course_id"],
                        [],
                    ),
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
                    "actionable": (
                        len(groups["act_now"])
                        + len(groups["this_week"])
                        + len(groups["next_week"])
                        + len(groups["third_week"])
                        + len(groups["no_due_date"])
                    ),
                    "urgent": len(groups["act_now"]),
                    "opens_soon": len(groups["opens_soon"]),
                    "projects": len(groups["urgent_projects"]),
                    "submitted": len(groups["submitted"]),
                    "courses_at_risk": len(
                        [
                            course
                            for course in course_summaries
                            if course["risk_level"] in {"at_risk", "critical"}
                        ]
                    ),
                    "courses_watch": len(
                        [
                            course
                            for course in course_summaries
                            if course["risk_level"] == "watch"
                        ]
                    ),
                    "courses_not_enough_data": len(
                        [
                            course
                            for course in course_summaries
                            if course["risk_level"] == "not_enough_data"
                        ]
                    ),
                    "healthy_courses": len(
                        [
                            course
                            for course in course_summaries
                            if course["risk_level"] == "healthy"
                        ]
                    ),
                    "courses_finished": len(
                        [course for course in course_summaries if course.get("course_finished")]
                    ),
                    "courses_passed": len(
                        [
                            course
                            for course in course_summaries
                            if course.get("course_result") == "passed"
                        ]
                    ),
                    "courses_failed": len(
                        [
                            course
                            for course in course_summaries
                            if course.get("course_result") == "failed"
                        ]
                    ),
                    "hidden_or_review": sum(
                        int(course.get("hidden_or_review_count") or 0)
                        for course in course_summaries
                    ),
                    "attendance_watch": len(
                        [
                            course
                            for course in course_summaries
                            if (course.get("attendance") or {}).get("level")
                            in {"watch", "at_risk", "critical"}
                        ]
                    ),
                    # Backward-compatible field, now correctly means forums that
                    # still require the student's own participation.
                    "discussions_attention": len(
                        discussion_groups["needs_action"]
                    ),
                    "discussions_actionable": len(
                        discussion_groups["needs_action"]
                    ),
                    "discussions_needs_action": len(
                        discussion_groups["needs_action"]
                    ),
                    "discussions_submitted": discussion_submitted_count,
                    "discussions_updates": len(discussion_groups["updates"]),
                    "discussions_missed": len(discussion_groups["missed"]),
                    "discussions_opens_soon": len(
                        discussion_groups["opens_soon"]
                    ),
                    "discussions_verification_needed": len(
                        discussion_groups["verification_needed"]
                    ),
                    "discussions_unread_messages": discussion_unread_messages,
                },
                "groups": groups,
                "discussions": {
                    # Retained for older frontends. It contains panel-worthy items,
                    # while the new frontend consumes the explicit groups below.
                    "attention": discussion_panel_items,
                    "groups": discussion_groups,
                    "all": visible_discussions,
                    "errors": dict(self.scraping.last_discussion_errors),
                    "summary": {
                        "total": len(visible_discussions),
                        "attention": len(discussion_groups["needs_action"]),
                        "actionable": len(discussion_groups["needs_action"]),
                        "needs_action": len(discussion_groups["needs_action"]),
                        "updates": len(discussion_groups["updates"]),
                        "submitted": discussion_submitted_count,
                        "missed": len(discussion_groups["missed"]),
                        "opens_soon": len(discussion_groups["opens_soon"]),
                        "verification_needed": len(
                            discussion_groups["verification_needed"]
                        ),
                        "closed": len(discussion_groups["closed"]),
                        "unread_messages": discussion_unread_messages,
                    },
                },
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
