from __future__ import annotations

from datetime import datetime, timezone

from config.settings import DASHBOARD_CACHE_FILE, SYNC_STATUS_FILE
from src.utils.file_utils import read_json, write_json


class CacheService:
    def load_dashboard(self) -> dict | None:
        return read_json(DASHBOARD_CACHE_FILE, default=None)

    def save_dashboard(self, payload: dict) -> None:
        write_json(DASHBOARD_CACHE_FILE, payload)

    def save_sync_status(self, status: dict) -> None:
        write_json(SYNC_STATUS_FILE, status)

    def load_sync_status(self) -> dict | None:
        return read_json(SYNC_STATUS_FILE, default=None)

    def mark_success(self) -> None:
        self.save_sync_status(
            {
                "status": "healthy",
                "last_successful_sync": datetime.now(timezone.utc).isoformat(),
                "message": "Live sync completed successfully."
            }
        )

    def mark_error(self, message: str) -> None:
        current = self.load_sync_status() or {}
        current["status"] = "error"
        current["message"] = message
        current["last_error_at"] = datetime.now(timezone.utc).isoformat()
        self.save_sync_status(current)