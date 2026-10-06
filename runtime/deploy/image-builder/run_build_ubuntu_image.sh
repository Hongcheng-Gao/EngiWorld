#!/usr/bin/env bash
if [[ -z "${BASH_VERSION:-}" ]]; then
  exec bash "$0" "$@"
fi

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_DIR="${VENV_DIR:-${BUNDLE_ROOT}/.venv-image-updater}"

if [[ -x "${VENV_DIR}/bin/python" ]]; then
  PYTHON_BIN="${PYTHON_BIN:-${VENV_DIR}/bin/python}"
elif [[ -x "${BUNDLE_ROOT}/.venv-master/bin/python" ]]; then
  PYTHON_BIN="${PYTHON_BIN:-${BUNDLE_ROOT}/.venv-master/bin/python}"
else
  echo "Image builder environment not found. Run deploy/image-updater/install_dependencies.sh first." >&2
  exit 1
fi

cd "${BUNDLE_ROOT}"
export PYTHONPATH="${BUNDLE_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
exec "${PYTHON_BIN}" scripts/build_volcengine_ubuntu_osworld_image.py "$@"
