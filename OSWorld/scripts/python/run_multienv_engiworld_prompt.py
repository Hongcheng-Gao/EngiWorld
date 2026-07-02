"""使用 OSWorld 通用 PromptAgent 跑 engiworld 评测。

PromptAgent (``mm_agents.agent.PromptAgent``) 是 OSWorld 老牌的"纯 prompt"式 agent：
不依赖任何厂商原生 computer-use tool，靠 system prompt + 自家 parser 把模型回复
解析成 pyautogui 代码 / bash / python 脚本。本 launcher 只暴露两档评测模式：

    --eval-mode gui  观察：screenshot ； 动作：pyautogui-only（已加固 AST 黑名单）
    --eval-mode cli  观察：上轮 terminal stdout + 可选 readimg 图像 ； 动作：bash / python / readimg

模型 / 后端路由（按 ``model`` 前缀分支）
----------------------------------------
PromptAgent 内部通过 ``self.model.startswith(...)`` 选择调哪家 API：

    gpt* / kimi* / glm* / qwen3.6* / doubao*  -> OpenAI 兼容 chat/completions
                                                  (OPENAI_API_KEY / OPENAI_BASE_URL)
    claude* -> Anthropic Messages   (ANTHROPIC_API_KEY)
    gemini* -> google-genai SDK     (GENAI_API_KEY / GENAI_BASE_URL)
    qwen*   -> DashScope SDK，仅认白名单：
              {qwen-vl-plus, qwen-vl-max,
               qwen-turbo, qwen-plus, qwen-max,
               qwen-max-0428/-0403/-0107/-longcontext}

注：``kimi*`` / ``glm*`` / ``qwen3.6*`` 走的是 msh 网关的 OpenAI 兼容协议；如果用其它
代理或自部署，需要相应调整 ``OPENAI_BASE_URL``。前缀都不匹配的 model（例如纯 ``qwen3-vl``）
会被 PromptAgent 抛 ``Invalid model``。

依赖的环境变量
--------------
按模型前缀按需配置（launcher 启动时会校验）：
  OPENAI_API_KEY     (gpt*)         必填
  OPENAI_BASE_URL    (gpt*)         选填，msh 网关填 ``https://openai.app.msh.team/v1``
  ANTHROPIC_API_KEY  (claude*)      必填
  ANTHROPIC_BASE_URL (claude*)      选填
  GENAI_API_KEY      (gemini*)      必填
  GENAI_BASE_URL     (gemini*)      选填
  DASHSCOPE_API_KEY  (qwen*)        必填

调用示例（从 Engiworld 工程根目录运行）
---------------------------------------
    cd /home/lihaoyang/code/Engiworld
    set -a; source .env.lihaoyang; set +a
    python OSWorld/scripts/python/run_multienv_engiworld_prompt.py \\
        --test_config_base_dir task/task-v \\
        --test_all_meta_path   task/task-v/eval_list_test.json \\
        --model gpt-5.5 \\
        --eval-mode gui \\
        --num_envs 4 --headless --max_steps 100 \\
        --result_dir eval_results/test_prompt_gpt
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from _engiworld_runtime import (
    add_common_engiworld_args,
    load_engiworld_task,
    require_msh_sandbox,
    run_eval_pool,
    setup_logging,
)

import lib_run_single
from lib_run_single import run_single_example, run_single_example_terminal
from mm_agents.agent import PromptAgent


_PREFIX_ENV = (
    # OpenAI-compatible 路径（含 msh 网关的 kimi / glm / qwen3.6 / doubao / openrouter 系列）
    ("gpt", "OPENAI_API_KEY"),
    ("kimi", "OPENAI_API_KEY"),
    ("glm", "OPENAI_API_KEY"),
    ("qwen3.6", "OPENAI_API_KEY"),
    ("doubao", "OPENAI_API_KEY"),
    ("openrouter/", "OPENAI_API_KEY"),  # msh 网关：openrouter/<vendor>-<model>
    # 原生 SDK 路径
    ("claude", "ANTHROPIC_API_KEY"),
    ("gemini", "GENAI_API_KEY"),
    ("qwen", "DASHSCOPE_API_KEY"),  # 顺序敏感：必须在 qwen3.6 之后
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="engiworld + 通用 PromptAgent 评测入口",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_common_engiworld_args(parser)
    parser.add_argument(
        "--model", type=str, required=True,
        help="模型 id；必须以 'gpt' / 'claude' / 'gemini' / 'qwen' 开头，"
             "否则 PromptAgent 内部 dispatch 会抛 'Invalid model'。",
    )
    parser.add_argument(
        "--eval-mode", dest="eval_mode", type=str, required=True,
        choices=["gui", "computer13", "gui-a11y", "gui-screenshot-a11y", "cli", "cli-text"],
        help="评测模式：'gui' = screenshot obs + pyautogui-only (加固) ；"
             "'computer13' = screenshot obs + computer13 action dict ablation ；"
             "'gui-a11y' = accessibility-tree obs + pyautogui-only ablation ；"
             "'cli' = terminal stdout obs + bash / python / readimg actions。",
    )
    parser.add_argument(
        "--reasoning_effort", type=str, default="high",
        choices=["low", "medium", "high"],
        help="OpenAI reasoning_effort 档位；仅对 gpt* 模型生效（其它 openai-compat "
             "网关收到该字段会被 PromptAgent 内部 gate 掉）。默认 'high'；"
             "OpenAI API 自身默认为 medium。",
    )
    return parser.parse_args()


def _validate_credentials(model: str) -> None:
    for prefix, env_var in _PREFIX_ENV:
        if model.startswith(prefix):
            if not os.environ.get(env_var):
                raise RuntimeError(
                    f"缺少 {env_var} 环境变量；model={model!r} 走 PromptAgent "
                    f"{prefix}* 分支必须配置。"
                )
            return
    raise RuntimeError(
        f"PromptAgent 不识别 model={model!r}：仅支持前缀 "
        f"{[p for p, _ in _PREFIX_ENV]}。kimi*/glm* 等需要先在 "
        f"mm_agents/agent.py 添加对应 dispatch 分支。"
    )


_FIRST_USER_PROMPT_BY_MODE = {
    "gui": (
        "Given the screenshot as below. What's the next step that you will do "
        "to help with the task?"
    ),
    "computer13": (
        "Given the screenshot as below. What's the next computer13 action that you will do "
        "to help with the task?"
    ),
    "gui-a11y": (
        "Given the accessibility tree below. What's the next step that you will do "
        "to help with the task?"
    ),
    "gui-screenshot-a11y": (
        "Given the screenshot and accessibility tree below. What's the next step that you will do "
        "to help with the task?"
    ),
    "cli": "Terminal observation: no commands have been executed yet.",
    "cli-text": "Terminal observation: no commands have been executed yet.",
}


def _make_temp_prompt_agent(args: argparse.Namespace) -> PromptAgent:
    """Build a PromptAgent purely to read its system_message; no env, no LLM calls."""
    return PromptAgent(
        eval_mode=args.eval_mode,
        platform="ubuntu",
        model=args.model,
        max_tokens=args.max_tokens,
        top_p=args.top_p,
        temperature=args.temperature,
        max_trajectory_length=args.max_trajectory_length,
        client_password=args.client_password or "password",
        max_retries=args.llm_retries,
        request_timeout=args.llm_request_timeout,
        reasoning_effort=args.reasoning_effort,
    )


def _backfill_prompt_artifacts(args: argparse.Namespace) -> None:
    """Overwrite system_prompt.txt / first_user_prompt.txt for every finished task.

    Runs at startup so reruns of an already-evaluated setting still get the new
    prompt artifacts populated (initial_screenshot.png cannot be backfilled —
    it's the live VM observation and only gets saved during a fresh run).
    """
    target_dir = Path(args.result_dir) / args.eval_mode / args.model
    if not target_dir.is_dir():
        return
    if not os.path.isfile(args.test_all_meta_path):
        return

    log = logging.getLogger("desktopenv.experiment")
    with open(args.test_all_meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    if args.domain != "all":
        meta = {args.domain: meta.get(args.domain, [])}

    agent = _make_temp_prompt_agent(args)
    base_system = agent.system_message
    first_user_text = _FIRST_USER_PROMPT_BY_MODE.get(args.eval_mode)

    written = 0
    for domain, ids in meta.items():
        for ex_id in ids:
            ex_dir = target_dir / domain / ex_id
            if not (ex_dir / "result.txt").exists():
                continue
            try:
                example = load_engiworld_task(args.test_config_base_dir, domain, ex_id)
            except Exception as exc:
                log.warning("Backfill: cannot load %s/%s: %s", domain, ex_id, exc)
                continue
            instruction = example.get("instruction", "")
            sys_text = base_system + "\nYou are asked to complete the following task: {}".format(instruction)
            try:
                (ex_dir / "system_prompt.txt").write_text(sys_text, encoding="utf-8")
                if first_user_text is not None:
                    (ex_dir / "first_user_prompt.txt").write_text(first_user_text, encoding="utf-8")
                written += 1
            except OSError as exc:
                log.warning("Backfill: cannot write to %s: %s", ex_dir, exc)
    if written:
        log.info("Prompt backfill: refreshed artifacts for %d finished task(s).", written)


def build_agent(args: argparse.Namespace, _env, os_type: str) -> PromptAgent:
    return PromptAgent(
        eval_mode=args.eval_mode,
        platform=os_type.lower(),
        model=args.model,
        max_tokens=args.max_tokens,
        top_p=args.top_p,
        temperature=args.temperature,
        max_trajectory_length=args.max_trajectory_length,
        client_password=args.client_password or "password",
        max_retries=args.llm_retries,
        request_timeout=args.llm_request_timeout,
        reasoning_effort=args.reasoning_effort,
    )


def main() -> None:
    args = parse_args()
    require_msh_sandbox(args.provider_name)
    _validate_credentials(args.model)
    setup_logging(args, "engiworld-prompt")
    _backfill_prompt_artifacts(args)
    run_single_fn = (
        run_single_example_terminal
        if args.eval_mode in ("cli", "cli-text")
        else run_single_example
    )
    run_eval_pool(
        args,
        build_agent_fn=build_agent,
        run_single_fn=run_single_fn,
    )


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    main()
