"""SQLite-backed metrics event store.

Per HARNESS_DESIGN.md §7 metrics taxonomy. Wave 1 emits events;
Wave 5 adds aggregation + dashboard.

Schema mirrors contracts/schemas/metrics-event.schema.json.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite


_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS metrics_events (
  event_id TEXT PRIMARY KEY,
  timestamp TEXT NOT NULL,
  run_id TEXT,
  category TEXT NOT NULL,
  metric_name TEXT NOT NULL,
  value TEXT NOT NULL,
  unit TEXT,
  context_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_run_id ON metrics_events(run_id);
CREATE INDEX IF NOT EXISTS idx_metric_name ON metrics_events(metric_name);
"""


class MetricsEmitter:
    def __init__(self, sqlite_path: Path):
        self._path = Path(sqlite_path)

    async def init(self) -> None:
        """Create the metrics_events table + indexes (idempotent)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._path) as db:
            await db.executescript(_SCHEMA_DDL)
            await db.commit()

    async def emit(
        self,
        run_id: str,
        category: str,
        metric_name: str,
        value: Any,
        unit: str | None = None,
        context: dict | None = None,
    ) -> None:
        """Append one event row.

        Caller is responsible for ensuring `category` ∈ metrics-event.schema.json
        category enum and `metric_name` ∈ metric_name enum.
        """
        event_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()
        ctx_json = json.dumps(context or {})
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "INSERT INTO metrics_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (event_id, ts, run_id, category, metric_name, str(value), unit, ctx_json),
            )
            await db.commit()
