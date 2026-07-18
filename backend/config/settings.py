from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


def _env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default

    try:
        value = int(raw)
    except ValueError:
        return default

    return max(minimum, min(maximum, value))


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().casefold()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
COURSE_CACHE_DIR = CACHE_DIR / "courses"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
COURSE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

CANVAS_BASE_URL = os.getenv("CANVAS_BASE_URL", "").strip()
CANVAS_API_TOKEN = os.getenv("CANVAS_API_TOKEN", "").strip()

# Fail fast on a stalled upstream connection. Status-code retries remain enabled,
# but socket read timeouts are not retried because three 30-second reads can
# make a single frontend request hang for roughly 90 seconds.
CANVAS_CONNECT_TIMEOUT_SECONDS = _env_int(
    "CANVAS_CONNECT_TIMEOUT_SECONDS",
    5,
    minimum=1,
    maximum=30,
)
CANVAS_READ_TIMEOUT_SECONDS = _env_int(
    "CANVAS_READ_TIMEOUT_SECONDS",
    20,
    minimum=5,
    maximum=120,
)
CANVAS_PROFILE_READ_TIMEOUT_SECONDS = _env_int(
    "CANVAS_PROFILE_READ_TIMEOUT_SECONDS",
    8,
    minimum=2,
    maximum=30,
)

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

DASHBOARD_CACHE_FILE = CACHE_DIR / "dashboard_cache.json"
SYNC_STATUS_FILE = CACHE_DIR / "sync_status.json"
COURSE_RULES_FILE = BASE_DIR / "config" / "course_rules.json"

# Refresh scalability controls. Defaults are deliberately conservative for
# Canvas and Render's free plan. The values are clamped to prevent accidental
# request storms.
ATHENA_REFRESH_MAX_WORKERS = _env_int(
    "ATHENA_REFRESH_MAX_WORKERS",
    3,
    minimum=1,
    maximum=8,
)
ATHENA_COURSE_CACHE_FALLBACK = _env_bool(
    "ATHENA_COURSE_CACHE_FALLBACK",
    True,
)
ATHENA_REFRESH_METRICS = _env_bool(
    "ATHENA_REFRESH_METRICS",
    True,
)

DEFAULT_PASSING_SCORE = int(os.getenv("DEFAULT_PASSING_SCORE", "61"))
DEFAULT_ZONE_POINTS = int(os.getenv("DEFAULT_ZONE_POINTS", "35"))
DEFAULT_PARTIAL_1_POINTS = int(os.getenv("DEFAULT_PARTIAL_1_POINTS", "10"))
DEFAULT_PARTIAL_2_POINTS = int(os.getenv("DEFAULT_PARTIAL_2_POINTS", "20"))
DEFAULT_FINAL_POINTS = int(os.getenv("DEFAULT_FINAL_POINTS", "35"))
DEFAULT_TOTAL_POINTS = int(os.getenv("DEFAULT_TOTAL_POINTS", "100"))
