"""Integration test for SQLite metrics emitter."""
import json
import pytest
import aiosqlite
from pathlib import Path
from harness.metrics.emitter import MetricsEmitter


@pytest.mark.asyncio
async def test_init_creates_table(tmp_path):
    db_path = tmp_path / "metrics.db"
    emitter = MetricsEmitter(db_path)
    await emitter.init()
    assert db_path.exists()
    # Verify table exists
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] async for row in cursor]
        assert "metrics_events" in tables


@pytest.mark.asyncio
async def test_emit_writes_row(tmp_path):
    emitter = MetricsEmitter(tmp_path / "metrics.db")
    await emitter.init()
    await emitter.emit(
        run_id="run-123",
        category="task_effectiveness",
        metric_name="task_success",
        value=True,
        unit="boolean",
        context={"stage": "feedback", "tier": 1},
    )
    async with aiosqlite.connect(tmp_path / "metrics.db") as db:
        cursor = await db.execute("SELECT run_id, category, metric_name, value FROM metrics_events")
        rows = [r async for r in cursor]
        assert len(rows) == 1
        run_id, category, metric_name, value = rows[0]
        assert run_id == "run-123"
        assert category == "task_effectiveness"
        assert metric_name == "task_success"


@pytest.mark.asyncio
async def test_emit_serializes_context_as_json(tmp_path):
    emitter = MetricsEmitter(tmp_path / "metrics.db")
    await emitter.init()
    await emitter.emit(
        run_id="r1",
        category="resource_efficiency",
        metric_name="token_consumed",
        value=1234,
        unit="tokens",
        context={"stage": "action", "lens": "C_product_ops"},
    )
    async with aiosqlite.connect(tmp_path / "metrics.db") as db:
        cursor = await db.execute("SELECT context_json FROM metrics_events")
        row = await cursor.fetchone()
        ctx = json.loads(row[0])
        assert ctx["stage"] == "action"
        assert ctx["lens"] == "C_product_ops"


@pytest.mark.asyncio
async def test_emit_handles_none_context(tmp_path):
    emitter = MetricsEmitter(tmp_path / "metrics.db")
    await emitter.init()
    await emitter.emit(
        run_id="r1",
        category="quality_of_service",
        metric_name="end_to_end_latency_ms",
        value=42.5,
    )
    async with aiosqlite.connect(tmp_path / "metrics.db") as db:
        cursor = await db.execute("SELECT context_json FROM metrics_events")
        row = await cursor.fetchone()
        # context defaults to "{}" not NULL
        assert json.loads(row[0]) == {}


@pytest.mark.asyncio
async def test_emit_assigns_unique_event_ids(tmp_path):
    emitter = MetricsEmitter(tmp_path / "metrics.db")
    await emitter.init()
    for i in range(5):
        await emitter.emit(
            run_id="r1",
            category="resource_efficiency",
            metric_name="token_consumed",
            value=i,
        )
    async with aiosqlite.connect(tmp_path / "metrics.db") as db:
        cursor = await db.execute("SELECT event_id FROM metrics_events")
        ids = {row[0] async for row in cursor}
        assert len(ids) == 5  # all unique


@pytest.mark.asyncio
async def test_init_idempotent(tmp_path):
    """Calling init() twice should not fail."""
    emitter = MetricsEmitter(tmp_path / "metrics.db")
    await emitter.init()
    await emitter.init()  # should be no-op
    await emitter.emit(run_id="r1", category="task_effectiveness", metric_name="task_success", value=True)


@pytest.mark.asyncio
async def test_creates_parent_directories(tmp_path):
    """Parent dir of sqlite_path should be created on emitter init."""
    db_path = tmp_path / "deep" / "nested" / "path" / "metrics.db"
    emitter = MetricsEmitter(db_path)
    await emitter.init()
    assert db_path.exists()
