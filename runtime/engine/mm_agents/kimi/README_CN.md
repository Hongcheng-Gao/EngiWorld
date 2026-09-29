[English](README.md) | [简体中文](README_CN.md)

# Kimi 智能体

`KimiAgent` 使用 Moonshot AI 的 Kimi 模型，通过截图观察桌面，输出 `pyautogui` 代码供 GUI 执行器运行。本页记录该独立适配器在 OSWorld 上评测 Kimi K2.5 和 K2.6 的设置。

## 文件

`kimi_agent.py` 为智能体实现。启动脚本位于 `scripts/python/run_multienv_kimi_k25.py`，K2.6 复用 K2.5 的启动脚本。

## K2.5 与 K2.6 的设置差异

两组评测主要区别是传给模型的图像历史长度，以及服务平台施加的限制。

### 1. `max_image_history_length`

- Kimi K2.5：`3`。
- Kimi K2.6：`8`–`10`。

K2.6 对较长多图上下文的处理更稳定，因此使用更长的图像历史；K2.5 保持默认值 `3`。

### 2. `temperature`

- 此配置中的 Moonshot AI K2.6 托管接口只接受 `temperature=1`。
- 自托管评测使用 `0`，便于比较重复运行。

使用托管端点复现时，由于温度固定为 `1`，不同运行之间可能存在波动。

### 3. 思考模式

K2.5 和 K2.6 都启用 `--thinking`。`KimiAgent` 内部会相应切换系统提示词和历史模板：`SYSTEM_PROMPT_THINKING`、`THOUGHT_HISTORY_TEMPLATE_THINKING`。

### 4. 其他设置

`max_tokens`、`top_p`、`coordinate_type`、`action_space`、`observation_type` 和屏幕尺寸等保持智能体默认值。

## 复现评测

启动器从 `KIMI_API_KEY` 环境变量读取密钥。端点写在 `KimiAgent.call_llm` 中。

### Kimi K2.6

```bash
export KIMI_API_KEY=your_kimi_api_key_here

PYTHONPATH=. python scripts/python/run_multienv_kimi_k25.py \
    --headless \
    --observation_type screenshot \
    --model kimi-k2.6 \
    --result_dir ./results \
    --test_all_meta_path evaluation_examples/test_nogdrive.json \
    --max_steps 100 \
    --num_envs 30 \
    --max_image_history_length 8 \
    --temperature 0 \
    --thinking
```

### Kimi K2.5

```bash
export KIMI_API_KEY=your_kimi_api_key_here

PYTHONPATH=. python scripts/python/run_multienv_kimi_k25.py \
    --headless \
    --observation_type screenshot \
    --model kimi-k2.5 \
    --result_dir ./results \
    --test_all_meta_path evaluation_examples/test_nogdrive.json \
    --max_steps 100 \
    --num_envs 32 \
    --max_image_history_length 3 \
    --temperature 0 \
    --thinking
```

需要更长视觉历史时，可将 K2.6 的 `--max_image_history_length` 提高到 `10`；`8` 是这组测试使用范围的下限。

## 已发布轨迹

原适配器的 K2.5 和 K2.6 评测轨迹已提交至 Hugging Face 的 OSWorld verified trajectories 数据集：

<https://huggingface.co/datasets/xlangai/ubuntu_osworld_verified_trajs>
