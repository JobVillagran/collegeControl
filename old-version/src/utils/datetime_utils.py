from __future__ import annotations

from datetime import datetime
import pytz
from backend.config.settings import APP_TIMEZONE

def now_local() -> datetime:
    tz = pytz.timezone(APP_TIMEZONE)
    return datetime.now(tz)

def now_iso() -> str:
    return now_local().isoformat()