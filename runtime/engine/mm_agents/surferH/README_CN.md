[English](README.md) | [简体中文](README_CN.md)

# Surfer H 引擎集成

此可选集成通过 H 的 Agent Platform（AGP）运行 Surfer H，使用 AWS EC2 环境和远程桌面驱动服务 RDDS。评测 EngiWorld 任务请使用[运行框架入口](../../../README_CN.md)。

## 依赖和设置

- Python 3.11 或更高版本，以及引擎依赖。
- AWS 凭据：配置在 `~/.aws/credentials`，或通过 `AWS_ACCESS_KEY_ID` 和 `AWS_SECRET_ACCESS_KEY` 提供。
- EC2 权限：`RunInstances`、`DescribeInstances`、`CreateTags` 和 `TerminateInstances`。
- `agp_client/` Python 包、`rdds/` 服务源码，以及所选智能体的 AGP 访问权限。这些集成专用依赖需要另行准备。

配置完成后，在 `runtime/engine/` 执行：

```bash
python mm_agents/surferH/run_benchmark_with_retries.py   --num_envs 5 --agent_identifier your-agent-identifier
```

日志写入 `results/benchmark_*.log`。

## 执行和恢复

每个 worker 恢复干净的虚拟机快照，最多等待 300 秒以确认 Flask 后端就绪，安装 RDDS，并检查 8087 端口的 `/health` 和 `/screenshot`。随后初始化任务，通过 `SurferAgent.predict()` 提交给智能体，再进行评分。初始化失败时，worker 会重建虚拟机，在配置的尝试次数内重试。worker 进程退出后，替代进程会继续处理队列。

每个任务的 `status.json` 首先记录 ID、指令、`running` 状态和开始时间。轨迹创建后立即通过回调保存 `trajectory_id`。完成时加入得分、耗时、AGP 消息和操作数量，并改为 `completed`；异常时改为 `error` 并记录错误消息。

## 网络设置

根据部署使用的客户端和 VPC 配置安全组：

| 端口 | 服务 |
|---|---|
| 22 | SSH |
| 80 | HTTP |
| 5000 | Flask 桌面后端 |
| 5910 | noVNC |
| 8006 | VNC |
| 8080 | VLC 评分服务 |
| 8081 | 附加虚拟机服务 |
| 8087 | RDDS，需可被 AGP 智能体访问 |
| 9222 | Chrome DevTools |

`install_rdds.py` 在启动 RDDS 前自动通过 UFW 放行 8087 端口。手动排查时可执行：

```bash
sudo ufw allow 8087/tcp
```
