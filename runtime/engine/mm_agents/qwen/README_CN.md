[English](README.md) | [简体中文](README_CN.md)

# Qwen 智能体

本包包含用于 OSWorld 的兼容 OpenAI 接口的 Qwen 视觉智能体。

## 智能体

`QwenAgent` 提供扩展动作、DashScope `enable_thinking` 处理和不可行任务的退出逻辑。新代码使用以下导入方式：

```python
from mm_agents.qwen import QwenAgent
```

## API 配置

智能体使用兼容 OpenAI 的 Chat Completions 端点：

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export OPENAI_API_KEY=dummy
```

可调整以下运行环境变量：

- `OSWORLD_MAX_RETRY_TIMES`
- `OSWORLD_OPENAI_TIMEOUT`
- `OSWORLD_HTTP_CONNECT_TIMEOUT`
- `OSWORLD_HTTP_READ_TIMEOUT`

## 运行示例

```bash
python scripts/python/run_multienv_qwen.py \
  --model qwen3.7-plus \
  --base_url "$OPENAI_BASE_URL" \
  --api_key "$OPENAI_API_KEY"
```
