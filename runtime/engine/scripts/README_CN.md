[English](README.md) | [简体中文](README_CN.md)

# 引擎脚本

`python/` 包含可选智能体运行器（`run_*.py`）、多环境运行器（`run_multienv_*.py`）和 `manual_examine.py`。`bash/` 包含启动脚本，例如 `run_dart_gui.sh`、`run_os_symphony.sh` 和 `run_manual_examine.sh`。EngiWorld 通用 GUI/CLI 接口见[运行框架入口](../../README_CN.md)。

在 `runtime/engine/` 目录执行这些引擎脚本：

```bash
python scripts/python/run_multienv.py   --provider_name docker --headless   --observation_type screenshot --model gpt-4o   --max_steps 15 --num_envs 10 --client_password password

bash scripts/bash/run_dart_gui.sh [args]
```

人工检查工具支持执行操作、核对任务定义和评分指标，并录制截图与视频：

```bash
python scripts/python/manual_examine.py   --headless --observation_type screenshot   --result_dir ./results_human_examine   --test_all_meta_path evaluation_examples/test_all.json   --domain libreoffice_impress   --example_id a669ef01-ded5-4099-9ea9-25e99b569840 --max_steps 3
```

上述示例使用引擎自带的示例任务格式，其他示例见 `bash/run_manual_examine.sh`。

脚本基于引擎目录解析导入路径。新增运行器应先设置路径，再导入引擎模块：

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import lib_run_single
from desktop_env.desktop_env import DesktopEnv
from mm_agents.your_agent import YourAgent
```
