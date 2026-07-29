#!/usr/bin/env bash
#
# Copy the firmware onto an ESP32 that already has MicroPython on it.
#
#     ./tools/deploy_node.sh
#     ./tools/deploy_node.sh /dev/ttyUSB1      # if you have more than one board
#
# Prerequisites: MicroPython flashed (docs/05-node-flash.md) and mpremote
# installed on your laptop:
#
#     pip install mpremote
#
# Re-run this every time you change the firmware. It overwrites the files on the
# board and restarts it, so the new code runs immediately.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FW="$REPO/firmware/room_sensor"
PORT="${1:-auto}"

# mpremote takes the port as a connect argument; "auto" finds the only board.
if [[ "$PORT" == "auto" ]]; then
  MP=(mpremote)
else
  MP=(mpremote connect "$PORT")
fi

if ! command -v mpremote > /dev/null; then
  echo "mpremote not found. Install it with:  pip install mpremote"
  exit 1
fi

# --- the one thing people forget --------------------------------------------
if [[ ! -f "$FW/config.py" ]]; then
  echo "Missing $FW/config.py"
  echo
  echo "Create it from the example and put your WiFi details in it:"
  echo "    cp firmware/room_sensor/config.example.py firmware/room_sensor/config.py"
  echo
  echo "(config.py is gitignored, so your password stays off GitHub.)"
  exit 1
fi

# Catch the most common config mistake before it turns into a confusing
# "wifi: could not connect" on the device.
if grep -q "your-wifi-name" "$FW/config.py"; then
  echo "config.py still has the placeholder WiFi name in it. Edit it first."
  exit 1
fi

echo "==> Board:"
"${MP[@]}" eval "import sys; print(' ', sys.implementation)" || {
  echo
  echo "Could not talk to the board. Things to check:"
  echo "  * Is it plugged in, with a DATA cable (not charge-only)?"
  echo "  * Is MicroPython flashed?  See docs/05-node-flash.md"
  echo "  * Is another program holding the port (Thonny, a serial monitor)?"
  exit 1
}

# --- MQTT library ------------------------------------------------------------
# umqtt.simple is not bundled with the ESP32 build. mpremote fetches it on this
# machine and copies it across, so the board itself does not need internet.
echo "==> Installing umqtt.simple"
"${MP[@]}" mip install umqtt.simple

# --- our code ----------------------------------------------------------------
echo "==> Copying libraries"
"${MP[@]}" mkdir :lib || true          # already exists after the mip install
for f in "$FW"/lib/*.py; do
  echo "    lib/$(basename "$f")"
  "${MP[@]}" cp "$f" ":lib/$(basename "$f")"
done

echo "==> Copying firmware"
for f in boot.py main.py config.py; do
  echo "    $f"
  "${MP[@]}" cp "$FW/$f" ":$f"
done

echo "==> Restarting the board"
"${MP[@]}" reset

cat <<'EOF'

Done. To watch it run:

    mpremote                      # Ctrl-] to exit, Ctrl-C to interrupt

You should see the WiFi connect, the sensor be identified, then a line per
reading. If the sensor is not found, the message will list what it saw on the
I2C bus — see docs/04-node-wiring.md.

And on the hub, to confirm the readings are arriving:

    mosquitto_sub -t 'home/#' -v
EOF
