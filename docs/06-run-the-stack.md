# 06 — Running the stack

This is the spine of the project: eight steps, each ending in something you can
see working. **Don't start the next one until the current one works.**

Steps 1 needs no hardware at all. Steps 2–4 need the Pi. Steps 5–8 need the ESP32.

| | Step | You end up with |
|---|---|---|
| 1 | [Run it all on your laptop](#step-1--run-it-all-on-your-laptop-no-hardware) | A working dashboard, fake data, **today** |
| 2 | [Pi on the network](#step-2--pi-on-the-network) | SSH, fixed IP |
| 3 | [Broker reachable](#step-3--broker-reachable) | Laptop → Pi → laptop round trip |
| 4 | [App on the Pi](#step-4--app-on-the-pi) | Dashboard on your phone |
| 5 | [ESP32 alive](#step-5--esp32-alive) | A Python prompt on the board |
| 6 | [Sensor wired](#step-6--sensor-wired) | Real numbers over USB |
| 7 | [Join the halves](#step-7--join-the-halves) | **Your room on your own dashboard** |
| 8 | [Make it permanent](#step-8--make-it-permanent) | Survives reboots, runs overnight |

---

## Step 1 — Run it all on your laptop (no hardware)

**This is the step to do while your parts are in the post.** It builds and debugs
roughly 70% of the project. When the hardware arrives you'll be plugging it into
something you already know works — instead of debugging new hardware and new
software at the same time, which is where most first projects die.

Install a broker on your laptop:

- **macOS:** `brew install mosquitto`
- **Debian / Ubuntu / WSL:** `sudo apt install mosquitto mosquitto-clients`
- **Windows:** installer at <https://mosquitto.org/download/>

Then set up Python:

```bash
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r hub/requirements.txt
```

Now four terminals. Activate the venv in each one.

```bash
# terminal 1 — the broker
mosquitto -c hub/mosquitto/room-sensors.conf -v
```
```bash
# terminal 2 — a pretend ESP32
python tools/fake_sensor.py
```
```bash
# terminal 3 — MQTT into SQLite
python server/collector.py
```
```bash
# terminal 4 — the dashboard
python server/api.py
```

Open <http://localhost:8000>.

You should see a live chart that grows every few seconds. To fill it out
immediately with a day of history, and add a second room so you can see
multi-node charts:

```bash
python tools/fake_sensor.py --backfill-hours 24 --once
python tools/fake_sensor.py --room study --node node2 --backfill-hours 24 --once
python tools/fake_sensor.py --room study --node node2      # leave it streaming
```

### Verify each layer

Check in this order, so a failure tells you *where* it is:

```bash
# 1. MQTT — is anything on the wire?
mosquitto_sub -t 'home/#' -v
```
```bash
# 2. Storage — did it get written?
sqlite3 readings.db 'select * from readings order by ts desc limit 5'
```
```bash
# 3. API — can it be read back?
curl localhost:8000/api/health
curl 'localhost:8000/api/readings?metric=temperature&hours=1'
```
```bash
# 4. Secrets — nothing private staged?
git status        # must NOT list config.py or readings.db
```

Then run the tests, which need no hardware either:

```bash
python3 tests/test_bme280.py      # sensor driver, against a simulated chip
python3 tests/test_contract.py    # real firmware -> broker -> SQLite -> API
```

The second one is worth understanding: it imports the actual
`firmware/room_sensor/main.py` and runs its publish path against your broker, so
you've verified the ESP32's side of the contract before owning an ESP32. See
[tests/README.md](../tests/README.md).

Once that's all green, you're done until the parcels arrive.

---

## Step 2 — Pi on the network

Follow [02 — Hub setup](02-hub-setup.md).

**Milestone:** `ssh you@<pi-ip>` works, and you've reserved that IP in your
router so it can't move.

---

## Step 3 — Broker reachable

Follow [03 — Mosquitto](03-hub-mosquitto.md).

**Milestone:** from your **laptop**, `mosquitto_sub -h <pi-ip> -t 'home/#' -v`
receives a message you publish from your laptop.

Proving the network path now — before any device depends on it — is what stops the
ESP32 step from becoming a guessing game.

---

## Step 4 — App on the Pi

On the Pi:

```bash
cd ~/Iot-systems
./hub/install.sh
```

That script installs the broker config, creates a venv, installs dependencies, and
registers two systemd services that start at boot. It's safe to re-run — it's also
how you apply changes after a `git pull`.

It prints a status block at the end. All three should be `[ok]`:

```
    [ok]   mosquitto
    [ok]   iot-collector
    [ok]   iot-api
```

Now push data at it **from your laptop**, so you're testing the real network path:

```bash
python tools/fake_sensor.py --host <pi-ip> --backfill-hours 24 --once
python tools/fake_sensor.py --host <pi-ip>
```

Open `http://<pi-ip>:8000` — **on your phone**, on the same WiFi.

**Milestone: a dashboard served by your own hardware, on your phone, charting data
over your own network.** Your laptop is no longer needed to serve anything.

```bash
# if something isn't running
systemctl status iot-collector iot-api
journalctl -u iot-collector -f
```

---

## Step 5 — ESP32 alive

Follow [05 — Flashing the node](05-node-flash.md), steps 1–5.

**Milestone:** `mpremote` gives you a `>>>` prompt and `2 + 2` returns `4`. No
sensor involved yet — one thing at a time.

---

## Step 6 — Sensor wired

Follow [04 — Node wiring](04-node-wiring.md).

**Milestone:** an I²C scan prints `['0x76']` (or `0x77`), and a manual read gives
you a real temperature. Breathe on the sensor and watch humidity climb.

---

## Step 7 — Join the halves

Set `MQTT_HOST` in `firmware/room_sensor/config.py` to your Pi's IP, then:

```bash
./tools/deploy_node.sh
mpremote                     # watch it: Ctrl-] to exit
```

You want:

```
wifi: connected. ip 192.168.1.87 gateway 192.168.1.1
sensor: BME280
mqtt: connected to 192.168.1.50:1883 as bedroom-node1
humidity=68.41 pressure=1008.72 temperature=27.34
```

On the Pi, confirm the readings are arriving:

```bash
mosquitto_sub -t 'home/#' -v
```

Now stop the fake sensor on your laptop. **If the chart keeps moving, it's real.**

### 🎉 Milestone

**Your room is on your own private dashboard, end to end, with nothing in the
cloud.** A sensor you wired, firmware you can read, a broker and database and web
page on hardware you own.

---

## Step 8 — Make it permanent

Three things separate a working experiment from something that's actually running.

**1. Off the laptop.** Unplug the ESP32 from your computer and into a phone
charger. It has no dependency on your laptop — `main.py` runs on power-up.

**2. Survives a reboot.** This is the real test:

```bash
sudo reboot            # on the Pi
```

Wait a minute, then:

```bash
systemctl status mosquitto iot-collector iot-api    # all three active again
curl localhost:8000/api/health
```

All three come back by themselves because `install.sh` enabled them. A hub that
needs you to log in and start things after every power cut isn't a hub.

**3. Survives a node dropping out.** Unplug the ESP32 for two minutes and watch
the dashboard: the tile goes amber and says `stale`, because the node's last-will
message told the broker it vanished. Plug it back in — it reconnects on its own and
the chart resumes with a visible gap. That gap is honest: it says "no data here"
rather than drawing a straight line through missing time.

**Then leave it overnight.** Come back in the morning to a graph of your room while
you slept — the air-conditioning cycling, the temperature bottoming out before
dawn, humidity moving opposite to it.

That's the point at which it stops being a project and starts being infrastructure.

---

## Where things live

| | |
|---|---|
| Database | `~/Iot-systems/readings.db` (gitignored) |
| Collector logs | `journalctl -u iot-collector -f` |
| API logs | `journalctl -u iot-api -f` |
| Broker logs | `journalctl -u mosquitto -f` |
| Broker config | `/etc/mosquitto/conf.d/room-sensors.conf` |
| Services | `/etc/systemd/system/iot-{collector,api}.service` |

Handy queries:

```bash
# highest and lowest today, per node
sqlite3 readings.db "select room||'/'||node, round(min(value),1), round(max(value),1)
  from readings where metric='temperature' and ts > strftime('%s','now','-1 day')
  group by room, node;"

# how big is it getting?
du -h readings.db
```

At 30-second intervals with three metrics, expect roughly 25 MB per node per year
— nothing. Readings older than 90 days are pruned automatically
(`RETENTION_DAYS` in `server/config.py`).

---

**Next:** [07 — Next steps](07-next-steps.md).
