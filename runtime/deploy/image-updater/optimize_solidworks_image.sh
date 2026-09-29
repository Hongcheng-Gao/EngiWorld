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
  bash deploy/image-updater/optimize_solidworks_image.sh \
    --image-id image-xxxxxxxx [upgrade options]

Creates and promotes a replacement SolidWorks Windows image. The process pauses
before capture so the evaluation user can accept the SolidWorks license and
finish first-run setup in the Volcengine VNC console. Type CAPTURE afterwards.

The old image is retained by default. Pass --delete-replaced-images only after
the replacement image has passed a task smoke test.
EOF
}

while (( $# > 0 )); do
  case "$1" in
    --image-id)
      if (( $# < 2 )) || [[ -z "$2" ]]; then
        echo "--image-id requires a value" >&2
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

if [[ -z "$IMAGE_ID" ]]; then
  usage >&2
  exit 2
fi

exec bash "${SCRIPT_DIR}/repair_windows_osworld_startup.sh" \
  --image-id "$IMAGE_ID" \
  --force-rebuild \
  --pause-before-capture \
  "${EXTRA_ARGS[@]}"
