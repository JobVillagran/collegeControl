from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

@dataclass
class Snapshot:
    captured_at: str
    timezone: str
    courses: list[dict[str, Any]]
    assignments: list[dict[str, Any]]

    def to_dict(self) -> dict:
        return asdict(self)