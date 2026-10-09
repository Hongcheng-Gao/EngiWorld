[English](README.md) | [简体中文](README_CN.md)

# EngiWorld 任务

1,301 个任务采用统一的目录结构：

```text
<类别>/<gui|cli>/<软件或软件1--软件2>/<任务编号>/
```

| 目录类别 | 论文任务类型 | 全量任务 |
|---|---|---:|
| `single-software-execution` | 单软件执行（Single-Software Execution） | 931 |
| `software-selection` | 软件选择（Software Selection） | 140 |
| `vision-guided-modeling` | 视觉引导建模（Vision-Guided Modeling） | 120 |
| `design-optimization` | 设计优化（Design Optimization） | 40 |
| `cross-software-coordination` | 跨软件协同（Cross-Software Coordination） | 60 |
| `open-environment-engineering` | 开放环境工程（Open-Environment Engineering） | 10 |

软件名称使用小写，不包含版本号；多个软件用 `--` 连接。开放环境工程使用 `cli/agent-selected/`。每个类别只包含实际存在的交互模式目录。

每个任务包含 `task-*.json` 定义、`init_file/` 输入文件和评分器（`eval.py`，以及需要时的 `ground_truth/`）。ID 格式为 `<类别>--<gui|cli>--<软件>--<任务编号>--<系统>`，系统保留原任务的 `ubuntu` 或 `windows`。反向建模任务在编号后保留 `-reverse`，用于区分同号任务。

在 `../runtime/` 执行 `python -m engiworld.prepare_tasks` 下载任务资源。`python -m engiworld.local_eval --task` 支持任务目录路径和 JSON ID。运行评测请参考[快速开始](../README_CN.md)。

论文主实验使用的 306 个任务列于 [`splits/main-306.txt`](splits/main-306.txt)。调度器通过 `--task-id-file ../task/splits/main-306.txt` 读取该清单。

目录类别和 JSON ID 已按 2026-10-09 新版论文统一命名。`task/aliases.json` 保留历史 JSON ID 和目录名的对应关系；本运行框架可继续使用旧标识选择任务。完整改名表见 [`id-migration-20261009.json`](id-migration-20261009.json)，任务名称与数量见 [`taxonomy.json`](taxonomy.json)。
