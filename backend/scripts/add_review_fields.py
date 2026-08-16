from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db import _engine


REQUIRED_COLUMNS = {
    "review_decision": "VARCHAR(32)",
    "review_note": "TEXT",
    "reviewed_at": "TIMESTAMP",
}


def main() -> None:
    inspector = inspect(_engine)
    existing = {
        column["name"]
        for column in inspector.get_columns("newsletters")
    }

    with _engine.begin() as connection:
        for name, sql_type in REQUIRED_COLUMNS.items():
            if name not in existing:
                connection.execute(
                    text(f"ALTER TABLE newsletters ADD COLUMN {name} {sql_type}")
                )
                print(f"Added newsletters.{name}")
            else:
                print(f"Already exists: newsletters.{name}")


if __name__ == "__main__":
    main()