#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_DIR="${VENV_DIR:-${BUNDLE_ROOT}/.venv-worker}"
PYTHON_BIN="${VENV_DIR}/bin/python"
if [[ ! -x "${PYTHON_BIN}" && -x "${VENV_DIR}/bin/arena-python" ]]; then
  PYTHON_BIN="${VENV_DIR}/bin/arena-python"
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Worker install dir is not ready: ${VENV_DIR}" >&2
  echo "Run:" >&2
  echo "  bash deploy/worker/install_worker_bundle.sh" >&2
  exit 1
fi

export ENGIWORLD_ENGINE_PATH="${ENGIWORLD_ENGINE_PATH:-${OSWORLD_PATH:-${BUNDLE_ROOT}/engine}}"
export OSWORLD_V2_PATH="${OSWORLD_V2_PATH:-${BUNDLE_ROOT}/third_party/OSWorld-V2}"
export TASK_ROOT="${TASK_ROOT:-${BUNDLE_ROOT}/task}"

default_worker_id() {
  local candidate
  for candidate in $(hostname -I 2>/dev/null); do
    if [[ "${candidate}" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] && \
       [[ "${candidate}" != 127.* ]]; then
      printf 'ip-%s\n' "${candidate//./-}"
      return
    fi
  done
  hostname
}

if [[ $# -eq 0 ]]; then
  BASE_WORKER_ID="${WORKER_ID:-$(default_worker_id)}"
  set -- \
    --worker-id "${BASE_WORKER_ID}" \
    --engine-path "${ENGIWORLD_ENGINE_PATH}" \
    --osworld-v2-path "${OSWORLD_V2_PATH}" \
    --task-root "${TASK_ROOT}" \
    --local-concurrency "${LOCAL_CONCURRENCY:-1}" \
    --agent-factory "${AGENT_FACTORY:-engiworld.agents.openai_compatible:create_agent}" \
    --model "${MODEL:-openai-compatible}" \
    --action-space "${ACTION_SPACE:-pyautogui}" \
    --observation-type "${OBSERVATION_TYPE:-screenshot}" \
    --gui-max-steps "${GUI_MAX_STEPS:-200}" \
    --cli-max-steps "${CLI_MAX_STEPS:-100}" \
    --gui-multi-max-steps "${GUI_MULTI_MAX_STEPS:-300}" \
    --cli-multi-max-steps "${CLI_MULTI_MAX_STEPS:-150}" \
    --open-ended-max-steps "${OPEN_ENDED_MAX_STEPS:-${TOP10_MAX_STEPS:-150}}" \
    --history-turns "${HISTORY_TURNS:-15}" \
    --sleep-after-execution "${SLEEP_AFTER_EXECUTION:-2.0}" \
    --screen-width "${SCREEN_WIDTH:-1920}" \
    --screen-height "${SCREEN_HEIGHT:-1080}" \
    --task-lease-ttl-seconds "${TASK_LEASE_TTL_SECONDS:-1800}" \
    --instance-lease-ttl-seconds "${INSTANCE_LEASE_TTL_SECONDS:-2100}" \
    --poll-interval-seconds "${POLL_INTERVAL_SECONDS:-5}" \
    --idle-exit-rounds "${WORKER_IDLE_EXIT_ROUNDS:-0}" \
    --s3-bucket "${VOLCENGINE_S3_BUCKET:-agent-eval-results}" \
    --headless
fi

cd "${BUNDLE_ROOT}"
exec "${PYTHON_BIN}" -m engiworld.scheduler.worker "$@"
