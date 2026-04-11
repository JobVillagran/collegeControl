from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
PROCESSED_DIR = DATA_DIR / "processed"
LOGS_DIR = DATA_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
TEMPLATES_DIR = BASE_DIR / "src" / "templates"
STORAGE_DIR = BASE_DIR / "storage"

for path in [DATA_DIR, SNAPSHOTS_DIR, PROCESSED_DIR, LOGS_DIR, REPORTS_DIR, STORAGE_DIR]:
    path.mkdir(parents=True, exist_ok=True)


def get_env_str(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    if not value:
        return default
    return int(value)


def get_env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip().lower()
    if not value:
        return default
    return value == "true"


CANVAS_BASE_URL = get_env_str("CANVAS_BASE_URL")
CANVAS_API_TOKEN = get_env_str("CANVAS_API_TOKEN")

APP_TIMEZONE = get_env_str("APP_TIMEZONE", "America/Guatemala")
DAYS_AHEAD_WARNING = get_env_int("DAYS_AHEAD_WARNING", 3)
SEND_EMAIL = get_env_bool("SEND_EMAIL", True)

EMAIL_SMTP_HOST = get_env_str("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT = get_env_int("EMAIL_SMTP_PORT", 587)
EMAIL_SENDER = get_env_str("EMAIL_SENDER")
EMAIL_APP_PASSWORD = get_env_str("EMAIL_APP_PASSWORD")
EMAIL_RECIPIENT = get_env_str("EMAIL_RECIPIENT")

CURRENT_SNAPSHOT_FILE = SNAPSHOTS_DIR / "current_snapshot.json"
PREVIOUS_SNAPSHOT_FILE = SNAPSHOTS_DIR / "previous_snapshot.json"

CHANGES_FILE = PROCESSED_DIR / "changes.json"
UPCOMING_FILE = PROCESSED_DIR / "upcoming.json"
SUMMARY_PAYLOAD_FILE = PROCESSED_DIR / "summary_payload.json"

SUMMARY_HTML_FILE = REPORTS_DIR / "latest_summary.html"
SUMMARY_TXT_FILE = REPORTS_DIR / "latest_summary.txt"

APP_LOG_FILE = LOGS_DIR / "app.log"

NOTIFICATION_STATE_FILE = STORAGE_DIR / "notification_state.json"