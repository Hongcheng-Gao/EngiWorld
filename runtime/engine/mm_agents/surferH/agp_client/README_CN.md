[English](README.md) | [简体中文](README_CN.md)

# agp-client

AgP（Agent Platform）客户端，用于创建轨迹并轮询其完成状态。

## 配置

使用 [uv](https://docs.astral.sh/uv/) 安装依赖：

```bash
uv sync
```

## 运行智能体

```python
import asyncio
from agp_client import AgPClient, AgPTaskRequest


async def main():
    async with AgPClient(api_key="your-api-key") as client:
        id = await client.create_trajectory(
            agent_identifier="sagent-prerelease",
            task=AgPTaskRequest(
                objective="What are the news?"
            ),
        )
        result = await client.wait_for_completion(id)
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
```

执行：

```bash
uv run python your_script.py
```
