from __future__ import annotations

from fastapi import Header, HTTPException, status

from config.settings import APP_ACCESS_KEY


def verify_app_key(x_app_key: str | None = Header(default=None, alias="X-App-Key")) -> None:
    if not APP_ACCESS_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="APP_ACCESS_KEY is not configured on the server.",
        )

    if not x_app_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access key.",
        )

    if x_app_key != APP_ACCESS_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access key.",
        )