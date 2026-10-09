[English](README.md) | [简体中文](README_CN.md)

# EngiWorld 运行框架

安装、镜像下载和本地评测见[快速开始](../README_CN.md)。本页介绍运行设置和云端调度。以下命令在本目录执行。

## 运行设置

使用 `python -m engiworld.local_eval` 运行本地评测。每个环境默认使用 4 个 CPU、16 GB 内存和 200 GB 虚拟磁盘，可通过 `ENGIWORLD_DOCKER_CPU_CORES`、`ENGIWORLD_DOCKER_RAM_SIZE`、`ENGIWORLD_DOCKER_DISK_SIZE` 调整。来宾系统用户密码通过 `--client-password` 或 `ENGIWORLD_CLIENT_PASSWORD` 设置。

| 设置 | 默认值 |
|---|---|
| 桌面分辨率 | 1920×1080，初始化前后均校准并验证 |
| 历史轮数 | 15 |
| 常规 GUI / CLI 轮数上限 | 200 / 100 |
| 跨软件协同 GUI / CLI 轮数上限 | 300 / 150 |
| 开放环境工程轮数上限 | 150 |
| 单任务活跃时间 | 5 小时（18000 秒） |

本地时间上限使用 `--task-timeout` 设置；云端使用 master 的 `--task-run-timeout-seconds` 或 `TASK_RUN_TIMEOUT_SECONDS`。本地计时包含虚拟机启动、初始化、模型请求、动作执行和评分。扣除框架登记的暂停区间，重叠暂停只扣除一次，恢复运行时保留此前的活跃时间。智能体的 WAIT 动作和请求重试计入时间预算。

活跃时间耗尽时记录 `completed / 0`、`active_time_budget_exhausted` 和 `native_evaluator_executed=false`。API 中断与环境故障单独记录。评分器执行故障记录为 `infra_incomplete`，得分为 `null`。结果包含 `wall_duration_seconds`、`paused_seconds` 和 `active_duration_seconds`。

## 云端调度

火山 ECS 调度通过 Redis 协调任务，通过对象存储保存结果。资源配置见 [`.env.example`](.env.example)，部署入口见 [`deploy/`](deploy/)。云端执行使用自定义镜像 ID。master 和 worker 的 `--task-root` / `TASK_ROOT` 都应指向 `../task`，并准备好任务资源。

## 通用模型接口

所有模型通过 `engiworld.agents.openai_compatible:create_agent` 使用兼容 OpenAI 的 Chat Completions API。添加模型只需配置模型名称和端点。

在 worker 环境中设置 `OPENAI_BASE_URL`、`OPENAI_API_KEY`，在 master 端选择模型：

```bash
python -m engiworld.scheduler.master plan \
  --task-root ../task --task-limit 1 --num-vms 1 \
  --agent openai-compatible \
  --agent-env ARENA_MODEL_NAME=your-model-name
```

`plan` 输出所选任务和模型配置。`scheduler.master` 分配任务，`scheduler.worker_entrypoint` 执行模型和评分器。

| 设置 | 环境变量 | 默认值 |
|---|---|---|
| 端点 | `OPENAI_BASE_URL`，也支持 `ARENA_MODEL_BASE_URL` | 自行设置 |
| API 密钥 | `OPENAI_API_KEY` | 在 worker 设置 |
| API 模型名称 | `ARENA_MODEL_NAME` | 通用接口必填，预设会自动填入 |
| 输出 token 上限 | `ARENA_MODEL_MAX_TOKENS` | **所有模型均为 16384** |
| token 上限字段 | `ARENA_MODEL_TOKEN_LIMIT_FIELD` | `max_tokens`，也支持 `max_completion_tokens` |
| 推理强度 | `ARENA_MODEL_REASONING_EFFORT` | 通用接口默认不设置，预设保留其设置 |
| 推理字段 | `ARENA_MODEL_REASONING_FIELD` | `reasoning_effort`，也支持 `reasoning`、`none` |
| 请求超时 | `ARENA_MODEL_TIMEOUT_SECONDS` | 600 秒 |
| 请求尝试次数 | `ARENA_MODEL_API_RETRIES` | 3 次，包含首次请求 |
| 流式返回 | `ARENA_MODEL_STREAM` | `true` |

只有收到完整的流式响应后才执行动作。中断或无效响应会重试，重试耗尽后记录为 API 中断。

## 视觉引导建模

`vision-guided-modeling/` 的参考图位于 `init_file/`，通过 `python -m engiworld.prepare_tasks` 下载。运行框架默认将图片放入模型消息：GUI 使用 `gui_message_initial`，CLI 使用 `cli_message_initial`。

## 开放环境工程

`open-environment-engineering/cli/agent-selected/` 使用没有预装工程软件的空白 `top-10` 基础镜像。模型自行选择、安装和配置工具，使用终端观察和 `open_engineering` 交互配置。

几何评分需要 FreeCAD。框架会在模型结束后检查并安装该依赖；镜像需要支持非交互式 sudo，并能访问 Ubuntu 软件源。
