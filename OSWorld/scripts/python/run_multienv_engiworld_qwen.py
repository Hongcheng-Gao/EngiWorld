"""使用 Qwen3-VL（千问）跑 engiworld 评测。

依赖的环境变量
--------------
DashScope 后端（``--api_backend dashscope``，默认）：
  DASHSCOPE_API_KEY    必填。阿里云 DashScope 的 API key。
  DASHSCOPE_BASE_URL   选填。覆盖 DashScope 接口地址，默认
                       ``https://dashscope.aliyuncs.com/api/v1``。

OpenAI 兼容后端（``--api_backend openai``）：
  OPENAI_API_KEY       必填。
  OPENAI_BASE_URL      选填。默认 DashScope 兼容模式
                       ``https://dashscope.aliyuncs.com/compatible-mode/v1``。
                       想接自托管 vLLM/SGLang 时改这个。

命令行参数说明（运行 ``--help`` 可看到完整 argparse 帮助，每项都会自动追加
``(default: X)``。下文给出含义和默认值）：

通用参数（所有 engiworld launcher 共有）：
  --test_config_base_dir   [必填] engiworld task 根目录
  --test_all_meta_path     [必填] eval 清单 JSON；Ubuntu/Windows 不能混跑
  --domain                 (默认 'all')
  --result_dir             (默认 './results')
  --num_envs               (默认 1)
  --headless               (默认 False) 无头模式，批量必开
  --max_steps              (默认 50)
  --max_trajectory_length  (默认 3)
  --sleep_after_execution  (默认 0.0)
  --screen_width           (默认 1920)
  --screen_height          (默认 1080)
  --client_password        (默认 '')
  --temperature            (默认 1.0)（注：Qwen3VLAgent 内部默认 0.0，命令行覆盖）
  --top_p                  (默认 0.9)
  --max_tokens             (默认 1500)（注：Qwen3VLAgent 内部默认 32768，建议调大）
  --log_level              (默认 'INFO')
  --provider_name          (默认/仅支持 'msh_sandbox')

千问专属参数：
  --model              [必填] Qwen 模型 id，例如 'qwen3-vl-plus'
  --action_space       (默认/仅支持 'pyautogui')
  --observation_type   (默认/仅支持 'screenshot')
  --coordinate_type    (默认 'relative') 点击坐标解码：
                         relative — 0~1000 相对坐标
                         qwen25   — Qwen2.5-VL 原生像素坐标格式
  --history_n          (默认 4) prompt 里保留几张历史截图
  --add_thought_prefix (默认 False) 在 assistant 输出前注入 thought 前缀
  --api_backend        (默认 'dashscope') SDK 后端，可选 'dashscope' / 'openai'
  --enable_thinking    (默认 False) DashScope 后端的 thinking 模式（CoT）；
                       只在 dashscope 后端有效
  --thinking_budget    (默认 32768) thinking 模式下 reasoning 部分的 token 预算

调用示例（从 Engiworld 工程根目录运行；DashScope 最常用）
---------------------------------------------------------
    cd /home/lihaoyang/code/Engiworld
    export DASHSCOPE_API_KEY=sk-...
    python OSWorld/scripts/python/run_multienv_engiworld_qwen.py \\
        --test_config_base_dir task/task-v \\
        --test_all_meta_path   task/task-v/eval_list_ubuntu.json \\
        --model qwen3-vl-plus --enable_thinking \\
        --num_envs 4 --headless --max_steps 100 --max_tokens 32768 \\
        --result_dir results_engiworld_qwen

调用示例（自托管 vLLM 走 OpenAI 协议）
--------------------------------------
    cd /home/lihaoyang/code/Engiworld
    export OPENAI_API_KEY=anything
    export OPENAI_BASE_URL=http://your-vllm-server/v1
    python OSWorld/scripts/python/run_multienv_engiworld_qwen.py \\
        --api_backend openai --model my-qwen3vl-deploy \\
        --test_config_base_dir task/task-v \\
        --test_all_meta_path   task/task-v/eval_list_ubuntu.json \\
        --num_envs 4 --headless --max_steps 100

注意 cwd
--------
所有 launcher 都从 ``/home/lihaoyang/code/Engiworld`` 这个工程根目录运行。
``logs/`` 和 ``--result_dir`` 都是 cwd 相对路径，会落在 Engiworld 根下。
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from _engiworld_runtime import (
    add_common_engiworld_args,
    require_msh_sandbox,
    run_eval_pool,
    setup_logging,
)

import lib_run_single
from mm_agents.qwen3vl_agent import Qwen3VLAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="engiworld + Qwen3-VL 评测入口",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_common_engiworld_args(parser)
    parser.add_argument(
        "--model", type=str, required=True,
        help="Qwen 模型 id，例如 'qwen3-vl-plus'。",
    )
    parser.add_argument(
        "--action_space", type=str, default="pyautogui", choices=["pyautogui"],
        help="动作空间，固定 'pyautogui'。",
    )
    parser.add_argument(
        "--observation_type", type=str, default="screenshot",
        choices=["screenshot"],
        help="观察类型，Qwen3-VL 只支持 'screenshot'。",
    )
    parser.add_argument(
        "--coordinate_type", type=str, default="relative",
        choices=["relative", "qwen25"],
        help="点击坐标解码方式。Qwen3-VL 通常用 'relative'。",
    )
    parser.add_argument(
        "--history_n", type=int, default=4,
        help="prompt 里保留几张历史截图。",
    )
    parser.add_argument(
        "--add_thought_prefix", action="store_true",
        help="在 assistant 输出前注入 thought 前缀，引导模型先思考。",
    )
    parser.add_argument(
        "--api_backend", type=str, default="dashscope",
        choices=["dashscope", "openai"],
        help="SDK 后端：dashscope 走原生 API，openai 走 OpenAI 兼容协议。",
    )
    parser.add_argument(
        "--enable_thinking", action="store_true",
        help="DashScope 后端的 thinking 模式（CoT）。",
    )
    parser.add_argument(
        "--thinking_budget", type=int, default=32768,
        help="thinking 模式下 reasoning 部分的 token 预算。",
    )
    return parser.parse_args()


def build_agent(args: argparse.Namespace, _env, os_type: str) -> Qwen3VLAgent:
    return Qwen3VLAgent(
        platform=os_type.lower(),
        model=args.model,
        max_tokens=args.max_tokens,
        top_p=args.top_p,
        temperature=args.temperature,
        action_space=args.action_space,
        observation_type=args.observation_type,
        history_n=args.history_n,
        add_thought_prefix=args.add_thought_prefix,
        coordinate_type=args.coordinate_type,
        api_backend=args.api_backend,
        enable_thinking=args.enable_thinking,
        thinking_budget=args.thinking_budget,
        max_retries=args.llm_retries,
    )


def main() -> None:
    args = parse_args()
    require_msh_sandbox(args.provider_name)
    if args.api_backend == "dashscope":
        if not os.environ.get("DASHSCOPE_API_KEY"):
            raise RuntimeError(
                "缺少 DASHSCOPE_API_KEY；--api_backend=dashscope 必须配置。"
            )
    elif args.api_backend == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError(
                "缺少 OPENAI_API_KEY；--api_backend=openai 必须配置。"
            )
    else:  # 防御：argparse 已限定 choices
        raise NotImplementedError(
            f"engiworld Qwen launcher 不支持 api_backend={args.api_backend!r}。"
        )
    setup_logging(args, "engiworld-qwen")
    run_eval_pool(
        args,
        build_agent_fn=build_agent,
        run_single_fn=lib_run_single.run_single_example,
    )


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    main()
