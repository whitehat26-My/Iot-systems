"""Server-side settings.

Unlike the ESP32's config.py, there are no secrets here, so this file IS
committed to git. Everything can be overridden with an environment variable,
which is how the systemd units on the Pi configure things without editing code.

Example:
    MQTT_HOST=192.168.1.50 python server/collector.py
"""

import os
from pathlib import Path

# Where this repo lives on disk. Used to locate the database and static files
# so the app works no matter which directory you launch it from.
REPO_ROOT = Path(__file__).resolve().parent.parent

# --- MQTT broker -----------------------------------------------------------
# On your laptop during step 1, the broker is local. On the Pi it is also
# local (the collector and broker run on the same box), so "localhost" is
# correct in both cases. Only the ESP32 needs the Pi's real LAN IP.
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

# Subscribe to everything under home/. The '#' wildcard means "this level and
# all levels below", so a brand-new node in a brand-new room is picked up with
# no server change at all — that is the whole point of using MQTT here.
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "home/#")

# --- Storage ---------------------------------------------------------------
DB_PATH = Path(os.environ.get("DB_PATH", REPO_ROOT / "readings.db"))

# How long to keep readings. A reading every 30s is ~2,900 rows/day per
# metric, which is trivial for SQLite, but pruning keeps the file small enough
# that it never becomes a problem on an SD card.
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "90"))

# --- Web -------------------------------------------------------------------
# 0.0.0.0 = listen on all interfaces, so you can reach the dashboard from your
# phone. This is LAN-only; do not port-forward it. See README security note.
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8000"))

STATIC_DIR = Path(__file__).resolve().parent / "static"

# Metrics we know how to display, in dashboard order, with their units.
# Adding a new sensor type means adding one line here.
KNOWN_METRICS = {
    "temperature": {"unit": "°C", "label": "Temperature"},
    "humidity": {"unit": "%", "label": "Humidity"},
    "pressure": {"unit": "hPa", "label": "Pressure"},
}
