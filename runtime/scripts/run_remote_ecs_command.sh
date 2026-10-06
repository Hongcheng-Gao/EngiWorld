#!/usr/bin/env bash
# Run one shell command across a list of ECS hosts through SSH.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/run_remote_ecs_command.sh --ips IP[,IP...] --command 'COMMAND' [options]
  bash scripts/run_remote_ecs_command.sh --ip-file hosts.txt --command 'COMMAND' [options]

Options:
  --ips VALUE              Comma-separated private/public IP addresses.
  --ip-file PATH           One IP address per line; blank lines and # comments are ignored.
  --command VALUE          Command evaluated by bash -lc on every remote host.
  --user USER              SSH user. Default: root.
  --identity PATH          SSH private key passed to ssh -i.
  --password               Prompt once for a shared SSH password without echoing it.
  --port PORT              SSH port. Default: 22.
  --parallel N             Maximum concurrent SSH commands. Default: 4.
  --workdir PATH           Run COMMAND after changing to this remote directory.
  --log-dir PATH           Local directory for one log per host. Default: ./remote-exec-<timestamp>.
  --strict-host-key-checking MODE
                           SSH setting, default: accept-new.
  --dry-run                Print resolved hosts and commands without connecting.
  -h, --help               Show this help.

Examples:
  bash scripts/run_remote_ecs_command.sh \
    --ips 10.0.0.10,10.0.0.11 \
    --identity ~/.ssh/agent-eval.pem \
    --command 'hostname && systemctl status arena-worker --no-pager'

  bash scripts/run_remote_ecs_command.sh \
    --ips 10.0.0.10,10.0.0.11 --user root --password \
    --command 'hostname'

  bash scripts/run_remote_ecs_command.sh \
    --ip-file worker-ips.txt --user root --parallel 8 \
    --workdir /root/worker/arena-osworld-worker-source \
    --command 'nohup bash deploy/worker/run_worker.sh > worker.log 2>&1 &'
EOF
}

IPS_RAW=""
IP_FILE=""
REMOTE_COMMAND=""
SSH_USER="root"
SSH_IDENTITY=""
USE_PASSWORD=false
SSH_PORT="22"
PARALLEL="4"
REMOTE_WORKDIR=""
LOG_DIR=""
STRICT_HOST_KEY_CHECKING="accept-new"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ips) IPS_RAW="${2:?missing value for --ips}"; shift 2 ;;
    --ip-file) IP_FILE="${2:?missing value for --ip-file}"; shift 2 ;;
    --command) REMOTE_COMMAND="${2:?missing value for --command}"; shift 2 ;;
    --user) SSH_USER="${2:?missing value for --user}"; shift 2 ;;
    --identity) SSH_IDENTITY="${2:?missing value for --identity}"; shift 2 ;;
    --password) USE_PASSWORD=true; shift ;;
    --port) SSH_PORT="${2:?missing value for --port}"; shift 2 ;;
    --parallel) PARALLEL="${2:?missing value for --parallel}"; shift 2 ;;
    --workdir) REMOTE_WORKDIR="${2:?missing value for --workdir}"; shift 2 ;;
    --log-dir) LOG_DIR="${2:?missing value for --log-dir}"; shift 2 ;;
    --strict-host-key-checking) STRICT_HOST_KEY_CHECKING="${2:?missing value}"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "${REMOTE_COMMAND}" ]]; then
  echo "--command is required" >&2
  usage >&2
  exit 2
fi
if [[ -n "${IPS_RAW}" && -n "${IP_FILE}" ]]; then
  echo "Use exactly one of --ips and --ip-file" >&2
  exit 2
fi
if [[ -z "${IPS_RAW}" && -z "${IP_FILE}" ]]; then
  echo "One of --ips or --ip-file is required" >&2
  exit 2
fi
if ! [[ "${PARALLEL}" =~ ^[1-9][0-9]*$ ]]; then
  echo "--parallel must be a positive integer" >&2
  exit 2
fi
if ! [[ "${SSH_PORT}" =~ ^[1-9][0-9]*$ ]]; then
  echo "--port must be a positive integer" >&2
  exit 2
fi
if [[ "${USE_PASSWORD}" == "true" && -n "${SSH_IDENTITY}" ]]; then
  echo "Use either --identity or --password, not both" >&2
  exit 2
fi
if [[ -n "${SSH_IDENTITY}" && ! -f "${SSH_IDENTITY}" ]]; then
  echo "SSH identity file not found: ${SSH_IDENTITY}" >&2
  exit 2
fi
if [[ -n "${IP_FILE}" && ! -f "${IP_FILE}" ]]; then
  echo "IP file not found: ${IP_FILE}" >&2
  exit 2
fi

hosts=()
if [[ -n "${IPS_RAW}" ]]; then
  IFS=',' read -r -a hosts <<< "${IPS_RAW}"
else
  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line%%#*}"
    line="${line//[[:space:]]/}"
    [[ -n "${line}" ]] && hosts+=("${line}")
  done < "${IP_FILE}"
fi

if [[ ${#hosts[@]} -eq 0 ]]; then
  echo "No hosts were resolved" >&2
  exit 2
fi

if [[ -n "${REMOTE_WORKDIR}" ]]; then
  REMOTE_COMMAND="cd -- $(printf '%q' "${REMOTE_WORKDIR}") && ${REMOTE_COMMAND}"
fi

if [[ -z "${LOG_DIR}" ]]; then
  LOG_DIR="remote-exec-$(date +%Y%m%d-%H%M%S)"
fi

echo "hosts=${#hosts[@]} parallel=${PARALLEL} user=${SSH_USER} port=${SSH_PORT}"
echo "command=${REMOTE_COMMAND}"
if [[ "${DRY_RUN}" == "true" ]]; then
  printf 'host=%s\n' "${hosts[@]}"
  exit 0
fi

mkdir -p "${LOG_DIR}"
ssh_args=(
  -p "${SSH_PORT}"
  -o ConnectTimeout=15
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=3
  -o "StrictHostKeyChecking=${STRICT_HOST_KEY_CHECKING}"
)
if [[ -n "${SSH_IDENTITY}" ]]; then
  ssh_args+=(-i "${SSH_IDENTITY}")
fi

askpass_dir=""
cleanup_askpass() {
  if [[ -n "${askpass_dir}" ]]; then
    rm -rf "${askpass_dir}"
  fi
}
trap cleanup_askpass EXIT

if [[ "${USE_PASSWORD}" == "true" ]]; then
  read -r -s -p "SSH password for ${SSH_USER}@<hosts>: " ARENA_REMOTE_SSH_PASSWORD
  echo
  if [[ -z "${ARENA_REMOTE_SSH_PASSWORD}" ]]; then
    echo "SSH password must not be empty" >&2
    exit 2
  fi
  export ARENA_REMOTE_SSH_PASSWORD
  umask 077
  askpass_dir="$(mktemp -d "${TMPDIR:-/tmp}/arena-ssh-askpass.XXXXXX")"
  askpass_program="${askpass_dir}/askpass"
  printf '%s\n' '#!/usr/bin/env sh' 'printf "%s\\n" "$ARENA_REMOTE_SSH_PASSWORD"' > "${askpass_program}"
  chmod 700 "${askpass_program}"
  ssh_args+=(
    -o BatchMode=no
    -o PreferredAuthentications=keyboard-interactive,password
    -o PubkeyAuthentication=no
  )
else
  ssh_args+=(-o BatchMode=yes)
fi

pids=()
pid_hosts=()
failed_hosts=()

wait_for_first() {
  local pid="${pids[0]}"
  local host="${pid_hosts[0]}"
  if ! wait "${pid}"; then
    failed_hosts+=("${host}")
  fi
  pids=("${pids[@]:1}")
  pid_hosts=("${pid_hosts[@]:1}")
}

for host in "${hosts[@]}"; do
  host="${host//[[:space:]]/}"
  [[ -n "${host}" ]] || continue
  log_path="${LOG_DIR}/${host//[^a-zA-Z0-9._-]/_}.log"
  echo "[$(date '+%H:%M:%S')] starting ${host}; log=${log_path}"
  if [[ "${USE_PASSWORD}" == "true" ]]; then
    SSH_ASKPASS="${askpass_program}" SSH_ASKPASS_REQUIRE=force DISPLAY=arena-ssh-askpass \
      ssh "${ssh_args[@]}" "${SSH_USER}@${host}" "bash -lc $(printf '%q' "${REMOTE_COMMAND}")" \
      >"${log_path}" 2>&1 &
  else
    ssh "${ssh_args[@]}" "${SSH_USER}@${host}" "bash -lc $(printf '%q' "${REMOTE_COMMAND}")" \
    >"${log_path}" 2>&1 &
  fi
  pids+=("$!")
  pid_hosts+=("${host}")

  if [[ ${#pids[@]} -ge ${PARALLEL} ]]; then
    wait_for_first
  fi
done

while [[ ${#pids[@]} -gt 0 ]]; do
  wait_for_first
done

if [[ ${#failed_hosts[@]} -gt 0 ]]; then
  printf 'failed_hosts=%s\n' "$(IFS=,; echo "${failed_hosts[*]}")" >&2
  echo "Logs: ${LOG_DIR}" >&2
  exit 1
fi

echo "all_hosts_succeeded=true logs=${LOG_DIR}"
