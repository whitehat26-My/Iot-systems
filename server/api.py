#!/usr/bin/env python3
"""The dashboard: a small JSON API plus one static HTML page.

Run it:
    python server/api.py                                  # plain
    uvicorn api:app --app-dir server --reload             # auto-reload while editing

Then open http://localhost:8000 (or http://<pi-ip>:8000 from your phone).

Note the `--app-dir server` above: `server/` is a plain folder of scripts, not
an installed package, so uvicorn needs telling where to look. Running
`python server/api.py` avoids the question entirely, which is why the systemd
unit does it that way.
"""

import time

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import API_HOST, API_PORT, KNOWN_METRICS, STATIC_DIR
import db

app = FastAPI(
    title="Iot-systems",
    description="Local room sensor dashboard. No cloud involved.",
    version="1.0.0",
)

# One long-lived connection. SQLite in WAL mode handles the collector writing
# while we read, and read-only queries here are short.
conn = db.connect()


@app.get("/api/health")
def health():
    """Cheap liveness check: is the API up and can it read the database?"""
    try:
        row = conn.execute("SELECT COUNT(*) AS n FROM readings").fetchone()
        return {"status": "ok", "readings": row["n"], "time": time.time()}
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"database error: {exc}")


@app.get("/api/metrics")
def metrics():
    """Which metrics exist in the database, with display labels and units.

    The dashboard calls this first and builds one chart per metric found, so a
    new sensor type appears in the UI without any front-end changes.
    """
    rows = conn.execute("SELECT DISTINCT metric FROM readings").fetchall()
    present = {r["metric"] for r in rows}

    # Keep KNOWN_METRICS ordering (temperature, humidity, pressure), then
    # append anything unexpected so nothing is silently hidden.
    ordered = [m for m in KNOWN_METRICS if m in present]
    ordered += sorted(present - set(KNOWN_METRICS))

    return [
        {
            "metric": m,
            "label": KNOWN_METRICS.get(m, {}).get("label", m.title()),
            "unit": KNOWN_METRICS.get(m, {}).get("unit", ""),
        }
        for m in ordered
    ]


@app.get("/api/nodes")
def nodes():
    """Every node we have heard from, and how long ago.

    `stale` is the useful field: it is what tells you a node has silently
    dropped off your WiFi, which is the most common real-world failure once
    the system is running.
    """
    now = time.time()
    result = []
    for n in db.nodes(conn):
        age = now - n["last_seen"]
        result.append(
            {
                **n,
                "seconds_ago": round(age, 1),
                # Nodes publish every 30s by default; 5 minutes of silence
                # means something is wrong, not just jitter.
                "stale": age > 300,
            }
        )
    return result


@app.get("/api/latest")
def latest():
    """Current value of every metric on every node — the tiles at the top."""
    now = time.time()
    order = list(KNOWN_METRICS)

    rows = [
        {
            **r,
            "unit": KNOWN_METRICS.get(r["metric"], {}).get("unit", ""),
            "label": KNOWN_METRICS.get(r["metric"], {}).get("label", r["metric"].title()),
            "seconds_ago": round(now - r["ts"], 1),
        }
        for r in db.latest_per_node(conn)
    ]

    # Group by node, and within a node show temperature, humidity, pressure —
    # the order a person cares about. The SQL returns them alphabetically, which
    # would lead with humidity and bury the temperature nobody came here to miss.
    rows.sort(key=lambda r: (
        r["room"],
        r["node"],
        order.index(r["metric"]) if r["metric"] in order else len(order),
        r["metric"],
    ))
    return rows


@app.get("/api/readings")
def readings(
    metric: str = Query("temperature", description="e.g. temperature, humidity"),
    hours: float = Query(24, gt=0, le=24 * 365, description="how far back to look"),
    room: str | None = Query(None),
    node: str | None = Query(None),
):
    """Time series for one metric, grouped into one series per node.

    Grouped server-side so the browser does not have to, and so adding a
    second room to the chart is free.
    """
    rows = db.recent(conn, metric=metric, hours=hours, room=room, node=node)

    series: dict[str, dict] = {}
    for r in rows:
        key = f"{r['room']}/{r['node']}"
        if key not in series:
            series[key] = {"name": key, "room": r["room"], "node": r["node"], "points": []}
        # Milliseconds, because that is what JavaScript's Date wants.
        series[key]["points"].append([round(r["ts"] * 1000), r["value"]])

    return {
        "metric": metric,
        "unit": KNOWN_METRICS.get(metric, {}).get("unit", ""),
        "label": KNOWN_METRICS.get(metric, {}).get("label", metric.title()),
        "hours": hours,
        "series": list(series.values()),
    }


# --- the page itself -------------------------------------------------------
# Mounted under /static so index.html can pull in chart.js from the same origin.
# Vendored, not a CDN: a local-only system should not need the internet to draw
# a graph.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    path = STATIC_DIR / "index.html"
    if not path.exists():  # pragma: no cover - defensive
        return JSONResponse({"error": f"missing {path}"}, status_code=500)
    return FileResponse(path)


if __name__ == "__main__":
    import uvicorn

    print(f"dashboard on http://{API_HOST}:{API_PORT}  (reading {db.DB_PATH})")
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")
