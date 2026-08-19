from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db import init_db


if __name__ == "__main__":
    init_db()
    print("Ensured newsletter_schedules and schedule_runs tables exist.")
