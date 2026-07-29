#!/usr/bin/env bash
#
# Set up the Raspberry Pi hub: broker, Python environment, and two services
# that start at boot.
#
# Run it from the repo root, on the Pi:
#
#     ./hub/install.sh
#
# Safe to run again. It re-creates the services from the templates and reinstalls
# dependencies, but never touches your database — so it is also how you apply
# changes after a `git pull`.

set -euo pipefail

# --- work out where we are and who we are -----------------------------------
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# The user who invoked the script, even under sudo, because the services must
# run as the human's account (which owns the repo), not as root.
RUN_USER="${SUDO_USER:-$(id -un)}"

if [[ "$RUN_USER" == "root" ]]; then
  echo "Refusing to install services that run as root."
  echo "Run this as your normal user (it will call sudo where it needs to)."
  exit 1
fi

echo "Repo:    $REPO"
echo "Service user: $RUN_USER"
echo

# --- 1. system packages ------------------------------------------------------
echo "==> Installing system packages"
sudo apt-get update -qq
# python3-venv is separate from python3 on Debian/Raspberry Pi OS.
# mosquitto is the broker; mosquitto-clients gives you mosquitto_sub/pub, which
# are how you debug everything later.
# sqlite3 is only the CLI, for poking at the database by hand.
sudo apt-get install -y mosquitto mosquitto-clients python3-venv python3-pip sqlite3

# --- 2. broker configuration -------------------------------------------------
# This is the step that makes the broker reachable from the ESP32 instead of
# from localhost only. See the comments in the config file itself.
echo "==> Configuring mosquitto"
sudo install -m 644 "$REPO/hub/mosquitto/room-sensors.conf" /etc/mosquitto/conf.d/room-sensors.conf
sudo systemctl enable mosquitto
sudo systemctl restart mosquitto

# --- 3. python environment ---------------------------------------------------
# A venv is not optional: modern Raspberry Pi OS marks the system Python as
# "externally managed" (PEP 668) and refuses `pip install` outside one.
echo "==> Creating virtualenv at $REPO/.venv"
if [[ ! -x "$REPO/.venv/bin/python" ]]; then
  python3 -m venv "$REPO/.venv"
fi
"$REPO/.venv/bin/pip" install --quiet --upgrade pip
"$REPO/.venv/bin/pip" install --quiet -r "$REPO/hub/requirements.txt"
echo "    $("$REPO/.venv/bin/python" --version) with dependencies installed"

# --- 4. services -------------------------------------------------------------
# The unit files in hub/systemd/ are templates: they carry __REPO__ and __USER__
# placeholders because the repo path and username differ on every machine.
echo "==> Installing systemd services"
for svc in iot-collector iot-api; do
  sed -e "s|__REPO__|$REPO|g" -e "s|__USER__|$RUN_USER|g" \
    "$REPO/hub/systemd/$svc.service" | sudo tee "/etc/systemd/system/$svc.service" > /dev/null
done

sudo systemctl daemon-reload
sudo systemctl enable iot-collector iot-api
sudo systemctl restart iot-collector iot-api

# --- 5. report ---------------------------------------------------------------
# Give the services a moment to either start or fail before we report.
sleep 2
echo
echo "==> Status"
for svc in mosquitto iot-collector iot-api; do
  if systemctl is-active --quiet "$svc"; then
    echo "    [ok]   $svc"
  else
    echo "    [FAIL] $svc  —  journalctl -u $svc -n 30"
  fi
done

# Best effort: the first global address on any interface. Used only for the
# hint below, so a blank result is not fatal.
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"

cat <<EOF

Done.

  Dashboard:   http://${IP:-<pi-ip>}:8000
  Broker:      ${IP:-<pi-ip>}:1883      <-- put this IP in the ESP32's config.py
  Logs:        journalctl -u iot-collector -f
               journalctl -u iot-api -f

Next: reserve this IP for the Pi in your router's DHCP settings, so it does not
change and leave your nodes talking to nothing. Then check the broker is
reachable across the network -- run this from your LAPTOP, not the Pi:

  mosquitto_sub -h ${IP:-<pi-ip>} -t 'home/#' -v

Nothing will print until a node publishes. To prove the path end to end before
the ESP32 exists, run this from your laptop too:

  python tools/fake_sensor.py --host ${IP:-<pi-ip>}
EOF
