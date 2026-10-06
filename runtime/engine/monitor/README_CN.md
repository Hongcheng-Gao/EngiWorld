[English](README.md) | [简体中文](README_CN.md)

# 引擎监控面板

此可选面板展示引擎任务的状态、得分、截图和执行步骤，读取引擎的示例与结果目录格式。EngiWorld 评测入口见[运行框架说明](../../README_CN.md)。

先启动任务运行器，再启动监控面板。在 `runtime/engine/monitor/` 创建 `.env`，将路径配置为要查看的运行记录：

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

`TASK_CONFIG_PATH` 指定任务清单，`EXAMPLES_BASE_PATH` 存放任务定义，`RESULTS_BASE_PATH` 存放执行结果。动作空间、观察类型和模型名称需与运行记录一致。`MAX_STEPS` 控制展示的步数上限，`FLASK_*` 配置 Web 服务。

## 使用 Docker

安装 Docker 和 Docker Compose 后，在监控目录执行：

```bash
docker compose up -d
```

访问 `http://<host>:8080`，或使用所配置的 `FLASK_PORT`。查看日志和停止面板：

```bash
docker compose logs -f
docker compose down
```

## 不使用 Docker

```bash
pip install -r requirements.txt
python main.py
```

界面支持任务分组、状态筛选和逐条查看轨迹。如果无法显示运行记录，请检查日志、配置路径、Docker 状态、端口占用，以及对应 Web 端口的网络访问情况。
