"""Stand-in for MicroPython's `dht`, for testing without hardware.

Simulates the real failure mode this project cares about: a DHT11 read by the
DHT22 driver returns a *valid checksum* but garbage numbers, because the two
chips encode their values differently. Set `ATTACHED` to the chip physically
present; the class you instantiate is the one the config claims.
"""

# What is really on the wire: "DHT11" or "DHT22".
ATTACHED = "DHT22"

# What a correctly-read sensor should report.
TRUE_TEMP = 27.4
TRUE_HUM = 68.2


class _Base:
    driver = None

    def __init__(self, pin):
        self.pin = pin
        self._t = None
        self._h = None

    def measure(self):
        if ATTACHED == self.driver:
            # Matched. A DHT11 only ever reports whole numbers.
            if self.driver == "DHT11":
                self._t, self._h = int(TRUE_TEMP), int(TRUE_HUM)
            else:
                self._t, self._h = TRUE_TEMP, TRUE_HUM
        elif self.driver == "DHT22" and ATTACHED == "DHT11":
            # A DHT11 sends its integer part in the byte the DHT22 driver treats
            # as the high half of a 16-bit tenths value: 27 -> (27<<8)/10.
            self._t = (int(TRUE_TEMP) << 8) / 10
            self._h = (int(TRUE_HUM) << 8) / 10
        else:
            # DHT11 driver on a DHT22: truncated nonsense, small but wrong.
            self._t = float(int(TRUE_TEMP) & 0xFF)
            self._h = float(int(TRUE_HUM) & 0xFF)

    def temperature(self):
        return self._t

    def humidity(self):
        return self._h


class DHT11(_Base):
    driver = "DHT11"


class DHT22(_Base):
    driver = "DHT22"
