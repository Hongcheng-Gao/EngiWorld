#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/run_engiworld_suite.sh plan gemini-retest
  bash scripts/run_engiworld_suite.sh start gemini-retest
  bash scripts/run_engiworld_suite.sh plan kimi-formal
  bash scripts/run_engiworld_suite.sh start kimi-formal

The script validates every group before start. It requires these variables, normally
loaded from ../.master.env:
  INIT_GUI_TASK_BUNDLE
  INIT_CLI_TASK_BUNDLE
  CLI_NO_INIT_TASK_BUNDLE
EOF
}

[[ $# -eq 2 ]] || { usage >&2; exit 2; }
COMMAND="$1"
SUITE="$2"
[[ "${COMMAND}" == "plan" || "${COMMAND}" == "start" ]] || {
  echo "Command must be plan or start" >&2
  exit 2
}
[[ "${SUITE}" == "gemini-retest" || "${SUITE}" == "kimi-formal" ]] || {
  echo "Suite must be gemini-retest or kimi-formal" >&2
  exit 2
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MASTER_ENV_FILE="${MASTER_ENV_FILE:-${BUNDLE_ROOT}/../.master.env}"
if [[ -f "${MASTER_ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${MASTER_ENV_FILE}"
fi

RUNNER="${BUNDLE_ROOT}/deploy/master/run_master.sh"
PYTHON_BIN="${BUNDLE_ROOT}/.venv-master/bin/python"
if [[ ! -x "${PYTHON_BIN}" && -x "${BUNDLE_ROOT}/.venv-master/bin/arena-python" ]]; then
  PYTHON_BIN="${BUNDLE_ROOT}/.venv-master/bin/arena-python"
fi
[[ -x "${RUNNER}" ]] || { echo "Master runner not found: ${RUNNER}" >&2; exit 2; }
[[ -x "${PYTHON_BIN}" ]] || { echo "Master Python not found: ${PYTHON_BIN}" >&2; exit 2; }

required_variables=(INIT_GUI_TASK_BUNDLE INIT_CLI_TASK_BUNDLE CLI_NO_INIT_TASK_BUNDLE)
for variable_name in "${required_variables[@]}"; do
  [[ -n "${!variable_name:-}" ]] || {
    echo "Required variable is not set: ${variable_name}" >&2
    exit 2
  }
done

if [[ "${SUITE}" == "gemini-retest" ]]; then
  MODEL_PROFILE="gemini-3.7-flash-high"
  SUITE_GROUPS=(
    gui-environment-solidworks
    gui-message-solidworks
    cli-readimg-top10
    cli-text-top10
  )
else
  MODEL_PROFILE="kimi-k3-max"
  SUITE_GROUPS=(
    init-gui-environment
    init-gui-message
    init-cli-environment-readimg
    init-cli-message-readimg
    init-cli-message
    cli-readimg-60
    cli-text-60
  )
fi

RUN_TAG="${RUN_TAG:-$(date +%Y%m%d-%H%M%S)}"
SUITE_STATE_DIR="${SUITE_STATE_DIR:-${BUNDLE_ROOT}/suite-runs/${SUITE}-${RUN_TAG}}"
mkdir -p "${SUITE_STATE_DIR}/plans" "${SUITE_STATE_DIR}/logs"

GROUP_EXPECTED_COUNT=0
GROUP_EVAL_MODE=""
GROUP_EXPERIMENT_PROFILE=""
GROUP_ARGS=()

configure_group() {
  local group="$1"
  case "${group}" in
    gui-environment-solidworks)
      GROUP_EXPECTED_COUNT=20
      GROUP_EVAL_MODE="gui"
      GROUP_EXPERIMENT_PROFILE="gui_main"
      GROUP_ARGS=(
        --task-file-path "${INIT_GUI_TASK_BUNDLE}"
        --task-root task
        --task-prefix init-image/environment/gui-solidworks/
      )
      ;;
    gui-message-solidworks)
      GROUP_EXPECTED_COUNT=20
      GROUP_EVAL_MODE="gui"
      GROUP_EXPERIMENT_PROFILE="gui_message_initial"
      GROUP_ARGS=(
        --task-file-path "${INIT_GUI_TASK_BUNDLE}"
        --task-root task
        --task-prefix init-image/messgae/gui-solidworks/
      )
      ;;
    cli-readimg-top10)
      GROUP_EXPECTED_COUNT=2
      GROUP_EVAL_MODE="cli"
      GROUP_EXPERIMENT_PROFILE="cli_main"
      GROUP_ARGS=(
        --task-file-path "${CLI_NO_INIT_TASK_BUNDLE}"
        --task-root task
        --task-id top-10-hardest/task-02
        --task-id top-10-hardest/task-09
      )
      ;;
    cli-text-top10)
      GROUP_EXPECTED_COUNT=2
      GROUP_EVAL_MODE="cli-text"
      GROUP_EXPERIMENT_PROFILE="cli_text"
      GROUP_ARGS=(
        --task-file-path "${CLI_NO_INIT_TASK_BUNDLE}"
        --task-root task
        --task-id top-10-hardest/task-02
        --task-id top-10-hardest/task-09
      )
      ;;
    init-gui-environment)
      GROUP_EXPECTED_COUNT=60
      GROUP_EVAL_MODE="gui"
      GROUP_EXPERIMENT_PROFILE="gui_main"
      GROUP_ARGS=(
        --task-file-path "${INIT_GUI_TASK_BUNDLE}"
        --task-root task
        --task-prefix init-image/environment/gui-
      )
      ;;
    init-gui-message)
      GROUP_EXPECTED_COUNT=60
      GROUP_EVAL_MODE="gui"
      GROUP_EXPERIMENT_PROFILE="gui_message_initial"
      GROUP_ARGS=(
        --task-file-path "${INIT_GUI_TASK_BUNDLE}"
        --task-root task
        --task-prefix init-image/messgae/gui-
      )
      ;;
    init-cli-environment-readimg)
      GROUP_EXPECTED_COUNT=60
      GROUP_EVAL_MODE="cli"
      GROUP_EXPERIMENT_PROFILE="cli_environment_initial"
      GROUP_ARGS=(
        --task-file-path "${INIT_CLI_TASK_BUNDLE}"
        --task-root task
        --task-prefix init-image/environment/cli-
      )
      ;;
    init-cli-message-readimg)
      GROUP_EXPECTED_COUNT=60
      GROUP_EVAL_MODE="cli"
      GROUP_EXPERIMENT_PROFILE="cli_message_initial"
      GROUP_ARGS=(
        --task-file-path "${INIT_CLI_TASK_BUNDLE}"
        --task-root task
        --task-prefix init-image/messgae/cli-
      )
      ;;
    init-cli-message)
      GROUP_EXPECTED_COUNT=60
      GROUP_EVAL_MODE="cli"
      GROUP_EXPERIMENT_PROFILE="cli_message_no_readimg"
      GROUP_ARGS=(
        --task-file-path "${INIT_CLI_TASK_BUNDLE}"
        --task-root task
        --task-prefix init-image/messgae/cli-
      )
      ;;
    cli-readimg-60)
      GROUP_EXPECTED_COUNT=60
      GROUP_EVAL_MODE="cli"
      GROUP_EXPERIMENT_PROFILE="cli_main"
      GROUP_ARGS=(
        --task-file-path "${CLI_NO_INIT_TASK_BUNDLE}"
        --task-root task
        --task-id-file experiment-sets/cli-no-init-60.ids
      )
      ;;
    cli-text-60)
      GROUP_EXPECTED_COUNT=60
      GROUP_EVAL_MODE="cli-text"
      GROUP_EXPERIMENT_PROFILE="cli_text"
      GROUP_ARGS=(
        --task-file-path "${CLI_NO_INIT_TASK_BUNDLE}"
        --task-root task
        --task-id-file experiment-sets/cli-no-init-60.ids
      )
      ;;
    *)
      echo "Unknown suite group: ${group}" >&2
      exit 2
      ;;
  esac

  GROUP_ARGS+=(
    --agent "${MODEL_PROFILE}"
    --num-vms "${GROUP_EXPECTED_COUNT}"
    --eval-mode "${GROUP_EVAL_MODE}"
    --experiment-profile "${GROUP_EXPERIMENT_PROFILE}"
  )
}

validate_plan() {
  local plan_path="$1"
  "${PYTHON_BIN}" - \
    "${plan_path}" \
    "${GROUP_EXPECTED_COUNT}" \
    "${MODEL_PROFILE}" \
    "${GROUP_EVAL_MODE}" \
    "${GROUP_EXPERIMENT_PROFILE}" <<'PY'
import json
import sys

plan_path, expected_count, profile, eval_mode, experiment_profile = sys.argv[1:]
with open(plan_path, "r", encoding="utf-8") as file:
    plan = json.load(file)

agent = plan.get("agent") or {}
expected = {
    "task_count": int(expected_count),
    "requested_instance_count": int(expected_count),
    "agent.profile": profile,
    "agent.eval_mode": eval_mode,
    "agent.experiment_profile": experiment_profile,
    "agent.max_steps": 200,
    "agent.gui_max_steps": 200,
    "agent.cli_max_steps": 100,
    "agent.gui_multi_max_steps": 300,
    "agent.cli_multi_max_steps": 150,
    "agent.top10_max_steps": 150,
    "agent.history_turns": 15,
    "agent.bash_timeout": 120,
    "agent.screen_width": 1920,
    "agent.screen_height": 1080,
}
actual = {
    "task_count": plan.get("task_count"),
    "requested_instance_count": plan.get("requested_instance_count"),
    **{f"agent.{key}": agent.get(key) for key in (
        "profile",
        "eval_mode",
        "experiment_profile",
        "max_steps",
        "gui_max_steps",
        "cli_max_steps",
        "gui_multi_max_steps",
        "cli_multi_max_steps",
        "top10_max_steps",
        "history_turns",
        "bash_timeout",
        "screen_width",
        "screen_height",
    )},
}
errors = [
    f"{key}: expected {value!r}, got {actual.get(key)!r}"
    for key, value in expected.items()
    if actual.get(key) != value
]
token_values = {
    key: value
    for key, value in (agent.get("env") or {}).items()
    if key.endswith("_MAX_TOKENS") or key.endswith("_MAX_MAX_TOKENS")
}
if list(token_values.values()) != ["16384"]:
    errors.append(f"agent output-token setting: expected one 16384 value, got {token_values!r}")
if errors:
    raise SystemExit("Plan validation failed:\n  " + "\n  ".join(errors))
print(
    f"validated tasks={plan['task_count']} profile={profile} "
    f"mode={eval_mode} experiment={experiment_profile}"
)
PY
}

echo "suite=${SUITE} command=${COMMAND} model_profile=${MODEL_PROFILE} run_tag=${RUN_TAG}"
echo "state_dir=${SUITE_STATE_DIR}"

for group in "${SUITE_GROUPS[@]}"; do
  configure_group "${group}"
  plan_path="${SUITE_STATE_DIR}/plans/${group}.json"
  plan_run_id="plan-${SUITE}-${group}-${RUN_TAG}"
  echo "[plan] ${group}"
  (
    cd "${BUNDLE_ROOT}"
    bash "${RUNNER}" plan --run-id "${plan_run_id}" "${GROUP_ARGS[@]}"
  ) > "${plan_path}"
  validate_plan "${plan_path}"
done

if [[ "${COMMAND}" == "plan" ]]; then
  echo "suite_plan_valid=true groups=${#SUITE_GROUPS[@]}"
  exit 0
fi

manifest_path="${SUITE_STATE_DIR}/runs.tsv"
: > "${manifest_path}"
for group in "${SUITE_GROUPS[@]}"; do
  configure_group "${group}"
  run_id="exp-${SUITE}-${group}-${MODEL_PROFILE}-${RUN_TAG}"
  log_path="${SUITE_STATE_DIR}/logs/${group}.log"
  echo "[start] ${group} run_id=${run_id} log=${log_path}"
  (
    cd "${BUNDLE_ROOT}"
    nohup bash "${RUNNER}" start \
      --run-id "${run_id}" \
      "${GROUP_ARGS[@]}" \
      --follow > "${log_path}" 2>&1 < /dev/null &
    printf '%s\t%s\t%s\t%s\n' "${group}" "${run_id}" "$!" "${log_path}" >> "${manifest_path}"
  )
done

echo "suite_started=true groups=${#SUITE_GROUPS[@]} manifest=${manifest_path}"
