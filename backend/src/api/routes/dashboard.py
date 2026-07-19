from fastapi import APIRouter, Depends, Query

from src.security import verify_app_key
from src.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", dependencies=[Depends(verify_app_key)])
def get_dashboard(refresh: bool = Query(default=False)):
    service = DashboardService()
    return service.get_dashboard(force_refresh=refresh)


# === ATHENA TEMP RUNTIME DIAGNOSTICS START ===
from hashlib import sha256 as _diagnostic_sha256
from pathlib import Path as _DiagnosticPath
import json as _diagnostic_json
import os as _diagnostic_os
import time as _diagnostic_time

import requests as _diagnostic_requests

from config import settings as _diagnostic_settings


def _diagnostic_fingerprint(
    value: str | None,
) -> str | None:
    if not value:
        return None

    return _diagnostic_sha256(
        value.encode("utf-8")
    ).hexdigest()[:12]


def _diagnostic_secret_metadata(
    name: str,
    loaded_value: str | None,
) -> dict:
    loaded_value = loaded_value or ""
    process_value = _diagnostic_os.environ.get(name)

    process_value_exists = (
        process_value is not None
    )

    return {
        "configured": bool(loaded_value),
        "length": len(loaded_value),
        "fingerprint":
            _diagnostic_fingerprint(
                loaded_value
            ),
        "process_env_present":
            process_value_exists,
        "process_env_length":
            len(process_value or ""),
        "process_env_fingerprint":
            _diagnostic_fingerprint(
                process_value
            ),
        "loaded_matches_process_env": (
            loaded_value == process_value
            if process_value_exists
            else False
        ),
        "has_outer_whitespace": (
            bool(loaded_value)
            and loaded_value
            != loaded_value.strip()
        ),
        "looks_quoted": (
            len(loaded_value) >= 2
            and loaded_value[0]
            == loaded_value[-1]
            and loaded_value[0]
            in {"'", '"'}
        ),
    }


def _diagnostic_json_file(
    path: _DiagnosticPath,
) -> dict:
    result = {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": None,
        "json_valid": None,
        "keys": [],
        "course_count": None,
    }

    if not path.exists():
        return result

    result["size_bytes"] = (
        path.stat().st_size
    )

    try:
        payload = _diagnostic_json.loads(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )

        result["json_valid"] = True

        if isinstance(payload, dict):
            result["keys"] = sorted(
                payload.keys()
            )

            courses = payload.get(
                "courses"
            )

            if isinstance(courses, list):
                result["course_count"] = (
                    len(courses)
                )

    except Exception as exc:
        result["json_valid"] = False
        result["error_type"] = (
            type(exc).__name__
        )

    return result


def _diagnostic_canvas_check(
    path: str,
    params: dict | None = None,
) -> dict:
    base_url = (
        _diagnostic_settings
        .CANVAS_BASE_URL
        .rstrip("/")
    )

    token = (
        _diagnostic_settings
        .CANVAS_API_TOKEN
    )

    result = {
        "path": path,
        "status": None,
        "duration_ms": None,
        "content_type": None,
        "www_authenticate_present": False,
        "error_type": None,
    }

    if not base_url:
        result["error_type"] = (
            "CanvasBaseUrlMissing"
        )
        return result

    if not token:
        result["error_type"] = (
            "CanvasTokenMissing"
        )
        return result

    started = (
        _diagnostic_time.perf_counter()
    )

    try:
        response = (
            _diagnostic_requests.get(
                f"{base_url}{path}",
                headers={
                    "Authorization":
                        f"Bearer {token}",
                    "Accept":
                        "application/json",
                },
                params=params,
                timeout=(5, 15),
                allow_redirects=False,
            )
        )

        result["duration_ms"] = round(
            (
                _diagnostic_time
                .perf_counter()
                - started
            )
            * 1000,
            2,
        )

        result["status"] = (
            response.status_code
        )

        result["content_type"] = (
            response.headers.get(
                "Content-Type"
            )
        )

        result[
            "www_authenticate_present"
        ] = bool(
            response.headers.get(
                "WWW-Authenticate"
            )
        )

    except Exception as exc:
        result["duration_ms"] = round(
            (
                _diagnostic_time
                .perf_counter()
                - started
            )
            * 1000,
            2,
        )

        result["error_type"] = (
            type(exc).__name__
        )

    return result


@router.get(
    "/diagnostics/runtime",
    dependencies=[
        Depends(verify_app_key)
    ],
    include_in_schema=False,
)
def runtime_diagnostics():
    course_cache_dir = (
        _diagnostic_settings
        .COURSE_CACHE_DIR
    )

    course_snapshots = (
        list(
            course_cache_dir.glob(
                "*.json"
            )
        )
        if course_cache_dir.exists()
        else []
    )

    return {
        "diagnostic_version": "1",
        "runtime": {
            "render_service_name":
                _diagnostic_os.environ.get(
                    "RENDER_SERVICE_NAME"
                ),
            "render_instance_id_present":
                bool(
                    _diagnostic_os.environ.get(
                        "RENDER_INSTANCE_ID"
                    )
                ),
            "render_git_commit":
                _diagnostic_os.environ.get(
                    "RENDER_GIT_COMMIT"
                ),
            "python_working_directory":
                _diagnostic_os.getcwd(),
        },
        "configuration": {
            "canvas_base_url":
                _diagnostic_settings
                .CANVAS_BASE_URL,
            "app_access_key":
                _diagnostic_secret_metadata(
                    "APP_ACCESS_KEY",
                    _diagnostic_settings
                    .APP_ACCESS_KEY,
                ),
            "canvas_api_token":
                _diagnostic_secret_metadata(
                    "CANVAS_API_TOKEN",
                    _diagnostic_settings
                    .CANVAS_API_TOKEN,
                ),
        },
        "canvas": {
            "users_self":
                _diagnostic_canvas_check(
                    "/api/v1/users/self"
                ),
            "courses":
                _diagnostic_canvas_check(
                    "/api/v1/courses",
                    {
                        "per_page": 1,
                        "include[]": "term",
                    },
                ),
        },
        "cache": {
            "dashboard":
                _diagnostic_json_file(
                    _diagnostic_settings
                    .DASHBOARD_CACHE_FILE
                ),
            "sync_status":
                _diagnostic_json_file(
                    _diagnostic_settings
                    .SYNC_STATUS_FILE
                ),
            "course_cache_directory": {
                "path": str(
                    course_cache_dir
                ),
                "exists":
                    course_cache_dir
                    .exists(),
                "snapshot_count":
                    len(
                        course_snapshots
                    ),
            },
        },
    }
# === ATHENA TEMP RUNTIME DIAGNOSTICS END ===

