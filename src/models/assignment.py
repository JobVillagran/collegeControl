from __future__ import annotations

from dataclasses import dataclass, asdict

@dataclass
class Assignment:
    course_name: str
    course_url: str
    assignment_name: str
    due_date_raw: str | None
    due_date_iso: str | None
    status: str
    score: str | None = None
    assignment_url: str | None = None

    def unique_key(self) -> str:
        return f"{self.course_name}::{self.assignment_name}"

    def to_dict(self) -> dict:
        return asdict(self)