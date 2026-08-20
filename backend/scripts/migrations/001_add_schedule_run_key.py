from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text


BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.db import _engine


def main() -> None:
    with _engine.begin() as connection:
        connection.execute(
            text(
                """
                ALTER TABLE schedule_runs
                ADD COLUMN IF NOT EXISTS run_key VARCHAR(128)
                """
            )
        )

        connection.execute(
            text(
                """
                UPDATE schedule_runs
                SET run_key = 'legacy-' || id::text
                WHERE run_key IS NULL
                """
            )
        )

        connection.execute(
            text(
                """
                ALTER TABLE schedule_runs
                ALTER COLUMN run_key SET NOT NULL
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                ix_schedule_runs_run_key
                ON schedule_runs (run_key)
                """
            )
        )

    print("Migration 001 complete: schedule_runs.run_key is ready.")


if __name__ == "__main__":
    main()
