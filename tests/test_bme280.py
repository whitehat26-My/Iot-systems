"""Exercise the BME280 driver and sensor detection on a PC, with a fake chip.

Catches the bugs that would otherwise wait for real hardware: byte order, signed
conversions, the shared-nibble H4/H5 packing, and the BMP280 detection path.
"""
import struct
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "mpshim"))
sys.path.insert(0, os.path.join(REPO, "firmware", "room_sensor", "lib"))
sys.path.insert(0, os.path.join(REPO, "firmware", "room_sensor"))
sys.path.insert(0, HERE)

time.sleep_ms = lambda ms: None  # MicroPython-ism

# Calibration constants of the shape a real BME280 ships with.
T = dict(T1=28244, T2=26571, T3=50)
P = dict(P1=37678, P2=-10684, P3=3024, P4=6534, P5=-138, P6=-7, P7=9900, P8=-10230, P9=4285)
H = dict(H1=75, H2=372, H3=0, H4=279, H5=50, H6=30)


def calib1(with_hum=True):
    b = bytearray(26)
    struct.pack_into("<H", b, 0, T["T1"])
    struct.pack_into("<hh", b, 2, T["T2"], T["T3"])
    struct.pack_into("<H", b, 6, P["P1"])
    struct.pack_into("<hhhhhhhh", b, 8, *[P[f"P{i}"] for i in range(2, 10)])
    b[25] = H["H1"] if with_hum else 0
    return bytes(b)


def calib2():
    # H4 = (0xE4 << 4) | (0xE5 & 0x0F);  H5 = (0xE6 << 4) | (0xE5 >> 4)
    e4 = H["H4"] >> 4
    e6 = H["H5"] >> 4
    e5 = ((H["H5"] & 0x0F) << 4) | (H["H4"] & 0x0F)
    return bytes([H["H2"] & 0xFF, H["H2"] >> 8, H["H3"], e4, e5, e6, H["H6"]])


def data_block(adc_t, adc_p, adc_h):
    return bytes([
        (adc_p >> 12) & 0xFF, (adc_p >> 4) & 0xFF, (adc_p & 0x0F) << 4,
        (adc_t >> 12) & 0xFF, (adc_t >> 4) & 0xFF, (adc_t & 0x0F) << 4,
        (adc_h >> 8) & 0xFF, adc_h & 0xFF,
    ])


class FakeChip:
    def __init__(self, chip_id=0x60, addr=0x76, adc=(519888, 326152, 26000)):
        self.chip_id = chip_id
        self.addr = addr
        self.adc = adc
        self.writes = []

    def scan(self):
        return [self.addr]

    def readfrom_mem(self, addr, reg, n):
        assert addr == self.addr, f"wrong address {hex(addr)}"
        if reg == 0xD0:
            return bytes([self.chip_id])
        if reg == 0xF3:
            return bytes([0x00])                  # never busy
        if reg == 0x88:
            return calib1(self.chip_id == 0x60)[:n]
        if reg == 0xE1:
            return calib2()[:n]
        if reg == 0xF7:
            return data_block(*self.adc)[:n]
        raise AssertionError(f"unexpected read of {hex(reg)}")

    def writeto_mem(self, addr, reg, data):
        self.writes.append((reg, data[0]))


fails = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not cond:
        fails.append(name)


import bme280  # noqa: E402
import machine  # noqa: E402

print("BME280 (chip id 0x60)")
chip = FakeChip(0x60)
machine.FAKE_I2C = chip
dev = bme280.BME280(machine.I2C(0))
check("identified as BME280", dev.name == "BME280", dev.name)
check("has_humidity true", dev.has_humidity is True)
check("soft reset issued", (0xE0, 0xB6) in chip.writes)
check("ctrl_hum configured", any(r == 0xF2 for r, _ in chip.writes))

t, p, h = dev.read()
print(f"    -> {t:.2f} C, {p:.2f} hPa, {h:.2f} %RH")
check("temperature plausible", 10 < t < 40, f"{t:.2f}")
check("pressure plausible", 850 < p < 1100, f"{p:.2f}")
check("humidity plausible", 0 <= h <= 100, f"{h:.2f}")
check("forced mode requested", any(r == 0xF4 and (v & 0x03) == 1 for r, v in chip.writes))

# Calibration unpacking: verify each constant survived the byte juggling.
print("calibration unpacking")
for key, want in list(T.items()) + list(P.items()) + list(H.items()):
    got = getattr(dev, "dig_" + key)
    check(f"dig_{key}", got == want, f"got {got}, want {want}")

# Monotonicity: a higher raw temperature reading must give a higher temperature.
print("monotonic in raw ADC")
cold = bme280.BME280(machine.I2C(0))
machine.FAKE_I2C = FakeChip(0x60, adc=(500000, 326152, 26000))
cold = bme280.BME280(machine.I2C(0))
t_cold = cold.read()[0]
machine.FAKE_I2C = FakeChip(0x60, adc=(540000, 326152, 26000))
hot = bme280.BME280(machine.I2C(0))
t_hot = hot.read()[0]
check("higher adc_t -> higher temp", t_hot > t_cold, f"{t_cold:.2f} -> {t_hot:.2f}")

print("BMP280 (chip id 0x58) — the mis-sold-module case")
machine.FAKE_I2C = FakeChip(0x58)
bmp = bme280.BME280(machine.I2C(0))
check("identified as BMP280", bmp.name == "BMP280", bmp.name)
check("has_humidity false", bmp.has_humidity is False)
t2, p2, h2 = bmp.read()
check("humidity is None, not 0", h2 is None, repr(h2))
check("temperature still works", 10 < t2 < 40, f"{t2:.2f}")

print("wrong chip / nothing there")
try:
    machine.FAKE_I2C = FakeChip(0x99)
    bme280.BME280(machine.I2C(0))
    check("rejects unknown chip id", False)
except bme280.BME280Error as e:
    check("rejects unknown chip id", "0x99" in str(e), str(e)[:60])


class Empty(FakeChip):
    def scan(self):
        return []


try:
    machine.FAKE_I2C = Empty()
    bme280.BME280(machine.I2C(0))
    check("reports empty bus", False)
except bme280.BME280Error as e:
    check("reports empty bus", "nothing at all" in str(e), str(e)[:50])

print("sensor.py auto-detection")
import sensor as sensor_lib  # noqa: E402

machine.FAKE_I2C = FakeChip(0x60)
s = sensor_lib.Sensor(scl_pin=22, sda_pin=21)
vals = s.read()
check("BME280 -> 3 metrics", set(vals) == {"temperature", "humidity", "pressure"}, str(sorted(vals)))

machine.FAKE_I2C = FakeChip(0x58)
s2 = sensor_lib.Sensor(scl_pin=22, sda_pin=21)
vals2 = s2.read()
check("BMP280 -> 2 metrics, no humidity", set(vals2) == {"temperature", "pressure"}, str(sorted(vals2)))
check("BMP280 warns the user", any("no humidity sensor" in n for n in s2.notes))

machine.FAKE_I2C = Empty()
try:
    sensor_lib.Sensor(scl_pin=22, sda_pin=21)
    check("no sensor raises NoSensor", False)
except sensor_lib.NoSensor as e:
    check("no sensor raises NoSensor", "3V3" in str(e))

print()
if fails:
    print(f"{len(fails)} FAILED: {fails}")
    sys.exit(1)
print("all checks passed")
