[English](README.md) | [简体中文](README_CN.md)

# agp-client

Client for AgP (Agent Platform) — create trajectories and poll for completion.

## Setup

Install dependencies with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

## Running an Agent

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

Run it:

```bash
uv run python your_script.py
```
