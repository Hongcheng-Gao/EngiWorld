#!/usr/bin/env bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi

set -euo pipefail

# Prevent macOS tar from emitting AppleDouble files and LIBARCHIVE xattrs.
export COPYFILE_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUT_DIR="${OUT_DIR:-${REPO_ROOT}/dist}"
MASTER_VERSION_FILE="${MASTER_VERSION_FILE:-${REPO_ROOT}/deploy/master/version.txt}"
MASTER_VERSION="${MASTER_VERSION:-$(tr -d '[:space:]' < "${MASTER_VERSION_FILE}")}"
BUNDLE_VERSION="${BUNDLE_VERSION:-v${MASTER_VERSION}-$(date +%Y%m%d-%H%M%S)}"
BUNDLE_NAME="${BUNDLE_NAME:-engiworld-master-source-${BUNDLE_VERSION}}"
INCLUDE_TASKS="${INCLUDE_TASKS:-0}"

BUILD_DIR="$(mktemp -d)"
STAGE_DIR="${BUILD_DIR}/${BUNDLE_NAME}"

cleanup() {
  rm -rf "${BUILD_DIR}"
}
trap cleanup EXIT

copy_path() {
  local rel_path="$1"
  if [[ ! -e "${REPO_ROOT}/${rel_path}" ]]; then
    return
  fi

  tar \
    --no-xattrs \
    --exclude ".git" \
    --exclude "*/.git" \
    --exclude "*/__pycache__" \
    --exclude "*/.pytest_cache" \
    --exclude "*/.mypy_cache" \
    --exclude "*/.ruff_cache" \
    --exclude "*/.DS_Store" \
    --exclude "._*" \
    --exclude "*/._*" \
    --exclude "__MACOSX" \
    --exclude "*/__MACOSX" \
    -C "${REPO_ROOT}" \
    -cf - "${rel_path}" | tar --no-xattrs -C "${STAGE_DIR}" -xf -
}

if [[ ! -d "${REPO_ROOT}/engine" ]]; then
  echo "engine not found. Restore the EngiWorld engine directory." >&2
  exit 1
fi

mkdir -p "${STAGE_DIR}" "${OUT_DIR}"

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
copy_path "engine"
copy_path "third_party/OSWorld-V2"

if [[ "${INCLUDE_TASKS}" == "1" || "${INCLUDE_TASKS}" == "true" ]]; then
  copy_path "task"
  TASKS_INCLUDED=true
else
  TASKS_INCLUDED=false
fi

# The repository may be checked out with core.autocrlf=true on Windows. Ensure
# every shell entrypoint in the Linux deployment bundle uses LF line endings.
while IFS= read -r -d '' shell_file; do
  sed -i.bak 's/\r$//' "${shell_file}"
  rm -f "${shell_file}.bak"
done < <(find "${STAGE_DIR}" -type f -name "*.sh" -print0)

cat > "${STAGE_DIR}/BUILD_INFO" <<EOF
bundle_name=${BUNDLE_NAME}
bundle_type=source-online-deps
master_version=${MASTER_VERSION}
master_version_file=deploy/master/version.txt
created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
includes_engine=engine
includes_osworld_v2=third_party/OSWorld-V2
includes_tasks=${TASKS_INCLUDED}
dependency_install=online
EOF

chmod +x "${STAGE_DIR}/deploy/master/install_master_bundle.sh"
chmod +x "${STAGE_DIR}/deploy/master/install_master_source_bundle.sh"
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
echo "Created master source bundle:"
echo "  ${ARCHIVE_PATH}"
echo
echo "Deploy on ECS:"
echo "  tar -xzf $(basename "${ARCHIVE_PATH}")"
echo "  cd ${BUNDLE_NAME}"
echo "  bash deploy/master/install_master_source_bundle.sh"
if [[ "${TASKS_INCLUDED}" == "false" ]]; then
  echo
  echo "Tasks are not included. Pass the task bundle object key when starting master:"
echo "  bash deploy/master/run_master.sh start --task-file-path tasks/run.tgz --task-root task --agent gemini-3.7-flash-high --num-vms 128 --follow"
  echo "If you still need an embedded task/ directory, rebuild with:"
  echo "  INCLUDE_TASKS=1 bash scripts/build_master_source_bundle.sh"
fi
