# 02 — Setting up the Pi 5 hub

**Goal:** a Raspberry Pi you can SSH into, at an address that won't change.

No monitor, no keyboard, no mouse. We set it up headless, which is both easier and
how you'd actually run a server.

**Time:** about 30 minutes, most of it waiting for the SD card to write.

---

## 1. Fit the cooler first

Do this before the card, because it's the one step that needs the board bare.

Clip the active cooler onto the Pi 5 — the two spring-loaded pins push through the
mounting holes — and plug its small fan cable into the 4-pin **FAN** header next to
the USB ports. It only fits one way.

The Pi 5 will throttle itself under sustained load without cooling. It won't be
damaged, but it will be slow and it will do it silently.

## 2. Write the OS

Download **Raspberry Pi Imager** from <https://www.raspberrypi.com/software/> and
install it on your laptop.

1. **Choose Device:** Raspberry Pi 5
2. **Choose OS:** Raspberry Pi OS (64-bit) — the default, with desktop, is fine.
   *Raspberry Pi OS Lite (64-bit)* is leaner and a better fit for a headless
   server if you're offered it.
3. **Choose Storage:** your microSD card. Check twice — it will be erased.
4. **Next** → it asks *"Would you like to apply OS customisation settings?"* →
   **Edit Settings**. This is the important part.

Fill in the customisation screen:

| Field | What to put |
|---|---|
| Hostname | `iothub` (anything; it's how you'll refer to it) |
| Username / password | your own — **write the password down** |
| Configure wireless LAN | your WiFi name and password, if not using Ethernet |
| Wireless LAN country | `MY` (or wherever you are) — WiFi won't start without it |
| Locale / timezone | `Asia/Kuala_Lumpur` or yours |
| **Services tab → Enable SSH** | **✅ Use password authentication** |

That SSH checkbox is what makes this headless. Miss it and you'll need a monitor
and keyboard to turn it on.

Write the card. Takes 5–15 minutes.

## 3. First boot

Put the card in the Pi, connect Ethernet if you're using it, then plug in the
official 27W supply.

The green LED will flicker as it boots. First boot takes a couple of minutes — it
expands the filesystem and reboots itself once. Be patient.

## 4. Find it and log in

From your laptop:

```bash
ssh yourusername@iothub.local
```

`.local` uses mDNS, which works on macOS and most Linux out of the box, and on
Windows 10/11. If it doesn't resolve, find the Pi's IP from your router's admin
page under "connected devices" / "DHCP clients", and use that instead:

```bash
ssh yourusername@192.168.1.50
```

Say `yes` to the host key prompt, enter your password, and you're in.

> **If SSH is refused:** the Pi is up but SSH is off, which means the checkbox in
> step 2 didn't take. Easiest fix: re-write the card with Imager, being sure to
> enable SSH. (Alternative: put the card in your laptop and create an empty file
> named `ssh` — no extension — in the boot partition.)

Update everything while you're here:

```bash
sudo apt update && sudo apt full-upgrade -y
```

## 5. Pin the Pi's address ← don't skip this

Your nodes need to know where the broker is, and MicroPython's MQTT client
**cannot resolve `iothub.local`** — there's no mDNS on the device. So the node
needs a literal IP, and that IP must not change.

Find it:

```bash
hostname -I
# 192.168.1.50 ...
```

Now **reserve that address for the Pi in your router**. Log into your router's
admin page and look for *DHCP Reservation*, *Static Lease*, *Address Reservation*
or *Bind IP to MAC* — the name varies by brand. Bind the Pi's MAC address to the
address it currently has.

Do it in the router rather than setting a static IP on the Pi itself. The router
knows what else is on the network, so it won't hand the same address to your
phone; a static IP set on the Pi can collide, and the resulting intermittent
failures are miserable to diagnose.

Get your MAC if the router doesn't show it clearly:

```bash
ip link show | grep -A1 -E "eth0|wlan0"
```

**Write the IP down.** It goes into the ESP32's `config.py` in step 7, and into
every `mosquitto_sub -h ...` command from here on.

## 6. Get the code

```bash
sudo apt install -y git
git clone https://github.com/whitehat26-My/Iot-systems.git
cd Iot-systems
```

---

## Optional: a sensor on the Pi itself

The Pi can sense its own room via its I²C header, using a second BME280.

**Read this first.** With an active cooler blowing warm air across the board, a
sensor mounted near the Pi reads **several degrees too high** — you'd be measuring
your Pi, not your room. Put it on a ~20cm cable, away from the case, before you
trust a single reading.

Enable I²C (it's off by default):

```bash
sudo raspi-config      # Interface Options -> I2C -> Yes, then reboot
```

Wire it to the 40-pin header:

| BME280 | Pi header | |
|---|---|---|
| VIN | pin 1 | 3.3V — **not** pin 2 or 4, those are 5V |
| GND | pin 6 | |
| SDA | pin 3 | GPIO2 |
| SCL | pin 5 | GPIO3 |

Check it's seen:

```bash
sudo apt install -y i2c-tools
i2cdetect -y 1        # expect 76 or 77 in the grid
```

> **A Pi 5 gotcha worth knowing even if you skip this:** the Pi 5's new RP1 I/O
> chip broke the old GPIO libraries. `RPi.GPIO` and legacy sysfs code **do not
> work** on a Pi 5 — use `gpiozero` with the `lgpio` backend, or `libgpiod`. A lot
> of tutorials online are still wrong about this and will waste your afternoon.
> I²C, which is what the BME280 uses, is unaffected.

Wiring a sensor to the Pi is optional and not needed for anything that follows.

---

**Next:** [03 — Mosquitto](03-hub-mosquitto.md) — the MQTT broker, and the one
setting that everybody gets wrong.
