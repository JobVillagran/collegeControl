from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status

from config.settings import APP_ACCESS_KEY


def verify_app_key(x_app_key: str | None = Header(default=None, alias="X-App-Key")) -> None:
    configured_key = (APP_ACCESS_KEY or "").strip()
    incoming_key = (x_app_key or "").strip()

    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="APP_ACCESS_KEY is not configured on the server.",
        )

    if not incoming_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access key.",
        )

    if not secrets.compare_digest(incoming_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access key.",
        )