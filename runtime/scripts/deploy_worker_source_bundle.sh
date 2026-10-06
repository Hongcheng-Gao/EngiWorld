#!/usr/bin/env bash
# Copy a worker source bundle to ECS hosts and install it through SSH.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/deploy_worker_source_bundle.sh --bundle PATH --ips IP[,IP...] [options]
  bash scripts/deploy_worker_source_bundle.sh --bundle PATH --ip-file hosts.txt [options]

Copies the source tgz to /tmp on every host, extracts it below /root/worker,
then runs deploy/worker/install_worker_source_bundle.sh inside that bundle.

Options:
  --bundle PATH            arena-osworld-worker-source-*.tgz to deploy.
  --ips VALUE              Comma-separated worker IP addresses.
  --ip-file PATH           One IP address per line; blank lines and # comments are ignored.
  --user USER              SSH user. Default: root.
  --identity PATH          SSH private key.
  --password               Prompt once for a shared SSH password.
  --port PORT              SSH port. Default: 22.
  --parallel N             Maximum hosts deployed concurrently. Default: 4.
  --log-dir PATH           Local per-host logs. Default: ./worker-deploy-<timestamp>.
  --replace                Replace an existing same-named extracted bundle.
  --install-osworld-v2     Set INSTALL_OSWORLD_V2=true for the source installer.
  --worker-extra VALUE     Set WORKER_EXTRA. Default: worker-api.
  --dry-run                Print resolved actions without SSH/SCP.
  -h, --help               Show this help.
EOF
}

BUNDLE=""
IPS_RAW=""
IP_FILE=""
SSH_USER="root"
SSH_IDENTITY=""
USE_PASSWORD=false
SSH_PORT="22"
PARALLEL="4"
LOG_DIR=""
REPLACE=false
INSTALL_OSWORLD_V2=false
WORKER_EXTRA="worker-api"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bundle) BUNDLE="${2:?missing value for --bundle}"; shift 2 ;;
    --ips) IPS_RAW="${2:?missing value for --ips}"; shift 2 ;;
    --ip-file) IP_FILE="${2:?missing value for --ip-file}"; shift 2 ;;
    --user) SSH_USER="${2:?missing value for --user}"; shift 2 ;;
    --identity) SSH_IDENTITY="${2:?missing value for --identity}"; shift 2 ;;
    --password) USE_PASSWORD=true; shift ;;
    --port) SSH_PORT="${2:?missing value for --port}"; shift 2 ;;
    --parallel) PARALLEL="${2:?missing value for --parallel}"; shift 2 ;;
    --log-dir) LOG_DIR="${2:?missing value for --log-dir}"; shift 2 ;;
    --replace) REPLACE=true; shift ;;
    --install-osworld-v2) INSTALL_OSWORLD_V2=true; shift ;;
    --worker-extra) WORKER_EXTRA="${2:?missing value for --worker-extra}"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "${BUNDLE}" && -f "${BUNDLE}" && "${BUNDLE}" == *.tgz ]] || {
  echo "--bundle must name an existing .tgz archive" >&2; exit 2;
}
[[ -z "${IPS_RAW}" || -z "${IP_FILE}" ]] || {
  echo "Use exactly one of --ips and --ip-file" >&2; exit 2;
}
[[ -n "${IPS_RAW}" || -n "${IP_FILE}" ]] || {
  echo "One of --ips or --ip-file is required" >&2; exit 2;
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

if ! bundle_top_dir="$(
  tar -tzf "${BUNDLE}" | awk '
    {
      name = $0
      sub(/^\.\//, "", name)
      split(name, parts, "/")
      top = parts[1]
      if (found || top == "" || top == "." || top == "__MACOSX" || top ~ /^\._/) {
        next
      }
      print top
      found = 1
    }
  '
)"; then
  echo "Failed to inspect worker bundle: ${BUNDLE}" >&2
  exit 2
fi
[[ -n "${bundle_top_dir}" && "${bundle_top_dir}" != "." && "${bundle_top_dir}" != */* ]] || {
  echo "Bundle has no safe top-level directory: ${BUNDLE}" >&2; exit 2;
}
bundle_name="$(basename "${BUNDLE}")"
remote_archive="/tmp/${bundle_name}"
remote_dir="/root/worker/${bundle_top_dir}"

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

LOG_DIR="${LOG_DIR:-worker-deploy-$(date +%Y%m%d-%H%M%S)}"
echo "bundle=${BUNDLE} hosts=${#hosts[@]} parallel=${PARALLEL}"
echo "remote_archive=${remote_archive} remote_dir=${remote_dir}"
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
  if [[ ! -e /dev/tty ]]; then
    echo "--password requires an interactive terminal (/dev/tty)." >&2
    exit 2
  fi
  if ! printf 'SSH password for %s@<workers>: ' "${SSH_USER}" > /dev/tty; then
    echo "--password could not open the interactive terminal (/dev/tty)." >&2
    exit 2
  fi
  if ! IFS= read -r -s ARENA_REMOTE_SSH_PASSWORD < /dev/tty; then
    printf '\n' > /dev/tty
    echo "Failed to read SSH password from /dev/tty." >&2
    exit 2
  fi
  printf '\n' > /dev/tty
  [[ -n "${ARENA_REMOTE_SSH_PASSWORD}" ]] || { echo "SSH password must not be empty" >&2; exit 2; }
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
  scp_args+=(
    -o BatchMode=no
    -o PreferredAuthentications=keyboard-interactive,password
    -o PubkeyAuthentication=no
  )
else
  ssh_args+=(-o BatchMode=yes)
  scp_args+=(-o BatchMode=yes)
fi

remote_command="set -euo pipefail
mkdir -p /root/worker
rm -rf $(printf '%q' "/root/worker/._${bundle_top_dir}") /root/worker/__MACOSX
if [[ -e $(printf '%q' "${remote_dir}") ]]; then"
if [[ "${REPLACE}" == true ]]; then
  remote_command+="
  rm -rf $(printf '%q' "${remote_dir}")"
else
  remote_command+="
  echo $(printf '%q' "Remote bundle directory exists: ${remote_dir}; re-run with --replace") >&2
  exit 3"
fi
remote_command+="
fi
tar --warning=no-unknown-keyword \
  --no-xattrs \
  --exclude='._*' \
  --exclude='*/._*' \
  --exclude='__MACOSX' \
  --exclude='*/__MACOSX' \
  -xzf $(printf '%q' "${remote_archive}") -C /root/worker
cd -- $(printf '%q' "${remote_dir}")
WORKER_EXTRA=$(printf '%q' "${WORKER_EXTRA}") INSTALL_OSWORLD_V2=$(printf '%q' "${INSTALL_OSWORLD_V2}") bash deploy/worker/install_worker_source_bundle.sh"

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
  echo "[$(date '+%H:%M:%S')] deploying ${host}; log=${log_path}"
  if [[ "${USE_PASSWORD}" == true ]]; then
    SSH_ASKPASS="${askpass_program}" SSH_ASKPASS_REQUIRE=force DISPLAY=arena-ssh-askpass \
      scp "${scp_args[@]}" "${BUNDLE}" "${SSH_USER}@${host}:${remote_archive}" >"${log_path}" 2>&1 && \
      SSH_ASKPASS="${askpass_program}" SSH_ASKPASS_REQUIRE=force DISPLAY=arena-ssh-askpass \
      ssh "${ssh_args[@]}" "${SSH_USER}@${host}" "bash -lc $(printf '%q' "${remote_command}")" >>"${log_path}" 2>&1 &
  else
    scp "${scp_args[@]}" "${BUNDLE}" "${SSH_USER}@${host}:${remote_archive}" >"${log_path}" 2>&1 && \
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
echo "all_hosts_deployed=true logs=${LOG_DIR}"
