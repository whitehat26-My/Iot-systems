"""Runs automatically on power-up, before main.py.

Its only job is to get the node onto WiFi. Keeping this separate from main.py
means that if the network is down you still land in a usable REPL — with the
board connected over USB you can press Ctrl-C, poke at things, and fix your
config without reflashing.
"""

import time

import network


def connect(ssid, password, timeout=25, led=None):
    """Bring up the WiFi interface. Returns the station object once connected.

    Raises OSError on timeout so the caller decides what to do — main.py
    reboots, which is the right move for an unattended sensor.
    """
    station = network.WLAN(network.STA_IF)
    station.active(True)

    if station.isconnected():
        print("wifi: already connected, ip", station.ifconfig()[0])
        return station

    print("wifi: connecting to", ssid)
    station.connect(ssid, password)

    deadline = time.time() + timeout
    while not station.isconnected():
        if time.time() > deadline:
            # Scan and report, because "it won't connect" is almost always one
            # of three things: a typo, a 5 GHz-only network, or being out of
            # range. This tells you which.
            try:
                names = [n[0].decode() for n in station.scan()]
                seen = ", ".join(names[:12]) or "none"
            except Exception:
                seen = "scan failed"
            station.active(False)
            raise OSError(
                "wifi: could not connect to {!r} within {}s.\n"
                "  Networks the ESP32 can see: {}\n"
                "  If yours is missing it is probably 5 GHz — the ESP32 is "
                "2.4 GHz only.".format(ssid, timeout, seen)
            )

        if led is not None:
            led.value(not led.value())      # blink while trying
        time.sleep(0.25)

    if led is not None:
        led.value(0)

    ip, netmask, gateway, dns = station.ifconfig()
    print("wifi: connected. ip", ip, "gateway", gateway)
    return station


# Nothing is executed at import time on purpose. main.py calls connect() so that
# it controls the retry and reboot policy in one place, and so a failure here
# never leaves you locked out of the REPL.
