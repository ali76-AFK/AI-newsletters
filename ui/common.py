from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://127.0.0.1:8000",
)


def api_request(
    method: str,
    path: str,
    json: dict[str, Any] | None = None,
    timeout: int = 10,
) -> dict[str, Any]:
    url = f"{BACKEND_URL}{path}"

    try:
        response = requests.request(
            method,
            url,
            json=json,
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}

    text = (response.text or "").strip()

    if not text:
        if response.status_code >= 400:
            return {
                "error": (
                    f"HTTP {response.status_code} "
                    "with empty response"
                )
            }
        return {"status": "ok"}

    try:
        data = response.json()
    except ValueError:
        if response.status_code >= 400:
            return {"error": text}
        return {"text": text}

    if response.status_code >= 400:
        if isinstance(data, dict):
            return {
                "error": data.get(
                    "detail",
                    f"HTTP {response.status_code}",
                )
            }
        return {"error": f"HTTP {response.status_code}"}

    return data


def api_get(
    path: str,
    timeout: int = 10,
) -> dict[str, Any]:
    return api_request(
        "GET",
        path,
        timeout=timeout,
    )


def api_post(
    path: str,
    json: dict[str, Any] | None = None,
    timeout: int = 10,
) -> dict[str, Any]:
    return api_request(
        "POST",
        path,
        json=json,
        timeout=timeout,
    )


def get_topics() -> list[str]:
    data = api_get("/api/subscribers/topics")
    return data if isinstance(data, list) else []


def get_schedules() -> dict[str, Any]:
    return api_get("/api/schedules")


def create_schedule(payload: dict[str, Any]) -> dict[str, Any]:
    return api_post(
        "/api/schedules",
        json=payload,
    )


def enable_schedule(schedule_id: int) -> dict[str, Any]:
    return api_post(f"/api/schedules/{schedule_id}/enable")


def disable_schedule(schedule_id: int) -> dict[str, Any]:
    return api_post(f"/api/schedules/{schedule_id}/disable")


def run_schedule_now(schedule_id: int) -> dict[str, Any]:
    return api_post(
        f"/api/schedules/{schedule_id}/run-now",
        timeout=60,
    )


def get_schedule_runs(schedule_id: int) -> dict[str, Any]:
    return api_get(
        f"/api/schedules/{schedule_id}/runs",
    )