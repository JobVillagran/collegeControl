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

for path in [DATA_DIR, SNAPSHOTS_DIR, PROCESSED_DIR, LOGS_DIR, REPORTS_DIR]:
    path.mkdir(parents=True, exist_ok=True)

CANVAS_BASE_URL = os.getenv("CANVAS_BASE_URL", "").strip()
CANVAS_LOGIN_URL = os.getenv("CANVAS_LOGIN_URL", "").strip()
CANVAS_EMAIL = os.getenv("CANVAS_EMAIL", "").strip()
CANVAS_PASSWORD = os.getenv("CANVAS_PASSWORD", "").strip()

APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Guatemala").strip()
HEADLESS = os.getenv("HEADLESS", "true").strip().lower() == "true"
DAYS_AHEAD_WARNING = int(os.getenv("DAYS_AHEAD_WARNING", "3"))

EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com").strip()
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "").strip()
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "").strip()
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "").strip()

CURRENT_SNAPSHOT_FILE = SNAPSHOTS_DIR / "current_snapshot.json"
PREVIOUS_SNAPSHOT_FILE = SNAPSHOTS_DIR / "previous_snapshot.json"

CHANGES_FILE = PROCESSED_DIR / "changes.json"
UPCOMING_FILE = PROCESSED_DIR / "upcoming.json"
SUMMARY_PAYLOAD_FILE = PROCESSED_DIR / "summary_payload.json"

SUMMARY_HTML_FILE = REPORTS_DIR / "latest_summary.html"
SUMMARY_TXT_FILE = REPORTS_DIR / "latest_summary.txt"

APP_LOG_FILE = LOGS_DIR / "app.log"

SEND_EMAIL = os.getenv("SEND_EMAIL", "true").strip().lower() == "true"