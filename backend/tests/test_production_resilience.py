from __future__ import annotations

from requests.adapters import HTTPAdapter

from src.services.canvas_api_service import CanvasAPIService
from src.services.scraping_service import ScrapingService


class CourseDiscoveryCanvasStub:
    def __init__(self) -> None:
        self.validate_calls = 0
        self.course_calls = 0

    def validate_connection(self) -> dict:
        self.validate_calls += 1
        raise AssertionError("get_courses must not call validate_connection first")

    def get_courses(self) -> list[dict]:
        self.course_calls += 1
        return [
            {
                "course_id": "210758",
                "course_name": "ANÁLISIS DE SISTEMAS II - 22026-090-037-3",
                "course_code": "220260900373",
                "course_url": "https://canvas.example/courses/210758",
                "workflow_state": "available",
                "term": {"id": 122, "name": "2-Semestre-Trimestre"},
            }
        ]

    def close(self) -> None:
        pass


def test_course_discovery_does_not_make_redundant_profile_request() -> None:
    canvas = CourseDiscoveryCanvasStub()
    service = ScrapingService(canvas_api=canvas)

    courses = service.get_courses()

    assert canvas.validate_calls == 0
    assert canvas.course_calls == 1
    assert [course["course_id"] for course in courses] == ["210758"]


def test_canvas_adapter_does_not_retry_socket_read_timeouts() -> None:
    service = CanvasAPIService()
    try:
        adapter = service.session.get_adapter("https://")
        assert isinstance(adapter, HTTPAdapter)
        assert adapter.max_retries.read == 0
        assert service.request_timeout[0] >= 1
        assert service.request_timeout[1] >= 5
        assert service.profile_timeout[1] <= service.request_timeout[1]
    finally:
        service.close()
