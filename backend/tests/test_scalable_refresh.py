from __future__ import annotations

from copy import deepcopy
from threading import Lock
from time import sleep

import pytest

from src.services.dashboard_service import CourseRefreshError, DashboardService
from src.services.scraping_service import ScrapingService


def make_course(course_id: str) -> dict:
    return {
        "course_id": course_id,
        "course_name": f"COURSE {course_id} - 22026-1900-040-A",
        "course_code": f"2202619000{course_id}A",
        "course_url": f"https://canvas.example/courses/{course_id}",
        "workflow_state": "available",
        "term": {"id": 122, "name": "2-Semestre-Trimestre"},
    }


class MemoryCache:
    def __init__(self) -> None:
        self.course_snapshots: dict[str, dict] = {}
        self.dashboard: dict | None = None
        self.status: tuple[str, str] | None = None

    def load_dashboard(self) -> dict | None:
        return deepcopy(self.dashboard)

    def save_dashboard(self, payload: dict) -> None:
        self.dashboard = deepcopy(payload)

    def mark_success(self, *, message: str) -> None:
        self.status = ("healthy", message)

    def mark_degraded(self, message: str) -> None:
        self.status = ("degraded", message)

    def mark_error(self, message: str) -> None:
        self.status = ("error", message)

    def save_course_snapshot(self, course_id: str, payload: dict) -> None:
        self.course_snapshots[str(course_id)] = {
            "cached_at": "2026-07-16T00:00:00+00:00",
            "data": deepcopy(payload),
        }

    def load_course_snapshot(self, course_id: str) -> dict | None:
        value = self.course_snapshots.get(str(course_id))
        return deepcopy(value) if value else None


class ConcurrencyTracker:
    def __init__(self) -> None:
        self.lock = Lock()
        self.active = 0
        self.maximum = 0
        self.closed = 0

    def enter(self) -> None:
        with self.lock:
            self.active += 1
            self.maximum = max(self.maximum, self.active)

    def exit(self) -> None:
        with self.lock:
            self.active -= 1

    def mark_closed(self) -> None:
        with self.lock:
            self.closed += 1


class Worker:
    def __init__(
        self,
        tracker: ConcurrencyTracker,
        *,
        failing_course_id: str | None = None,
    ) -> None:
        self.tracker = tracker
        self.failing_course_id = failing_course_id

    def collect_course_data(self, course: dict, *, current_user: dict) -> dict:
        self.tracker.enter()
        try:
            sleep(0.04)
            course_id = str(course["course_id"])
            if course_id == self.failing_course_id:
                raise RuntimeError("simulated Canvas failure")
            return {
                "course_id": course_id,
                "assignments": [],
                "discussions": [],
                "assignment_groups": [],
                "discussion_error": None,
                "grade_page_available": True,
            }
        finally:
            self.tracker.exit()

    def close(self) -> None:
        self.tracker.mark_closed()


class RootScrapingStub:
    def close(self) -> None:
        pass


class FakeCanvasForSingleCourse:
    def __init__(self) -> None:
        self.grade_page_calls = 0

    def get_grade_page_payload_for_course(self, course_id: str) -> dict:
        self.grade_page_calls += 1
        return {
            "available": True,
            "assignments_by_id": {},
            "submissions_by_assignment_id": {},
            "assignment_groups": [],
        }

    def get_assignments_for_course(
        self,
        course_id: str,
        course_name: str,
        course_url: str,
    ) -> list[dict]:
        return []

    def get_discussion_topics_for_course(
        self,
        course_id: str,
        course_name: str,
        course_url: str,
    ) -> list[dict]:
        return []

    def get_assignment_groups_for_course(self, course_id: str) -> list[dict]:
        return []

    def close(self) -> None:
        pass


def make_dashboard_service(
    *,
    cache: MemoryCache,
    factory,
    max_workers: int = 3,
    allow_fallback: bool = True,
) -> DashboardService:
    return DashboardService(
        scraping=RootScrapingStub(),
        cache=cache,
        max_workers=max_workers,
        scraping_factory=factory,
        allow_course_cache_fallback=allow_fallback,
    )


def test_refresh_uses_bounded_course_concurrency_and_preserves_order() -> None:
    courses = [make_course(str(index)) for index in range(1, 7)]
    tracker = ConcurrencyTracker()
    cache = MemoryCache()
    service = make_dashboard_service(
        cache=cache,
        max_workers=3,
        factory=lambda: Worker(tracker),
    )

    results, metrics, cached_ids, errors = service._collect_courses_concurrently(
        courses,
        current_user={"id": "99", "name": "Student"},
    )

    assert list(results) == ["1", "2", "3", "4", "5", "6"]
    assert [item["course_id"] for item in metrics] == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
    ]
    assert 2 <= tracker.maximum <= 3
    assert tracker.closed == 6
    assert cached_ids == []
    assert errors == {}


def test_failed_course_uses_matching_course_snapshot() -> None:
    courses = [make_course("1"), make_course("2")]
    tracker = ConcurrencyTracker()
    cache = MemoryCache()
    service = make_dashboard_service(
        cache=cache,
        factory=lambda: Worker(tracker, failing_course_id="2"),
    )

    cached_result = {
        "course_id": "2",
        "assignments": [{"assignment_id": "cached"}],
        "discussions": [],
        "assignment_groups": [],
        "discussion_error": None,
        "grade_page_available": True,
        "course_fingerprint": service._course_fingerprint(courses[1]),
    }
    cache.save_course_snapshot("2", cached_result)

    results, metrics, cached_ids, _ = service._collect_courses_concurrently(
        courses,
        current_user={"id": "99", "name": "Student"},
    )

    assert cached_ids == ["2"]
    assert results["2"]["assignments"] == [{"assignment_id": "cached"}]
    assert metrics[1]["source"] == "course_cache_fallback"
    assert "simulated Canvas failure" in results["2"]["fallback_error"]


def test_failed_course_without_valid_snapshot_fails_the_refresh() -> None:
    course = make_course("2")
    tracker = ConcurrencyTracker()
    cache = MemoryCache()
    service = make_dashboard_service(
        cache=cache,
        factory=lambda: Worker(tracker, failing_course_id="2"),
    )

    cache.save_course_snapshot(
        "2",
        {
            "course_id": "2",
            "assignments": [],
            "discussions": [],
            "assignment_groups": [],
            "course_fingerprint": {
                "course_id": "2",
                "course_code": "old-course-code",
                "term_id": "121",
            },
        },
    )

    with pytest.raises(CourseRefreshError):
        service._collect_courses_concurrently(
            [course],
            current_user={"id": "99", "name": "Student"},
        )


def test_single_course_collection_reads_grade_page_once() -> None:
    canvas = FakeCanvasForSingleCourse()
    service = ScrapingService(canvas_api=canvas)

    result = service.collect_course_data(
        make_course("1"),
        current_user={"id": "99", "name": "Student"},
    )

    assert canvas.grade_page_calls == 1
    assert result["assignments"] == []
    assert result["discussions"] == []
    assert result["assignment_groups"] == []


class CurrentUserCanvasStub:
    def get_current_user_profile(self) -> dict:
        return {"id": "99", "name": "Student"}


class FullRootScrapingStub(RootScrapingStub):
    def __init__(self, courses: list[dict]) -> None:
        self.courses = courses
        self.canvas_api = CurrentUserCanvasStub()
        self.last_discussion_errors: dict[str, str] = {}

    def get_courses(self) -> list[dict]:
        return deepcopy(self.courses)

    def _filter_dashboard_assignments(self, assignments: list[dict]) -> list[dict]:
        return assignments

    def discussion_to_dashboard_assignment(self, discussion: dict) -> None:
        return None


class EmptyComparisonStub:
    def build_groups(self, assignments: list[dict]) -> dict:
        return {
            "act_now": [],
            "this_week": [],
            "next_week": [],
            "third_week": [],
            "no_due_date": [],
            "opens_soon": [],
            "urgent_projects": [],
            "submitted": [],
        }

    def build_discussion_groups(self, discussions: list[dict]) -> dict:
        return {
            "needs_action": [],
            "updates": [],
            "missed": [],
            "verification_needed": [],
            "submitted": [],
            "opens_soon": [],
            "closed": [],
        }


class GradeAnalyticsStub:
    def analyze_course(
        self,
        *,
        course: dict,
        assignments: list[dict],
        assignment_groups: list[dict],
    ) -> dict:
        return {
            "course_id": str(course["course_id"]),
            "course_name": course["course_name"],
            "risk_level": "healthy",
            "course_finished": False,
            "course_result": None,
            "hidden_or_review_count": 0,
            "attendance": {"level": "healthy"},
        }


def test_full_refresh_preserves_dashboard_contract() -> None:
    courses = [make_course("1"), make_course("2")]
    tracker = ConcurrencyTracker()
    cache = MemoryCache()
    service = DashboardService(
        scraping=FullRootScrapingStub(courses),
        comparison=EmptyComparisonStub(),
        cache=cache,
        grade_analytics=GradeAnalyticsStub(),
        max_workers=2,
        scraping_factory=lambda: Worker(tracker),
    )

    payload = service.refresh_dashboard()

    assert set(payload) == {
        "sync",
        "summary",
        "groups",
        "discussions",
        "courses",
    }
    assert payload["sync"]["status"] == "healthy"
    assert payload["sync"]["metrics"]["course_count"] == 2
    assert [course["course_id"] for course in payload["courses"]] == ["1", "2"]
    assert cache.status is not None and cache.status[0] == "healthy"
