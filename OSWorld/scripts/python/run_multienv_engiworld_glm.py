"""使用 智谱 AutoGLM (GLM 系列) 跑 engiworld 评测。

LLM 调用走 OpenAI 兼容协议（msh 网关支持），与 GPT/Qwen 共用 OPENAI_* env。

依赖的环境变量
--------------
OPENAI_API_KEY    必填。OpenAI 兼容网关的 API key。
OPENAI_BASE_URL   选填。OpenAI 兼容地址；msh 网关请填
                  ``https://openai.app.msh.team/v1``，缺省走官方 ``https://api.openai.com/v1``。

命令行参数
----------
通用参数（所有 engiworld launcher 共有）：见 ``_engiworld_runtime.add_common_engiworld_args``。

GLM 专属参数：
  --model              [必填] GLM 模型 id，例如 'glm-5.1'、'autoglm-os'
  --action_space       (默认/仅支持 'autoglm_computer_use')
  --observation_type   (默认/仅支持 'a11y_tree')   AutoGLM agent 强制依赖无障碍树
  --image_width        (默认 1280) 截图 resize 后的宽度
  --image_height       (默认 720)  截图 resize 后的高度

注意事项
--------
* AutoGLM agent 内部 prompt / a11y 解析按 **Ubuntu** 写死；Windows task 不保证可用，
  ``--test_all_meta_path`` 建议只放 ``-ubuntu`` 任务。
* gen_func 走原生 ``requests.post``（保留 GLM 专用 stop tokens
  ``<|user|> <|observation|> </answer>``）；msh 网关若不识别会被忽略。
* ``--max_tokens`` 默认 1500 偏小，GLM 通常建议 4096+，跑批量评测请显式覆盖。
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

import backoff
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from _engiworld_runtime import (
    add_common_engiworld_args,
    require_msh_sandbox,
    run_eval_pool,
    setup_logging,
)

import lib_run_single
from mm_agents._rate_limit import acquire_rpm_slot
from mm_agents.autoglm_v import AutoGLMAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="engiworld + 智谱 AutoGLM 评测入口",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_common_engiworld_args(parser)
    parser.add_argument(
        "--model", type=str, required=True,
        help="GLM 模型 id，例如 'glm-5.1' / 'autoglm-os'。",
    )
    parser.add_argument(
        "--action_space", type=str, default="autoglm_computer_use",
        choices=["autoglm_computer_use"],
        help="动作空间，固定 'autoglm_computer_use'。",
    )
    parser.add_argument(
        "--observation_type", type=str, default="a11y_tree",
        choices=["a11y_tree"],
        help="观察类型；AutoGLM agent 只支持 'a11y_tree'。",
    )
    parser.add_argument(
        "--image_width", type=int, default=1280,
        help="发送给模型的截图宽度（resize 后）。",
    )
    parser.add_argument(
        "--image_height", type=int, default=720,
        help="发送给模型的截图高度（resize 后）。",
    )
    return parser.parse_args()


def _build_call_llm(args: argparse.Namespace):
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    url = f"{base_url.rstrip('/')}/chat/completions"
    max_tries = max(1, int(args.llm_retries))

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException,),
        max_tries=max_tries,
        jitter=backoff.full_jitter,
    )
    def call_llm(messages):
        acquire_rpm_slot()
        logger = logging.getLogger("desktopenv.experiment")
        logger.info("Calling GLM (model=%s)...", args.model)
        data = {
            "model": args.model,
            "messages": messages,
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
            "top_p": args.top_p,
            "skip_special_tokens": False,
            "stream": False,
            "include_stop_str_in_output": True,
            "stop": ["<|user|>", "<|observation|>", "</answer>"],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}",
        }
        resp = requests.post(url, json=data, headers=headers, timeout=120.0)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    return call_llm


def build_agent(args: argparse.Namespace, _env, os_type: str) -> AutoGLMAgent:
    return AutoGLMAgent(
        action_space=args.action_space,
        observation_type=args.observation_type,
        max_trajectory_length=args.max_trajectory_length,
        screen_size=(args.screen_width, args.screen_height),
        image_size=(args.image_width, args.image_height),
        client_password=args.client_password or "password",
        gen_func=_build_call_llm(args),
    )


def main() -> None:
    args = parse_args()
    require_msh_sandbox(args.provider_name)
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "缺少 OPENAI_API_KEY；engiworld GLM launcher 走 OpenAI 兼容协议，必须配置。"
        )
    setup_logging(args, "engiworld-glm")
    run_eval_pool(
        args,
        build_agent_fn=build_agent,
        run_single_fn=lib_run_single.run_single_example_autoglm,
    )


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    main()
