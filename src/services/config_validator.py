from __future__ import annotations

from config.settings import (
    CANVAS_LOGIN_URL,
    CANVAS_EMAIL,
    CANVAS_PASSWORD,
    SEND_EMAIL,
    EMAIL_SMTP_HOST,
    EMAIL_SMTP_PORT,
    EMAIL_SENDER,
    EMAIL_APP_PASSWORD,
    EMAIL_RECIPIENT,
)


def validate_required_config() -> None:
    missing: list[str] = []

    if not CANVAS_LOGIN_URL:
        missing.append("CANVAS_LOGIN_URL")
    if not CANVAS_EMAIL:
        missing.append("CANVAS_EMAIL")
    if not CANVAS_PASSWORD:
        missing.append("CANVAS_PASSWORD")

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