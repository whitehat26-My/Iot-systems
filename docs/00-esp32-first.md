# 00 — Start with just the ESP32

**The cheap route: RM 47–86, no Raspberry Pi.** Your laptop is the hub. Buy the Pi
later, once you know you want it.

This is the recommended way to start. The ESP32 is the harder and more
interesting half — wiring, flashing, debugging a board with no screen — and it's
where the actual learning is. The Pi is mostly `apt install`.

**Nothing here is throwaway work.** Your laptop does exactly what the Pi will do,
running the same code from the same repo. When the Pi arrives, it takes over and
the only change on the node is one line.

---

## What to buy now

Just the node section of [01 — Parts list](01-parts-list.md):

- [ ] ESP32 DevKitC — RM 20–35 (two if you can)
- [ ] BME280 module — RM 12–20 (watch for BMP280s sold as BME280)
- [ ] Breadboard 830 pts — RM 8–12
- [ ] Dupont jumper wires — RM 5–8
- [ ] USB **data** cable, matching your board's socket — RM 5–15

Skip the entire Pi section. You already own the hub — it's the laptop you're
reading this on.

## The route

| | Step | Doc |
|---|---|---|
| 1 | Build the software stack on your laptop, with a fake sensor | [06 § Step 1](06-run-the-stack.md#step-1--run-it-all-on-your-laptop-no-hardware) |
| 2 | Make the broker reachable from your ESP32 | [below](#make-your-laptop-reachable) |
| 3 | Flash MicroPython, get a REPL | [05](05-node-flash.md) |
| 4 | Wire the sensor, prove I²C sees it | [04](04-node-wiring.md) |
| 5 | Point the node at your laptop and publish | [below](#point-the-node-at-your-laptop) |
| — | *later*: move the hub to a Pi | [below](#when-the-pi-arrives) |

Skip docs 02 and 03 for now — those are Pi setup. Come back to them when you buy
one.

---

## Make your laptop reachable

The node connects to your laptop over WiFi, so two things have to be true that
didn't matter when everything was on one machine.

### 1. Find your laptop's IP

```bash
# macOS
ipconfig getifaddr en0

# Linux
hostname -I | awk '{print $1}'

# Windows (PowerShell)
(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Wi-Fi').IPAddress
```

You want something like `192.168.1.23`. If it starts with `169.254.` you aren't
properly on the network.

**This address will change** when your laptop reconnects or your router reboots,
and then your node is publishing into the void. Two options:

- **Reserve it in your router** (DHCP reservation, same technique as
  [02 § 5](02-hub-setup.md#5-pin-the-pis-address--dont-skip-this)). Do this — it
  takes two minutes and saves a confusing evening later.
- Or just re-check the IP and re-run `./tools/deploy_node.sh` when things stop
  working.

### 2. Let the broker through your firewall ← the one that bites

This is the laptop equivalent of Mosquitto's localhost-only trap. Our config
already binds `0.0.0.0`, so the broker is listening — but your OS firewall may
drop the incoming connection before it gets there, and the ESP32 just reports a
generic timeout.

**macOS** — the first time you run `mosquitto` you get a dialog: *"Do you want the
application to accept incoming network connections?"* Click **Allow**. If you
clicked Deny once, fix it in System Settings → Network → Firewall → Options.

**Windows** — Defender Firewall prompts on first run. Tick **Private networks**
and allow. If you missed it: Windows Security → Firewall & network protection →
Allow an app through firewall → find mosquitto.

**Linux** — usually no firewall by default. If you run `ufw`:
```bash
sudo ufw allow from 192.168.0.0/16 to any port 1883 comment 'MQTT on LAN'
```

### 3. Prove it before involving the ESP32

From a **phone or another computer** on the same WiFi — not the laptop itself,
that would prove nothing:

```bash
mosquitto_sub -h 192.168.1.23 -t 'home/#' -v
```

No second machine handy? This at least confirms the broker is bound correctly
rather than only on localhost:

```bash
# macOS / Linux
lsof -nP -iTCP:1883 -sTCP:LISTEN
# want 0.0.0.0:1883 or *:1883 — NOT 127.0.0.1:1883
```

---

## Point the node at your laptop

In `firmware/room_sensor/config.py`:

```python
MQTT_HOST = "192.168.1.23"    # your laptop's IP, not the Pi's
```

Everything else is identical to the Pi route. Deploy and watch:

```bash
./tools/deploy_node.sh
mpremote                      # Ctrl-] to exit
```

Then, with the broker + collector + api running on your laptop, open
<http://localhost:8000>. Stop `fake_sensor.py`, and if the chart keeps moving it's
your actual room.

**That's the milestone** — and it's the same milestone as the full build. You have
a real sensor, publishing over your network, into your own database and dashboard.

---

## What running on a laptop costs you

Worth being clear about, because these are exactly the itches the Pi scratches.

**No 24/7 collection.** Close the lid and collection stops. Your overnight graph —
the air-conditioning cycling, temperature bottoming out before dawn — needs the
laptop awake all night. You can force that:

```bash
caffeinate -s          # macOS, Ctrl-C to stop
```
```powershell
powercfg /change standby-timeout-ac 0     # Windows, 0 = never
```

**The node handles the gaps by itself.** When your laptop sleeps, the ESP32 gets a
network error, backs off (1s, 2s, 4s… up to 60s), and keeps retrying forever. After
10 consecutive failures it reboots itself and starts over. When the laptop comes
back it reconnects with no intervention. You'll see a gap in the chart — which is
honest, it says "no data here" rather than drawing a line through missing time.

If the constant reboots bother you, raise `MAX_FAILURES_BEFORE_REBOOT` in
`config.py`. They're harmless either way.

**Four terminals to start.** On the Pi these are systemd services that come back
after a power cut. On the laptop you start them by hand each time.

**No access when you're out.** The dashboard exists only while your laptop is on
and on the same network.

None of these are reasons not to start here. They're the reasons the Pi is worth
RM 450 *later* — once you've felt the lack rather than taken my word for it.

---

## When the Pi arrives

Migration is genuinely small, and **your history comes with you.**

1. Set the Pi up: [02 — Hub setup](02-hub-setup.md) and
   [03 — Mosquitto](03-hub-mosquitto.md).

2. Install the stack on it:
   ```bash
   git clone https://github.com/whitehat26-My/Iot-systems.git
   cd Iot-systems && ./hub/install.sh
   ```

3. **Carry your readings over.** On the laptop, take a proper SQLite backup — use
   `.backup`, not `cp`, so it's safe even with the collector still running:
   ```bash
   sqlite3 readings.db ".backup readings-backup.db"
   scp readings-backup.db you@<pi-ip>:~/Iot-systems/readings.db
   ```
   Then restart the services on the Pi:
   ```bash
   sudo systemctl restart iot-collector iot-api
   ```
   Every reading you've collected so far shows up on the Pi's dashboard. The
   database is portable — it's one file, and `server/` is the same code on both
   machines.

4. **Repoint the node** — one line in `config.py`:
   ```python
   MQTT_HOST = "192.168.1.50"    # was your laptop, now the Pi
   ```
   ```bash
   ./tools/deploy_node.sh
   ```

5. Shut down the terminals on your laptop. Done — it's now 24/7.

That's the whole migration. Nothing is rewritten, nothing is lost, and the node
never knew anything changed except one IP address.

---

**Next:** [06 § Step 1](06-run-the-stack.md#step-1--run-it-all-on-your-laptop-no-hardware)
— build the software stack today, before the parts arrive.
