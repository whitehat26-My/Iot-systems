# Iot-systems

My first IoT project: sense my room, keep the data at home.

A Raspberry Pi 5 acts as an always-on hub. Cheap ESP32 boards act as sensor nodes,
one per room. Nothing leaves the house — no cloud accounts, no subscriptions, no
vendor app.

```
   ESP32 + BME280              Raspberry Pi 5 (hub)               Any browser
   (in your room)                                                 on your LAN
                          ┌────────────────────────────┐
   ┌──────────────┐       │  mosquitto  (MQTT broker)  │        ┌──────────────┐
   │ read sensor  │       │       ↓                    │        │              │
   │      ↓       │ WiFi  │  collector.py → SQLite     │  HTTP  │  phone or    │
   │ publish MQTT │──────▶│       ↓                    │───────▶│  laptop      │
   │      ↓       │       │  api.py (FastAPI)          │        │              │
   │ sleep 30s    │       │       ↓                    │        └──────────────┘
   └──────────────┘       │  static/index.html (chart) │
                          └────────────────────────────┘
      ~RM 40 per room          runs 24/7, one-time cost
```

Why this split: the Pi is a poor sensor node (expensive, hot, mains-powered) but an
excellent always-on brain. Once it exists, **each extra room costs about RM 40 and
needs zero changes to the hub** — a new node just starts publishing another MQTT
topic.

## Start here

Read the docs in order. Each one ends in something visibly working, and you
shouldn't start the next until the current one does.

| Doc | What you get | Hardware needed |
|---|---|---|
| [01 — Parts list](docs/01-parts-list.md) | A shopping list, ~RM 460–570 | none |
| [02 — Hub setup](docs/02-hub-setup.md) | A Pi you can SSH into | Pi 5 |
| [03 — Mosquitto](docs/03-hub-mosquitto.md) | An MQTT broker your whole LAN can reach | Pi 5 |
| [04 — Node wiring](docs/04-node-wiring.md) | A sensor the ESP32 can see | ESP32 + BME280 |
| [05 — Flashing the node](docs/05-node-flash.md) | MicroPython running on the ESP32 | ESP32 |
| [06 — Run the stack](docs/06-run-the-stack.md) | The whole thing, surviving reboots | all |
| [07 — Next steps](docs/07-next-steps.md) | Where to go after it works | — |

**You can start today, before buying anything.** [Step 1 of doc 06](docs/06-run-the-stack.md#step-1--run-it-all-on-your-laptop-no-hardware)
runs the entire software stack on your laptop against a fake sensor. That's most of
the project built and debugged while your parts are still in the post — so when the
hardware arrives you're plugging it into something you already know works.

## Quickstart (laptop, no hardware)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r hub/requirements.txt

mosquitto -c hub/mosquitto/room-sensors.conf -v   # terminal 1: broker
python tools/fake_sensor.py                       # terminal 2: pretend ESP32
python server/collector.py                        # terminal 3: MQTT → SQLite
python server/api.py                              # terminal 4: dashboard
```

Open <http://localhost:8000>.

To fill the charts with a day of history straight away:

```bash
python tools/fake_sensor.py --backfill-hours 24 --once
```

(If you want auto-reload while editing the server, use
`uvicorn api:app --app-dir server --reload`. The `--app-dir` matters: `server/`
is a plain folder of scripts, not an installed package.)

## Layout

```
docs/                 the walkthrough, in order
hub/                  how the Pi runs the app (install.sh, mosquitto.conf, systemd units)
server/               the app itself — portable, develop on laptop, deploy to Pi
firmware/room_sensor/ MicroPython that runs ON the ESP32
tools/                fake_sensor.py (no hardware needed), deploy_node.sh
tests/                run on a PC, no hardware — see tests/README.md
```

`server/` is deliberately Pi-agnostic: it's plain Python that runs anywhere. `hub/`
holds the Pi-specific glue. That's what lets you develop on your laptop and deploy
with a `git pull`.

The tests need no ESP32: `python3 tests/test_bme280.py` checks the sensor driver
against a simulated chip, and `tests/test_contract.py` runs the real firmware's
publish path through your broker and out the API, so the two halves can't drift
apart unnoticed.

## A note on security

The MQTT broker starts with **anonymous access, bound to your LAN only**. That is a
reasonable default for a first project on a home network you trust, and it keeps
step 3 from turning into a certificate tutorial.

It is **not** safe to expose to the internet. Do not port-forward 1883 or 8000.
When you want access from outside your house, use a VPN (Tailscale/WireGuard) rather
than opening ports — see [07 — Next steps](docs/07-next-steps.md#hardening-mqtt).

Your WiFi password goes in `firmware/room_sensor/config.py`, which is gitignored.
Only `config.example.py` is committed. Check `git status` before your first push.
