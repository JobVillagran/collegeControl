from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from time import perf_counter
from typing import Callable

from config.settings import (
    ATHENA_COURSE_CACHE_FALLBACK,
    ATHENA_REFRESH_MAX_WORKERS,
    ATHENA_REFRESH_METRICS,
)
from src.services.cache_service import CacheService
from src.services.comparison_service import ComparisonService
from src.services.grade_analytics_service import GradeAnalyticsService
from src.services.scraping_service import ScrapingService


class CourseRefreshError(RuntimeError):
    pass


class DashboardService:
    """Build the dashboard with bounded course-level concurrency.

    Canvas calls inside a course keep their required order, but independent
    courses are processed in parallel. Each worker owns its own requests
    session, avoiding unsafe cross-thread Session sharing.
    """

    _refresh_lock = Lock()

    def __init__(
        self,
        *,
        scraping: ScrapingService | None = None,
        comparison: ComparisonService | None = None,
        cache: CacheService | None = None,
        grade_analytics: GradeAnalyticsService | None = None,
        max_workers: int | None = None,
        scraping_factory: Callable[[], ScrapingService] | None = None,
        allow_course_cache_fallback: bool | None = None,
    ) -> None:
        self.scraping = scraping or ScrapingService()
        self.comparison = comparison or ComparisonService()
        self.cache = cache or CacheService()
        self.grade_analytics = grade_analytics or GradeAnalyticsService()
        self.max_workers = max(1, min(8, max_workers or ATHENA_REFRESH_MAX_WORKERS))
        self.scraping_factory = scraping_factory or ScrapingService
        self.allow_course_cache_fallback = (
            ATHENA_COURSE_CACHE_FALLBACK
            if allow_course_cache_fallback is None
            else allow_course_cache_fallback
        )

    def get_dashboard(self, force_refresh: bool = False) -> dict:
        if not force_refresh:
            cached = self.cache.load_dashboard()
            if cached:
                return cached

        return self.refresh_dashboard()

    def refresh_dashboard(self) -> dict:
        acquired = self._refresh_lock.acquire(blocking=False)
        if not acquired:
            cached = self.cache.load_dashboard()
            if cached:
                response = deepcopy(cached)
                previous_sync = response.get("sync") or {}
                response["sync"] = {
                    **previous_sync,
                    "status": previous_sync.get("status") or "healthy",
                    "source": "cache_while_refreshing",
                    "refresh_in_progress": True,
                    "message": "Another refresh is already running. Showing the latest cache.",
                }
                self._close_scraping()
                return response

            # First startup with no cache: wait for the active refresh. If it
            # succeeds, reuse its cache; if it fails, perform one new attempt.
            self._refresh_lock.acquire()
            self._refresh_lock.release()
            cached = self.cache.load_dashboard()
            if cached:
                self._close_scraping()
                return cached
            acquired = self._refresh_lock.acquire()

        try:
            return self._perform_refresh()
        except Exception as exc:
            self.cache.mark_error(str(exc))
            cached = self.cache.load_dashboard()
            if cached:
                response = deepcopy(cached)
                response["sync"] = {
                    "status": "error",
                    "source": "cache_fallback",
                    "last_synced_at": (cached.get("sync") or {}).get(
                        "last_synced_at"
                    ),
                    "message": (
                        "Live sync failed. Showing cached data. "
                        f"Error: {exc}"
                    ),
                }
                return response
            raise
        finally:
            self._close_scraping()
            if acquired:
                self._refresh_lock.release()

    def _close_scraping(self) -> None:
        close = getattr(self.scraping, "close", None)
        if callable(close):
            close()

    def _perform_refresh(self) -> dict:
        refresh_started = perf_counter()
        courses = self.scraping.get_courses()
        current_user = self.scraping.canvas_api.get_current_user_profile()

        (
            course_results,
            course_metrics,
            cached_course_ids,
            discussion_errors,
        ) = self._collect_courses_concurrently(
            courses,
            current_user=current_user,
        )

        assignments_by_course = {
            course_id: result["assignments"]
            for course_id, result in course_results.items()
        }
        discussions_by_course = {
            course_id: result["discussions"]
            for course_id, result in course_results.items()
        }
        assignment_groups_by_course = {
            course_id: result["assignment_groups"]
            for course_id, result in course_results.items()
        }
        self.scraping.last_discussion_errors = dict(discussion_errors)

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
                assignments=assignments_by_course.get(
                    str(course["course_id"]),
                    [],
                ),
                assignment_groups=assignment_groups_by_course.get(
                    str(course["course_id"]),
                    [],
                ),
            )
            for course in courses
        ]

        refresh_duration = round(perf_counter() - refresh_started, 3)
        cached_count = len(cached_course_ids)
        # Preserve the existing healthy/error status contract. Additional
        # fields explain that only part of the refresh used stale data.
        sync_status = "error" if cached_count else "healthy"
        sync_source = (
            "canvas_api_with_course_cache"
            if cached_count
            else "canvas_api"
        )
        sync_message = (
            f"Live data loaded; {cached_count} course(s) used a cached fallback."
            if cached_count
            else "Live data loaded successfully."
        )

        sync_payload = {
            "status": sync_status,
            "source": sync_source,
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
            "message": sync_message,
            "degraded": bool(cached_count),
        }
        if ATHENA_REFRESH_METRICS:
            sync_payload["metrics"] = {
                "duration_seconds": refresh_duration,
                "configured_max_workers": self.max_workers,
                "effective_workers": min(self.max_workers, len(courses)),
                "course_count": len(courses),
                "live_course_count": len(courses) - cached_count,
                "cached_course_count": cached_count,
                "cached_course_ids": cached_course_ids,
                "course_timings": course_metrics,
            }

        payload = {
            "sync": sync_payload,
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
                    [
                        course
                        for course in course_summaries
                        if course.get("course_finished")
                    ]
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
                "errors": dict(discussion_errors),
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
        if cached_count:
            self.cache.mark_degraded(sync_message)
        else:
            self.cache.mark_success(message=sync_message)
        return payload

    def _collect_courses_concurrently(
        self,
        courses: list[dict],
        *,
        current_user: dict,
    ) -> tuple[dict[str, dict], list[dict], list[str], dict[str, str]]:
        if not courses:
            return {}, [], [], {}

        effective_workers = min(self.max_workers, len(courses))
        results: dict[str, dict] = {}
        metrics_by_course: dict[str, dict] = {}
        cached_course_ids: list[str] = []
        discussion_errors: dict[str, str] = {}

        with ThreadPoolExecutor(
            max_workers=effective_workers,
            thread_name_prefix="athena-course",
        ) as executor:
            future_to_course: dict[Future, dict] = {
                executor.submit(
                    self._collect_single_course,
                    course,
                    current_user,
                ): course
                for course in courses
            }

            for future in as_completed(future_to_course):
                course = future_to_course[future]
                course_id = str(course["course_id"])
                try:
                    result, duration_seconds = future.result()
                    result["course_fingerprint"] = self._course_fingerprint(course)
                    self.cache.save_course_snapshot(course_id, result)
                    source = "live"
                except Exception as exc:
                    fallback = (
                        self.cache.load_course_snapshot(course_id)
                        if self.allow_course_cache_fallback
                        else None
                    )
                    if (
                        fallback is None
                        or not self._snapshot_matches_course(
                            fallback["data"],
                            course,
                        )
                    ):
                        raise CourseRefreshError(
                            f"Course {course_id} ({course.get('course_name')}): {exc}"
                        ) from exc

                    result = deepcopy(fallback["data"])
                    duration_seconds = None
                    source = "course_cache_fallback"
                    cached_course_ids.append(course_id)
                    result["fallback_error"] = str(exc)
                    result["fallback_cached_at"] = fallback.get("cached_at")

                results[course_id] = result
                if result.get("discussion_error"):
                    discussion_errors[course_id] = str(result["discussion_error"])

                metrics_by_course[course_id] = {
                    "course_id": course_id,
                    "course_name": course.get("course_name"),
                    "source": source,
                    "duration_seconds": (
                        round(duration_seconds, 3)
                        if duration_seconds is not None
                        else None
                    ),
                    "assignment_count": len(result.get("assignments") or []),
                    "discussion_count": len(result.get("discussions") or []),
                    "assignment_group_count": len(
                        result.get("assignment_groups") or []
                    ),
                }

        ordered_results = {
            str(course["course_id"]): results[str(course["course_id"])]
            for course in courses
        }
        ordered_metrics = [
            metrics_by_course[str(course["course_id"])]
            for course in courses
        ]
        ordered_cached_ids = [
            str(course["course_id"])
            for course in courses
            if str(course["course_id"]) in set(cached_course_ids)
        ]
        ordered_discussion_errors = {
            str(course["course_id"]): discussion_errors[str(course["course_id"])]
            for course in courses
            if str(course["course_id"]) in discussion_errors
        }
        return (
            ordered_results,
            ordered_metrics,
            ordered_cached_ids,
            ordered_discussion_errors,
        )

    def _collect_single_course(
        self,
        course: dict,
        current_user: dict,
    ) -> tuple[dict, float]:
        started = perf_counter()
        worker = self.scraping_factory()
        try:
            result = worker.collect_course_data(
                course,
                current_user=current_user,
            )
            return result, perf_counter() - started
        finally:
            close = getattr(worker, "close", None)
            if callable(close):
                close()

    @staticmethod
    def _course_fingerprint(course: dict) -> dict:
        term = course.get("term") or {}
        term_id = term.get("id") if isinstance(term, dict) else None
        return {
            "course_id": str(course.get("course_id") or ""),
            "course_code": str(course.get("course_code") or ""),
            "term_id": str(term_id) if term_id is not None else None,
        }

    def _snapshot_matches_course(self, snapshot: dict, course: dict) -> bool:
        return snapshot.get("course_fingerprint") == self._course_fingerprint(course)
