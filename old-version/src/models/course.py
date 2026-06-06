from __future__ import annotations

from dataclasses import dataclass, asdict

@dataclass
class Course:
    course_name: str
    course_url: str
    course_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)