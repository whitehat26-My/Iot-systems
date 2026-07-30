"""Figure out which sensor is actually attached, and read it.

Four things can be on the end of those wires, and beginners routinely get a
different one from the one they ordered:

  * BME280 - temperature, humidity, pressure over I2C     (what we recommend)
  * BMP280 - temperature and pressure only, no humidity   (often mis-sold as a BME280)
  * DHT22  - temperature and humidity over one data pin   (white module)
  * DHT11  - same, but much coarser                       (blue module, in most starter kits)

Rather than making you edit code to match, this detects what is present and
tells you clearly. If humidity is missing, it says so in as many words instead
of quietly publishing zeros.

DHT11 vs DHT22 cannot be told apart electrically - both answer on one wire with
the same framing - so that one comes from DHT_TYPE in config.py. Get it wrong and
the readings are wildly out rather than slightly out, so we range-check them and
say which setting to change.
"""

from machine import I2C, Pin

import bme280

# Anything outside these is not a room; it is a misconfigured sensor.
_PLAUSIBLE_TEMP = (-40, 85)
_PLAUSIBLE_HUM = (0, 100)


class NoSensor(Exception):
    pass


class Sensor:
    """Wraps whichever sensor is present behind one read() -> dict."""

    def __init__(self, scl_pin, sda_pin, dht_pin=None, i2c_address=None, dht_type="DHT22"):
        self.kind = None
        self.device = None
        self.notes = []

        # --- try I2C first (BME280 / BMP280) --------------------------------
        try:
            i2c = I2C(0, scl=Pin(scl_pin), sda=Pin(sda_pin))
            found = i2c.scan()
        except Exception as exc:              # bad pin numbers, shorted bus
            found = []
            self.notes.append("I2C bus would not start: {}".format(exc))

        if found:
            self.notes.append("I2C devices: " + ", ".join(hex(a) for a in found))
            try:
                self.device = bme280.BME280(i2c, address=i2c_address)
                self.kind = self.device.name
                if not self.device.has_humidity:
                    # The single most common surprise in this whole project.
                    self.notes.append(
                        "This is a BMP280, not a BME280 - it has no humidity sensor. "
                        "Temperature and pressure will work; humidity will be absent."
                    )
                return
            except Exception as exc:
                self.notes.append("I2C device found but not a BME/BMP280: {}".format(exc))
        else:
            self.notes.append("nothing responded on I2C - check SDA/SCL and 3V3")

        # --- fall back to a DHT11/DHT22 on a single data pin -----------------
        if dht_pin is not None:
            wanted = (dht_type or "DHT22").upper()
            try:
                import dht
                cls = {"DHT22": dht.DHT22, "DHT11": dht.DHT11}.get(wanted)
                if cls is None:
                    raise ValueError(
                        "DHT_TYPE must be 'DHT22' or 'DHT11', not {!r}".format(dht_type))

                self.device = cls(Pin(dht_pin))
                self.device.measure()          # prove it before claiming success
                temp = self.device.temperature()
                hum = self.device.humidity()

                # Reading a DHT11 with the DHT22 driver produces a valid checksum
                # but nonsense values (the two encode their numbers differently),
                # so a checksum test would not catch this. A range check does.
                if not (_PLAUSIBLE_TEMP[0] <= temp <= _PLAUSIBLE_TEMP[1]
                        and _PLAUSIBLE_HUM[0] <= hum <= _PLAUSIBLE_HUM[1]):
                    other = "DHT11" if wanted == "DHT22" else "DHT22"
                    raise ValueError(
                        "{} gave implausible readings ({}C, {}%). You almost "
                        "certainly have a {} - set DHT_TYPE = '{}' in config.py. "
                        "(Blue module = DHT11, white = DHT22.)".format(
                            wanted, temp, hum, other, other))

                self.kind = wanted
                self.notes.append("using {} on pin {}".format(wanted, dht_pin))
                if wanted == "DHT11":
                    # Worth saying plainly: the flat-looking chart that follows is
                    # the sensor, not a bug in anything here.
                    self.notes.append(
                        "DHT11 reports whole degrees only (+/-2C, +/-5%RH), so your "
                        "chart will look like a staircase. A BME280 (~RM15) is a "
                        "large upgrade for little money.")
                return
            except Exception as exc:
                self.notes.append("no {} on pin {}: {}".format(wanted, dht_pin, exc))

        raise NoSensor(
            "No sensor detected.\n  " + "\n  ".join(self.notes)
            + "\n\nCheck: VCC to 3V3 (not 5V), GND to GND, SDA to the SDA pin, "
              "SCL to the SCL pin. See docs/04-node-wiring.md."
        )

    def read(self):
        """Return a dict of metric name -> value. Keys vary by sensor, which is
        exactly why the server stores readings one row per metric."""
        if self.kind in ("BME280", "BMP280"):
            temperature, pressure, humidity = self.device.read()
            out = {
                "temperature": round(temperature, 2),
                "pressure": round(pressure, 2),
            }
            if humidity is not None:
                out["humidity"] = round(humidity, 2)
            return out

        # DHT11/DHT22. measure() must be called before reading, and the datasheet
        # requires at least 1-2 seconds between measurements — our publish
        # interval is far longer than that, so no extra delay is needed here.
        # No pressure from either: these chips don't measure it.
        self.device.measure()
        return {
            "temperature": round(self.device.temperature(), 2),
            "humidity": round(self.device.humidity(), 2),
        }
