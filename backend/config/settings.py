from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CANVAS_BASE_URL = os.getenv("CANVAS_BASE_URL", "").strip()
CANVAS_API_TOKEN = os.getenv("CANVAS_API_TOKEN", "").strip()
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Guatemala").strip()

APP_ACCESS_KEY = os.getenv("APP_ACCESS_KEY", "").strip()

# Support both FRONTEND_ORIGINS and FRONTEND_ORIGIN
FRONTEND_ORIGINS_RAW = (
    os.getenv("FRONTEND_ORIGINS")
    or os.getenv("FRONTEND_ORIGIN")
    or "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174,https://jobvillagran.github.io"
).strip()

FRONTEND_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in FRONTEND_ORIGINS_RAW.split(",")
    if origin.strip()
]

DASHBOARD_CACHE_FILE = BASE_DIR / "data" / "cache" / "dashboard_cache.json"
SYNC_STATUS_FILE = BASE_DIR / "data" / "cache" / "sync_status.json"
COURSE_RULES_FILE = BASE_DIR / "config" / "course_rules.json"

DEFAULT_PASSING_SCORE = int(os.getenv("DEFAULT_PASSING_SCORE", "61"))
DEFAULT_ZONE_POINTS = int(os.getenv("DEFAULT_ZONE_POINTS", "35"))
DEFAULT_PARTIAL_1_POINTS = int(os.getenv("DEFAULT_PARTIAL_1_POINTS", "10"))
DEFAULT_PARTIAL_2_POINTS = int(os.getenv("DEFAULT_PARTIAL_2_POINTS", "20"))
DEFAULT_FINAL_POINTS = int(os.getenv("DEFAULT_FINAL_POINTS", "35"))
DEFAULT_TOTAL_POINTS = int(os.getenv("DEFAULT_TOTAL_POINTS", "100"))