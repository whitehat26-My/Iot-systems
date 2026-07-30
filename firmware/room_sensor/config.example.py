"""Node settings — COPY THIS FILE to config.py and edit it.

    cp firmware/room_sensor/config.example.py firmware/room_sensor/config.py

config.py is listed in .gitignore, so your WiFi password stays off GitHub.
This example file, with its placeholder values, is the only one committed.
Never put your real password in this file.
"""

# --- WiFi -------------------------------------------------------------------
# IMPORTANT: the ESP32 has a 2.4 GHz radio only. It cannot see a 5 GHz network.
# If your router advertises "MyWiFi" and "MyWiFi_5G" as separate names, use the
# 2.4 GHz one here. If it advertises a single name for both bands, that is fine.
WIFI_SSID = "your-wifi-name"
WIFI_PASSWORD = "your-wifi-password"

# --- Where the hub is -------------------------------------------------------
# The Raspberry Pi's address on your network. Must be a literal IP: MicroPython's
# MQTT client cannot resolve "raspberrypi.local" (no mDNS on the device).
#
# Find it by running `hostname -I` on the Pi. Then reserve that address for the
# Pi in your router's DHCP settings — otherwise it can change on a reboot and
# this node will sit there publishing into the void.
MQTT_HOST = "192.168.1.50"
MQTT_PORT = 1883

# --- Who this node is -------------------------------------------------------
# These two build the MQTT topics: home/<ROOM>/<NODE>/temperature and so on.
# A second node needs a different NODE (and usually a different ROOM); nothing
# on the server has to change for it to appear on the dashboard.
ROOM = "bedroom"
NODE = "node1"

# --- How often to publish ---------------------------------------------------
# 30 seconds is a good default: fine enough to see the air-conditioning switch
# on, coarse enough that a month of data stays small. Room temperature does not
# change fast, so going below ~10s buys you nothing but noise.
PUBLISH_INTERVAL = 30

# --- Wiring -----------------------------------------------------------------
# I2C pins for the BME280. These are the ESP32's defaults; change them only if
# you wired it differently.
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21

# Leave as None unless you are using a DHT sensor instead of a BME280, in which
# case set it to the GPIO number its DATA pin is on. Most starter kits ship a DHT
# rather than a BME280, so if you bought a kit this is probably you.
DHT_PIN = None

# Which DHT you have. These cannot be told apart electrically, so you must say.
#
#   "DHT11"  blue module   - whole degrees only, +/-2C, +/-5%RH.  In most kits.
#   "DHT22"  white module  - 0.1C resolution, +/-0.5C.            Better.
#
# Get this wrong and the readings come out wildly off rather than slightly off;
# the firmware range-checks them on startup and tells you to change this line.
#
# Worth knowing: a DHT11's whole-degree output makes the temperature chart a
# staircase rather than a curve. A BME280 (~RM15) fixes that and adds pressure.
DHT_TYPE = "DHT22"

# Most ESP32 DevKitC boards have an LED on GPIO2. Some use GPIO5, a few have
# none at all. Set to None to disable the blinking; it is only a convenience.
LED_PIN = 2

# --- Behaviour when things go wrong -----------------------------------------
# After this many consecutive failures (sensor or network), reboot the board.
# An ESP32 that has been up for weeks occasionally wedges its WiFi stack, and a
# reboot is a reliable, boring fix that needs nobody in the room.
MAX_FAILURES_BEFORE_REBOOT = 10
