"""DailyCapManager — enforce per-day total cap and per-channel sub-caps.

Per Wave 3 plan §Phase 0 Task 3. Persisted to SQLite so server restart
does not reset mid-day counts.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


_SCHEMA = """
CREATE TABLE IF NOT EXISTS submit_counts (
    date TEXT NOT NULL,
    channel TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (date, channel)
);
"""


class CapExceededError(Exception):
    def __init__(self, scope: str, used: int, cap: int):
        self.scope = scope
        self.used = used
        self.cap = cap
        super().__init__(f"{scope} cap exceeded: {used}/{cap} for today")


class DailyCapManager:
    def __init__(
        self,
        db_path: Path,
        total_cap: int = 50,
        linkedin_subcap: int = 15,
    ):
        self._db_path = Path(db_path)
        self._total_cap = total_cap
        self._linkedin_subcap = linkedin_subcap
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as db:
            db.executescript(_SCHEMA)

    def _today(self) -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def used_today(self, channel: str | None = None) -> int:
        with sqlite3.connect(self._db_path) as db:
            if channel is None:
                cur = db.execute(
                    "SELECT COALESCE(SUM(count), 0) FROM submit_counts WHERE date = ?",
                    (self._today(),),
                )
            else:
                cur = db.execute(
                    "SELECT COALESCE(SUM(count), 0) FROM submit_counts WHERE date = ? AND channel = ?",
                    (self._today(), channel),
                )
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def check_and_reserve(self, channel: str) -> None:
        """Atomically check both total cap AND channel-specific cap; reserve a slot.

        Raises CapExceededError if either cap would be exceeded by this
        reservation. On success, increments the count by 1.
        """
        with sqlite3.connect(self._db_path) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                cur = db.execute(
                    "SELECT COALESCE(SUM(count), 0) FROM submit_counts WHERE date = ?",
                    (self._today(),),
                )
                total_used = int(cur.fetchone()[0] or 0)
                if total_used >= self._total_cap:
                    raise CapExceededError("daily total", total_used, self._total_cap)

                if channel == "linkedin":
                    cur = db.execute(
                        "SELECT COALESCE(SUM(count), 0) FROM submit_counts WHERE date = ? AND channel = ?",
                        (self._today(), channel),
                    )
                    li_used = int(cur.fetchone()[0] or 0)
                    if li_used >= self._linkedin_subcap:
                        raise CapExceededError("linkedin", li_used, self._linkedin_subcap)

                db.execute(
                    "INSERT INTO submit_counts (date, channel, count) VALUES (?, ?, 1) "
                    "ON CONFLICT(date, channel) DO UPDATE SET count = count + 1",
                    (self._today(), channel),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise

    def remaining(self) -> dict[str, int]:
        """Return remaining slots: {'total': N, 'linkedin': M}."""
        return {
            "total": max(0, self._total_cap - self.used_today()),
            "linkedin": max(0, self._linkedin_subcap - self.used_today("linkedin")),
        }
