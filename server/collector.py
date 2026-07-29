#!/usr/bin/env python3
"""Subscribe to MQTT, write every reading into SQLite.

This is the bridge between the devices and the dashboard. It is deliberately
the dumbest component in the system: listen, parse, store. It holds no state of
its own, so if it crashes, systemd restarts it and nothing is lost beyond the
readings published in the gap.

Run it:
    python server/collector.py

Topics it understands
---------------------
    home/<room>/<node>/<metric>   e.g. home/bedroom/node1/temperature -> "24.61"
    home/<room>/<node>/state      a JSON object of several metrics at once

The nodes publish both: individual topics (easy to read with mosquitto_sub, and
what other MQTT tools expect) and a single JSON snapshot (one atomic message,
so all three values share a timestamp). We store from the individual topics and
use `state` only for metrics we did not otherwise see, so nothing is
double-counted.
"""

import json
import signal
import sys
import time

import paho.mqtt.client as mqtt

from config import MQTT_HOST, MQTT_PORT, MQTT_TOPIC, RETENTION_DAYS
import db

# Prune at most once an hour; there is no point running a DELETE on every message.
PRUNE_INTERVAL = 3600
_last_prune = 0.0

conn = db.connect()


def log(msg: str) -> None:
    """Timestamped line to stdout. systemd captures this into the journal, so
    `journalctl -u iot-collector -f` is your live debugging view on the Pi."""
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}", flush=True)


def parse_topic(topic: str):
    """home/bedroom/node1/temperature -> ('bedroom', 'node1', 'temperature').

    Returns None for anything that does not match, so a stray message on an
    unexpected topic is ignored rather than crashing the collector.
    """
    parts = topic.split("/")
    if len(parts) != 4 or parts[0] != "home":
        return None
    _, room, node, metric = parts
    if not room or not node or not metric:
        return None
    return room, node, metric


def store(room: str, node: str, metric: str, raw_value, ts: float | None = None) -> bool:
    """Coerce a value to float and store it. Returns True if stored.

    `ts` lets a publisher supply its own timestamp; None means "stamp on
    arrival", which is what the ESP32 needs since it has no clock of its own.
    """
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        log(f"  ignoring non-numeric value for {metric}: {raw_value!r}")
        return False

    # A disconnected or faulty sensor often reports absurd numbers rather than
    # failing outright. Rejecting them here keeps one bad reading from making
    # the chart's y-axis useless.
    if metric == "temperature" and not -50 <= value <= 100:
        log(f"  rejecting implausible temperature: {value}")
        return False
    if metric == "humidity" and not 0 <= value <= 100:
        log(f"  rejecting implausible humidity: {value}")
        return False

    db.insert(conn, room, node, metric, value, ts=ts)
    return True


def on_connect(client, userdata, flags, reason_code, properties):
    """Called on every successful connect — including reconnects, which is why
    the subscribe lives here rather than in main()."""
    if reason_code == 0:
        log(f"connected to {MQTT_HOST}:{MQTT_PORT}, subscribing to {MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC, qos=1)
    else:
        # Most common cause: the broker is listening on localhost only and you
        # connected from another machine. See docs/03-hub-mosquitto.md.
        log(f"connect failed: {reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties):
    if reason_code != 0:
        log(f"unexpected disconnect ({reason_code}); paho will retry automatically")


def on_message(client, userdata, msg):
    global _last_prune

    parsed = parse_topic(msg.topic)
    if parsed is None:
        return
    room, node, metric = parsed

    # Liveness topics carry words like "online", not numbers. They are for other
    # MQTT tools (and for our own will message) to watch — skip them silently
    # rather than logging a "non-numeric value" complaint every time.
    if metric == "status":
        return

    payload = msg.payload.decode("utf-8", errors="replace").strip()

    if metric == "state":
        # A JSON snapshot: {"temperature": 24.6, "humidity": 61.2, ...}
        # We only store keys we did not already receive on their own topic,
        # which in practice means this is a no-op safety net. It matters when a
        # node is configured to publish *only* the snapshot.
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            log(f"  bad JSON on {msg.topic}: {payload[:80]!r}")
            return
        if not isinstance(data, dict):
            return

        # A publisher that knows the real time may supply it. The ESP32 does
        # not (no battery-backed clock, and we do not make it wait for NTP), so
        # its readings are stamped on arrival — accurate to well under a second,
        # which is plenty for room temperature. tools/fake_sensor.py does send
        # one, which is what lets it backfill believable history.
        ts = None
        raw_ts = data.get("ts")
        if raw_ts is not None:
            try:
                candidate = float(raw_ts)
                # Sanity-check it: a device with a wrong clock would otherwise
                # write readings into 1970 or 2087 and wreck every chart range.
                if abs(candidate - time.time()) < 10 * 365 * 86400:
                    ts = candidate
                else:
                    log(f"  ignoring implausible timestamp {candidate}")
            except (TypeError, ValueError):
                log(f"  ignoring non-numeric ts: {raw_ts!r}")

        for key, value in data.items():
            # Skip bookkeeping fields the node includes for its own diagnostics.
            if key in ("uptime", "rssi", "node", "room", "sensor", "ts"):
                continue
            # De-duplicate against the per-metric topics only for *live*
            # snapshots. A snapshot carrying its own timestamp is explicitly
            # historical (a backfill), so it must not be discarded just because
            # a live reading for the same metric happened to arrive seconds ago.
            if ts is None and _recently_stored(room, node, key):
                continue
            if store(room, node, key, value, ts=ts):
                log(f"{room}/{node} {key} = {value} (from state)")
    else:
        if store(room, node, metric, payload):
            _mark_stored(room, node, metric)
            log(f"{room}/{node} {metric} = {payload}")

    # Housekeeping, piggybacked on message traffic so we need no timer thread.
    now = time.time()
    if now - _last_prune > PRUNE_INTERVAL:
        _last_prune = now
        removed = db.prune(conn)
        if removed:
            log(f"pruned {removed} readings older than {RETENTION_DAYS} days")


# --- de-duplication between individual topics and the JSON snapshot ---------
# Nodes publish the individual topics and then the snapshot, within the same
# few milliseconds. This remembers what arrived recently so the snapshot does
# not insert a second copy.
_seen: dict[tuple[str, str, str], float] = {}
_SEEN_WINDOW = 10  # seconds


def _mark_stored(room: str, node: str, metric: str) -> None:
    _seen[(room, node, metric)] = time.time()


def _recently_stored(room: str, node: str, metric: str) -> bool:
    ts = _seen.get((room, node, metric))
    return ts is not None and (time.time() - ts) < _SEEN_WINDOW


def main() -> None:
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="iot-collector",
        # A persistent session means the broker queues QoS-1 messages for us
        # while we are restarting, instead of dropping them.
        clean_session=False,
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # If the collector dies, anything watching this topic learns about it.
    client.will_set("home/hub/collector/status", "offline", qos=1, retain=True)

    def shutdown(signum, frame):
        log("shutting down")
        client.publish("home/hub/collector/status", "offline", qos=1, retain=True)
        client.disconnect()
        conn.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    log(f"storing readings in {db.DB_PATH}")

    # Retry the first connection rather than exiting: on the Pi, the collector
    # and the broker start at roughly the same moment during boot, and the
    # broker sometimes wins the race by a second or two.
    delay = 1
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            break
        except OSError as exc:
            log(f"broker not reachable ({exc}); retrying in {delay}s")
            time.sleep(delay)
            delay = min(delay * 2, 30)

    client.publish("home/hub/collector/status", "online", qos=1, retain=True)

    # Blocks forever, reconnecting on its own if the broker restarts.
    client.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()
