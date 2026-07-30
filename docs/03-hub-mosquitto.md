# 03 — The MQTT broker

**Goal:** a broker on the Pi that your whole network can reach — verified from
your laptop, before any device depends on it.

**Time:** 10 minutes.

---

## What MQTT is doing here

MQTT is a tiny publish/subscribe protocol built for exactly this: small devices,
unreliable networks, one central point. A node *publishes* a reading to a topic
like `home/bedroom/node1/temperature`; anything that *subscribed* to that topic
gets a copy. The broker (Mosquitto) is the post office in the middle.

Why bother, instead of having the ESP32 POST to the API directly?

- **Nothing needs to know about anything else.** Add a node in the study and the
  server needs no change at all — it's already subscribed to `home/#`.
- **You can watch the raw traffic.** `mosquitto_sub -t 'home/#' -v` shows every
  reading as it arrives, which makes "is the sensor broken or is my server
  broken?" a five-second question instead of an afternoon.
- **It's the actual standard.** Home Assistant, Node-RED, Grafana and ESPHome all
  speak it, so nothing you build here is a dead end.

Our topic scheme:

```
home/<room>/<node>/<metric>      home/bedroom/node1/temperature   ->  "24.61"
home/<room>/<node>/state         a JSON snapshot of all metrics at once
home/<room>/<node>/status        "online" / "offline"
```

## Install and configure

On the Pi, from the repo:

```bash
sudo apt install -y mosquitto mosquitto-clients
sudo cp hub/mosquitto/room-sensors.conf /etc/mosquitto/conf.d/
sudo systemctl enable mosquitto
sudo systemctl restart mosquitto
systemctl status mosquitto        # expect: active (running)
```

(If you'd rather do everything at once, `./hub/install.sh` in
[06](06-run-the-stack.md) includes this step.)

---

## ⚠️ The one that gets everybody

**A stock Mosquitto install listens on `localhost` only.**

Everything works when you test on the Pi itself. Then your ESP32 refuses to
connect and reports something useless like `connect failed` or `ECONNABORTED`,
with nothing in the way of an explanation. People lose entire evenings to this,
usually blaming their WiFi or the ESP32.

The fix is these two lines, which is why `hub/mosquitto/room-sensors.conf` ships
as a real file rather than as an instruction to go and edit something:

```
listener 1883 0.0.0.0
allow_anonymous true
```

`0.0.0.0` means "accept connections on every network interface". That's what lets
the ESP32 in.

Confirm it took. You want to see `0.0.0.0` or `*` — **not** `127.0.0.1`:

```bash
ss -ltnp | grep 1883
# LISTEN 0 100 0.0.0.0:1883 0.0.0.0:*  users:(("mosquitto",...))
```

If `ss` isn't found (it lives in `/usr/sbin`, which isn't always on a normal
user's PATH), either of these does the same job:

```bash
/usr/sbin/ss -ltn | grep 1883
lsof -nP -iTCP:1883 -sTCP:LISTEN      # want *:1883, not 127.0.0.1:1883
```

## Prove it works from another machine

This is the actual milestone, and the reason to do it now: **verify the network
path before a device depends on it.** Otherwise, when the ESP32 fails later, you
won't know whether the problem is the board, the WiFi, or the broker.

**Terminal 1, on your laptop** (replace with your Pi's IP):

```bash
mosquitto_sub -h 192.168.1.50 -t 'home/#' -v
```

It will sit there silently. That's correct — nothing is publishing yet.

> No `mosquitto_sub` on your laptop? macOS: `brew install mosquitto`.
> Debian/Ubuntu: `sudo apt install mosquitto-clients`.
> Windows: install Mosquitto from <https://mosquitto.org/download/>.

**Terminal 2, also on your laptop:**

```bash
mosquitto_pub -h 192.168.1.50 -t 'home/test/hello' -m 'it works'
```

Terminal 1 should immediately print:

```
home/test/hello it works
```

**That round trip — laptop → Pi → laptop — is the milestone.** Your broker is
reachable across your network.

### If nothing arrives

Work down this list in order; it's roughly most to least likely.

| Symptom | Cause | Fix |
|---|---|---|
| `Connection refused` | Broker on localhost only | The config above isn't applied. Check `ss -ltnp \| grep 1883` and `sudo systemctl restart mosquitto` |
| `Connection refused` | Broker not running | `systemctl status mosquitto`, then `journalctl -u mosquitto -n 30` |
| `Host is unreachable` / timeout | Wrong IP | `hostname -I` on the Pi |
| Timeout, right IP | Laptop and Pi on different networks | Guest WiFi and 2.4/5GHz bands are often isolated from each other. Get both on the same network. |
| Connects, no messages | Typo in the topic | Subscribe to `#` (everything) to check |

Turn up the logging if you're stuck. Add `log_type debug` to the config,
restart, and watch:

```bash
journalctl -u mosquitto -f
```

Every connection attempt is logged with a reason, which usually ends the mystery
immediately. Take the line out again afterwards — it's noisy.

## A word on security

The broker accepts **anonymous connections from anywhere on your LAN**. That is a
deliberate choice: it's a home network you control, and requiring certificates to
get your first reading would be a miserable start.

**Do not port-forward 1883 on your router.** An open MQTT broker on the public
internet gets found within hours — they're indexed by scanners — and anyone can
then read your sensor data or publish fake readings into your database.

If you want your dashboard while you're out of the house, use a VPN
(Tailscale is the easy option) rather than opening ports. Adding a username,
password and TLS is covered in [07 — Next steps](07-next-steps.md#hardening-mqtt),
and is worth doing before this ever leaves your LAN.

---

**Next:** [06 — Run the stack](06-run-the-stack.md) to get the collector and
dashboard running on the Pi, or [04 — Node wiring](04-node-wiring.md) if your
ESP32 has arrived and you want to jump to hardware.
