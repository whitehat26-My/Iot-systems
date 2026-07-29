"""Minimal BME280 / BMP280 driver for MicroPython.

Written for this project from the Bosch BME280 datasheet (document
BST-BME280-DS002), using the datasheet's floating-point compensation formulas.
Not a copy of anyone else's library — you can read all of it, which is the point.

The BME280 and BMP280 are register-compatible except that the BMP280 has no
humidity sensor. This driver reads the chip ID and simply reports `has_humidity`
so the layer above can react, rather than silently returning zeros — which
matters because a lot of modules sold as "BME280" are actually BMP280s.

Usage:
    from machine import I2C, Pin
    i2c = I2C(0, scl=Pin(22), sda=Pin(21))
    sensor = BME280(i2c)
    t, p, h = sensor.read()          # °C, hPa, %RH (h is None on a BMP280)
"""

import time
from ustruct import unpack, unpack_from

# Register addresses (datasheet section 5.3)
_REG_ID = 0xD0
_REG_RESET = 0xE0
_REG_STATUS = 0xF3
_REG_CTRL_MEAS = 0xF4
_REG_CTRL_HUM = 0xF2
_REG_CONFIG = 0xF5
_REG_DATA = 0xF7        # press_msb; 8 bytes of measurement follow
_REG_CALIB_1 = 0x88     # 26 bytes: dig_T1..T3, dig_P1..P9, dig_H1
_REG_CALIB_2 = 0xE1     # 7 bytes:  dig_H2..H6

CHIP_BME280 = 0x60
CHIP_BMP280 = 0x58      # 0x56 / 0x57 are pre-production BMP280 samples

# Oversampling x1 on everything, filter off. This is the datasheet's
# recommendation for "weather monitoring" — the lowest-power setting, and
# entirely adequate when we sample once every 30 seconds.
_OSRS_X1 = 1
_MODE_FORCED = 1        # take one measurement, then return to sleep


class BME280Error(Exception):
    pass


class BME280:
    def __init__(self, i2c, address=None):
        self.i2c = i2c

        # The address depends on how the module ties the SDO pin: 0x76 when it
        # is pulled low, 0x77 when high. Boards disagree, so try both.
        if address is None:
            found = self.i2c.scan()
            for candidate in (0x76, 0x77):
                if candidate in found:
                    address = candidate
                    break
            else:
                raise BME280Error(
                    "no BME280 found at 0x76 or 0x77. I2C scan saw: "
                    + (", ".join(hex(a) for a in found) if found else "nothing at all")
                )
        self.address = address

        self.chip_id = self._read8(_REG_ID)
        if self.chip_id == CHIP_BME280:
            self.has_humidity = True
            self.name = "BME280"
        elif self.chip_id in (CHIP_BMP280, 0x56, 0x57):
            self.has_humidity = False
            self.name = "BMP280"
        else:
            raise BME280Error(
                "unexpected chip id {}. Expected 0x60 (BME280) or 0x58 (BMP280) — "
                "is this really a BME280 module?".format(hex(self.chip_id))
            )

        # Soft reset, then give it the datasheet's 2ms start-up time.
        self._write8(_REG_RESET, 0xB6)
        time.sleep_ms(5)

        self._load_calibration()

        if self.has_humidity:
            self._write8(_REG_CTRL_HUM, _OSRS_X1)
        self._write8(_REG_CONFIG, 0)      # IIR filter off, no standby (forced mode)

        self.t_fine = 0

    # --- raw I2C helpers ----------------------------------------------------
    def _read(self, reg, length):
        return self.i2c.readfrom_mem(self.address, reg, length)

    def _read8(self, reg):
        return self._read(reg, 1)[0]

    def _write8(self, reg, value):
        self.i2c.writeto_mem(self.address, reg, bytes([value]))

    # --- calibration --------------------------------------------------------
    def _load_calibration(self):
        """Read the factory calibration constants burned into each individual
        chip. Every BME280 needs its own; that is why raw readings are useless
        without this step."""
        c = self._read(_REG_CALIB_1, 26)

        # '<' little endian, 'H' unsigned 16-bit, 'h' signed 16-bit.
        self.dig_T1 = unpack_from("<H", c, 0)[0]
        self.dig_T2, self.dig_T3 = unpack_from("<hh", c, 2)

        self.dig_P1 = unpack_from("<H", c, 6)[0]
        (self.dig_P2, self.dig_P3, self.dig_P4, self.dig_P5,
         self.dig_P6, self.dig_P7, self.dig_P8, self.dig_P9) = unpack_from("<hhhhhhhh", c, 8)

        if not self.has_humidity:
            return

        self.dig_H1 = c[25]
        h = self._read(_REG_CALIB_2, 7)
        self.dig_H2 = unpack_from("<h", h, 0)[0]
        self.dig_H3 = h[2]

        # dig_H4 and dig_H5 are signed 12-bit values that share byte h[3]'s
        # neighbour — H4 takes the low nibble of h[4], H5 the high nibble.
        self.dig_H4 = (unpack("<b", h[3:4])[0] << 4) | (h[4] & 0x0F)
        self.dig_H5 = (unpack("<b", h[5:6])[0] << 4) | (h[4] >> 4)
        self.dig_H6 = unpack("<b", h[6:7])[0]

    # --- measurement --------------------------------------------------------
    def read(self):
        """Trigger one measurement and return (temperature_C, pressure_hPa,
        humidity_pct). Humidity is None on a BMP280."""
        # Forced mode: one shot, then back to sleep. Cheaper than continuous
        # mode and there is nothing to gain from running the sensor between
        # our 30-second samples.
        self._write8(_REG_CTRL_MEAS, (_OSRS_X1 << 5) | (_OSRS_X1 << 2) | _MODE_FORCED)

        # Bit 3 of the status register is high while a conversion is running.
        # x1 oversampling completes in about 10ms; the loop bounds it anyway so
        # a wiring fault cannot hang the node forever.
        for _ in range(100):
            if not (self._read8(_REG_STATUS) & 0x08):
                break
            time.sleep_ms(2)
        else:
            raise BME280Error("sensor never finished its measurement")

        d = self._read(_REG_DATA, 8)

        # Pressure and temperature are 20-bit, humidity 16-bit.
        adc_p = (d[0] << 12) | (d[1] << 4) | (d[2] >> 4)
        adc_t = (d[3] << 12) | (d[4] << 4) | (d[5] >> 4)
        adc_h = (d[6] << 8) | d[7]

        temperature = self._compensate_temperature(adc_t)   # also sets t_fine
        pressure = self._compensate_pressure(adc_p)
        humidity = self._compensate_humidity(adc_h) if self.has_humidity else None
        return temperature, pressure, humidity

    def _compensate_temperature(self, adc_t):
        """Datasheet section 4.2.3, floating-point variant.

        `t_fine` is a high-resolution intermediate that the pressure and
        humidity formulas both need, which is why temperature must be
        compensated first."""
        var1 = (adc_t / 16384.0 - self.dig_T1 / 1024.0) * self.dig_T2
        var2 = adc_t / 131072.0 - self.dig_T1 / 8192.0
        var2 = var2 * var2 * self.dig_T3
        self.t_fine = var1 + var2
        return self.t_fine / 5120.0

    def _compensate_pressure(self, adc_p):
        """Datasheet section 4.2.3. Returns hPa (the formula yields Pa)."""
        var1 = self.t_fine / 2.0 - 64000.0
        var2 = var1 * var1 * self.dig_P6 / 32768.0
        var2 = var2 + var1 * self.dig_P5 * 2.0
        var2 = var2 / 4.0 + self.dig_P4 * 65536.0
        var1 = (self.dig_P3 * var1 * var1 / 524288.0 + self.dig_P2 * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * self.dig_P1

        if var1 == 0.0:
            return 0.0      # would divide by zero; means the calibration is bad

        p = 1048576.0 - adc_p
        p = (p - var2 / 4096.0) * 6250.0 / var1
        var1 = self.dig_P9 * p * p / 2147483648.0
        var2 = p * self.dig_P8 / 32768.0
        p = p + (var1 + var2 + self.dig_P7) / 16.0
        return p / 100.0

    def _compensate_humidity(self, adc_h):
        """Datasheet section 4.2.3, clamped to 0-100%."""
        h = self.t_fine - 76800.0
        h = (adc_h - (self.dig_H4 * 64.0 + self.dig_H5 / 16384.0 * h)) * (
            self.dig_H2 / 65536.0 * (
                1.0 + self.dig_H6 / 67108864.0 * h * (1.0 + self.dig_H3 / 67108864.0 * h)
            )
        )
        h = h * (1.0 - self.dig_H1 * h / 524288.0)
        return max(0.0, min(100.0, h))
