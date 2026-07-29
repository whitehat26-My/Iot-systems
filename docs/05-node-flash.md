# 05 — Getting MicroPython onto the ESP32

**Goal:** type Python at your ESP32 and have it answer.

**Time:** 20 minutes the first time, 2 minutes every time after.

---

## 1. Plug it in and find the port

Connect the board with your **data** USB cable. Then find out what your computer
called it:

**Linux**
```bash
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
dmesg | tail -5            # shows what just connected
```
Usually `/dev/ttyUSB0`. You'll need permission to use it:
```bash
sudo usermod -a -G dialout $USER    # then log out and back in
```

**macOS**
```bash
ls /dev/cu.usbserial-* /dev/cu.usbmodem* 2>/dev/null
```

**Windows**
Device Manager → *Ports (COM & LPT)*. Look for `Silicon Labs CP210x` or
`USB-SERIAL CH340`. Note the COM number, e.g. `COM3`.

### If nothing appears

| Cause | Fix |
|---|---|
| **Charge-only cable** | By far the most common. Try a different cable — one you know transfers data from a phone. |
| **Missing USB-serial driver** | The board's USB chip needs a driver. CP210x: [Silicon Labs](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers). CH340/CH341: search "CH340 driver" for your OS. macOS and Linux usually have both built in; Windows often doesn't. |
| **Port held by another program** | Close Thonny, Arduino IDE, or any serial monitor. Only one program can hold the port. |
| **Dead board** | Try your spare. |

Which chip you have is printed on the small square IC near the USB socket.

## 2. Install the tools

On your laptop, in the repo:

```bash
python3 -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install esptool mpremote
```

`esptool` writes firmware to the chip. `mpremote` talks to MicroPython once it's
running — REPL, file copy, the lot.

## 3. Download MicroPython

Get the latest **ESP32 / generic** `.bin` from
<https://micropython.org/download/ESP32_GENERIC/>.

Take the newest stable release (not a nightly). The file looks like
`ESP32_GENERIC-20250911-v1.26.0.bin`.

## 4. Erase, then flash

Erasing first avoids inheriting junk from whatever the factory left on it:

```bash
esptool --port /dev/ttyUSB0 erase-flash
esptool --port /dev/ttyUSB0 --baud 460800 write-flash 0x1000 ESP32_GENERIC-20250911-v1.26.0.bin
```

Substitute your port (`COM3` on Windows, `/dev/cu.usbserial-0001` on macOS) and
your filename.

> **Older esptool** used underscores: `erase_flash`, `write_flash`. If you get
> "unknown command", try that spelling.

> **"Failed to connect… Wrong boot mode detected"** — some boards need help
> entering bootloader mode. Hold the **BOOT** button, run the command, and release
> BOOT once "Connecting..." appears. If there's no BOOT button, try a lower baud
> (`--baud 115200`).

Flashing takes 15–30 seconds. You want `Hash of data verified.` at the end.

## 5. Say hello

```bash
mpremote
```

Press Enter. You should get:

```
MicroPython v1.26.0 on 2025-09-11; Generic ESP32 module with ESP32
Type "help()" for more information.
>>>
```

**That's the milestone.** Try it:

```python
>>> 2 + 2
4
>>> import machine
>>> machine.freq()
160000000
```

Blink the onboard LED:

```python
>>> from machine import Pin
>>> led = Pin(2, Pin.OUT)
>>> led.value(1)      # on
>>> led.value(0)      # off
```

If nothing lights up, your board's LED may be on a different pin (try 5, or 13) or
it may not have one. Not a problem — it's only a convenience, and you can set
`LED_PIN = None` in `config.py`.

**Exit the REPL with `Ctrl-]`.** (`Ctrl-C` interrupts a running program; `Ctrl-D`
soft-reboots the board.) Those three are worth remembering — they're how you get
control of a board that's busy running `main.py`.

## 6. Set your config

```bash
cp firmware/room_sensor/config.example.py firmware/room_sensor/config.py
```

Edit `config.py`:

```python
WIFI_SSID = "YourWiFi"          # 2.4 GHz — the ESP32 cannot see 5 GHz
WIFI_PASSWORD = "..."
MQTT_HOST = "192.168.1.50"      # your Pi's IP, from doc 02
ROOM = "bedroom"
NODE = "node1"
```

`config.py` is gitignored, so your password stays off GitHub. Only
`config.example.py` is committed. Check with `git status` before you push.

## 7. Deploy

```bash
./tools/deploy_node.sh
```

That installs the MQTT library, copies `boot.py`, `main.py`, `config.py` and
`lib/`, and restarts the board. Re-run it any time you change the firmware.

If you're on Windows without a bash shell, do it by hand:

```bash
mpremote mip install umqtt.simple
mpremote mkdir :lib
mpremote cp firmware/room_sensor/lib/bme280.py :lib/bme280.py
mpremote cp firmware/room_sensor/lib/sensor.py :lib/sensor.py
mpremote cp firmware/room_sensor/boot.py :boot.py
mpremote cp firmware/room_sensor/main.py :main.py
mpremote cp firmware/room_sensor/config.py :config.py
mpremote reset
```

## 8. Watch it run

```bash
mpremote
```

```
--- bedroom-node1 starting ---
wifi: connecting to YourWiFi
wifi: connected. ip 192.168.1.87 gateway 192.168.1.1
sensor: BME280
  - I2C devices: 0x76
mqtt: connected to 192.168.1.50:1883 as bedroom-node1
humidity=68.41 pressure=1008.72 temperature=27.34
humidity=68.38 pressure=1008.70 temperature=27.35
```

A line every 30 seconds. **Your node is live.**

### Common first-run messages

**`wifi: could not connect ... Networks the ESP32 can see: ...`**
It lists what it found, which tells you which problem you have. If your network
isn't in the list it's almost certainly 5 GHz-only — the ESP32 has a 2.4 GHz radio
and cannot see 5 GHz at all. If it *is* in the list, it's a password typo.

**`No sensor detected`**
The message lists what was on the I²C bus. Go back to
[04 — Node wiring](04-node-wiring.md).

**`This is a BMP280, not a BME280`**
You were sold the wrong chip. Temperature and pressure still work; humidity won't
appear. See the BME280 trap in [01](01-parts-list.md).

**`network error (1), reconnecting in 1s: [Errno 104] ECONNRESET`** or similar
The board is fine and on WiFi; it can't reach the broker. Nine times out of ten
this is the Mosquitto localhost-only default — see
[03 — Mosquitto](03-hub-mosquitto.md). Also check `MQTT_HOST` matches
`hostname -I` on the Pi.

**Nothing at all after `--- starting ---`**
Press `Ctrl-C` to interrupt, then `Ctrl-D` to soft-reboot and watch it again from
the top.

---

**Next:** [06 — Run the stack](06-run-the-stack.md) — join the node to the hub and
watch your room appear on a chart.
