from __future__ import annotations

from config.settings import (
    APP_TIMEZONE,
    CURRENT_SNAPSHOT_FILE,
    PREVIOUS_SNAPSHOT_FILE,
)
from src.models.snapshot import Snapshot
from src.utils.datetime_utils import now_iso
from src.utils.file_utils import read_json, write_json


class SnapshotService:
    def build_snapshot(self, courses: list[dict], assignments: list[dict]) -> dict:
        snapshot = Snapshot(
            captured_at=now_iso(),
            timezone=APP_TIMEZONE,
            courses=courses,
            assignments=assignments,
        )
        return snapshot.to_dict()

    def load_previous_snapshot(self) -> dict:
        return read_json(
            PREVIOUS_SNAPSHOT_FILE,
            default={"courses": [], "assignments": []},
        )

    def save_current_snapshot(self, snapshot: dict) -> None:
        existing_current = read_json(CURRENT_SNAPSHOT_FILE, default=None)
        if existing_current:
            write_json(PREVIOUS_SNAPSHOT_FILE, existing_current)
        write_json(CURRENT_SNAPSHOT_FILE, snapshot)