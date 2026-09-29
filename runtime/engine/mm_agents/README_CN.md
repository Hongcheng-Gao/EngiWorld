[English](README.md) | [简体中文](README_CN.md)

# 智能体

## 基于提示词的智能体

### 支持的模型

此目录的基础智能体支持以下模型：

- `GPT-3.5`（gpt-3.5-turbo-16k 等）
- `GPT-4`（gpt-4-0125-preview、gpt-4-1106-preview 等）
- `GPT-4V`（gpt-4-vision-preview 等）
- `Gemini-Pro`
- `Gemini-Pro-Vision`
- `Claude-3, 2`（claude-3-haiku-2024030、claude-3-sonnet-2024022 等）

也包含开源社区模型：

- `Mixtral 8x7B`
- `QWEN`、`QWEN-VL`
- `CogAgent`
- `Llama3`

后续会继续集成其他基础模型。

### 使用方法

```python
from mm_agents.agent import PromptAgent

agent = PromptAgent(
    model="gpt-4-vision-preview",
    observation_type="screenshot",
)
agent.reset()
# say we have an instruction and observation
instruction = "Please help me to find the nearest restaurant."
obs = {"screenshot": open("path/to/observation.jpg", 'rb').read()}
response, actions = agent.predict(
    instruction,
    obs
)
```

### 观察空间与动作空间

支持的观察空间：

- `a11y_tree`：当前屏幕的无障碍树。
- `screenshot`：当前屏幕截图。
- `screenshot_a11y_tree`：截图及无障碍树信息。
- `som`：当前屏幕的 Set-of-Mark 标记，包含表格元数据。

支持的动作空间：

- `pyautogui`：包含有效 `pyautogui` 调用的 Python 代码。
- `computer_13`：一组预定义的枚举动作。

向智能体提供观察时，`obs` 应为包含对应信息的字典：

```python
# continue from the previous code snippet
obs = {
    "screenshot": open("path/to/observation.jpg", 'rb').read(),
    "a11y_tree": ""  # [a11y_tree data]
}
response, actions = agent.predict(
    instruction,
    obs
)
```

## 高效智能体、Q* 智能体等

后续会继续更新。
