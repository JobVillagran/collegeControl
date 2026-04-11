from __future__ import annotations

from config.settings import (
    CANVAS_LOGIN_URL,
    CANVAS_EMAIL,
    CANVAS_PASSWORD,
)

def validate_required_config() -> None:
    missing = []

    if not CANVAS_LOGIN_URL:
        missing.append("CANVAS_LOGIN_URL")
    if not CANVAS_EMAIL:
        missing.append("CANVAS_EMAIL")
    if not CANVAS_PASSWORD:
        missing.append("CANVAS_PASSWORD")

    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )