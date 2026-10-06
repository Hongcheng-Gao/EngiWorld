[English](README.md) | [简体中文](README_CN.md)

# EngiWorld 环境引擎

本目录实现 EngiWorld 的环境和执行层。安装和运行请进入上一级[运行框架目录](../README_CN.md)，或查看仓库[快速开始](../../README_CN.md)。

- `desktop_env/`：环境生命周期、后端、任务初始化、观察、动作和评分集成。
- `lib_run_single.py`：GUI/CLI 任务循环、轨迹记录、终端动作和最终产物评分。
- `mm_agents/cli_policy.py`：工程 CLI 工具与产物完整性规则。
- `mm_agents/`：交互提示词、参考图配置、解析和智能体工具。通用模型接口位于 [`src/engiworld/agents/`](../src/engiworld/agents/)。
- [`../../task/`](../../task/)：EngiWorld 任务定义、输入文件与工程产物评分器。

在上一级 `runtime/` 目录使用 `python -m engiworld.local_eval` 运行评测。组件许可证见[第三方声明](../../THIRD_PARTY_NOTICES.md)。
