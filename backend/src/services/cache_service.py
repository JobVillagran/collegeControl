from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from config.settings import COURSE_CACHE_DIR, DASHBOARD_CACHE_FILE, SYNC_STATUS_FILE
from src.utils.file_utils import read_json, write_json


class CacheService:
    COURSE_CACHE_VERSION = 1

    def load_dashboard(self) -> dict | None:
        return read_json(DASHBOARD_CACHE_FILE, default=None)

    def save_dashboard(self, payload: dict) -> None:
        write_json(DASHBOARD_CACHE_FILE, payload)

    def save_sync_status(self, status: dict) -> None:
        write_json(SYNC_STATUS_FILE, status)

    def load_sync_status(self) -> dict | None:
        return read_json(SYNC_STATUS_FILE, default=None)

    def save_course_snapshot(self, course_id: str, payload: dict) -> None:
        write_json(
            self._course_cache_file(course_id),
            {
                "version": self.COURSE_CACHE_VERSION,
                "course_id": str(course_id),
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "data": payload,
            },
        )

    def load_course_snapshot(self, course_id: str) -> dict | None:
        envelope = read_json(self._course_cache_file(course_id), default=None)
        if not isinstance(envelope, dict):
            return None

        if envelope.get("version") != self.COURSE_CACHE_VERSION:
            return None

        if str(envelope.get("course_id") or "") != str(course_id):
            return None

        data = envelope.get("data")
        if not isinstance(data, dict):
            return None

        return {
            "cached_at": envelope.get("cached_at"),
            "data": data,
        }

    def mark_success(self, *, message: str = "Live sync completed successfully.") -> None:
        self.save_sync_status(
            {
                "status": "healthy",
                "last_successful_sync": datetime.now(timezone.utc).isoformat(),
                "message": message,
            }
        )

    def mark_degraded(self, message: str) -> None:
        current = self.load_sync_status() or {}
        current["status"] = "error"
        current["degraded"] = True
        current["message"] = message
        current["last_degraded_sync"] = datetime.now(timezone.utc).isoformat()
        self.save_sync_status(current)

    def mark_error(self, message: str) -> None:
        current = self.load_sync_status() or {}
        current["status"] = "error"
        current["message"] = message
        current["last_error_at"] = datetime.now(timezone.utc).isoformat()
        self.save_sync_status(current)

    @staticmethod
    def _course_cache_file(course_id: str) -> Path:
        safe_course_id = "".join(
            character
            for character in str(course_id)
            if character.isalnum() or character in {"-", "_"}
        )
        if not safe_course_id:
            raise ValueError("course_id cannot be empty")
        return COURSE_CACHE_DIR / f"{safe_course_id}.json"
