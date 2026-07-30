# 04 — Wiring the sensor

**Goal:** four wires, and proof that the ESP32 can see the sensor.

**Time:** 10 minutes. Nothing here can hurt you or the board — it's all 3.3V.

---

## Before you start

**Unplug the ESP32 from USB.** Wire it up with no power, then plug in. Hot-wiring
a powered board is how you short 3V3 to GND with a slipped jumper.

## The four connections

| BME280 pin | ESP32 pin | Note |
|---|---|---|
| **VIN** (or VCC / 3V3) | **3V3** | **Not 5V.** Most breakouts have a regulator and tolerate 5V, but the ESP32's logic is 3.3V and 3V3 is always safe. |
| **GND** | **GND** | Any of the GND pins — there are several. |
| **SDA** (or SDI) | **GPIO21** | I²C data |
| **SCL** (or SCK) | **GPIO22** | I²C clock |

### 4-pin or 6-pin module?

Both are common and both work. If yours has only `VIN GND SCL SDA`, wire those
four and you're done — skip to the diagram.

If it has **six pins** (`VCC GND SCL SDA CSB SDO`, sometimes silkscreened `CSE`
and `SDC`), wire the same four and **leave CSB and SDO unconnected to begin
with.** Those two are for SPI mode and for choosing the I²C address, and most
boards pull them to sensible defaults with onboard resistors.

**But not all of them do**, and that's the one extra way a 6-pin board can fail:

- **CSB** selects the mode. It must be **HIGH** for I²C. If the board doesn't pull
  it up, the chip sits in SPI mode and ignores I²C entirely — your scan finds
  nothing at all.
- **SDO** selects the address: LOW → `0x76`, HIGH → `0x77`. Left floating on a
  board without a pull resistor, the address is unpredictable and the scan can
  come up empty, or find the chip only intermittently.

So if your scan below returns `[]` on a 6-pin board and the wiring is definitely
right, add these two jumpers before assuming the module is dead:

| Pin | Connect to | Effect |
|---|---|---|
| CSB / CSE | **3V3** | Forces I²C mode |
| SDO / SDC | **GND** | Fixes the address at `0x76` |

That combination is unambiguous and always works. It's two extra wires and it
turns an intermittent mystery into a sensor that just answers.

```
      ESP32 DevKitC                       BME280
    ┌───────────────┐                  ┌───────────┐
    │           3V3 ├──────────────────┤ VIN       │
    │           GND ├──────────────────┤ GND       │
    │        GPIO21 ├──────────────────┤ SDA       │
    │        GPIO22 ├──────────────────┤ SCL       │
    │               │                  │ CSB  ─── unconnected
    │   [USB]       │                  │ SDO  ─── unconnected
    └───────────────┘                  └───────────┘
```

Mount the ESP32 across the breadboard's centre channel, so each pin gets its own
row. Then run the four jumpers.

### Two things to check before powering on

1. **Count the pins twice.** GPIO21 and GPIO22 are next to each other on most
   DevKitC boards, and the silkscreen is small. Getting SDA and SCL swapped is
   the single most common wiring error — the symptom is an I²C scan that finds
   nothing at all.
2. **Confirm you're in the 3V3 row, not 5V.** They're often adjacent.

Now plug in USB.

---

## Prove the sensor is there

Do this *before* running any sensor code. It separates "wiring is wrong" from
"code is wrong" — two problems that look identical from the outside, and the
reason beginners get stuck for days.

You need MicroPython on the board first; if you haven't done that, go to
[05 — Flashing the node](05-node-flash.md) and come back.

Open a REPL:

```bash
mpremote
```

Then type (or paste):

```python
from machine import I2C, Pin
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
print([hex(a) for a in i2c.scan()])
```

### What you want to see

```
['0x76']
```

or `['0x77']`. Either is correct — the address depends on how your module ties its
SDO pin, and the firmware tries both. **That's the milestone: the ESP32 can see
your sensor.**

### If you get `[]`

An empty list means nothing responded. In order of likelihood:

| Cause | Check |
|---|---|
| SDA and SCL swapped | Swap them. Costs nothing to try, and it's the most common fault. |
| A jumper not fully seated | Push each one in firmly. Breadboard jumpers back out easily. |
| **6-pin board, CSB/SDO floating** | Tie **CSB → 3V3** and **SDO → GND**, as described above. This is the usual answer on a 6-pin module whose wiring looks correct. |
| No power to the module | Many boards have a power LED. If you have a multimeter, check 3.3V between VIN and GND. |
| Wrong row on the breadboard | The centre channel splits the board — a wire one row off connects to nothing. |
| Dead module | If you bought two ESP32s, swap the board. If not, this is where a spare would have helped. |

Also try scanning the other bus, in case your board maps things differently:

```python
i2c = I2C(1, scl=Pin(22), sda=Pin(21))
print([hex(a) for a in i2c.scan()])
```

### Which chip did you actually get?

Now the useful part — find out whether you got a real BME280:

```python
print(hex(i2c.readfrom_mem(0x76, 0xD0, 1)[0]))   # use 0x77 if that's your address
```

| Result | Meaning |
|---|---|
| `0x60` | **BME280.** Temperature, humidity and pressure. What you wanted. |
| `0x58` | **BMP280** — no humidity sensor. You were sold the wrong chip. |
| anything else | Not a BME/BMP280 at all. |

This check exists because **the two chips ship on the same purple PCB** — many
boards have `BME/BMP280` printed on the silkscreen, with nothing to tell you which
one was fitted. The chip ID is the only reliable answer, and it's why the firmware
reads it on every boot.

If it's `0x58`, you have a decision: return it, or carry on with temperature and
pressure only. Everything in this project works either way — the firmware detects
it, tells you in as many words, and simply doesn't publish humidity. The dashboard
then shows two charts instead of three.

This is worth checking *now* rather than discovering it in a week when you notice
the humidity chart is missing.

### Read an actual temperature

```python
import sys
sys.path.append('/lib')
import bme280
s = bme280.BME280(i2c)
print(s.name, s.read())
```

```
BME280 (27.34, 1008.72, 68.41)
```

Temperature °C, pressure hPa, humidity %. **Real numbers, from your actual room.**

Breathe on the sensor and read it again — humidity should jump several percent and
come back down over a minute. That's the moment it stops being abstract.

---

## If you have a DHT11 or DHT22 instead

Kit sensors are usually a DHT11. They're simpler to wire — one data line, no I²C:

| DHT pin | ESP32 | Note |
|---|---|---|
| VCC / + | **3V3** | Some modules want 5V; 3V3 works on the 3-pin breakout boards. |
| DATA / S | **GPIO13** | Any free GPIO; 13 is the default below. |
| GND / − | **GND** | |

Bare 4-pin DHT sensors (not on a small PCB) also need a 10kΩ resistor between
DATA and VCC. Modules with three pins already have it fitted.

Then in `config.py`:

```python
DHT_PIN = 13
DHT_TYPE = "DHT11"      # blue module. White module -> "DHT22"
```

**Getting `DHT_TYPE` wrong doesn't fail cleanly.** The two chips share a wire
protocol but encode numbers differently, so a mismatch passes the checksum and
returns garbage — a DHT11 read as a DHT22 reports around 691 °C. The firmware
range-checks the first reading and tells you which value to change, so you'll see
a clear message rather than a nonsense chart.

Test it from the REPL:

```python
import dht
from machine import Pin
d = dht.DHT11(Pin(13))     # or dht.DHT22
d.measure()
print(d.temperature(), d.humidity())
```

A DHT11 prints whole numbers (`27 68`). That's the sensor, not a bug — it's why a
BME280 is worth the extra RM15.

## Adding the OLED later

If you buy the SSD1306 display, it shares this same I²C bus — VIN to 3V3, GND to
GND, SDA to GPIO21, SCL to GPIO22, in parallel with the BME280. I²C is a bus:
multiple devices coexist as long as their addresses differ, and the OLED is
usually `0x3C`. Your scan will then show `['0x3c', '0x76']`.

No extra pins needed. That's why I²C sensors are worth preferring.

---

**Next:** [05 — Flashing the node](05-node-flash.md) if you haven't yet, otherwise
[06 — Run the stack](06-run-the-stack.md) to get it publishing.
