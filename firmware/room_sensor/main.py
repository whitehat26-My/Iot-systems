"""The sensor node: read the room, publish it, sleep, repeat. Forever.

Runs automatically after boot.py. Over USB you will see each reading printed, so
this doubles as the diagnostic view during steps 5-7.

Failure handling is the interesting part. This board will sit on a shelf for
months with nobody watching it, so every step assumes things break:

  * The sensor is re-detected if it stops responding (a nudged wire).
  * MQTT reconnects on any network error, with backoff.
  * After MAX_FAILURES_BEFORE_REBOOT consecutive failures it reboots, which
    clears the occasional wedged WiFi stack.
  * A last-will message tells the hub when this node drops off, so the
    dashboard can show it as stale rather than showing a stale number as if it
    were current.
"""

import json
import sys
import time

from machine import Pin, reset

import boot
import config

try:
    from umqtt.simple import MQTTClient
except ImportError:
    print("\nMissing the umqtt library. From your laptop, run:\n")
    print("    mpremote mip install umqtt.simple\n")
    print("(or ./tools/deploy_node.sh, which does it for you)")
    raise


led = Pin(config.LED_PIN, Pin.OUT) if getattr(config, "LED_PIN", None) is not None else None

TOPIC_BASE = "home/{}/{}".format(config.ROOM, config.NODE)
STATUS_TOPIC = TOPIC_BASE + "/status"

# A stable client id. Reusing it means a node that reboots replaces its old
# session on the broker instead of accumulating ghosts.
CLIENT_ID = "{}-{}".format(config.ROOM, config.NODE)


def blink(times=1, ms=60):
    if led is None:
        return
    for _ in range(times):
        led.value(1)
        time.sleep_ms(ms)
        led.value(0)
        time.sleep_ms(ms)


def connect_mqtt():
    """Connect to the broker, announcing ourselves and arranging a last will."""
    client = MQTTClient(
        CLIENT_ID,
        config.MQTT_HOST,
        port=config.MQTT_PORT,
        keepalive=max(60, config.PUBLISH_INTERVAL * 3),
    )

    # The broker sends this on our behalf if we vanish without saying goodbye —
    # a power cut, a crash, or WiFi dropping. Retained, so anything subscribing
    # later still learns we are gone.
    client.set_last_will(STATUS_TOPIC, b"offline", retain=True, qos=0)

    client.connect()
    client.publish(STATUS_TOPIC, b"online", retain=True, qos=0)
    print("mqtt: connected to {}:{} as {}".format(config.MQTT_HOST, config.MQTT_PORT, CLIENT_ID))
    return client


def publish(client, values):
    """One topic per metric, plus a JSON snapshot.

    Per-metric topics are what other MQTT tools expect and what makes
    `mosquitto_sub -t 'home/#' -v` readable. The snapshot gives the whole
    reading atomically, and is the fallback the collector uses for any metric it
    did not see individually.
    """
    for metric, value in values.items():
        client.publish("{}/{}".format(TOPIC_BASE, metric), str(value))

    snapshot = dict(values)
    snapshot["node"] = config.NODE
    snapshot["room"] = config.ROOM
    # Seconds of uptime. Useful later: a node whose uptime keeps resetting is
    # rebooting, which is a very different problem from one that never connects.
    snapshot["uptime"] = time.ticks_ms() // 1000
    # Deliberately NO timestamp: this board has no battery-backed clock, so any
    # time it reported would be wrong. The hub stamps readings on arrival.
    client.publish("{}/state".format(TOPIC_BASE), json.dumps(snapshot))


def make_sensor():
    """Detect the attached sensor, printing what was found and any caveats."""
    import sensor as sensor_lib

    device = sensor_lib.Sensor(
        scl_pin=config.I2C_SCL_PIN,
        sda_pin=config.I2C_SDA_PIN,
        dht_pin=getattr(config, "DHT_PIN", None),
    )
    print("sensor:", device.kind)
    for note in device.notes:
        print("  -", note)
    return device


def main():
    print("\n--- {} starting ---".format(CLIENT_ID))
    blink(2)

    # WiFi first. If this fails there is nothing to do but reboot and retry —
    # the router may still be coming up after a power cut, which is exactly the
    # situation this needs to survive unattended.
    try:
        boot.connect(config.WIFI_SSID, config.WIFI_PASSWORD, led=led)
    except OSError as exc:
        print(exc)
        print("rebooting in 30s to try again")
        time.sleep(30)
        reset()

    sensor = make_sensor()
    client = connect_mqtt()
    blink(3)

    failures = 0
    backoff = 1

    while True:
        try:
            values = sensor.read()
            publish(client, values)

            # A compact line per reading, so watching over USB tells you
            # everything at a glance.
            print(" ".join("{}={}".format(k, v) for k, v in sorted(values.items())))

            blink(1, 30)
            failures = 0
            backoff = 1
            time.sleep(config.PUBLISH_INTERVAL)

        except OSError as exc:
            # Network trouble: broker restarted, WiFi blipped, cable unplugged.
            failures += 1
            print("network error ({}), reconnecting in {}s: {}".format(failures, backoff, exc))
            try:
                client.disconnect()
            except Exception:
                pass                        # already dead; nothing to clean up

            time.sleep(backoff)
            backoff = min(backoff * 2, 60)  # back off, but keep trying forever

            try:
                client = connect_mqtt()
            except OSError as exc2:
                print("  still down: {}".format(exc2))

        except Exception as exc:
            # Sensor trouble: a wire came loose, or the chip stopped answering.
            failures += 1
            print("sensor error ({}): {}".format(failures, exc))
            sys.print_exception(exc)
            time.sleep(5)
            try:
                sensor = make_sensor()      # re-detect; often just a nudged wire
            except Exception as exc2:
                print("  re-detect failed: {}".format(exc2))

        if failures >= config.MAX_FAILURES_BEFORE_REBOOT:
            # The reliable, boring fix that needs nobody in the room.
            print("{} consecutive failures — rebooting".format(failures))
            time.sleep(1)
            reset()


if __name__ == "__main__":
    main()
