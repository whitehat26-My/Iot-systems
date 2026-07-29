"""Figure out which sensor is actually attached, and read it.

Three things can be on the end of those wires, and beginners routinely get a
different one from the one they ordered:

  * BME280 - temperature, humidity, pressure over I2C     (what we recommend)
  * BMP280 - temperature and pressure only, no humidity   (often mis-sold as a BME280)
  * DHT22  - temperature and humidity over one data pin   (the cheaper alternative)

Rather than making you edit code to match, this detects what is present and
tells you clearly. If humidity is missing, it says so in as many words instead
of quietly publishing zeros.
"""

from machine import I2C, Pin

import bme280


class NoSensor(Exception):
    pass


class Sensor:
    """Wraps whichever sensor is present behind one read() -> dict."""

    def __init__(self, scl_pin, sda_pin, dht_pin=None, i2c_address=None):
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

        # --- fall back to a DHT22 on a single data pin -----------------------
        if dht_pin is not None:
            try:
                import dht
                self.device = dht.DHT22(Pin(dht_pin))
                self.device.measure()          # prove it before claiming success
                self.kind = "DHT22"
                self.notes.append("using DHT22 on pin {}".format(dht_pin))
                return
            except Exception as exc:
                self.notes.append("no DHT22 on pin {}: {}".format(dht_pin, exc))

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

        # DHT22. measure() must be called before reading, and the datasheet
        # requires at least 2 seconds between measurements — our publish
        # interval is far longer than that, so no extra delay is needed here.
        self.device.measure()
        return {
            "temperature": round(self.device.temperature(), 2),
            "humidity": round(self.device.humidity(), 2),
        }
