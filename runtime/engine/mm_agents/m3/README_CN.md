[English](README.md) | [简体中文](README_CN.md)

# M3 智能体

独立的 M3 智能体模块，用于在 [OSWorld](https://github.com/xlang-ai/OSWorld) 中评测 M3 训练模型，提供系统提示词、响应解析和截图处理，通过兼容 Anthropic Messages 的端点调用模型。

传输使用 [`anthropic` Python SDK](https://github.com/anthropics/anthropic-sdk-python)。端点、密钥和模型名称来自 `ANTHROPIC_BASE_URL`、`ANTHROPIC_API_KEY`、`ANTHROPIC_MODEL`，也可通过构造函数的对应参数提供。

## 文件

| 文件 | 用途 |
|---|---|
| `prompts.py` | `M3_SYSTEM_PROMPT_TEMPLATE`，填入 `{date_str, client_password}` 后作为系统消息 |
| `parser.py` | `parse_m3_response()` 提取 `<tool_call>` 块并转换为 pyautogui 代码 |
| `agent.py` | `M3Agent` 类，实现 `predict`、`reset`、`set_api_log_dir` 生命周期及 Anthropic 调用 |
| `__init__.py` | 导出 `M3Agent`、提示词模板和解析函数 |

## 行为

- 1920×1080 截图，原样发送，不缩放。
- 使用 `[0, 1000]` 归一化坐标，即 `coordinate_type="relative"`。
- 系统提示词由 `M3_SYSTEM_PROMPT_TEMPLATE.format(date_str=..., client_password=...)` 生成，作为首条 `system` 消息。
- 16 种计算机操作，包括 `left_click`、`key`、`type`、`scroll`、`wait`、`done`、`screenshot` 等。
- 工具调用为 `<tool_call>{...}</tool_call>` 包裹的 JSON，内部为 `{"name": "computer", "arguments": {...}}`。
- 最近截图数超过保留下限 `keep_min` 后，每次成批移除 `chunk` 步的旧截图，替换为简短文本。近期截图数在 `[keep_min, keep_min+chunk-1]` 内变化，以便在两次清理之间保持消息前缀字节一致，复用提示词缓存。
- 停止序列为 `["</tool_call>", "Perform the next action. Perform"]`。
- `[INFEASIBLE]` 返回特殊动作 `FAIL`。
- 修复 BPE 导致的畸形动作名，如 `_lick` → `_click`、`"key_ "` → `"key_"`，以及截断的尾部 token。

## 图像历史裁剪

OSWorld 轨迹可能持续 50–100 步。M3 只保留近期截图，将旧截图替换为 `Tool result: Success`，以控制上下文。

`M3Agent` 构造函数的两个参数：

| 参数 | 默认值 | 含义 |
|---|---|---|
| `only_n_most_recent_images`，别名 `max_trajectory_length` | `10` | 清理后至少保留的近期截图数量，记为 `keep_min`，不是上限 |
| `image_truncation_threshold` | `20` | 每次清理的批量大小，记为 `chunk`，不移除不足一批的截图 |

设置 `only_n_most_recent_images=10` 并不将图片数固定为 10。进入稳定裁剪阶段后，每轮近期截图数量在 `keep_min` 至 `keep_min+chunk-1` 之间变化；默认是 10–29 张，加上始终保留的初始截图，每次请求为 11–30 张。

算法见 `agent.py:_build_messages`：

```python
k = len(self.responses)               # how many turns have happened so far
remove = max(0, k - keep_min)         # candidate count over the lower bound
remove -= remove % chunk              # round DOWN to a multiple of chunk
                                      # (don't drop a partial chunk)
```

最早的 `remove` 张工具结果截图会替换为文本，后续截图继续保留为图片。初始截图（第 0 步）始终保留，因为任务指令可能引用它。

默认 `keep_min=10`、`chunk=20` 的示例：

| 步数 k | k − keep_min | 取整后的 remove | 发送图片数 |
|---:|---:|---:|---:|
| 9 | −1 | 0 | 1 张初始图 + 9 = 10 |
| 10 | 0 | 0 | 1 + 10 = 11 |
| 19 | 9 | 0 | 1 + 19 = 20 |
| 29 | 19 | 0 | 1 + 29 = 30，首次清理前峰值 |
| 30 | 20 | 20 | 1 + 10 = 11，首次清理 |
| 49 | 39 | 20 | 1 + 29 = 30，再次达到峰值 |
| 50 | 40 | 40 | 1 + 10 = 11，第二次清理 |

总图片数逐渐升至 `keep_min+chunk`，再回落至 `keep_min+1`。

批量清理的原因是提示词缓存会根据消息前缀计算哈希；原配置采用 5 分钟 TTL。每步删除一张图会不断改变前缀，批量删除则能在连续 20 次请求中保持前缀一致，增加缓存复用、降低延迟与长轨迹的输入 token 开销。

若模型忘记已滚出屏幕的信息，可增大 `keep_min`。若端点缓存有效期较长，可增大 `chunk`；上下文预算紧张时可减小到 `5`，代价是更频繁的缓存失效。`chunk=1` 等同于逐步只保留最后 `keep_min` 张近期图。运行参数 `--max_trajectory_length` 对应 `keep_min`，`chunk` 只能通过构造函数设置。

## 与运行器的接口

`M3Agent.__init__` 接受与 `PromptAgent` 相同的参数，可接入 `run.py` 和 `scripts/python/run_multienv_*.py`：

- `platform`、`model`、`max_tokens`、`top_p`、`temperature`、`action_space`、`observation_type`、`client_password` 的含义一致。
- `max_trajectory_length` 映射到 `only_n_most_recent_images`。
- 接受但忽略 `a11y_tree_max_tokens`，因为 M3 只使用截图。
- 其他参数由 `**_unused` 接收。
- `platform="macos"` 时在系统提示词后附加 `MACOS_KEYBOARD_MAPPING`。
- `reset(_logger, vm_ip=...)` 接受但忽略 `vm_ip`，模型请求通过 LLM 端点发送。

`M3Agent.predict(instruction, obs)` 返回 `[response_text, pyautogui_code]`。`WAIT`、`DONE`、`FAIL`、`CALL_USER` 等特殊动作保持为独立字符串，供 `desktop_env.env.step` 识别。

`set_api_log_dir(path)` 为每次模型调用保存 `NNN_<ts>.json`，包含请求、响应和重试元数据。`request_body` 是实际发送的 Anthropic Messages API 内容，包含顶层 `system`、`image.source.base64` 块和 `stop_sequences`，可用 `anthropic.Anthropic().messages.create(**request_body)` 重放。

## 最小示例

```python
from mm_agents.m3 import M3Agent

agent = M3Agent(
    base_url="https://your-anthropic-compatible-endpoint",
    api_key="sk-...",           # or a JWT — header style auto-detected by prefix
    model="<model-name>",
    max_tokens=8192,
    temperature=0.6,
)
agent.reset(runtime_logger)
if hasattr(agent, "set_api_log_dir"):
    agent.set_api_log_dir(os.path.join(example_result_dir, "api_logs"))

response, actions = agent.predict(instruction, obs)
# actions is a list of pyautogui-code strings or special tokens
# ("WAIT" / "DONE" / "FAIL" / "CALL_USER") that desktop_env.env.step accepts
```

`base_url`、`api_key`、`model` 的默认值也可来自 `ANTHROPIC_BASE_URL`、`ANTHROPIC_API_KEY`、`ANTHROPIC_MODEL`。`ANTHROPIC_AUTH_TOKEN` 是密钥变量的旧别名。

如果端点需要额外 HTTP 请求头，如网关路由、`anthropic-beta` 或链路追踪，可通过构造参数 `extra_headers`、运行参数 `--extra_headers` 或环境变量 `ANTHROPIC_EXTRA_HEADERS` 提供 JSON 字典，原样传给 SDK 的 `default_headers`。

```bash
# CLI flag
--extra_headers '{"X-Custom-Routing": "my-upstream"}'

# env var
export ANTHROPIC_EXTRA_HEADERS='{"X-Custom-Routing": "my-upstream"}'
```

## 使用并行运行器

```bash
# Option A — env vars (matches the Anthropic SDK convention)
export ANTHROPIC_BASE_URL=https://api.anthropic.com
export ANTHROPIC_API_KEY=sk-...
export ANTHROPIC_MODEL=<model-name>

PYTHONPATH=. python scripts/python/run_multienv_m3.py \
    --headless --observation_type screenshot \
    --provider_name aws --num_envs 5 --max_steps 100 \
    --result_dir ./results \
    --test_all_meta_path evaluation_examples/test_all.json

# Option B — CLI flags
PYTHONPATH=. python scripts/python/run_multienv_m3.py \
    --base_url https://api.anthropic.com \
    --api_key sk-... \
    --model <model-name> \
    --headless --observation_type screenshot \
    --provider_name aws --num_envs 5 --max_steps 100 \
    --result_dir ./results \
    --test_all_meta_path evaluation_examples/test_all.json
```

## 自动选择认证请求头

| token 前缀 | 请求头 | SDK 参数 |
|---|---|---|
| `sk-...` | `x-api-key: ...` | `api_key=` |
| 其他，如 JWT | `Authorization: Bearer ...` | `auth_token=` |

`M3Agent` 根据前缀自动选择。

## 响应格式重试

`predict()` 最多尝试 `M3_MAX_LLM_RETRIES+1` 次，默认共 3 次。以下情况会重新请求：

1. SDK 自身重试后，`_call_llm` 仍因网络或服务端错误抛出异常。
2. 返回文本非空，但解析不到任何 pyautogui 动作。

重试不消耗环境步数。每步重试记录保存在 `api_logs/NNN_*.json` 的 `_retry_attempts` 中。

## 运行参数

| 参数 | 默认值 | 作用 |
|---|---|---|
| `--enable_proxy` | 关闭 | 允许配置 `"proxy": true` 的任务执行代理初始化；关闭时任务仍运行，但跳过代理步骤 |

临时云端故障（容量、限流、网络波动）的恢复参数：

| 环境变量 | 默认值 | 作用 |
|---|---|---|
| `M3_TASK_MAX_REQUEUE` | `3` | 基础设施临时错误后，单任务重新入队的最大次数 |
| `M3_TASK_REQUEUE_BACKOFF_S` | `5.0` | 重新入队前等待的秒数 |

截图传输编码：

| 环境变量 | 默认值 | 作用 |
|---|---|---|
| `M3_IMAGE_FORMAT` | `JPEG` | 可选 `JPEG` 或 `PNG`；原配置中 JPEG 可显著减小传输体积 |
| `M3_IMAGE_QUALITY` | `90` | JPEG 质量，范围 1–100；PNG 模式忽略 |
