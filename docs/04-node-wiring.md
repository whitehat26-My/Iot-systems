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

Leave any other pins on the module (CSB, SDO) unconnected — they're for SPI mode
and for selecting the I²C address, and the defaults are fine.

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

## Adding the OLED later

If you buy the SSD1306 display, it shares this same I²C bus — VIN to 3V3, GND to
GND, SDA to GPIO21, SCL to GPIO22, in parallel with the BME280. I²C is a bus:
multiple devices coexist as long as their addresses differ, and the OLED is
usually `0x3C`. Your scan will then show `['0x3c', '0x76']`.

No extra pins needed. That's why I²C sensors are worth preferring.

---

**Next:** [05 — Flashing the node](05-node-flash.md) if you haven't yet, otherwise
[06 — Run the stack](06-run-the-stack.md) to get it publishing.
