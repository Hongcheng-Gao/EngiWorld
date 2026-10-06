#!/usr/bin/env bash
if [[ -z "${BASH_VERSION:-}" ]]; then
  exec bash "$0" "$@"
fi

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_DIR="${VENV_DIR:-${BUNDLE_ROOT}/.venv-image-updater}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
TARGET_SITE_PACKAGES="${VENV_DIR}/site-packages"
FALLBACK_PYTHON="${VENV_DIR}/bin/python"

cd "${BUNDLE_ROOT}"

if [[ ! -f "${BUNDLE_ROOT}/pyproject.toml" || ! -d "${BUNDLE_ROOT}/src" ]]; then
  echo "arena-osworld source bundle is incomplete: ${BUNDLE_ROOT}" >&2
  exit 1
fi

echo "Installing custom-image updater dependencies into ${VENV_DIR}"

if [[ -x "${VENV_DIR}/bin/python" ]] \
  && "${VENV_DIR}/bin/python" -m pip --version >/dev/null 2>&1; then
  INSTALL_PYTHON="${VENV_DIR}/bin/python"
  echo "Reusing existing Python environment."
  "${INSTALL_PYTHON}" -m pip install --upgrade pip setuptools wheel
  "${INSTALL_PYTHON}" -m pip install --no-build-isolation .
elif "${PYTHON_BIN}" -m venv "${VENV_DIR}"; then
  INSTALL_PYTHON="${VENV_DIR}/bin/python"
  "${INSTALL_PYTHON}" -m pip install --upgrade pip setuptools wheel
  "${INSTALL_PYTHON}" -m pip install --no-build-isolation .
else
  echo "python venv is unavailable; falling back to pip --target." >&2
  if ! "${PYTHON_BIN}" -m pip --version >/dev/null 2>&1; then
    echo "pip is unavailable for ${PYTHON_BIN}. Install python3-pip or set PYTHON_BIN." >&2
    exit 1
  fi

  mkdir -p "${VENV_DIR}/bin" "${TARGET_SITE_PACKAGES}"
  for python_entry in "${VENV_DIR}/bin"/python*; do
    if [[ -e "${python_entry}" || -L "${python_entry}" ]]; then
      rm -f "${python_entry}"
    fi
  done
  rm -f "${VENV_DIR}/pyvenv.cfg"

  PIP_ROOT_USER_ACTION=ignore "${PYTHON_BIN}" -m pip install \
    --target "${TARGET_SITE_PACKAGES}" \
    .
  printf '%s\n' \
    '#!/usr/bin/env bash' \
    "export PYTHONPATH=\"${TARGET_SITE_PACKAGES}\${PYTHONPATH:+:\${PYTHONPATH}}\"" \
    "exec \"${PYTHON_BIN}\" \"\$@\"" \
    > "${FALLBACK_PYTHON}"
  chmod +x "${FALLBACK_PYTHON}"
  INSTALL_PYTHON="${FALLBACK_PYTHON}"
fi

"${INSTALL_PYTHON}" - <<'PY'
from pathlib import Path

from volcenginesdkecs.api import ECSApi

from engiworld.scheduler.volcengine_ecs import VolcengineEcsClient

required_sdk_methods = (
    "create_image",
    "delete_images",
    "describe_cloud_assistant_status",
    "describe_images",
    "describe_invocation_results",
    "install_cloud_assistant",
    "modify_image_attribute",
    "reboot_instances",
    "run_command",
    "run_instances",
    "stop_instances",
)
missing = [name for name in required_sdk_methods if not hasattr(ECSApi, name)]
if missing:
    raise SystemExit("Volcengine ECS SDK is missing APIs: " + ", ".join(missing))

assert hasattr(VolcengineEcsClient, "install_cloud_assistant")
assert Path("deploy/image-builder/bootstrap_ubuntu_osworld.sh").is_file()
assert Path("deploy/vm-updater/osworld_updater.py").is_file()
assert Path("scripts/build_volcengine_ubuntu_osworld_image.py").is_file()
assert Path("scripts/upgrade_volcengine_custom_images_with_updater.py").is_file()
print("Custom-image updater dependencies are ready.")
PY

echo
echo "Preview all managed custom images with:"
echo "  bash deploy/image-updater/run_upgrade.sh"
