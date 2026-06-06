from parsers.date_parser import extract_due_date_iso

def test_extract_due_date_iso_returns_value():
    raw = "Tarea 2 - entrega 10 abr en 23:59"
    result = extract_due_date_iso(raw)
    assert result is not None