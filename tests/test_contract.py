"""End-to-end contract test: the REAL firmware publish path -> broker ->
collector -> SQLite -> API.

Runs firmware/room_sensor/main.py's own publish() and connect_mqtt() with a fake
sensor chip, then checks the rows the collector actually wrote. If the firmware's
topics and the collector's parser ever drift apart, this fails.
"""
import json
import sqlite3
import os
import sys
import time
import types
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "mpshim"))
sys.path.insert(0, os.path.join(REPO, "firmware", "room_sensor", "lib"))
sys.path.insert(0, os.path.join(REPO, "firmware", "room_sensor"))
sys.path.insert(0, HERE)

time.sleep_ms = lambda ms: None
time.ticks_ms = lambda: int(time.monotonic() * 1000)

# --- config the node would have -------------------------------------------
cfg = types.ModuleType("config")
cfg.WIFI_SSID = "x"
cfg.WIFI_PASSWORD = "y"
cfg.MQTT_HOST = "localhost"
cfg.MQTT_PORT = 1883
cfg.ROOM = "testroom"
cfg.NODE = "testnode"
cfg.PUBLISH_INTERVAL = 30
cfg.I2C_SCL_PIN = 22
cfg.I2C_SDA_PIN = 21
cfg.DHT_PIN = None
cfg.LED_PIN = None
cfg.MAX_FAILURES_BEFORE_REBOOT = 10
sys.modules["config"] = cfg

import machine  # noqa: E402
from test_bme280 import FakeChip  # reuse the fake chip  # noqa: E402

machine.FAKE_I2C = FakeChip(0x60)

import main as firmware  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not cond:
        fails.append(name)


# Clear any rows left behind by an earlier run that died before its cleanup.
# Without this, the "no duplicate rows" check counts last run's rows too and
# fails for a reason that has nothing to do with the code under test.
_pre = sqlite3.connect(os.path.join(REPO, "readings.db"))
_pre.execute("CREATE TABLE IF NOT EXISTS readings (id INTEGER PRIMARY KEY AUTOINCREMENT,"
             " ts REAL, room TEXT, node TEXT, metric TEXT, value REAL)")
_pre.execute("DELETE FROM readings WHERE room='testroom'")
_pre.commit()
_pre.close()

print("firmware publish path")
sensor = firmware.make_sensor()
values = sensor.read()
check("sensor read gives 3 metrics", set(values) == {"temperature", "humidity", "pressure"})

client = firmware.connect_mqtt()
firmware.publish(client, values)
time.sleep(2.5)

topics = [t for t, _ in client.sent]
print("    topics sent:", topics)
check("per-metric topic present", "home/testroom/testnode/temperature" in topics)
check("state snapshot present", "home/testroom/testnode/state" in topics)
check("status announced online", ("home/testroom/testnode/status", "online") in client.sent)

snap = json.loads(next(m for t, m in client.sent if t.endswith("/state")))
check("snapshot carries room/node", snap.get("room") == "testroom" and snap.get("node") == "testnode")
check("snapshot has uptime", "uptime" in snap)
check("snapshot has NO ts (board has no clock)", "ts" not in snap)

client.disconnect()

print("collector stored it")
db = sqlite3.connect(os.path.join(REPO, "readings.db"))
db.row_factory = sqlite3.Row
rows = db.execute(
    "SELECT metric, value, ts FROM readings WHERE room='testroom' AND node='testnode'"
).fetchall()
got = {r["metric"] for r in rows}
check("all three metrics landed in SQLite", got == {"temperature", "humidity", "pressure"}, str(sorted(got)))
check("no duplicate rows from the snapshot", len(rows) == 3, f"{len(rows)} rows")
if rows:
    check("stamped on arrival (within 60s of now)", abs(rows[0]["ts"] - time.time()) < 60)

print("API exposes it")
nodes = json.loads(urllib.request.urlopen("http://localhost:8000/api/nodes", timeout=5).read())
check("node appears in /api/nodes", any(n["room"] == "testroom" for n in nodes))
data = json.loads(urllib.request.urlopen(
    "http://localhost:8000/api/readings?metric=temperature&hours=1&room=testroom", timeout=5).read())
check("readings series returned", data["series"] and data["series"][0]["points"], str(data["series"])[:60])
check("unit attached", data["unit"] == "°C", data["unit"])

# Clean up so the demo database is not polluted by the test node.
db.execute("DELETE FROM readings WHERE room='testroom'")
db.commit()
db.close()

print()
if fails:
    print(f"{len(fails)} FAILED: {fails}")
    sys.exit(1)
print("contract holds: firmware -> broker -> collector -> SQLite -> API")
