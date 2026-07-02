"""使用 Anthropic Claude（computer-use）跑 engiworld 评测。

依赖的环境变量
--------------
按 ``--api_provider`` 选择对应凭据：

* ``--api_provider anthropic``（默认）
    - ANTHROPIC_API_KEY    Anthropic 官方 API key。
    - ANTHROPIC_BASE_URL   选填。覆盖 Anthropic 接口地址（接代理 / 私有部署）。
                           anthropic SDK 会自动读这个 env，无需改代码。
* ``--api_provider bedrock``
    - AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION 等
      标准 AWS 凭据链。
* ``--api_provider vertex``
    - 走 GCloud 默认凭据（gcloud auth / GOOGLE_APPLICATION_CREDENTIALS 等），
      没有单一必填 env。

命令行参数说明（运行 ``--help`` 可看到完整 argparse 帮助，每项都会自动追加
``(default: X)``。下文给出含义和默认值）：

通用参数（所有 engiworld launcher 共有）：
  --test_config_base_dir   [必填] engiworld task 根目录
  --test_all_meta_path     [必填] eval 清单 JSON；Ubuntu/Windows 不能混跑
  --domain                 (默认 'all') 只跑某个软件
  --result_dir             (默认 './results') 输出根目录
  --num_envs               (默认 1) 并行 VM 数
  --headless               (默认 False) 无头模式启动 VM；批量必开
  --max_steps              (默认 50) 单 task 最大步数
  --max_trajectory_length  (默认 3) agent 上下文里保留几步历史
  --sleep_after_execution  (默认 0.0) 每步 action 后等几秒
  --screen_width           (默认 1920)
  --screen_height          (默认 1080)
  --client_password        (默认 '') VM 内密码
  --temperature            (默认 1.0)
  --top_p                  (默认 0.9)
  --max_tokens             (默认 1500) Claude thinking 模式要 4096+
  --log_level              (默认 'INFO')
  --provider_name          (默认/仅支持 'msh_sandbox')

Claude 专属参数：
  --model              [必填] Claude 模型 id，例如 'claude-sonnet-4-5-20250929'
  --api_provider       (默认 'anthropic') Anthropic SDK 后端：
                         anthropic — 官方 API（认 ANTHROPIC_BASE_URL）
                         bedrock   — AWS Bedrock
                         vertex    — Google Vertex AI
  --action_space       (默认/仅支持 'claude_computer_use')
  --observation_type   (默认 'screenshot') 可选：
                         screenshot / a11y_tree / screenshot_a11y_tree / som；
                         a11y_tree 类需要 VM 暴露 atspi/UIA 树
  --no_thinking        (默认 False) 关闭 Claude 的 scratchpad thinking
  --use_isp            (默认 False) 启用 interleaved scratchpad（更长上下文更贵）

调用示例（从 Engiworld 工程根目录运行）
---------------------------------------
    cd /home/lihaoyang/code/Engiworld
    export ANTHROPIC_API_KEY=sk-ant-...
    python OSWorld/scripts/python/run_multienv_engiworld_claude.py \\
        --test_config_base_dir task/task-v \\
        --test_all_meta_path   task/task-v/eval_list_ubuntu.json \\
        --model claude-sonnet-4-5-20250929 \\
        --api_provider anthropic --num_envs 4 --headless \\
        --max_tokens 4096 --max_steps 100 \\
        --result_dir results_engiworld_claude

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
from mm_agents.anthropic import AnthropicAgent
from mm_agents.anthropic.utils import APIProvider, validate_model_support


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="engiworld + Anthropic Claude 评测入口",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_common_engiworld_args(parser)
    parser.add_argument(
        "--model", type=str, required=True,
        help="Claude 模型 id，例如 'claude-sonnet-4-5-20250929'。",
    )
    parser.add_argument(
        "--action_space", type=str, default="claude_computer_use",
        choices=["claude_computer_use"],
        help="动作空间，固定 Claude 自带的 computer-use tool。",
    )
    parser.add_argument(
        "--observation_type", type=str, default="screenshot",
        choices=["screenshot", "a11y_tree", "screenshot_a11y_tree", "som"],
        help="观察类型；a11y_tree 类需要 VM 暴露无障碍树。",
    )
    parser.add_argument(
        "--api_provider", type=str, default="anthropic",
        choices=["anthropic", "bedrock", "vertex"],
        help="Anthropic SDK 后端。'anthropic' 走官方 API（认 ANTHROPIC_BASE_URL）。",
    )
    parser.add_argument(
        "--no_thinking", action="store_true",
        help="关闭 Claude 的 scratchpad thinking（默认开）。",
    )
    parser.add_argument(
        "--use_isp", action="store_true",
        help="启用 interleaved scratchpad（ISP）模式：更长上下文、token 更贵。",
    )
    return parser.parse_args()


_API_PROVIDER_ENUM = {
    "anthropic": APIProvider.ANTHROPIC,
    "bedrock": APIProvider.BEDROCK,
    "vertex": APIProvider.VERTEX,
}


def build_agent(args: argparse.Namespace, env, os_type: str) -> AnthropicAgent:
    return AnthropicAgent(
        env=env,
        platform=os_type,
        model=args.model,
        provider=_API_PROVIDER_ENUM[args.api_provider],
        max_tokens=args.max_tokens or 4096,
        top_p=args.top_p,
        temperature=args.temperature,
        action_space=args.action_space,
        observation_type=args.observation_type,
        max_trajectory_length=args.max_trajectory_length,
        provider_name=args.provider_name,
        screen_size=(args.screen_width, args.screen_height),
        no_thinking=args.no_thinking,
        use_isp=args.use_isp,
        max_retries=args.llm_retries,
    )


def _validate_api_credentials(api_provider: str) -> None:
    if api_provider == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "缺少 ANTHROPIC_API_KEY；--api_provider=anthropic 必须配置。"
            )
    elif api_provider == "bedrock":
        missing = [
            v for v in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")
            if not os.environ.get(v)
        ]
        if missing:
            raise RuntimeError(
                f"--api_provider=bedrock 缺少 AWS 凭据环境变量: {missing!r}"
            )
    elif api_provider == "vertex":
        # AnthropicVertex 走 GCloud 默认凭据链；没有单一必填 env，跳过校验。
        return
    else:  # 防御：argparse 已限定 choices
        raise NotImplementedError(
            f"engiworld Claude launcher 不支持 api_provider={api_provider!r}。"
        )


def main() -> None:
    args = parse_args()
    require_msh_sandbox(args.provider_name)
    _validate_api_credentials(args.api_provider)

    validation_kwargs = {"no_thinking": args.no_thinking, "use_isp": args.use_isp}
    if args.temperature is not None:
        validation_kwargs["temperature"] = args.temperature
    if args.top_p is not None:
        validation_kwargs["top_p"] = args.top_p
    validate_model_support(args.model, **validation_kwargs)

    setup_logging(args, "engiworld-claude")
    run_eval_pool(
        args,
        build_agent_fn=build_agent,
        run_single_fn=lib_run_single.run_single_example,
    )


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    main()
