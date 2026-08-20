from __future__ import annotations

import logging
import signal
import time
from datetime import datetime, timezone

from .db import get_session, init_db
from .schedule_service import scan_due_schedules_once


LOGGER = logging.getLogger("newsletter_scheduler")
SCAN_INTERVAL_SECONDS = 60

_running = True


def _stop_worker(
    signum: int,
    frame: object | None,
) -> None:
    global _running
    LOGGER.info("scheduler_stop_signal", extra={"signal": signum})
    _running = False


def scan_once() -> dict:
    now_utc = datetime.now(timezone.utc)

    with get_session() as db:
        result = scan_due_schedules_once(
            db=db,
            now_utc=now_utc,
        )

    LOGGER.info(
        "scheduler_scan_complete",
        extra={
            "scanned_at": result["scanned_at"],
            "due_schedule_count": result["due_schedule_count"],
            "results": result["results"],
        },
    )
    return result


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s %(message)s"
        ),
    )

    signal.signal(signal.SIGINT, _stop_worker)
    signal.signal(signal.SIGTERM, _stop_worker)

    init_db()

    LOGGER.info(
        "scheduler_started",
        extra={"scan_interval_seconds": SCAN_INTERVAL_SECONDS},
    )

    while _running:
        started_monotonic = time.monotonic()

        try:
            scan_once()
        except Exception:  # noqa: BLE001
            LOGGER.exception("scheduler_scan_failed")

        elapsed_seconds = time.monotonic() - started_monotonic
        remaining_seconds = max(
            0.0,
            SCAN_INTERVAL_SECONDS - elapsed_seconds,
        )

        deadline = time.monotonic() + remaining_seconds

        while _running and time.monotonic() < deadline:
            time.sleep(
                min(
                    0.5,
                    deadline - time.monotonic(),
                )
            )

    LOGGER.info("scheduler_stopped")


if __name__ == "__main__":
    main()
