from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

from backend.app.scheduler_worker import scan_once


def test_scan_once_calls_schedule_service():
    expected = {
        "scanned_at": "2026-08-17T16:00:00+00:00",
        "due_schedule_count": 0,
        "results": [],
    }

    fixed_now = datetime(
        2026,
        8,
        17,
        16,
        0,
        tzinfo=timezone.utc,
    )

    with patch(
        "backend.app.scheduler_worker.scan_due_schedules_once",
        return_value=expected,
    ) as mock_scan:
        with patch(
            "backend.app.scheduler_worker.datetime",
        ) as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.timezone = timezone

            result = scan_once()

    assert result == expected
    mock_scan.assert_called_once()

    _, kwargs = mock_scan.call_args
    assert kwargs["now_utc"] == fixed_now
