#!/usr/bin/env bash
# Securely copy one worker environment file to multiple ECS hosts.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/deploy_worker_env.sh --env-file PATH --ips IP[,IP...] [options]
  bash scripts/deploy_worker_env.sh --env-file PATH --ip-file hosts.txt [options]

Options:
  --env-file PATH         Local worker environment file to distribute.
  --ips VALUE             Comma-separated worker IP addresses.
  --ip-file PATH          One IP address per line; blank lines and # comments are ignored.
  --remote-path PATH      Destination path. Default: /root/worker/worker.env.
  --user USER             SSH user. Default: root.
  --identity PATH         SSH private key.
  --password              Prompt once for a shared SSH password.
  --port PORT             SSH port. Default: 22.
  --parallel N            Maximum hosts updated concurrently. Default: 4.
  --log-dir PATH          Local per-host logs. Default: ./worker-env-deploy-<timestamp>.
  --dry-run               Print resolved targets without SSH/SCP.
  -h, --help              Show this help.
EOF
}

ENV_FILE=""
IPS_RAW=""
IP_FILE=""
REMOTE_PATH="/root/worker/worker.env"
SSH_USER="root"
SSH_IDENTITY=""
USE_PASSWORD=false
SSH_PORT="22"
PARALLEL="4"
LOG_DIR=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file) ENV_FILE="${2:?missing value for --env-file}"; shift 2 ;;
    --ips) IPS_RAW="${2:?missing value for --ips}"; shift 2 ;;
    --ip-file) IP_FILE="${2:?missing value for --ip-file}"; shift 2 ;;
    --remote-path) REMOTE_PATH="${2:?missing value for --remote-path}"; shift 2 ;;
    --user) SSH_USER="${2:?missing value for --user}"; shift 2 ;;
    --identity) SSH_IDENTITY="${2:?missing value for --identity}"; shift 2 ;;
    --password) USE_PASSWORD=true; shift ;;
    --port) SSH_PORT="${2:?missing value for --port}"; shift 2 ;;
    --parallel) PARALLEL="${2:?missing value for --parallel}"; shift 2 ;;
    --log-dir) LOG_DIR="${2:?missing value for --log-dir}"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "${ENV_FILE}" && -f "${ENV_FILE}" ]] || {
  echo "--env-file must name an existing file" >&2; exit 2;
}
[[ -z "${IPS_RAW}" || -z "${IP_FILE}" ]] || {
  echo "Use exactly one of --ips and --ip-file" >&2; exit 2;
}
[[ -n "${IPS_RAW}" || -n "${IP_FILE}" ]] || {
  echo "One of --ips or --ip-file is required" >&2; exit 2;
}
[[ "${REMOTE_PATH}" == /* && "${REMOTE_PATH}" != */ ]] || {
  echo "--remote-path must be an absolute file path" >&2; exit 2;
}
[[ "${USE_PASSWORD}" != true || -z "${SSH_IDENTITY}" ]] || {
  echo "Use either --identity or --password, not both" >&2; exit 2;
}
[[ -z "${SSH_IDENTITY}" || -f "${SSH_IDENTITY}" ]] || {
  echo "SSH identity file not found: ${SSH_IDENTITY}" >&2; exit 2;
}
[[ -z "${IP_FILE}" || -f "${IP_FILE}" ]] || {
  echo "IP file not found: ${IP_FILE}" >&2; exit 2;
}
[[ "${PARALLEL}" =~ ^[1-9][0-9]*$ && "${SSH_PORT}" =~ ^[1-9][0-9]*$ ]] || {
  echo "--parallel and --port must be positive integers" >&2; exit 2;
}

if command -v sha256sum >/dev/null 2>&1; then
  ENV_SHA256="$(sha256sum "${ENV_FILE}" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  ENV_SHA256="$(shasum -a 256 "${ENV_FILE}" | awk '{print $1}')"
else
  echo "sha256sum or shasum is required" >&2
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
[[ ${#hosts[@]} -gt 0 ]] || { echo "No hosts were resolved" >&2; exit 2; }

LOG_DIR="${LOG_DIR:-worker-env-deploy-$(date +%Y%m%d-%H%M%S)}"
remote_parent="$(dirname "${REMOTE_PATH}")"
remote_upload="/tmp/arena-worker-env-${ENV_SHA256:0:12}-$$"
remote_staged="${REMOTE_PATH}.tmp.$$"

echo "env_file=${ENV_FILE} hosts=${#hosts[@]} parallel=${PARALLEL}"
echo "remote_path=${REMOTE_PATH} sha256=${ENV_SHA256}"
if [[ "${DRY_RUN}" == true ]]; then
  printf 'host=%s\n' "${hosts[@]}"
  exit 0
fi

mkdir -p "${LOG_DIR}"
ssh_args=(-p "${SSH_PORT}" -o ConnectTimeout=15 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=accept-new)
scp_args=(-P "${SSH_PORT}" -o ConnectTimeout=15 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=accept-new)
if [[ -n "${SSH_IDENTITY}" ]]; then
  ssh_args+=(-i "${SSH_IDENTITY}")
  scp_args+=(-i "${SSH_IDENTITY}")
fi

askpass_dir=""
cleanup_askpass() { [[ -z "${askpass_dir}" ]] || rm -rf "${askpass_dir}"; }
trap cleanup_askpass EXIT
if [[ "${USE_PASSWORD}" == true ]]; then
  read -r -s -p "SSH password for ${SSH_USER}@<workers>: " ARENA_REMOTE_SSH_PASSWORD
  echo
  [[ -n "${ARENA_REMOTE_SSH_PASSWORD}" ]] || {
    echo "SSH password must not be empty" >&2; exit 2;
  }
  export ARENA_REMOTE_SSH_PASSWORD
  umask 077
  askpass_dir="$(mktemp -d "${TMPDIR:-/tmp}/arena-ssh-askpass.XXXXXX")"
  askpass_program="${askpass_dir}/askpass"
  printf '%s\n' '#!/usr/bin/env sh' 'printf "%s\\n" "$ARENA_REMOTE_SSH_PASSWORD"' > "${askpass_program}"
  chmod 700 "${askpass_program}"
  ssh_args+=(-o BatchMode=no -o PreferredAuthentications=keyboard-interactive,password -o PubkeyAuthentication=no)
  scp_args+=(-o BatchMode=no -o PreferredAuthentications=keyboard-interactive,password -o PubkeyAuthentication=no)
else
  ssh_args+=(-o BatchMode=yes)
  scp_args+=(-o BatchMode=yes)
fi

remote_command="set -euo pipefail
trap 'rm -f $(printf '%q' "${remote_upload}") $(printf '%q' "${remote_staged}")' EXIT
mkdir -p $(printf '%q' "${remote_parent}")
install -m 600 $(printf '%q' "${remote_upload}") $(printf '%q' "${remote_staged}")
printf '%s  %s\\n' $(printf '%q' "${ENV_SHA256}") $(printf '%q' "${remote_staged}") | sha256sum -c -
mv -f $(printf '%q' "${remote_staged}") $(printf '%q' "${REMOTE_PATH}")
chmod 600 $(printf '%q' "${REMOTE_PATH}")
echo worker_env_installed=true path=$(printf '%q' "${REMOTE_PATH}") sha256=$(printf '%q' "${ENV_SHA256}")"

pids=()
pid_hosts=()
failed_hosts=()
wait_for_first() {
  local pid="${pids[0]}" host="${pid_hosts[0]}"
  if ! wait "${pid}"; then failed_hosts+=("${host}"); fi
  pids=("${pids[@]:1}")
  pid_hosts=("${pid_hosts[@]:1}")
}

for host in "${hosts[@]}"; do
  host="${host//[[:space:]]/}"
  [[ -n "${host}" ]] || continue
  log_path="${LOG_DIR}/${host//[^a-zA-Z0-9._-]/_}.log"
  echo "[$(date '+%H:%M:%S')] updating ${host}; log=${log_path}"
  if [[ "${USE_PASSWORD}" == true ]]; then
    SSH_ASKPASS="${askpass_program}" SSH_ASKPASS_REQUIRE=force DISPLAY=arena-ssh-askpass \
      scp "${scp_args[@]}" "${ENV_FILE}" "${SSH_USER}@${host}:${remote_upload}" >"${log_path}" 2>&1 && \
      SSH_ASKPASS="${askpass_program}" SSH_ASKPASS_REQUIRE=force DISPLAY=arena-ssh-askpass \
      ssh "${ssh_args[@]}" "${SSH_USER}@${host}" "bash -lc $(printf '%q' "${remote_command}")" >>"${log_path}" 2>&1 &
  else
    scp "${scp_args[@]}" "${ENV_FILE}" "${SSH_USER}@${host}:${remote_upload}" >"${log_path}" 2>&1 && \
      ssh "${ssh_args[@]}" "${SSH_USER}@${host}" "bash -lc $(printf '%q' "${remote_command}")" >>"${log_path}" 2>&1 &
  fi
  pids+=("$!")
  pid_hosts+=("${host}")
  [[ ${#pids[@]} -lt ${PARALLEL} ]] || wait_for_first
done

while [[ ${#pids[@]} -gt 0 ]]; do wait_for_first; done
if [[ ${#failed_hosts[@]} -gt 0 ]]; then
  printf 'failed_hosts=%s\n' "$(IFS=,; echo "${failed_hosts[*]}")" >&2
  echo "Logs: ${LOG_DIR}" >&2
  exit 1
fi
echo "all_worker_envs_installed=true logs=${LOG_DIR}"
