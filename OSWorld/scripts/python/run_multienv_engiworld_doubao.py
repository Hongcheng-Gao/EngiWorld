"""使用豆包 / UI-TARS（Doubao）跑 engiworld 评测。

依赖的环境变量
--------------
DOUBAO_API_URL    必填。豆包 OpenAI 兼容接口的 base_url（本身就是 base_url，
                  不是 override）。例如官方
                  ``https://ark.cn-beijing.volces.com/api/v3`` 或自托管
                  UI-TARS endpoint。uitars_agent.py:443 写死从 env 读。
DOUBAO_API_KEY    必填。豆包/UI-TARS 服务的 API key。

命令行参数说明（运行 ``--help`` 可看到完整 argparse 帮助，每项都会自动追加
``(default: X)``。下文给出含义和默认值）：

通用参数（所有 engiworld launcher 共有）：
  --test_config_base_dir   [必填] engiworld task 根目录
  --test_all_meta_path     [必填] eval 清单 JSON；Ubuntu/Windows 不能混跑
  --domain                 (默认 'all')
  --result_dir             (默认 './results')
  --num_envs               (默认 1)
  --headless               (默认 False) 无头模式，批量必开
  --max_steps              (默认 50) UI-TARS 纯视觉 grounding 建议 50~100
  --max_trajectory_length  (默认 3)
  --sleep_after_execution  (默认 0.0)
  --screen_width           (默认 1920)
  --screen_height          (默认 1080)
  --client_password        (默认 '')
  --temperature            (默认 1.0)（注：UITARSAgent 内部默认 0.0，命令行覆盖）
  --top_p                  (默认 0.9)
  --max_tokens             (默认 1500)
  --log_level              (默认 'INFO')
  --provider_name          (默认/仅支持 'msh_sandbox')

豆包专属参数：
  --model              [必填] UI-TARS 模型 id，例如 'uitars-72b-dpo'
  --action_space       (默认/仅支持 'pyautogui')
  --observation_type   (默认 'screenshot') 可选：
                         screenshot / a11y_tree / screenshot_a11y_tree / som

UI-TARS 内部 runtime_conf 已在 build_agent 里固定为：
  infer_mode=qwen2vl_user, prompt_style=qwen2vl_user, language=Chinese,
  history_n=5, screen_size 跟随 --screen_width/--screen_height。

调用示例（从 Engiworld 工程根目录运行）
---------------------------------------
    cd /home/lihaoyang/code/Engiworld
    export DOUBAO_API_URL=https://ark.cn-beijing.volces.com/api/v3
    export DOUBAO_API_KEY=...
    python OSWorld/scripts/python/run_multienv_engiworld_doubao.py \\
        --test_config_base_dir task/task-v \\
        --test_all_meta_path   task/task-v/eval_list_ubuntu.json \\
        --model uitars-72b-dpo --num_envs 4 --headless --max_steps 100 \\
        --result_dir results_engiworld_doubao

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
from mm_agents.uitars_agent import UITARSAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="engiworld + 豆包 UI-TARS 评测入口",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_common_engiworld_args(parser)
    parser.add_argument(
        "--model", type=str, required=True,
        help="UI-TARS 模型 id，例如 'uitars-72b-dpo'。",
    )
    parser.add_argument(
        "--action_space", type=str, default="pyautogui", choices=["pyautogui"],
        help="动作空间，固定 'pyautogui'。",
    )
    parser.add_argument(
        "--observation_type", type=str, default="screenshot",
        choices=["screenshot", "a11y_tree", "screenshot_a11y_tree", "som"],
        help="观察类型；带 a11y_tree 的需要 VM 暴露无障碍树。",
    )
    return parser.parse_args()


def build_agent(args: argparse.Namespace, _env, os_type: str) -> UITARSAgent:
    runtime_conf = {
        "infer_mode": "qwen2vl_user",
        "prompt_style": "qwen2vl_user",
        "input_swap": True,
        "language": "Chinese",
        "max_steps": args.max_steps,
        "history_n": 5,
        "screen_height": args.screen_height,
        "screen_width": args.screen_width,
    }
    return UITARSAgent(
        model=args.model,
        platform=os_type.lower(),
        max_tokens=args.max_tokens,
        top_p=args.top_p,
        temperature=args.temperature,
        action_space=args.action_space,
        observation_type=args.observation_type,
        max_trajectory_length=args.max_trajectory_length,
        runtime_conf=runtime_conf,
        max_retries=args.llm_retries,
    )


def main() -> None:
    args = parse_args()
    require_msh_sandbox(args.provider_name)
    missing = [v for v in ("DOUBAO_API_URL", "DOUBAO_API_KEY") if not os.environ.get(v)]
    if missing:
        raise RuntimeError(
            f"engiworld 豆包 launcher 缺少环境变量: {missing!r}（DOUBAO_API_URL 是 base_url 本身）。"
        )
    setup_logging(args, "engiworld-doubao")
    run_eval_pool(
        args,
        build_agent_fn=build_agent,
        run_single_fn=lib_run_single.run_single_example,
    )


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    main()
