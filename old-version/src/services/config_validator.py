from __future__ import annotations

from backend.config.settings import (
    CANVAS_BASE_URL,
    CANVAS_API_TOKEN,
    SEND_EMAIL,
    EMAIL_SMTP_HOST,
    EMAIL_SMTP_PORT,
    EMAIL_SENDER,
    EMAIL_APP_PASSWORD,
    EMAIL_RECIPIENT,
)


def validate_required_config() -> None:
    missing: list[str] = []

    if not CANVAS_BASE_URL:
        missing.append("CANVAS_BASE_URL")
    if not CANVAS_API_TOKEN:
        missing.append("CANVAS_API_TOKEN")

    if SEND_EMAIL:
        if not EMAIL_SMTP_HOST:
            missing.append("EMAIL_SMTP_HOST")
        if not EMAIL_SMTP_PORT:
            missing.append("EMAIL_SMTP_PORT")
        if not EMAIL_SENDER:
            missing.append("EMAIL_SENDER")
        if not EMAIL_APP_PASSWORD:
            missing.append("EMAIL_APP_PASSWORD")
        if not EMAIL_RECIPIENT:
            missing.append("EMAIL_RECIPIENT")

    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )