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
      **Buy the 4GB.** See the RAM note below if you're tempted by 8GB.

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

### How much RAM? 4GB.

Measured on a running hub, this is what the whole stack actually uses:

| | RAM |
|---|---|
| Mosquitto | 8 MB |
| `collector.py` | 24 MB |
| `api.py` + dashboard | 47 MB |
| **This entire project** | **~130 MB** |
| Raspberry Pi OS Lite, idle | ~300 MB |
| *later:* Home Assistant | ~1.5 GB |
| *later:* InfluxDB + Grafana | ~1 GB |
| **All of the above at once** | **~3 GB** |

So you would have to be running Home Assistant *and* Grafana *and* InfluxDB
together before 4GB felt tight. The sensor project alone uses about 3% of it.
**2GB is also genuinely enough** for everything in this repo — it just leaves no
headroom for the Home Assistant path later.

8GB only earns its price for things this project doesn't do: a Frigate camera NVR
with object detection, a dozen containers, using the Pi as a daily desktop, or
running local LLMs.

**Better use of the ~RM150 difference: put it toward the NVMe HAT + SSD** in the
optional table below. SD-card corruption is the number-one way a Pi fails, and it
fails silently. RAM you never allocate prevents nothing; an SSD prevents the
failure you will actually hit. 4GB + NVMe beats 8GB + SD card for this build.

The one honest caveat: Pi RAM is soldered, so this isn't upgradeable later. If you
already know a camera NVR is in your future, take the 8GB. Otherwise, if you ever
outgrow 4GB, a *second* Pi is usually a better answer than one bigger one.

**Free upgrade if you have a spare cable:** run the Pi on **Ethernet** instead of
WiFi. It's a 24/7 server — wired is one less thing that can drop out at 3am.

---

## The node — ESP32 (~RM 47–86)

- [ ] **ESP32 dev board** — RM 20–35
      Search: `ESP32 DevKitC ESP32-WROOM-32 38-pin`
      **Buy two if you can.** A known-good spare removes "is the board dead?" from
      every future debugging session, and node #2 is inevitable.
      **Check which USB socket you're actually buying.** Listings routinely show a
      USB-C board in the main photo while the selected variant is micro-USB, and
      then your cable doesn't fit. Match the cable to the variant, not the picture.
      If you get a choice of USB-serial chip, **CP2102 is slightly better than
      CH340** — fewer driver headaches on macOS and Windows. Either works.

- [ ] **BME280 sensor module** — RM 15–35
      Search: `BME280 I2C module 3.3V`
      Temperature, humidity **and** pressure over I²C. Read the warning below.
      **Three things to get right when picking a variant:**
      - **"Soldered"** if the listing offers it. Otherwise the header pins arrive
        loose in the bag and you need a soldering iron to attach them. Paying a
        few ringgit more beats buying an RM60 iron for one job.
      - **3.3V version**, not the 5V one. We wire VIN straight to the ESP32's
        3V3 pin, so the 3.3V board connects directly with no regulator or level
        shifter in the way. The 5V board works too, but you're paying for parts
        that only exist to protect a 5V system you don't have.
      - **4-pin** (VIN, GND, SCL, SDA) is all you need. 6-pin boards add CSB and
        SDO for SPI mode, which we don't use.
      Cheap listings around RM12 exist, but that's exactly where BMP280s get
      substituted. Around RM20–35 from a seller with real sales history is a
      reasonable price for not having to send it back.

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

### Cheaper sensor alternatives

A **DHT22 / AM2302** (RM 10–15, **white** module) also does temperature and
humidity. Less accurate, slower, and its one-wire protocol fails intermittently on
longer wires. A **DHT11** (**blue** module) is cheaper again and considerably
worse — see the kit section below.

The firmware supports all of them. Set `DHT_PIN` and `DHT_TYPE` in `config.py`.

---

## Buying an all-in-one starter kit?

Kits on Shopee/Lazada run about **RM 55–80** and typically bundle: ESP32,
breadboard, jumper wires, USB cable, an OLED, a PIR motion sensor, a relay,
LEDs, resistors, buttons and a storage case. That is genuinely good value — it
covers the whole node *plus* several of the optional extras below.

**Three things to check before you buy:**

**1. Which temp/humidity sensor?** Almost every kit ships a **DHT11**, and it's
the weakest part of the box:

| | DHT11 (typical kit) | DHT22 | BME280 |
|---|---|---|---|
| Temperature resolution | **whole degrees** | 0.1 °C | 0.01 °C |
| Accuracy | ±2 °C, ±5 %RH | ±0.5 °C, ±2 %RH | ±0.5 °C, ±3 %RH |
| Pressure | — | — | ✅ |

Whole-degree resolution is the problem. Your chart becomes a staircase —
`27, 27, 27, 28` — instead of a curve, and you'll never see the air-conditioning
switch on. **Buy the kit and add a BME280 for ~RM15.** Best of both.

The firmware works fine with a DHT11 — set `DHT_TYPE = "DHT11"` in `config.py` —
it just tells you on startup what you're giving up.

**2. Does the photo match the variant you selected?** Kit listings usually offer
"basic" and "advance" versions at different prices, and the main photo is often of
the *advance* one. Check the description for the per-variant contents rather than
counting parts in the picture.

**3. The relay.** Kits include a 1- or 2-channel relay module. Great for switching
a low-voltage LED or USB fan to learn with. **Do not wire it to a wall socket** —
see the mains warning below.

Kits do *not* usually include a Raspberry Pi, which is fine: on the
[ESP32-first route](00-esp32-first.md) you don't need one yet.

---

## Optional, once the basics work

| Item | Approx. | Why |
|---|---|---|
| Soldering iron + solder | RM 40–80 | **Only if** a module arrives with loose header pins. Buy "pre-soldered" variants and you can skip this entirely — nothing in this project requires soldering. |
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
