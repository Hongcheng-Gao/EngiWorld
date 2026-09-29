#!/usr/bin/env bash
set -euo pipefail

: "${OSWORLD_BUNDLE_URL:?OSWORLD_BUNDLE_URL is required}"
: "${OSWORLD_ARCHIVE_SHA256:?OSWORLD_ARCHIVE_SHA256 is required}"
: "${OSWORLD_CONTENT_SHA256:?OSWORLD_CONTENT_SHA256 is required}"
: "${OSWORLD_BUNDLE_VERSION:?OSWORLD_BUNDLE_VERSION is required}"
: "${OSWORLD_BUNDLE_ROOT_DIR:?OSWORLD_BUNDLE_ROOT_DIR is required}"
: "${OSWORLD_UPDATER_B64:?OSWORLD_UPDATER_B64 is required}"

OSWORLD_INSTALL_PROFILE="${OSWORLD_INSTALL_PROFILE:-desktop}"
OSWORLD_USER="${OSWORLD_USER:-user}"
OSWORLD_SERVER_DIR="${OSWORLD_SERVER_DIR:-/home/${OSWORLD_USER}/server}"
OSWORLD_PYTHON_DIR="${OSWORLD_PYTHON_DIR:-/opt/arena-osworld-python}"
OSWORLD_RUNTIME_DIR="${OSWORLD_RUNTIME_DIR:-/opt/arena-osworld-runtime}"
OSWORLD_UPDATER_DIR="${OSWORLD_UPDATER_DIR:-/opt/arena-osworld-updater}"
OSWORLD_UPDATER_CONFIG="${OSWORLD_UPDATER_CONFIG:-/etc/arena-osworld-updater.json}"

if [[ "$(uname -m)" != "x86_64" ]]; then
  echo "Expected x86_64, found $(uname -m)" >&2
  exit 1
fi

source /etc/os-release
if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" ]]; then
  echo "Expected Ubuntu 24.04, found ${PRETTY_NAME:-unknown}" >&2
  exit 1
fi
if [[ "${OSWORLD_INSTALL_PROFILE}" != "minimal" && "${OSWORLD_INSTALL_PROFILE}" != "desktop" ]]; then
  echo "Unsupported install profile: ${OSWORLD_INSTALL_PROFILE}" >&2
  exit 1
fi

if ! id "${OSWORLD_USER}" >/dev/null 2>&1; then
  useradd --create-home --user-group --shell /bin/bash "${OSWORLD_USER}"
fi
OSWORLD_HOME="$(getent passwd "${OSWORLD_USER}" | cut -d: -f6)"
OSWORLD_UID="$(id -u "${OSWORLD_USER}")"
OSWORLD_GROUP="$(id -gn "${OSWORLD_USER}")"

echo '{"event":"ubuntu_osworld_bootstrap_started"}'

# Ubuntu cloud images include Python. Download and verify the private TOS
# payload before lengthy package installation so the presigned URL is used
# while it has nearly its full lifetime remaining.
command -v python3 >/dev/null
install -d -m 0755 "${OSWORLD_UPDATER_DIR}" "$(dirname "${OSWORLD_UPDATER_CONFIG}")"
printf '%s' "${OSWORLD_UPDATER_B64}" | base64 --decode > "${OSWORLD_UPDATER_DIR}/osworld_updater.py"
chmod 0755 "${OSWORLD_UPDATER_DIR}/osworld_updater.py"

python3 - "${OSWORLD_UPDATER_CONFIG}" "${OSWORLD_SERVER_DIR}" <<'PY'
import json
import sys

path, current_dir = sys.argv[1:]
with open(path, "w", encoding="utf-8") as output:
    json.dump(
        {
            "current_dir": current_dir,
            "stop_command": [],
            "start_command": [],
            "health_url": "",
            "health_timeout_seconds": 120,
        },
        output,
        indent=2,
    )
PY

python3 "${OSWORLD_UPDATER_DIR}/osworld_updater.py" apply \
  --config "${OSWORLD_UPDATER_CONFIG}" \
  --url "${OSWORLD_BUNDLE_URL}" \
  --archive-sha256 "${OSWORLD_ARCHIVE_SHA256}" \
  --content-sha256 "${OSWORLD_CONTENT_SHA256}" \
  --version "${OSWORLD_BUNDLE_VERSION}" \
  --root-dir "${OSWORLD_BUNDLE_ROOT_DIR}" \
  --skip-health

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  at-spi2-core \
  ca-certificates \
  curl \
  dbus-user-session \
  dbus-x11 \
  ffmpeg \
  gnome-screenshot \
  libxkbcommon0 \
  libxcursor1 \
  libxtst6 \
  python3 \
  python3-pip \
  python3-pyatspi \
  python3-tk \
  python3-venv \
  python3-xlib \
  scrot \
  socat \
  wmctrl \
  x11-utils \
  xclip \
  xvfb

if [[ "${OSWORLD_INSTALL_PROFILE}" == "desktop" ]]; then
  apt-get install -y --no-install-recommends \
    fonts-dejavu \
    fonts-liberation \
    fonts-noto-core \
    fonts-noto-cjk \
    novnc \
    websockify \
    x11vnc \
    xfce4 \
    xfce4-goodies \
    xfce4-terminal
fi

python3 -m venv --system-site-packages "${OSWORLD_PYTHON_DIR}"
"${OSWORLD_PYTHON_DIR}/bin/python" -m pip install --no-cache-dir --upgrade pip setuptools wheel
"${OSWORLD_PYTHON_DIR}/bin/python" -m pip install --no-cache-dir \
  Flask \
  lxml \
  numpy \
  Pillow \
  pynput \
  PyAutoGUI \
  pygame \
  python-xlib \
  requests

install -d -m 0755 "${OSWORLD_RUNTIME_DIR}"
cat > "${OSWORLD_RUNTIME_DIR}/serve.py" <<PY
import sys

SERVER_DIR = ${OSWORLD_SERVER_DIR@Q}
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from main import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
PY

cat > "${OSWORLD_RUNTIME_DIR}/start-session.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

export HOME="__OSWORLD_HOME__"
export DISPLAY=:0
export XAUTHORITY="${HOME}/.Xauthority"
export XDG_RUNTIME_DIR="/tmp/arena-osworld-runtime-__OSWORLD_UID__"
export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"

mkdir -p "${XDG_RUNTIME_DIR}"
chmod 0700 "${XDG_RUNTIME_DIR}"
rm -f "${XDG_RUNTIME_DIR}/bus"
touch "${XAUTHORITY}"

/usr/bin/Xvfb :0 -screen 0 1920x1080x24 -ac \
  +extension RANDR +extension GLX +extension XTEST &

for _ in $(seq 1 30); do
  if /usr/bin/xdpyinfo -display :0 >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
/usr/bin/xdpyinfo -display :0 >/dev/null

/usr/bin/dbus-daemon --session \
  --address="${DBUS_SESSION_BUS_ADDRESS}" \
  --nofork --nopidfile --syslog-only &
for _ in $(seq 1 20); do
  [[ -S "${XDG_RUNTIME_DIR}/bus" ]] && break
  sleep 0.25
done

if [[ "__OSWORLD_INSTALL_PROFILE__" == "desktop" ]]; then
  /usr/bin/startxfce4 >/tmp/arena-osworld-xfce.log 2>&1 &
  sleep 3
fi

exec __OSWORLD_PYTHON_DIR__/bin/python __OSWORLD_RUNTIME_DIR__/serve.py
EOF
sed -i \
  -e "s|__OSWORLD_HOME__|${OSWORLD_HOME}|g" \
  -e "s|__OSWORLD_UID__|${OSWORLD_UID}|g" \
  -e "s|__OSWORLD_INSTALL_PROFILE__|${OSWORLD_INSTALL_PROFILE}|g" \
  -e "s|__OSWORLD_PYTHON_DIR__|${OSWORLD_PYTHON_DIR}|g" \
  -e "s|__OSWORLD_RUNTIME_DIR__|${OSWORLD_RUNTIME_DIR}|g" \
  "${OSWORLD_RUNTIME_DIR}/start-session.sh"
chmod 0755 "${OSWORLD_RUNTIME_DIR}/start-session.sh"

cat > /etc/systemd/system/osworld_session.service <<EOF
[Unit]
Description=OSWorld desktop session and guest server
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=60
StartLimitBurst=6

[Service]
Type=simple
User=${OSWORLD_USER}
Group=${OSWORLD_GROUP}
WorkingDirectory=${OSWORLD_HOME}
ExecStart=${OSWORLD_RUNTIME_DIR}/start-session.sh
Environment=PYTHONUNBUFFERED=1
Restart=on-failure
RestartSec=3
KillMode=control-group
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
EOF

if [[ "${OSWORLD_INSTALL_PROFILE}" == "desktop" ]]; then
  cat > /etc/systemd/system/x11vnc.service <<EOF
[Unit]
Description=x11vnc for OSWorld display
After=osworld_session.service

[Service]
Type=simple
User=${OSWORLD_USER}
ExecStartPre=/bin/bash -c 'for i in {1..60}; do DISPLAY=:0 /usr/bin/xdpyinfo >/dev/null 2>&1 && exit 0; sleep 1; done; exit 1'
ExecStart=/usr/bin/x11vnc -display :0 -rfbport 5900 -shared -forever -nopw -q
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

  cat > /etc/systemd/system/novnc.service <<'EOF'
[Unit]
Description=noVNC for OSWorld
After=x11vnc.service

[Service]
Type=simple
ExecStart=/usr/bin/websockify --web=/usr/share/novnc 8006 localhost:5900
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
fi

chown -R "${OSWORLD_USER}:${OSWORLD_GROUP}" "${OSWORLD_HOME}" "${OSWORLD_SERVER_DIR}"
python3 - "${OSWORLD_UPDATER_CONFIG}" "${OSWORLD_SERVER_DIR}" <<'PY'
import json
import sys

path, current_dir = sys.argv[1:]
with open(path, "w", encoding="utf-8") as output:
    json.dump(
        {
            "current_dir": current_dir,
            "stop_command": ["systemctl", "stop", "osworld_session.service"],
            "start_command": ["systemctl", "start", "osworld_session.service"],
            "health_url": "http://127.0.0.1:5000/health",
            "health_timeout_seconds": 120,
        },
        output,
        indent=2,
    )
PY
cat > "${OSWORLD_UPDATER_DIR}/update-osworld" <<EOF
#!/usr/bin/env bash
exec python3 "${OSWORLD_UPDATER_DIR}/osworld_updater.py" apply --config "${OSWORLD_UPDATER_CONFIG}" "\$@"
EOF
chmod 0755 "${OSWORLD_UPDATER_DIR}/update-osworld"

systemctl daemon-reload
systemctl enable --now osworld_session.service
if [[ "${OSWORLD_INSTALL_PROFILE}" == "desktop" ]]; then
  systemctl enable --now x11vnc.service novnc.service
fi

for _ in $(seq 1 90); do
  if curl -fsS --max-time 5 http://127.0.0.1:5000/health > /tmp/osworld-health.json; then
    if python3 - "${OSWORLD_CONTENT_SHA256}" /tmp/osworld-health.json <<'PY'
import json
import sys

expected, path = sys.argv[1:]
with open(path, encoding="utf-8") as source:
    payload = json.load(source)
raise SystemExit(0 if payload.get("status") == "ok" and payload.get("content_sha256") == expected else 1)
PY
    then
      break
    fi
  fi
  sleep 2
done

curl -fsS --max-time 5 http://127.0.0.1:5000/health > /tmp/osworld-health.json
python3 - "${OSWORLD_CONTENT_SHA256}" /tmp/osworld-health.json <<'PY'
import json
import sys

expected, path = sys.argv[1:]
with open(path, encoding="utf-8") as source:
    payload = json.load(source)
if payload.get("status") != "ok" or payload.get("content_sha256") != expected:
    raise SystemExit(f"Unexpected OSWorld health response: {payload}")
PY
curl -fsS --max-time 15 http://127.0.0.1:5000/screenshot -o /tmp/osworld-bootstrap.png
test -s /tmp/osworld-bootstrap.png

python3 - "${OSWORLD_BUNDLE_VERSION}" "${OSWORLD_CONTENT_SHA256}" "${OSWORLD_INSTALL_PROFILE}" "${OSWORLD_SERVER_DIR}" <<'PY'
import json
import sys

version, content_sha256, profile, server_dir = sys.argv[1:]
print(json.dumps({
    "event": "ubuntu_osworld_bootstrap_ready",
    "status": "ready",
    "version": version,
    "content_sha256": content_sha256,
    "install_profile": profile,
    "server_dir": server_dir,
    "health_url": "http://127.0.0.1:5000/health",
}))
PY
