"""使用 Kimi（Moonshot Chat Completions API）跑 engiworld 评测。

依赖的环境变量
--------------
KIMI_API_KEY    必填。Moonshot 的 API key（也可指向兼容 Moonshot Chat Completions
                协议的自建/代理服务的 token）。
KIMI_BASE_URL   选填。OpenAI 约定的 base_url（client 会自动追加
                ``/chat/completions``），默认 ``https://api.moonshot.ai/v1``
                （见 mm_agents/kimi/kimi_agent.py 的 call_llm）。
                想接 OpenAI 兼容代理 / 自托管 Kimi 时改这个。

命令行参数说明（运行 ``--help`` 可看到完整 argparse 帮助，每项都会自动追加
``(default: X)``。下文给出含义和默认值）：

通用参数（所有 engiworld launcher 共有）：
  --test_config_base_dir   [必填] engiworld task 根目录，例如
                           /home/lihaoyang/code/Engiworld/task/task-v
  --test_all_meta_path     [必填] eval 清单 JSON：{"<app>": ["<task-id>", ...]}；
                           Ubuntu/Windows 不能混跑
  --domain                 (默认 'all') 只跑某个软件，'all' 表示全跑
  --result_dir             (默认 './results') 输出根目录，最终路径
                           <result_dir>/<action_space>/<observation_type>/<model>/<domain>/<task-id>/
  --num_envs               (默认 1) 并行 VM 数；4 台通常够 desktop 评测用
  --headless               (默认 False) 无头模式启动 VM；批量评测必须开
  --max_steps              (默认 50) 单 task 最多步数；CAD 类建议 50~100
  --max_trajectory_length  (默认 3) agent 上下文里保留几步历史
  --sleep_after_execution  (默认 0.0) 每条 action 后等几秒让 UI 稳定；卡顿建议 1~3
  --screen_width           (默认 1920) VM 屏幕宽度（像素）
  --screen_height          (默认 1080) VM 屏幕高度（像素）
  --client_password        (默认 '') VM 内 sudo/解锁屏密码
                           （Ubuntu 镜像常见 'osworld-public-evaluation'）
  --temperature            (默认 1.0) LLM 采样温度
  --top_p                  (默认 0.95) nucleus sampling 阈值
  --max_tokens             (默认 4096) LLM 回复 token 上限
  --log_level              (默认 'INFO') stdout 日志级别；文件日志固定 DEBUG
  --provider_name          (默认/仅支持 'msh_sandbox')

Kimi 专属参数：
  --model                  [必填] Kimi 模型 id，例如 'kimi-k2.5'
  --action_space           (默认 'pyautogui') 可选 'pyautogui' / 'computer_13'
                             pyautogui   — 输出 pyautogui 代码块（Kimi 原生）
                             computer_13 — 输出 13 个语义动作 JSON dict
                                           （绝对像素坐标，由 DesktopEnv 直接派发）
  --observation_type       (默认 'screenshot') 可选
                             screenshot / a11y_tree / screenshot_a11y_tree
                             a11y 文本只附在当前 turn，历史保持原样
  --coordinate_type        (默认 'relative') 仅 pyautogui 路径生效；computer_13 路径
                           固定用绝对像素，本参数被忽略。
                             relative — 0~1000 的相对坐标（Kimi-VL 默认）
                             absolute — 直接像素坐标
                             qwen25   — Qwen2.5-VL 风格（与 Kimi 不兼容，留作 fallback）
  --max_image_history_length
                           (默认 3) prompt 里保留几张历史截图，越多越占 token
  --thinking               (默认 False) 开启 Kimi 的 reasoning_content 思考模式；
                           复杂 CAD 任务建议开

调用示例（从 Engiworld 工程根目录运行）
---------------------------------------
    cd /home/lihaoyang/code/Engiworld
    export KIMI_API_KEY=sk-...
    python OSWorld/scripts/python/run_multienv_engiworld_kimi.py \\
        --test_config_base_dir task/task-v \\
        --test_all_meta_path   task/task-v/eval_list_ubuntu.json \\
        --model kimi-k2.5 --thinking --num_envs 4 --headless \\
        --max_steps 100 --result_dir results_engiworld_kimi

注意 cwd
--------
所有 launcher 都设计为从 ``/home/lihaoyang/code/Engiworld`` 这个工程根目录运行。
``logs/`` 和 ``--result_dir`` 都是 cwd 相对路径，会落在 Engiworld 根下。
脚本内部用 ``__file__`` 拼出 OSWorld 包路径（``sys.path.insert(0, ".../OSWorld")``），
所以 ``import desktop_env / mm_agents`` 不依赖 cwd。
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
from mm_agents.kimi import KimiAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="engiworld + Kimi 评测入口",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_common_engiworld_args(parser)
    for action in parser._actions:
        if action.dest == "top_p":
            action.default = 0.95
        elif action.dest == "max_tokens":
            action.default = 4096
    parser.add_argument(
        "--model", type=str, required=True,
        help="Kimi 模型 id，例如 'kimi-k2.5'。",
    )
    parser.add_argument(
        "--action_space", type=str, default="pyautogui",
        choices=["pyautogui", "computer_13"],
        help="动作空间。pyautogui = Kimi 原生（输出 pyautogui 代码块）；"
             "computer_13 = 输出 13 个语义动作 JSON dict。",
    )
    parser.add_argument(
        "--observation_type", type=str, default="screenshot",
        choices=["screenshot", "a11y_tree", "screenshot_a11y_tree"],
        help="观察类型。screenshot = 纯截图；a11y_tree = 纯 a11y 文本；"
             "screenshot_a11y_tree = 截图 + a11y 文本（两路融合）。som 不支持。",
    )
    parser.add_argument(
        "--coordinate_type", type=str, default="relative",
        choices=["relative", "absolute", "qwen25"],
        help="点击坐标解码方式。Kimi-VL 默认 'relative'（0~1000 相对坐标）。",
    )
    parser.add_argument(
        "--max_image_history_length", type=int, default=3,
        help="prompt 里保留几张历史截图（越多 token 越贵）。",
    )
    parser.add_argument(
        "--thinking", action="store_true",
        help="开启 Kimi 思考模式（reasoning_content）。复杂任务建议开。",
    )
    return parser.parse_args()


def build_agent(args: argparse.Namespace, _env, os_type: str) -> KimiAgent:
    return KimiAgent(
        model=args.model,
        max_steps=args.max_steps,
        max_image_history_length=args.max_image_history_length,
        platform=os_type.lower(),
        max_tokens=args.max_tokens,
        top_p=args.top_p,
        temperature=args.temperature,
        action_space=args.action_space,
        observation_type=args.observation_type,
        screen_size=(args.screen_width, args.screen_height),
        coordinate_type=args.coordinate_type,
        password=args.client_password or "osworld-public-evaluation",
        thinking=args.thinking,
        max_retries=args.llm_retries,
    )


def main() -> None:
    args = parse_args()
    require_msh_sandbox(args.provider_name)
    if not os.environ.get("KIMI_API_KEY"):
        raise RuntimeError("缺少 KIMI_API_KEY 环境变量；engiworld Kimi launcher 必须配置。")
    setup_logging(args, "engiworld-kimi")
    run_eval_pool(
        args,
        build_agent_fn=build_agent,
        run_single_fn=lib_run_single.run_single_example_kimi,
    )


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    main()
