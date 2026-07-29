"""SQLite storage for sensor readings.

Why SQLite: it is a single file, it needs no server process, and the `sqlite3`
module is already in Python's standard library — nothing to install. For one
reading every 30 seconds it will not break a sweat. If you outgrow it, doc 07
covers moving to InfluxDB + Grafana.

Both collector.py and api.py import from here so the schema is defined exactly
once.
"""

import sqlite3
import time
from pathlib import Path

from config import DB_PATH, RETENTION_DAYS

# One row per (time, node, metric) triple. Storing readings "long" like this
# rather than one column per metric means adding a new sensor type never
# requires a schema migration.
SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      REAL    NOT NULL,          -- unix seconds, UTC
    room    TEXT    NOT NULL,          -- e.g. 'bedroom'
    node    TEXT    NOT NULL,          -- e.g. 'node1'
    metric  TEXT    NOT NULL,          -- e.g. 'temperature'
    value   REAL    NOT NULL
);

-- The dashboard always asks "recent readings for this metric", so index in
-- that order. Without this, queries scan the whole table once you have a few
-- hundred thousand rows.
CREATE INDEX IF NOT EXISTS idx_readings_lookup
    ON readings (metric, ts DESC);

CREATE INDEX IF NOT EXISTS idx_readings_node
    ON readings (room, node, ts DESC);
"""


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the database, creating it and its schema if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)

    # check_same_thread=False because FastAPI may serve requests from a
    # different thread than the one that opened the connection.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # WAL mode lets the collector write while the API reads, without them
    # blocking each other. On the default journal mode they would.
    conn.execute("PRAGMA journal_mode=WAL")

    # NORMAL instead of FULL: we lose at most the last few readings if the Pi
    # loses power mid-write, which for room temperature is a fine trade for
    # dramatically fewer SD-card writes.
    conn.execute("PRAGMA synchronous=NORMAL")

    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def insert(conn, room: str, node: str, metric: str, value: float, ts: float | None = None) -> None:
    """Store one reading. `ts` defaults to now."""
    conn.execute(
        "INSERT INTO readings (ts, room, node, metric, value) VALUES (?, ?, ?, ?, ?)",
        (ts if ts is not None else time.time(), room, node, metric, value),
    )
    conn.commit()


def recent(conn, metric: str, hours: float = 24, room: str | None = None, node: str | None = None):
    """Readings for one metric over the last `hours`, oldest first.

    Oldest-first because that is the order a chart wants to plot.
    """
    sql = "SELECT ts, room, node, value FROM readings WHERE metric = ? AND ts >= ?"
    params: list = [metric, time.time() - hours * 3600]

    if room:
        sql += " AND room = ?"
        params.append(room)
    if node:
        sql += " AND node = ?"
        params.append(node)

    sql += " ORDER BY ts ASC"
    return [dict(r) for r in conn.execute(sql, params)]


def latest_per_node(conn):
    """The most recent value of every metric, for every node.

    Powers the "current conditions" tiles at the top of the dashboard. The
    window function picks row 1 per (room, node, metric) group ordered by
    newest first.
    """
    sql = """
    SELECT room, node, metric, value, ts FROM (
        SELECT room, node, metric, value, ts,
               ROW_NUMBER() OVER (
                   PARTITION BY room, node, metric ORDER BY ts DESC
               ) AS rn
        FROM readings
    ) WHERE rn = 1
    ORDER BY room, node, metric
    """
    return [dict(r) for r in conn.execute(sql)]


def nodes(conn):
    """Every (room, node) pair we have ever heard from, with last-seen time."""
    sql = """
    SELECT room, node, MAX(ts) AS last_seen, COUNT(*) AS reading_count
    FROM readings GROUP BY room, node ORDER BY room, node
    """
    return [dict(r) for r in conn.execute(sql)]


def prune(conn, retention_days: int = RETENTION_DAYS) -> int:
    """Delete readings older than the retention window. Returns rows removed."""
    cutoff = time.time() - retention_days * 86400
    cur = conn.execute("DELETE FROM readings WHERE ts < ?", (cutoff,))
    conn.commit()
    return cur.rowcount
