from __future__ import annotations

import re
from datetime import datetime
from dateutil import parser as date_parser
import pytz
from backend.config.settings import APP_TIMEZONE

SPANISH_MONTHS = {
    "ene": "Jan",
    "feb": "Feb",
    "mar": "Mar",
    "abr": "Apr",
    "may": "May",
    "jun": "Jun",
    "jul": "Jul",
    "ago": "Aug",
    "sep": "Sep",
    "oct": "Oct",
    "nov": "Nov",
    "dic": "Dec",
}

def normalize_spanish_date_text(text: str) -> str:
    normalized = text.lower()
    for es, en in SPANISH_MONTHS.items():
        normalized = re.sub(rf"\b{es}\b", en, normalized, flags=re.IGNORECASE)
    return normalized

def extract_due_date_iso(raw_text: str | None) -> str | None:
    if not raw_text:
        return None

    normalized = normalize_spanish_date_text(raw_text)

    match = re.search(r"(\d{1,2}\s+[A-Za-z]{3}.*?\d{1,2}:\d{2})", normalized)
    if not match:
        return None

    date_fragment = match.group(1)
    current_year = datetime.now().year
    date_fragment = f"{date_fragment} {current_year}"

    try:
        parsed = date_parser.parse(date_fragment, fuzzy=True, dayfirst=True)
        tz = pytz.timezone(APP_TIMEZONE)
        localized = tz.localize(parsed)
        return localized.isoformat()
    except Exception:
        return None