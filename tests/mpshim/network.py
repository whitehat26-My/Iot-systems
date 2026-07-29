"""Stand-in for MicroPython's `network`. Pretends WiFi is already up."""

STA_IF = 0
AP_IF = 1


class WLAN:
    def __init__(self, iface=STA_IF):
        self._active = False

    def active(self, v=None):
        if v is None:
            return self._active
        self._active = bool(v)

    def isconnected(self):
        return True

    def connect(self, ssid, password):
        pass

    def scan(self):
        return [(b"FakeNet", b"", 1, -50, 0, 0)]

    def ifconfig(self):
        return ("192.168.1.99", "255.255.255.0", "192.168.1.1", "192.168.1.1")
