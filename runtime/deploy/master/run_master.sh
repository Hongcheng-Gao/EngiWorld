#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_DIR="${VENV_DIR:-${BUNDLE_ROOT}/.venv-master}"
PYTHON_BIN="${VENV_DIR}/bin/python"
if [[ ! -x "${PYTHON_BIN}" && -x "${VENV_DIR}/bin/arena-python" ]]; then
  PYTHON_BIN="${VENV_DIR}/bin/arena-python"
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Master install dir is not ready: ${VENV_DIR}" >&2
  echo "Run one of:" >&2
  echo "  bash deploy/master/install_master_source_bundle.sh" >&2
  echo "  bash deploy/master/install_master_bundle.sh" >&2
  exit 1
fi

cd "${BUNDLE_ROOT}"
exec "${PYTHON_BIN}" -m engiworld.scheduler.master "$@"
