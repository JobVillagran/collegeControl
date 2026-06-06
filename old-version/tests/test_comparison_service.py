from backend.src.services.comparison_service import ComparisonService

def test_compare_detects_new_assignment():
    service = ComparisonService()

    previous = {"assignments": []}
    current = {
        "assignments": [
            {
                "course_name": "Arquitectura",
                "assignment_name": "Tarea 1",
                "due_date_iso": "2026-04-10T23:59:00-06:00",
                "score": None,
            }
        ]
    }

    result = service.compare(previous, current)
    assert len(result["new_assignments"]) == 1