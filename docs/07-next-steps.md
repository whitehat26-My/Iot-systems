# 07 — Next steps

Ordered roughly by value-for-effort. Nothing here is required; the system is
complete without it.

---

## Add a second node (~RM 40, one hour)

The cheapest satisfying upgrade, and the reason the hub was worth its price.

1. Wire up another ESP32 + BME280 exactly as before.
2. Copy your `config.py`, change two lines:
   ```python
   ROOM = "study"
   NODE = "node2"
   ```
3. `./tools/deploy_node.sh /dev/ttyUSB1`

That's it. **Nothing on the Pi changes.** The collector is subscribed to `home/#`,
the API groups by node automatically, and the dashboard adds a second line to every
chart and a new node in the filter. This is what MQTT bought you.

Good next rooms: the kitchen (watch cooking spike the humidity), outside in the
shade (see how much the walls actually buy you), or the fridge.

## Show the reading on the device (RM 12–18)

An SSD1306 OLED shares the BME280's I²C pins — no extra wiring. You get a little
device that shows the temperature on its own, which makes it feel finished.

```python
# in main.py, after make_sensor()
import ssd1306
display = ssd1306.SSD1306_I2C(128, 64, i2c)
display.fill(0)
display.text("{:.1f} C".format(values["temperature"]), 0, 0)
display.text("{:.0f} %".format(values["humidity"]), 0, 16)
display.show()
```

`mpremote mip install ssd1306` to get the driver.

## Motion detection (RM 6–10)

A PIR sensor (HC-SR501) has three pins: VCC to 5V (this one *does* want 5V), GND,
and OUT to any free GPIO. It pulls OUT high for a few seconds when it sees
movement.

```python
from machine import Pin
pir = Pin(13, Pin.IN)
if pir.value():
    client.publish("home/bedroom/node1/motion", "1")
```

Publish it as a metric and it appears on the dashboard like any other. Worth
knowing: PIR sensors need a minute after power-on to settle, and they false-trigger
on moving warm air — including from an air-conditioner.

## Hardening MQTT

Do this before the broker is reachable from anywhere but your own LAN.

**1. Username and password.** On the Pi:

```bash
sudo mosquitto_passwd -c /etc/mosquitto/passwd iotnode      # prompts for a password
sudo chown mosquitto:mosquitto /etc/mosquitto/passwd
sudo chmod 640 /etc/mosquitto/passwd
```

Then in `/etc/mosquitto/conf.d/room-sensors.conf`, replace
`allow_anonymous true` with:

```
allow_anonymous false
password_file /etc/mosquitto/passwd
```

Restart, then tell both ends who they are:

```python
# firmware/room_sensor/main.py, in connect_mqtt()
client = MQTTClient(CLIENT_ID, config.MQTT_HOST, port=config.MQTT_PORT,
                    user="iotnode", password="...", keepalive=...)
```
```python
# server/collector.py, in main() before connect()
client.username_pw_set("iotnode", "...")
```

Put those credentials in `config.py` (gitignored), not in the committed files.

**2. TLS** is a bigger job — you generate a CA and a server certificate, copy the
CA cert onto every node, and MicroPython's TLS is memory-hungry on an ESP32. Worth
it if you're publishing across an untrusted network; overkill inside your own house.

**3. Remote access: use a VPN, not a port forward.** This is the important one.

**Do not port-forward 1883 or 8000.** An exposed MQTT broker gets found within
hours — scanners index them continuously — and anyone can then read your data or
inject fake readings. An exposed dashboard is a foothold in your home network.

Install [Tailscale](https://tailscale.com/) on the Pi and your phone instead:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Your devices get private addresses reachable from anywhere, with nothing open to
the internet. Free for personal use, and about ten minutes of work.

## Grafana and InfluxDB

When you want proper dashboards — multi-year zooming, alert rules, annotations —
this is the standard destination. Run both in Docker on the Pi:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER      # log out and back in
```

Then point Telegraf (or a small Python bridge, reusing `collector.py`'s MQTT
handling) at InfluxDB, and add InfluxDB as a Grafana data source.

**Do it as an addition, not a replacement.** Keep SQLite and the simple dashboard
running — they're 200 lines you fully understand, which is exactly what you want
when something breaks at midnight. This is also where 4GB of RAM starts to earn
its price.

## Home Assistant

If you'd rather have a polished app, phone notifications and automations than
write code, Home Assistant is the answer. It auto-discovers MQTT devices, so your
existing nodes largely just appear.

Install it as a container alongside what you have. The honest trade: you get a
great deal of capability for very little work, and you stop learning how any of it
works. Having built this first, you're in a good position to make that trade
deliberately.

## Reliability upgrades

**NVMe instead of the SD card** (~RM 180). SD cards wear out and fail by corrupting
data. An M.2 HAT plus a small SSD is the single biggest reliability improvement
available to a Pi 5, and it's much faster. Clone the card across with
`rpi-clone` or Raspberry Pi Imager.

**Automatic backups.** The database is one file, so this is easy:

```bash
# crontab -e, daily at 3am
0 3 * * * sqlite3 ~/Iot-systems/readings.db ".backup ~/backup-$(date +\%F).db"
```

Use `.backup` rather than `cp` — it's safe to run while the collector is writing.

**Watchdog.** `sudo apt install watchdog` and enable the Pi's hardware watchdog, so
a fully wedged kernel reboots itself. Rare, but it's the difference between a
five-minute gap and a week-long one while you're away.

## Control — and mains voltage

Sensing is read-only and completely safe. Switching things is where you can get
hurt, so:

**Do not build your own mains switching.** 240V AC kills people, and a relay module
on a breadboard next to a jumper wire is exactly the wrong place to learn that.

**Buy a smart plug that runs open firmware instead.** A Sonoff S26 or similar,
flashed with [Tasmota](https://tasmota.github.io/) or
[ESPHome](https://esphome.io/), speaks MQTT to *your* broker — no cloud, no
account. All the mains wiring is done properly inside a moulded enclosure by
people who do it for a living.

Then automation is just a few lines on the Pi, subscribing to your temperature
topic and publishing to the plug's command topic:

```python
if temperature > 30.0:
    client.publish("cmnd/fan-plug/POWER", "ON")
```

For low-voltage things — a 5V USB fan, an LED strip — a transistor or a small
relay driven from a GPIO is fine and genuinely worth learning. It's mains
specifically that you should buy rather than build.

---

## Ideas worth trying

- **Dew point and "feels like"** — compute them from temperature and humidity in
  `collector.py`, store as extra metrics. They appear on the dashboard for free.
- **Sensor on the balcony** — quantify how much your walls are actually doing.
- **CSV export** — one more FastAPI route, and you can plot a month in a
  spreadsheet.
- **Battery node** — an ESP32 in deep sleep between readings runs for months on
  18650 cells. This is where the ESP32 comprehensively beats the Pi, and it's a
  genuinely different engineering problem: every millisecond awake costs you days
  of runtime.
- **CO₂** — an MH-Z19 or SCD40 (RM 80–150) measures actual CO₂. Bedroom levels
  overnight are often startling, and it's the one measurement here that might
  change your behaviour.

---

Back to the [README](../README.md).
