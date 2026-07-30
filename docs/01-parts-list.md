# 01 — Parts list

Rough mid-2026 street prices in RM (Shopee / Lazada / Cytron / local electronics
shops). **Verify before ordering** — these move around, and Pi stock especially
comes and goes.

> ### Buying the ESP32 only? (recommended)
>
> **Skip straight to [the node section](#the-node--esp32-rm-4786) — RM 47–86.**
> Your laptop acts as the hub, so you need none of the Pi hardware below. That's
> the route in [00 — Start with just the ESP32](00-esp32-first.md), and nothing
> you build is wasted when you add a Pi later.
>
> The Pi section is here for when you're ready for 24/7 collection.

Full build total: **roughly RM 460–570.** About 85% of that is the Pi, and it's a
one-time cost — once the hub exists, each additional room costs about RM 40.

---

## The hub — Raspberry Pi 5 (~RM 410–485)

*Not needed for Route A. Your laptop does this job until you buy one.*

- [ ] **Raspberry Pi 5** — RM 300–350
      Search: `Raspberry Pi 5 4GB`
      **2GB (~RM 250) is genuinely plenty for this project.** Take 4GB only if you
      might later add Home Assistant or Grafana. 8GB/16GB is money wasted here.

- [ ] **Official 27W USB-C power supply** — RM 55–70
      Search: `Raspberry Pi 5 official power supply 27W`
      **Not optional, and don't substitute.** The Pi 5 negotiates 5V/5A over
      USB-PD. A generic charger causes undervoltage throttling and silently
      current-limits the USB ports. This is the most common cause of "my Pi is
      randomly unstable" — people blame the board for months.

- [ ] **Active cooler** — RM 25–35
      Search: `Raspberry Pi 5 active cooler`
      The Pi 5 thermally throttles under sustained load without one. The official
      cooler clips on and plugs into the board's dedicated fan header.

- [ ] **microSD card, 32GB** — RM 25–40
      Search: `Samsung Evo Plus 32GB A2` or `SanDisk Extreme 32GB`
      **Buy a real brand.** Cheap and counterfeit cards are the number-one Pi
      reliability problem, and they fail by silently corrupting data rather than
      dying cleanly. 32GB is ample; take 64GB if it costs the same.

- [ ] **USB microSD card reader** — RM 10–15 — *only if your laptop has no SD slot.*
      You need some way to write the OS image.

**Don't buy both a case and the active cooler.** The official Pi 5 case includes
its own fan, so it replaces the cooler. A bare board on a desk with the active
cooler is completely fine to start.

**Free upgrade if you have a spare cable:** run the Pi on **Ethernet** instead of
WiFi. It's a 24/7 server — wired is one less thing that can drop out at 3am.

---

## The node — ESP32 (~RM 47–86)

- [ ] **ESP32 dev board** — RM 20–35
      Search: `ESP32 DevKitC ESP32-WROOM-32 38-pin`
      **Buy two if you can.** A known-good spare removes "is the board dead?" from
      every future debugging session, and node #2 is inevitable.

- [ ] **BME280 sensor module** — RM 12–20
      Search: `BME280 I2C module 3.3V`
      Temperature, humidity **and** pressure over I²C. Read the warning below.

- [ ] **Breadboard, 830 tie points** — RM 8–12
      Search: `breadboard 830 tie points`
      The 400-point size fits the ESP32 but leaves almost no room for wires.
      Spend the extra RM 3.

- [ ] **Dupont jumper wires** — RM 5–8
      Search: `dupont jumper wire male to male 20cm`
      Grab a mixed pack with male-to-female if it's the same price.

- [ ] **USB data cable** — RM 5–15
      **Must carry data, not just charge**, and must match your board's socket —
      check whether yours is micro-USB or USB-C *before* ordering. A charge-only
      cable is the single most common cause of "my board won't connect".

### ⚠️ The BME280 trap

Many cheap listings say "BME280" but ship a **BMP280**, which has **no humidity
sensor**. The two look nearly identical.

- Buy from a seller whose listing explicitly mentions humidity, with real photos.
- Our firmware reads the chip ID on boot and tells you which one you actually
  got — BME280 reports `0x60`, BMP280 reports `0x58`. So you'll know within a
  minute of powering it on, instead of wondering for a week why humidity is
  always zero.

### Cheaper sensor alternative

A **DHT22 / AM2302** (RM 10–15) also does temperature and humidity. It's less
accurate, slower (one reading every 2 seconds at most), and its one-wire protocol
fails intermittently on longer wires. The BME280 is the better experience, but the
firmware supports both — set `DHT_PIN` in `config.py` if you go this way.

---

## Optional, once the basics work

| Item | Approx. | Why |
|---|---|---|
| 2nd BME280 + female-female jumpers | RM 20 | Let the Pi sense its own room too, via its I²C header. Put it on a ~20cm cable — see the thermal warning in [02](02-hub-setup.md). |
| SSD1306 OLED 0.96" I²C | RM 12–18 | Shows the reading on the device itself. Shares the ESP32's existing I²C pins, so no extra wiring. |
| PIR sensor HC-SR501 | RM 6–10 | Motion detection. The natural step 2. |
| BH1750 light sensor | RM 8–12 | Room brightness, also I²C. |
| NVMe HAT + small SSD | RM 80 + RM 100 | Retires the SD card — faster and far more reliable. A good six-months-in upgrade. |
| Multimeter | RM 30–60 | Answers "is this pin actually at 3.3V?" in five seconds. |

## Don't buy yet

- **Relay modules, or anything that switches mains.** 240V AC kills people. When
  you want to control a lamp, we'll use a ready-made ESPHome- or
  Tasmota-flashable smart plug, so nothing you build ever touches mains wiring.
- **"37-in-1" sensor megakits.** Mostly parts you'll never use.
- **A monitor, keyboard or mouse for the Pi.** We set it up headless over SSH.

## What you already have

- A laptop (Windows, macOS or Linux — all fine)
- Home WiFi with a **2.4 GHz** band. The ESP32 cannot see 5 GHz networks. If your
  router advertises `MyWiFi` and `MyWiFi_5G` separately, the node uses the 2.4 GHz
  one. The Pi handles either, or Ethernet.
- Access to your router's admin page — needed once, to reserve the Pi's IP.

---

**Next:** while you wait for delivery, go to
[06 — Run the stack](06-run-the-stack.md#step-1--run-it-all-on-your-laptop-no-hardware)
and build the entire software side on your laptop. It works with no hardware at
all, and it's most of the project.
