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
  echo "Updater environment not found. Run deploy/image-updater/install_dependencies.sh first." >&2
  exit 1
fi

cd "${BUNDLE_ROOT}"
export PYTHONPATH="${BUNDLE_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

if (( $# > 0 )); then
  exec "${PYTHON_BIN}" scripts/upgrade_volcengine_custom_images_with_updater.py "$@"
fi

PROJECT_NAME="${VOLCENGINE_PROJECT_NAME:-agent-eval}"
ARGS=(
  --all-managed-images
  --project-name "${PROJECT_NAME}"
  --continue-on-error
)

if [[ "${IMAGE_UPDATER_APPLY:-false}" != "true" ]]; then
  ARGS+=(--dry-run)
fi
if [[ "${IMAGE_UPDATER_PROMOTE:-false}" == "true" ]]; then
  ARGS+=(--promote)
fi
if [[ "${IMAGE_UPDATER_DELETE_REPLACED_IMAGES:-false}" == "true" ]]; then
  ARGS+=(--promote --delete-replaced-images)
fi
if [[ "${IMAGE_UPDATER_DELETE_BOUND_SNAPSHOTS:-false}" == "true" ]]; then
  ARGS+=(--promote --delete-replaced-images --delete-bound-snapshots)
fi
if [[ "${IMAGE_UPDATER_CLEANUP_ON_ERROR:-false}" == "true" ]]; then
  ARGS+=(--cleanup-on-error)
fi

exec "${PYTHON_BIN}" scripts/upgrade_volcengine_custom_images_with_updater.py "${ARGS[@]}"
