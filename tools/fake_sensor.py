#!/usr/bin/env python3
"""Pretend to be an ESP32, so you can build the whole system before it arrives.

This publishes exactly what firmware/room_sensor/main.py publishes, on exactly
the same topics. The collector, the database and the dashboard cannot tell the
difference — which is the point. Build and debug the software half while your
parts are still in the post, and when the real hardware shows up you are
plugging it into something you already know works.

Basic use (talks to a broker on this machine):

    python tools/fake_sensor.py

Once the Pi is running the broker, point at it and confirm the network path
works before the ESP32 is involved:

    python tools/fake_sensor.py --host 192.168.1.50

Simulate a second room, to see multi-node charts:

    python tools/fake_sensor.py --room study --node node2 --interval 5

Backfill a day of history so the 24h chart has something to draw immediately:

    python tools/fake_sensor.py --backfill-hours 24 --once
"""

import argparse
import json
import math
import random
import sys
import time

import paho.mqtt.client as mqtt

# A plausible Malaysian bedroom: warm, humid, and air-conditioned in the small
# hours. Values drift smoothly rather than jumping, so the chart looks like real
# sensor data instead of noise.
BASE_TEMP = 27.5      # °C mean
TEMP_SWING = 2.5      # °C peak-to-mean over a day
BASE_HUMIDITY = 68.0  # %
BASE_PRESSURE = 1009.0  # hPa


def node_bias(room: str, node: str) -> tuple[float, float, float]:
    """A small, stable per-node offset for (temperature, humidity, pressure).

    Two rooms in the same house are never identical, and without this every
    node draws the same curve — the lines land exactly on top of each other and
    a multi-node chart looks broken rather than informative. Derived from the
    name so it is stable across restarts.
    """
    seed = sum(ord(c) * (i + 1) for i, c in enumerate(f"{room}/{node}"))
    rng = random.Random(seed)
    return (
        rng.uniform(-1.2, 1.2),    # °C
        rng.uniform(-6.0, 6.0),    # %RH — rooms differ most here
        rng.uniform(-0.6, 0.6),    # hPa — barely varies within one house
    )


def reading(ts: float, temp_offset: float = 0.0, bias: tuple = (0.0, 0.0, 0.0)) -> dict:
    """Synthesise one plausible sample for the given time.

    Deterministic in `ts` apart from a small noise term, so a backfill produces
    a smooth curve rather than a jagged mess.
    """
    # Fraction through the day, 0.0 at midnight.
    day = (ts % 86400) / 86400.0
    tb, hb, pb = bias

    # Coolest around 05:00, warmest around 15:00 — hence the phase shift.
    temp = BASE_TEMP + TEMP_SWING * math.sin((day - 0.21) * 2 * math.pi) + temp_offset + tb
    temp += random.uniform(-0.12, 0.12)

    # Humidity runs opposite to temperature: cool air holds less moisture.
    humidity = BASE_HUMIDITY - 9 * math.sin((day - 0.21) * 2 * math.pi) + hb
    humidity += random.uniform(-0.5, 0.5)
    humidity = max(0.0, min(100.0, humidity))

    pressure = BASE_PRESSURE + 1.6 * math.sin(day * 4 * math.pi) + pb + random.uniform(-0.1, 0.1)

    return {
        "temperature": round(temp, 2),
        "humidity": round(humidity, 2),
        "pressure": round(pressure, 2),
    }


def publish(client, room: str, node: str, values: dict, ts: float | None = None):
    """Publish the same shape the real firmware does: one topic per metric,
    plus a single JSON snapshot on .../state.

    When `ts` is given we publish ONLY the snapshot, carrying that timestamp.
    That is how backfill works: the collector honours a `ts` field in the JSON,
    so historical readings land at their real times instead of all bunching up
    at "now". Skipping the per-metric topics avoids them being stored with the
    arrival time and winning the de-duplication race.

    Returns the MQTTMessageInfo for the snapshot, so a caller that needs
    delivery guaranteed can wait on it.
    """
    prefix = f"home/{room}/{node}"
    snapshot = {**values, "sensor": "fake", "node": node, "room": room}

    if ts is None:
        for metric, value in values.items():
            client.publish(f"{prefix}/{metric}", str(value), qos=1)
    else:
        snapshot["ts"] = round(ts, 3)

    return client.publish(f"{prefix}/state", json.dumps(snapshot), qos=1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="localhost", help="MQTT broker (the Pi's IP, once it exists)")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--room", default="bedroom")
    ap.add_argument("--node", default="node1")
    ap.add_argument("--interval", type=float, default=5.0, help="seconds between readings (default 5, faster than the real node so charts fill quickly)")
    ap.add_argument("--backfill-hours", type=float, default=0, help="publish this many hours of history first")
    ap.add_argument("--backfill-step", type=float, default=300, help="seconds between backfilled samples (default 300)")
    ap.add_argument("--once", action="store_true", help="exit after the backfill instead of streaming")
    ap.add_argument("--offset", type=float, default=0.0, help="°C offset, to make a second node differ")
    args = ap.parse_args()
    bias = node_bias(args.room, args.node)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"fake-{args.room}-{args.node}")

    try:
        client.connect(args.host, args.port, keepalive=60)
    except OSError as exc:
        print(f"could not reach the broker at {args.host}:{args.port} — {exc}", file=sys.stderr)
        print("\nIs mosquitto running? On your laptop:", file=sys.stderr)
        print("    mosquitto -c hub/mosquitto/room-sensors.conf -v", file=sys.stderr)
        print("\nIf you are pointing at the Pi and it refuses the connection, the broker is", file=sys.stderr)
        print("probably still listening on localhost only — see docs/03-hub-mosquitto.md.", file=sys.stderr)
        return 1

    client.loop_start()
    print(f"publishing as home/{args.room}/{args.node}/... to {args.host}:{args.port}")

    if args.backfill_hours:
        now = time.time()
        start = now - args.backfill_hours * 3600
        count = 0
        ts = start
        while ts < now:
            info = publish(client, args.room, args.node, reading(ts, args.offset, bias), ts=ts)
            # Wait for the broker to acknowledge each message before sending the
            # next. Without this, a burst of a few hundred QoS-1 publishes
            # overruns paho's in-flight window, the surplus sits in a local
            # queue, and disconnect() throws that queue away — so most of the
            # backfill silently never arrives. Locally the round trip is well
            # under a millisecond, so this costs nothing noticeable.
            info.wait_for_publish(timeout=10)
            ts += args.backfill_step
            count += 1
        print(f"backfilled {count} readings over {args.backfill_hours}h")

    if args.once:
        client.loop_stop()
        client.disconnect()
        return 0

    try:
        while True:
            values = reading(time.time(), args.offset, bias)
            publish(client, args.room, args.node, values)
            print(f"  {values['temperature']}°C  {values['humidity']}%  {values['pressure']}hPa", flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        client.loop_stop()
        client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
