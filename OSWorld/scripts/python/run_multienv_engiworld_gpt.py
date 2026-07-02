"""使用 OpenAI GPT-5.4（Responses API + computer-use tool）跑 engiworld 评测。

依赖的环境变量
--------------
OPENAI_API_KEY    必填。OpenAI API key（必须有 computer-use 权限）。
OPENAI_BASE_URL   选填。OpenAI 兼容地址。openai SDK 会自动读这个 env，
                  gpt54_agent 里 ``OpenAI(api_key=...)`` 没显式传 base_url，
                  所以设置即生效。Azure 兼容代理 / 私有部署用得上。

命令行参数说明（运行 ``--help`` 可看到完整 argparse 帮助，每项都会自动追加
``(default: X)``。下文给出含义和默认值）：

通用参数（所有 engiworld launcher 共有）：
  --test_config_base_dir   [必填] engiworld task 根目录
  --test_all_meta_path     [必填] eval 清单 JSON；Ubuntu/Windows 不能混跑
  --domain                 (默认 'all')
  --result_dir             (默认 './results')
  --num_envs               (默认 1)
  --headless               (默认 False) 无头模式，批量必开
  --max_steps              (默认 50) computer-use 建议 50~100
  --max_trajectory_length  (默认 3)
  --sleep_after_execution  (默认 0.0) CAD 卡顿建议 1~3
  --screen_width           (默认 1920)
  --screen_height          (默认 1080)
  --client_password        (默认 '') GPT54Agent 在 msh_sandbox 下回退到 'password'
  --temperature            (默认 1.0)
  --top_p                  (默认 0.9)
  --max_tokens             (默认 1500) GPT-5.4 通常不设，由 reasoning_effort 控
  --log_level              (默认 'INFO')
  --provider_name          (默认/仅支持 'msh_sandbox')

GPT-5.4 专属参数：
  --model              [必填] OpenAI 模型 id，例如 'gpt-5.4'
  --action_space       (默认/仅支持 'pyautogui')
  --observation_type   (默认/仅支持 'screenshot')
  --reasoning_effort   (默认 'xhigh') 思考强度档位：
                         none    — 不思考，最快最便宜
                         low     — 浅思考
                         medium  — 中等
                         high    — 深思考
                         xhigh   — 超深思考
                       工程任务建议 high 或 xhigh

调用示例（从 Engiworld 工程根目录运行）
---------------------------------------
    cd /home/lihaoyang/code/Engiworld
    export OPENAI_API_KEY=sk-...
    python OSWorld/scripts/python/run_multienv_engiworld_gpt.py \\
        --test_config_base_dir task/task-v \\
        --test_all_meta_path   task/task-v/eval_list_ubuntu.json \\
        --model gpt-5.4 --reasoning_effort xhigh \\
        --num_envs 4 --headless --max_steps 100 \\
        --result_dir results_engiworld_gpt

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
from mm_agents.gpt54_agent import GPT54Agent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="engiworld + OpenAI GPT-5.4 computer-use 评测入口",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_common_engiworld_args(parser)
    parser.add_argument(
        "--model", type=str, required=True,
        help="OpenAI 模型 id，例如 'gpt-5.4'。",
    )
    parser.add_argument(
        "--action_space", type=str, default="pyautogui", choices=["pyautogui"],
        help="动作空间，固定 'pyautogui'。",
    )
    parser.add_argument(
        "--observation_type", type=str, default="screenshot",
        choices=["screenshot"],
        help="观察类型，GPT-5.4 computer-use 只支持 'screenshot'。",
    )
    parser.add_argument(
        "--reasoning_effort", type=str, default="xhigh",
        choices=["none", "low", "medium", "high", "xhigh"],
        help="思考强度（none/low/medium/high/xhigh）。工程任务建议 high+。",
    )
    return parser.parse_args()


def build_agent(args: argparse.Namespace, env, os_type: str) -> GPT54Agent:
    return GPT54Agent(
        env=env,
        platform=os_type.lower(),
        model=args.model,
        max_tokens=args.max_tokens if args.max_tokens else None,
        top_p=args.top_p,
        temperature=args.temperature,
        action_space=args.action_space,
        observation_type=args.observation_type,
        max_trajectory_length=args.max_trajectory_length,
        client_password=args.client_password,
        provider_name=args.provider_name,
        screen_width=args.screen_width,
        screen_height=args.screen_height,
        sleep_after_execution=args.sleep_after_execution,
        reasoning_effort=args.reasoning_effort,
        max_retries=args.llm_retries,
    )


def main() -> None:
    args = parse_args()
    require_msh_sandbox(args.provider_name)
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("缺少 OPENAI_API_KEY 环境变量；engiworld GPT launcher 必须配置。")
    setup_logging(args, "engiworld-gpt")
    run_eval_pool(
        args,
        build_agent_fn=build_agent,
        run_single_fn=lib_run_single.run_single_example_gpt54,
    )


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    main()
