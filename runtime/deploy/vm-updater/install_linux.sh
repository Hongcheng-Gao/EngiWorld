#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${VM_OSWORLD_UPDATER_INSTALL_DIR:-/opt/arena-osworld-updater}"
CONFIG_PATH="${VM_OSWORLD_UPDATER_CONFIG:-/etc/arena-osworld-updater.json}"
CURRENT_DIR="${VM_OSWORLD_CURRENT_DIR:-/home/user/server}"
SERVICE_NAME="${VM_OSWORLD_SERVICE_NAME:-osworld_server.service}"
HEALTH_URL="${VM_OSWORLD_HEALTH_URL:-http://127.0.0.1:5000/health}"

sudo install -d -m 0755 "${INSTALL_DIR}"
sudo install -m 0755 "${SCRIPT_DIR}/osworld_updater.py" "${INSTALL_DIR}/osworld_updater.py"

TEMP_CONFIG="$(mktemp)"
cleanup() {
  rm -f "${TEMP_CONFIG}"
}
trap cleanup EXIT

python3 -c 'import json,sys; json.dump({"current_dir":sys.argv[1],"stop_command":["systemctl","stop",sys.argv[2]],"start_command":["systemctl","start",sys.argv[2]],"health_url":sys.argv[3],"health_timeout_seconds":90},open(sys.argv[4],"w"),indent=2)' "${CURRENT_DIR}" "${SERVICE_NAME}" "${HEALTH_URL}" "${TEMP_CONFIG}"
sudo install -m 0644 "${TEMP_CONFIG}" "${CONFIG_PATH}"

sudo tee "${INSTALL_DIR}/update-osworld" >/dev/null <<EOF
#!/usr/bin/env bash
exec python3 "${INSTALL_DIR}/osworld_updater.py" apply --config "${CONFIG_PATH}" "\$@"
EOF
sudo chmod 0755 "${INSTALL_DIR}/update-osworld"

echo "Installed OSWorld updater: ${INSTALL_DIR}/update-osworld"
echo "Updater config: ${CONFIG_PATH}"
