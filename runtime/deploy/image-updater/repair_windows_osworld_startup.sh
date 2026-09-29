#!/usr/bin/env bash
if [[ -z "${BASH_VERSION:-}" ]]; then
  exec bash "$0" "$@"
fi

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_ID=""
EXTRA_ARGS=()

usage() {
  cat <<'EOF'
Usage:
  bash deploy/image-updater/repair_windows_osworld_startup.sh \
    --image-id image-xxxxxxxx [upgrade options]

The replacement image is promoted to the source image name. The old image is
retained by default for rollback. Add --dry-run to inspect the plan first, or
--delete-replaced-images to delete the old image after successful promotion.
Add --pause-before-capture when GUI-only setup, such as accepting an application
license agreement as the evaluation user, must be completed before capture. This
mode always creates a fresh replacement even when updater tags already match.
EOF
}

while (( $# > 0 )); do
  case "$1" in
    --image-id)
      if (( $# < 2 )) || [[ -z "$2" ]]; then
        echo "--image-id requires a value" >&2
        exit 2
      fi
      if [[ -n "${IMAGE_ID}" ]]; then
        echo "Only one --image-id may be specified" >&2
        exit 2
      fi
      IMAGE_ID="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -z "${IMAGE_ID}" ]]; then
  usage >&2
  exit 2
fi

exec bash "${SCRIPT_DIR}/run_upgrade.sh" \
  --image-id "${IMAGE_ID}" \
  --project-name "${VOLCENGINE_PROJECT_NAME:-agent-eval}" \
  --bootstrap-transport execute \
  --promote \
  "${EXTRA_ARGS[@]}"
