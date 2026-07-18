from src.services.scraping_service import ScrapingService


def make_service() -> ScrapingService:
    # These tests exercise pure filtering helpers and do not need a live
    # Canvas connection, so avoid running ScrapingService.__init__.
    return ScrapingService.__new__(ScrapingService)


def course(
    course_id: str,
    name: str,
    code: str,
    term_id: int,
    *,
    workflow_state: str = "available",
) -> dict:
    return {
        "course_id": course_id,
        "course_name": name,
        "course_code": code,
        "workflow_state": workflow_state,
        "term": {
            "id": term_id,
            "name": "2-Semestre-Trimestre",
        },
        "start_at": "2026-07-01T00:00:00Z",
        "end_at": "2026-11-30T23:59:59Z",
    }


def test_extracts_standard_hyphenated_code() -> None:
    service = make_service()
    item = course(
        "203394",
        "ARQUITECTURA DE COMPUTADORAS II - 22026-1900-040-A",
        "220261900040A",
        122,
    )

    assert service._extract_term_key(item) == (2026, 2)


def test_extracts_irregular_three_digit_block_and_numeric_section() -> None:
    service = make_service()
    item = course(
        "210758",
        "ANÁLISIS DE SISTEMAS II - 22026-090-037-3",
        "220260900373",
        122,
    )

    assert service._extract_term_key(item) == (2026, 2)


def test_extracts_compact_canvas_course_code() -> None:
    service = make_service()
    item = course(
        "210758",
        "ANÁLISIS DE SISTEMAS II",
        "220260900373",
        122,
    )

    assert service._extract_term_key(item) == (2026, 2)


def test_filter_keeps_every_course_in_latest_canvas_term() -> None:
    service = make_service()

    current_courses = [
        course(
            "203394",
            "ARQUITECTURA DE COMPUTADORAS II - 22026-1900-040-A",
            "220261900040A",
            122,
        ),
        course(
            "210758",
            "ANÁLISIS DE SISTEMAS II - formato excepcional",
            "CODIGO-SIN-PATRON",
            122,
        ),
    ]

    previous_course = {
        **course(
            "188376",
            "SISTEMAS OPERATIVOS II - 12026-1900-033-A",
            "120261900033A",
            123,
        ),
        "term": {
            "id": 123,
            "name": "1-Semestre-Trimestre",
        },
        "start_at": "2026-01-01T00:00:00Z",
        "end_at": "2026-06-30T23:59:59Z",
    }

    filtered = service._filter_current_term_courses(
        [previous_course, *current_courses]
    )

    assert {item["course_id"] for item in filtered} == {
        "203394",
        "210758",
    }
