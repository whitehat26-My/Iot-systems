# Tests

These run on your **laptop or the Pi** — no ESP32 and no sensor required. That's
the point: they check the parts that would otherwise only fail once you had
hardware in your hands and no way to tell whether the bug was in the wiring, the
driver, or the server.

`mpshim/` provides just enough fake MicroPython (`machine`, `network`, `ustruct`,
`umqtt.simple`) that the *real* firmware files can be imported and run on a PC,
against a fake BME280 chip.

## test_bme280.py

No setup needed:

```bash
python3 tests/test_bme280.py
```

Checks the sensor driver against a simulated chip:

- Every calibration constant survives the byte unpacking — including `dig_H4` and
  `dig_H5`, which are signed 12-bit values that *share a byte*. Get that wrong and
  humidity is subtly incorrect in a way you would never notice by eye.
- Compensation maths produces plausible values, and temperature rises when the raw
  reading rises (catches a sign error).
- A BMP280 is identified as a BMP280 and reports humidity as `None`, not `0` — so
  a mis-sold module announces itself instead of quietly logging zeros forever.
- An empty I²C bus and an unknown chip both produce a useful error message.

## test_contract.py

Needs the broker, collector and API running (steps 1–4 of
[docs/06](../docs/06-run-the-stack.md)):

```bash
python3 tests/test_contract.py
```

Runs the **real** `firmware/room_sensor/main.py` publish path against your actual
broker, then checks what came out the far end: the topics the node sends, the rows
the collector wrote, and the JSON the API serves.

This is the one that catches drift between the firmware and the server. If someone
renames a topic on one side, the two halves stop agreeing — and that failure is
very hard to diagnose on a board with no screen.

It cleans up after itself, so the `testroom` node won't pollute your dashboard.
