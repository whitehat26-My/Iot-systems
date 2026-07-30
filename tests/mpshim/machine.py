"""Just enough of MicroPython's `machine` to exercise the firmware on a PC."""


class Pin:
    OUT = 1
    IN = 0

    def __init__(self, n, mode=None):
        self.n = n
        self._v = 0

    def value(self, v=None):
        if v is None:
            return self._v
        self._v = int(bool(v))


# Populated by the test before constructing Sensor().
FAKE_I2C = None


class I2C:
    def __init__(self, bus, scl=None, sda=None):
        if FAKE_I2C is None:
            raise OSError("no fake I2C installed")
        self._d = FAKE_I2C

    def scan(self):
        return self._d.scan()

    def readfrom_mem(self, addr, reg, n):
        return self._d.readfrom_mem(addr, reg, n)

    def writeto_mem(self, addr, reg, data):
        return self._d.writeto_mem(addr, reg, data)


def reset():
    raise SystemExit("machine.reset() called")
