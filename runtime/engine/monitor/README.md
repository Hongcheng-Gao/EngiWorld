[English](README.md) | [简体中文](README_CN.md)

# Engine monitor

This optional dashboard displays engine task status, scores, screenshots, and execution steps. It reads the engine's example and result layout. EngiWorld evaluation entry points are described in the [runtime guide](../../README.md).

Start the task runner before starting the monitor. In `runtime/engine/monitor/`, create `.env` and configure paths for the run being viewed:

```dotenv
TASK_CONFIG_PATH=../evaluation_examples/test.json
EXAMPLES_BASE_PATH=../evaluation_examples/examples
RESULTS_BASE_PATH=../results
ACTION_SPACE=pyautogui
OBSERVATION_TYPE=screenshot
MODEL_NAME=computer-use-preview
MAX_STEPS=150
FLASK_PORT=8080
FLASK_HOST=0.0.0.0
FLASK_DEBUG=false
```

`TASK_CONFIG_PATH` selects the task list, `EXAMPLES_BASE_PATH` contains task definitions, and `RESULTS_BASE_PATH` contains execution outputs. The action space, observation type, and model must match the run. `MAX_STEPS` controls the displayed step limit; `FLASK_*` settings configure the web server.

## Docker

With Docker and Docker Compose installed, run from the monitor directory:

```bash
docker compose up -d
```

Open `http://<host>:8080` (or the configured `FLASK_PORT`). To view logs or stop the monitor:

```bash
docker compose logs -f
docker compose down
```

## Without Docker

```bash
pip install -r requirements.txt
python main.py
```

The interface groups tasks, filters their status, and opens individual trajectories. If it cannot display a run, check the logs, configured paths, Docker state, port availability, and network access to the configured web port.
