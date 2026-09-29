#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_DIR="${VENV_DIR:-${BUNDLE_ROOT}/.venv-master}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
TARGET_SITE_PACKAGES="${VENV_DIR}/site-packages"
FALLBACK_PYTHON="${VENV_DIR}/bin/python"

cd "${BUNDLE_ROOT}"

echo "Using source bundle: ${BUNDLE_ROOT}"
echo "Using install dir: ${VENV_DIR}"

if [[ ! -d "${BUNDLE_ROOT}/src" || ! -f "${BUNDLE_ROOT}/pyproject.toml" ]]; then
  echo "source bundle is incomplete: ${BUNDLE_ROOT}" >&2
  exit 1
fi

if [[ ! -d "${BUNDLE_ROOT}/engine" ]]; then
  echo "EngiWorld engine directory not found: ${BUNDLE_ROOT}/engine" >&2
  exit 1
fi

if [[ "${INSTALL_OSWORLD_V2:-false}" == "true" && ! -d "${BUNDLE_ROOT}/third_party/OSWorld-V2" ]]; then
  echo "OSWorld V2 directory not found: ${BUNDLE_ROOT}/third_party/OSWorld-V2" >&2
  exit 1
fi

if "${PYTHON_BIN}" -m venv "${VENV_DIR}"; then
  INSTALL_PYTHON="${VENV_DIR}/bin/python"
  "${INSTALL_PYTHON}" -m pip install --upgrade pip setuptools wheel
  "${INSTALL_PYTHON}" -m pip install --no-build-isolation .
else
  echo
  echo "python venv is unavailable. Falling back to pip --target installation." >&2
  echo "On Ubuntu this usually means python3-venv is missing; if apt is available, install:" >&2
  echo "  sudo apt-get update && sudo apt-get install -y python3-venv python3-pip" >&2
  echo

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

  PIP_ROOT_USER_ACTION=ignore "${PYTHON_BIN}" -m pip install --target "${TARGET_SITE_PACKAGES}" .
  cat > "${FALLBACK_PYTHON}" <<EOF
#!/usr/bin/env bash
export PYTHONPATH="${TARGET_SITE_PACKAGES}\${PYTHONPATH:+:\${PYTHONPATH}}"
exec "${PYTHON_BIN}" "\$@"
EOF
  chmod +x "${FALLBACK_PYTHON}"
  INSTALL_PYTHON="${FALLBACK_PYTHON}"
fi

if [[ "${INSTALL_OSWORLD_V2:-false}" == "true" ]]; then
  "${INSTALL_PYTHON}" -m pip install -e "${BUNDLE_ROOT}/third_party/OSWorld-V2"
fi

"${INSTALL_PYTHON}" - <<'PY'
from pathlib import Path

import boto3
from volcenginesdkecs.api import ECSApi

from engiworld.scheduler.master import build_parser
from engiworld.scheduler.volcengine_ecs import VolcengineLaunchConfig

assert build_parser()
assert boto3
assert hasattr(ECSApi, "run_command")
assert hasattr(ECSApi, "describe_cloud_assistant_status")
assert hasattr(ECSApi, "describe_invocation_results")
assert VolcengineLaunchConfig
assert Path("engine").is_dir()
print("engiworld master source bundle is installed.")
PY

echo
echo "Run with:"
echo "  bash deploy/master/run_master.sh start --task-file-path tasks/run.tgz --task-root task --agent gemini-3.7-flash-high --num-vms 128 --follow"
