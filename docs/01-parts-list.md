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

### Where to buy a Pi (Malaysia)

Raspberry Pi runs an **Approved Reseller** programme — hand-picked partners in
over 60 countries. Buying from one means genuine boards, correct regional power
supplies, and somebody to talk to if a unit is faulty.

The authoritative list is <https://www.raspberrypi.com/resellers/> — filter by
country. Check it before ordering, because the list does change.

| Where | Why |
|---|---|
| **[Cytron Technologies](https://my.cytron.io/)** | Penang-based, a Raspberry Pi Approved Reseller, and the usual first stop in Malaysia. Domestic shipping, local warranty, and they stock the official PSU, cooler and cases alongside the board. |
| **[element14 Malaysia](https://my.element14.com/buy-raspberry-pi)** | Official distributor (Farnell/Avnet). Reliable and well stocked; sometimes better on business orders, and they list stock levels honestly. |
| **[MyDuino](https://myduino.com/)** | Another established local maker-electronics shop, often competitive on price. |
| **Shopee / Lazada** | Fine **if** it's the retailer's own official store. Cytron and others run them. A random marketplace seller is where you get grey imports, the wrong plug, or a board with no warranty. |

**⚠️ Ignore "Raspberry Pi price guide" blog pages.** Searching for prices surfaces
a lot of auto-generated SEO pages on unrelated domains — cycling brands, expired
sites, content farms. They scrape stale numbers and exist to collect affiliate
clicks. Get prices from the reseller's own site.

**How to sanity-check a price:** total the four things you actually need (board,
official PSU, cooling, SD card). If a bundle costs much more than that sum, you
are paying for HDMI cables you will never plug in — see the next section.

### ⚠️ All-in-one Pi kits are usually a bad deal

Bundles branded "Raspberry Pi 5 Starter Kit" are common and often cost far more
than their contents. One seen at RM831 for a 4GB kit, against RM455–580 for the
same parts bought individually — a 43–83% markup.

Unlike the ESP32 kits (which genuinely add value with sensors you'd want anyway),
Pi kits mostly bundle things you already need, plus one thing you don't:

- **Micro-HDMI cables — usually two.** We set the Pi up headless over SSH; you
  will never plug a monitor in. That's RM30–50 of the price, unused.
- **The power supply is the part to check.** Kits frequently include a generic
  5V/5A adapter rather than the official 27W PD unit, and often with the wrong
  plug for your country — a US two-pin adapter is no use on Malaysian Type G
  sockets. This is the one component not to compromise on: an inadequate supply
  causes exactly the random instability people spend months blaming the board
  for. If the kit's PSU is generic you will buy the official one anyway, on top
  of an already-inflated price.

**Price any kit against the four things you actually need** — board, official
PSU, cooling, decent SD card — before assuming a bundle saves money. It usually
doesn't, and the difference buys several more sensor nodes or the NVMe upgrade.

**Don't let an out-of-stock variant push you up a tier.** Bundles routinely have
the mid-range RAM option greyed out while the expensive one is available, and it
is very easy to shrug and take the 8GB for a few hundred ringgit more. Before you
do: check the same seller's **bare board** listing, since bundle and mainboard
stock are tracked separately, then check the other resellers. Nothing here needs
a Pi urgently — on the [ESP32-first route](00-esp32-first.md) your laptop is the
hub, so waiting a fortnight for a restock costs you nothing at all.

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
      - **Voltage and pin count are the same choice, not two.** Sellers list them
        as separate options, but in practice:
        | Listing says | What it is | Pins |
        |---|---|---|
        | **3.3V** | bare breakout — no regulator, chip pins exposed | **6** (adds CSB, SDO) |
        | **5V** | adds a regulator + I²C level shifter, which consume those pins | **4** |

        So "3.3V and 4-pin" is not a thing you can buy. **Either works on an
        ESP32** — pick on price and stock, not on this. Wiring for both is in
        [04](04-node-wiring.md); the short version is that **VCC goes to 3V3
        either way**, even on a board sold as 5V.
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
