#!/usr/bin/env bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi

set -euo pipefail

# Prevent macOS tar from emitting AppleDouble files and LIBARCHIVE xattrs.
export COPYFILE_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_PYTHON_BIN="$(
  command -v python3.12 \
    || command -v python3.11 \
    || command -v python3
)"
PYTHON_BIN="${PYTHON_BIN:-${DEFAULT_PYTHON_BIN}}"
OUT_DIR="${OUT_DIR:-${REPO_ROOT}/dist}"
MASTER_VERSION_FILE="${MASTER_VERSION_FILE:-${REPO_ROOT}/deploy/master/version.txt}"
MASTER_VERSION="${MASTER_VERSION:-$(tr -d '[:space:]' < "${MASTER_VERSION_FILE}")}"
BUNDLE_VERSION="${BUNDLE_VERSION:-v${MASTER_VERSION}-$(date +%Y%m%d-%H%M%S)}"
BUNDLE_NAME="${BUNDLE_NAME:-engiworld-master-${BUNDLE_VERSION}}"
INCLUDE_TASKS="${INCLUDE_TASKS:-0}"
TARGET_PLATFORM="${TARGET_PLATFORM:-manylinux2014_x86_64}"
TARGET_PYTHON_VERSION="${TARGET_PYTHON_VERSION:-3.12}"
TARGET_IMPLEMENTATION="${TARGET_IMPLEMENTATION:-cp}"
TARGET_ABI="${TARGET_ABI:-cp312}"
SOURCE_WHEEL_CC="${SOURCE_WHEEL_CC:-/bin/false}"
SOURCE_WHEEL_CXX="${SOURCE_WHEEL_CXX:-/bin/false}"

BUILD_DIR="$(mktemp -d)"
STAGE_DIR="${BUILD_DIR}/${BUNDLE_NAME}"
WHEELHOUSE_DIR="${STAGE_DIR}/wheelhouse"
REQUIREMENTS_FILE="${BUILD_DIR}/requirements.master.txt"
SOURCE_WHEEL_REQUIREMENTS_FILE="${BUILD_DIR}/requirements.master-source-wheels.txt"

cleanup() {
  rm -rf "${BUILD_DIR}"
}
trap cleanup EXIT

copy_path() {
  local rel_path="$1"
  if [[ ! -e "${REPO_ROOT}/${rel_path}" ]]; then
    return
  fi
  mkdir -p "${STAGE_DIR}/$(dirname "${rel_path}")"
  cp -R "${REPO_ROOT}/${rel_path}" "${STAGE_DIR}/${rel_path}"
}

mkdir -p "${STAGE_DIR}" "${WHEELHOUSE_DIR}" "${OUT_DIR}"

copy_path "pyproject.toml"
copy_path "README.md"
copy_path "src"
copy_path "configs"
copy_path "experiment-sets"
copy_path "deploy/master"
copy_path "deploy/image-updater"
copy_path "deploy/image-builder"
copy_path "deploy/vm-updater"
copy_path "scripts/build_volcengine_ubuntu_osworld_image.py"
copy_path "scripts/upgrade_volcengine_custom_images_with_updater.py"
copy_path "scripts/deploy_worker_source_bundle.sh"
copy_path "scripts/deploy_worker_env.sh"
copy_path "scripts/build_runtime_api_config.py"
copy_path "scripts/run_remote_ecs_command.sh"
copy_path "scripts/check_vm_osworld_health.py"
copy_path "scripts/run_engiworld_suite.sh"

if [[ "${INCLUDE_TASKS}" == "1" || "${INCLUDE_TASKS}" == "true" ]]; then
  copy_path "task"
  TASKS_INCLUDED=true
else
  TASKS_INCLUDED=false
fi

"${PYTHON_BIN}" - <<PY > "${REQUIREMENTS_FILE}"
from pathlib import Path
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError as exc:
        raise SystemExit("Python 3.11+ or the tomli package is required to parse pyproject.toml") from exc

pyproject = tomllib.loads(Path("${REPO_ROOT}/pyproject.toml").read_text())
dependencies = pyproject.get("project", {}).get("dependencies")
if not dependencies:
    raise SystemExit("Could not find [project].dependencies in pyproject.toml")

for requirement in dependencies:
    print(requirement)
PY
cp "${REQUIREMENTS_FILE}" "${STAGE_DIR}/requirements.master.txt"

if [[ -n "${MASTER_SOURCE_WHEEL_REQUIREMENTS:-}" ]]; then
  printf "%s\n" "${MASTER_SOURCE_WHEEL_REQUIREMENTS}" > "${SOURCE_WHEEL_REQUIREMENTS_FILE}"
else
  : > "${SOURCE_WHEEL_REQUIREMENTS_FILE}"
fi
cp "${SOURCE_WHEEL_REQUIREMENTS_FILE}" "${STAGE_DIR}/requirements.master-source-wheels.txt"

echo "Building engiworld master wheel..."
PROJECT_WHEEL_ARGS=()
if "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1
import setuptools.build_meta
PY
then
  PROJECT_WHEEL_ARGS+=(--no-build-isolation)
fi
"${PYTHON_BIN}" -m pip wheel \
  "${PROJECT_WHEEL_ARGS[@]}" \
  --no-deps \
  --wheel-dir "${WHEELHOUSE_DIR}" \
  "${REPO_ROOT}"

if [[ -s "${SOURCE_WHEEL_REQUIREMENTS_FILE}" ]]; then
  echo "Building source-only pure Python wheels..."
  while IFS= read -r requirement; do
    requirement="${requirement%%#*}"
    requirement="$(echo "${requirement}" | xargs)"
    if [[ -z "${requirement}" ]]; then
      continue
    fi
    echo "  ${requirement}"
    CC="${SOURCE_WHEEL_CC}" CXX="${SOURCE_WHEEL_CXX}" \
      "${PYTHON_BIN}" -m pip wheel \
        --no-cache-dir \
        --no-deps \
        --no-binary=:all: \
        --wheel-dir "${WHEELHOUSE_DIR}" \
        "${requirement}"
  done < "${SOURCE_WHEEL_REQUIREMENTS_FILE}"

  "${PYTHON_BIN}" - <<PY
from pathlib import Path

wheelhouse = Path("${WHEELHOUSE_DIR}")
bad_wheels = sorted(
    wheel.name
    for wheel in wheelhouse.glob("*.whl")
    if not wheel.name.endswith("-none-any.whl")
)
if bad_wheels:
    raise SystemExit(
        "Source wheel prebuild produced platform-specific wheel(s): "
        + ", ".join(bad_wheels)
    )
PY
fi

echo "Downloading dependency wheels for ${TARGET_PLATFORM}, Python ${TARGET_PYTHON_VERSION}..."
"${PYTHON_BIN}" -m pip download \
  --dest "${WHEELHOUSE_DIR}" \
  --find-links "${WHEELHOUSE_DIR}" \
  --only-binary=:all: \
  --platform "${TARGET_PLATFORM}" \
  --python-version "${TARGET_PYTHON_VERSION}" \
  --implementation "${TARGET_IMPLEMENTATION}" \
  --abi "${TARGET_ABI}" \
  -r "${REQUIREMENTS_FILE}"

cat > "${STAGE_DIR}/BUILD_INFO" <<EOF
bundle_name=${BUNDLE_NAME}
master_version=${MASTER_VERSION}
master_version_file=deploy/master/version.txt
created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
target_platform=${TARGET_PLATFORM}
target_python_version=${TARGET_PYTHON_VERSION}
target_implementation=${TARGET_IMPLEMENTATION}
target_abi=${TARGET_ABI}
includes_tasks=${TASKS_INCLUDED}
source_wheel_cc=${SOURCE_WHEEL_CC}
source_wheel_cxx=${SOURCE_WHEEL_CXX}
EOF

chmod +x "${STAGE_DIR}/deploy/master/install_master_bundle.sh"
chmod +x "${STAGE_DIR}/deploy/master/run_master.sh"
chmod +x "${STAGE_DIR}/deploy/image-updater/install_dependencies.sh"
chmod +x "${STAGE_DIR}/deploy/image-updater/run_upgrade.sh"
chmod +x "${STAGE_DIR}/deploy/image-updater/repair_windows_osworld_startup.sh"
chmod +x "${STAGE_DIR}/deploy/image-builder/bootstrap_ubuntu_osworld.sh"
chmod +x "${STAGE_DIR}/deploy/image-builder/run_build_ubuntu_image.sh"
chmod +x "${STAGE_DIR}/deploy/vm-updater/install_linux.sh"
chmod +x "${STAGE_DIR}/deploy/vm-updater/osworld_updater.py"
chmod +x "${STAGE_DIR}/scripts/build_volcengine_ubuntu_osworld_image.py"
chmod +x "${STAGE_DIR}/scripts/upgrade_volcengine_custom_images_with_updater.py"
chmod +x "${STAGE_DIR}/scripts/deploy_worker_source_bundle.sh"
chmod +x "${STAGE_DIR}/scripts/deploy_worker_env.sh"
chmod +x "${STAGE_DIR}/scripts/build_runtime_api_config.py"
chmod +x "${STAGE_DIR}/scripts/run_remote_ecs_command.sh"
chmod +x "${STAGE_DIR}/scripts/check_vm_osworld_health.py"
chmod +x "${STAGE_DIR}/scripts/run_engiworld_suite.sh"

ARCHIVE_PATH="${OUT_DIR}/${BUNDLE_NAME}.tgz"
tar \
  --no-xattrs \
  --exclude "._*" \
  --exclude "*/._*" \
  --exclude "__MACOSX" \
  --exclude "*/__MACOSX" \
  -czf "${ARCHIVE_PATH}" -C "${BUILD_DIR}" "${BUNDLE_NAME}"

echo
echo "Created master bundle:"
echo "  ${ARCHIVE_PATH}"
echo "  tasks included: ${TASKS_INCLUDED}"
echo
echo "Deploy on ECS:"
echo "  tar -xzf $(basename "${ARCHIVE_PATH}")"
echo "  cd ${BUNDLE_NAME}"
echo "  bash deploy/master/install_master_bundle.sh"
if [[ "${TASKS_INCLUDED}" == "false" ]]; then
  echo
  echo "Tasks are not included. Pass the task bundle object key when starting master:"
  echo "  bash deploy/master/run_master.sh start --task-file-path tasks/run.tgz --task-root task --agent gemini-3.7-flash-high --num-vms 128 --follow"
fi
