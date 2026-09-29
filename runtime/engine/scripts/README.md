[English](README.md) | [简体中文](README_CN.md)

# Engine scripts

`python/` contains optional agent runners (`run_*.py`), multi-environment runners (`run_multienv_*.py`), and `manual_examine.py`. `bash/` contains shell launchers, including `run_dart_gui.sh`, `run_os_symphony.sh`, and `run_manual_examine.sh`. For the shared EngiWorld GUI/CLI interface, use the [runtime entry points](../../README.md).

Run these engine scripts from `runtime/engine/`:

```bash
python scripts/python/run_multienv.py   --provider_name docker --headless   --observation_type screenshot --model gpt-4o   --max_steps 15 --num_envs 10 --client_password password

bash scripts/bash/run_dart_gui.sh [args]
```

Manual examination supports executing actions, checking task definitions and metrics, and recording screenshots and videos:

```bash
python scripts/python/manual_examine.py   --headless --observation_type screenshot   --result_dir ./results_human_examine   --test_all_meta_path evaluation_examples/test_all.json   --domain libreoffice_impress   --example_id a669ef01-ded5-4099-9ea9-25e99b569840 --max_steps 3
```

The example above uses the engine's bundled example-task format. See `bash/run_manual_examine.sh` for further examples.

Scripts resolve imports relative to the engine directory. New runners should initialize the import path before importing engine modules:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import lib_run_single
from desktop_env.desktop_env import DesktopEnv
from mm_agents.your_agent import YourAgent
```
