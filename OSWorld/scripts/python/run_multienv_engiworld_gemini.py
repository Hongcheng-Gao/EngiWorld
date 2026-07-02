"""使用 Google Gemini（经由通用 PromptAgent）跑 engiworld 评测。

OSWorld 还没有专门的 Gemini computer-use agent；本入口走 ``mm_agents.agent.PromptAgent``
里的 Gemini 分支。模型 id 不做白名单校验，由 PromptAgent / 后端 API 自行决定是否接受。

依赖的环境变量
--------------
GENAI_API_KEY      必填。Gemini API key（PromptAgent 内部通过 ``google.genai.Client``
                   读取）。
GENAI_BASE_URL     选填。OpenAI/Vertex 兼容代理的根地址，例如
                   ``https://openai.app.msh.team/``；不设则走 Google 默认 endpoint。
GENAI_API_VERSION  选填。``v1beta`` / ``v1``，默认 ``v1beta``。仅在 GENAI_BASE_URL
                   被设置时生效。

命令行参数说明（运行 ``--help`` 可看到完整 argparse 帮助，每项都会自动追加
``(default: X)``。下文给出含义和默认值）：

通用参数（所有 engiworld launcher 共有）：
  --test_config_base_dir   [必填] engiworld task 根目录
  --test_all_meta_path     [必填] eval 清单 JSON；Ubuntu/Windows 不能混跑
  --domain                 (默认 'all')
  --result_dir             (默认 './results')
  --num_envs               (默认 1)
  --headless               (默认 False) 无头模式，批量必开
  --max_steps              (默认 50) PromptAgent 不擅长长链路，无需拉太大
  --max_trajectory_length  (默认 3)
  --sleep_after_execution  (默认 0.0)
  --screen_width           (默认 1920)
  --screen_height          (默认 1080)
  --client_password        (默认 '') 此处为空时 PromptAgent 内部回退到 'password'
  --temperature            (默认 1.0)
  --top_p                  (默认 0.9)
  --max_tokens             (默认 1500)
  --log_level              (默认 'INFO')
  --provider_name          (默认/仅支持 'msh_sandbox')

Gemini 专属参数：
  --model              [必填] Gemini 模型 id
  --action_space       (默认 'pyautogui') 可选：
                         pyautogui    — 输出 Python 代码（推荐）
                         computer_13  — OSWorld 自定义的 13 个枚举动作
  --observation_type   (默认 'screenshot') 可选：
                         screenshot           — 仅截图
                         a11y_tree            — 仅无障碍树
                         screenshot_a11y_tree — 截图 + 无障碍树
                         som                  — set-of-mark 标注的截图

调用示例（从 Engiworld 工程根目录运行）
---------------------------------------
    cd /home/lihaoyang/code/Engiworld
    export GENAI_API_KEY=sk-...
    export GENAI_BASE_URL=https://openai.app.msh.team/   # 可选
    python OSWorld/scripts/python/run_multienv_engiworld_gemini.py \\
        --test_config_base_dir task/task-v \\
        --test_all_meta_path   task/task-v/eval_list_ubuntu.json \\
        --model gemini-3-flash-preview --observation_type screenshot \\
        --num_envs 4 --headless --max_steps 50 \\
        --result_dir results_engiworld_gemini

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
from mm_agents.agent import PromptAgent

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="engiworld + Gemini（经 PromptAgent）评测入口",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_common_engiworld_args(parser)
    parser.add_argument(
        "--model", type=str, required=True,
        help="Gemini 模型 id。",
    )
    parser.add_argument(
        "--action_space", type=str, default="pyautogui",
        choices=["pyautogui", "computer_13"],
        help="动作空间。'pyautogui' 输出 Python 代码；'computer_13' 输出枚举动作。",
    )
    parser.add_argument(
        "--observation_type", type=str, default="screenshot",
        choices=["screenshot", "a11y_tree", "screenshot_a11y_tree", "som"],
        help="观察类型。",
    )
    return parser.parse_args()


def build_agent(args: argparse.Namespace, _env, os_type: str) -> PromptAgent:
    return PromptAgent(
        platform=os_type.lower(),
        model=args.model,
        max_tokens=args.max_tokens,
        top_p=args.top_p,
        temperature=args.temperature,
        action_space=args.action_space,
        observation_type=args.observation_type,
        max_trajectory_length=args.max_trajectory_length,
        client_password=args.client_password or "password",
        max_retries=args.llm_retries,
    )


def main() -> None:
    args = parse_args()
    require_msh_sandbox(args.provider_name)
    if not os.environ.get("GENAI_API_KEY"):
        raise RuntimeError(
            "缺少 GENAI_API_KEY 环境变量；engiworld Gemini launcher 必须配置。"
        )
    setup_logging(args, "engiworld-gemini")
    run_eval_pool(
        args,
        build_agent_fn=build_agent,
        run_single_fn=lib_run_single.run_single_example,
    )


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    main()
