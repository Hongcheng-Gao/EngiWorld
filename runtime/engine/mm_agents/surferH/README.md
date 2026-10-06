[English](README.md) | [简体中文](README_CN.md)

# Surfer H engine integration

This optional integration runs Surfer H through H's Agent Platform (AGP), with AWS EC2 environments and the Remote Desktop Driver Server (RDDS). For EngiWorld task evaluation, use the [runtime entry points](../../../README.md).

## Requirements and setup

- Python 3.11 or newer and the engine dependencies.
- AWS credentials, supplied through `~/.aws/credentials` or `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.
- EC2 permissions: `RunInstances`, `DescribeInstances`, `CreateTags`, and `TerminateInstances`.
- The `agp_client/` Python package and `rdds/` server source, plus AGP access for the selected agent. These integration-specific dependencies must be provisioned separately.

Run from `runtime/engine/` after configuring the integration:

```bash
python mm_agents/surferH/run_benchmark_with_retries.py   --num_envs 5 --agent_identifier your-agent-identifier
```

Logs are written to `results/benchmark_*.log`.

## Execution and recovery

Each worker restores a clean VM snapshot, waits up to 300 seconds for the Flask backend, installs RDDS, and checks `/health` and `/screenshot` on port 8087. It then initializes the task, submits it through `SurferAgent.predict()`, and evaluates the result. Setup failures cause the worker to recreate the VM and retry within the configured attempt limits. A replacement process resumes the queue if a worker dies.

Each task's `status.json` starts with its ID, instruction, `running` status, and start time. A callback saves `trajectory_id` as soon as it exists. Completion adds the score, elapsed time, AGP message, and action count, then sets `completed`; an exception sets `error` and records its message.

## Networking

Configure the security group for the deployment's clients and VPC:

| Port | Service |
|---|---|
| 22 | SSH |
| 80 | HTTP |
| 5000 | Flask desktop backend |
| 5910 | noVNC |
| 8006 | VNC |
| 8080 | VLC evaluator service |
| 8081 | Additional VM service |
| 8087 | RDDS; reachable by the AGP agent |
| 9222 | Chrome DevTools |

The supplied `install_rdds.py` opens port 8087 in UFW before starting RDDS. For manual diagnosis:

```bash
sudo ufw allow 8087/tcp
```
