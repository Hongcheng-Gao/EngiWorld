"""Shared runtime for engiworld task layout.

Engiworld tasks live at::

    <test_config_base_dir>/<domain>/<example_id>/<example_id>.json

Asset paths inside each task spec (``upload_file.parameters.files[].local_path``)
are relative to the ``<domain>`` directory and are absolutised at load time.

Per-task ``snapshot`` is consumed by the ``msh_sandbox`` provider; no global AWS
image lookup happens here. Task ids must end with ``-ubuntu`` or ``-windows``;
each worker resolves the OS per task and rebuilds its agent accordingly, so a
single eval list can mix Ubuntu and Windows tasks freely.

Each engiworld launcher is just argparse + agent factory + a call to
:func:`run_eval_pool`. No backwards-compat path layout is supported.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import json
import logging
import os
import signal
import sys
import time
from multiprocessing import Manager, Process, current_process
from typing import Any, Callable, Dict, List, Optional, Tuple

from lib_results_logger import (
    ACTION_KINDS,
    _model_results_dir,
    log_task_error,
    reconcile_results_from_disk,
)
from mm_agents._rate_limit import RpmManager, set_active_limiter

SUPPORTED_PROVIDER = "msh-sandbox"
SUPPORTED_OS_TYPES = ("Ubuntu", "Windows")


# ---------- argument & logging helpers ----------------------------------


def add_common_engiworld_args(parser: argparse.ArgumentParser) -> None:
    """注册所有 engiworld launcher 共用的命令行参数。provider 锁死 msh_sandbox。"""
    # ---- VM / 运行环境 ----
    # 注：launcher 处建议给 ArgumentParser 传 formatter_class=
    # argparse.ArgumentDefaultsHelpFormatter，下面 help 文案不再重复"默认 X"，
    # `--help` 会自动追加 "(default: X)"。
    parser.add_argument(
        "--headless", action="store_true",
        help="无头模式启动 VM：不把虚机画面渲染到当前桌面，批量评测必须开",
    )
    parser.add_argument(
        "--client_password", type=str, default="",
        help="VM 内 sudo/解锁屏密码（Ubuntu 镜像常见 'osworld-public-evaluation'，Windows 一般留空）",
    )
    parser.add_argument(
        "--screen_width", type=int, default=1920,
        help="VM 屏幕宽度（像素）。task ground truth 多按 1920x1080 校准",
    )
    parser.add_argument(
        "--screen_height", type=int, default=1080,
        help="VM 屏幕高度（像素）",
    )
    parser.add_argument(
        "--sleep_after_execution", type=float, default=0.0,
        help="每执行完一条 pyautogui action 后等几秒让 UI 稳定再截下一帧（CAD 卡顿建议 1~3）",
    )
    parser.add_argument(
        "--max_steps", type=int, default=50,
        help="单个 task 最多允许的 agent step 数（一个 step = 推理一次 + 执行其产生的 action 列表）；超出即判失败",
    )
    parser.add_argument(
        "--max_trajectory_length", type=int, default=3,
        help="agent 上下文里保留几步历史，用于裁剪 prompt 长度",
    )
    parser.add_argument(
        "--provider_name", type=str,
        default=SUPPORTED_PROVIDER, choices=[SUPPORTED_PROVIDER],
        help="VM provider；engiworld 只适配 msh_sandbox，写其它值 argparse 会直接拒",
    )
    parser.add_argument(
        "--spec", type=str, default="g4il.2xlarge",
        help="msh_sandbox 的 session spec（资源规格名），如 'g4il.2xlarge' / 'default'",
    )
    # ---- task 输入 / 结果输出 ----
    parser.add_argument(
        "--test_config_base_dir", type=str, required=True,
        help="[必填] engiworld task 根目录，例如 /home/.../Engiworld/task/task-v",
    )
    parser.add_argument(
        "--test_all_meta_path", type=str, required=True,
        help='[必填] eval 清单 JSON，格式 {"<app>": ["<task-id>", ...]}；Ubuntu/Windows 可以混在一份清单里跑，worker 按 task id 后缀逐个切换',
    )
    parser.add_argument(
        "--domain", type=str, default="all",
        help="只跑某一个软件，例如 'blender'；'all' 表示 eval list 里的所有软件",
    )
    parser.add_argument(
        "--result_dir", type=str, default="./results",
        help="结果输出根目录；最终路径 "
             "<result_dir>/<eval_mode>/<model>/<domain>/<task-id>/",
    )
    parser.add_argument(
        "--num_envs", type=int, default=1,
        help="并行 VM 数；会启 N 个子进程，每个进程独占一台 VM，从同一个队列里抢 task",
    )
    parser.add_argument(
        "--log_level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="stdout 日志级别（文件日志固定 DEBUG）",
    )
    # ---- LLM 采样参数 ----
    parser.add_argument(
        "--temperature", type=float, default=1.0,
        help="LLM 采样温度。0 = 贪心，越大越发散；computer-use 模型通常推荐 0.5~1.0",
    )
    parser.add_argument(
        "--top-p", type=float, default=None,
        help="nucleus sampling 阈值；不传则不向 API 发送该字段（部分模型如 gpt-5.5 拒绝 top_p）",
    )
    parser.add_argument(
        "--max_tokens", type=int, default=None,
        help="LLM 单次回复 token 上限；不传则交由厂商默认（OpenAI/Gemini 分支不下发该字段，"
             "Claude 因 Anthropic API 强制要求会兜底到模型单次输出上限）。"
             "带 thinking 的模型若要手工限制建议 ≥4096。",
    )
    parser.add_argument(
        "--llm_retries", type=int, default=10,
        help="LLM 调用最多尝试次数（含首发）。空 response / 限流等被当成软拒绝，"
             "走指数退避 + jitter 自动重试。200 envs 撞 50 RPM 时建议 60+",
    )
    parser.add_argument(
        "--llm_request_timeout", type=int, default=1800,
        help="单次 LLM HTTP 请求的 read timeout（秒）；connect timeout 固定 10s。"
             "默认 1800 = 30min。requests 库默认无超时——网关静默丢请求时主线程会"
             "永远卡死在 socket recv，sandbox 心跳线程仍每 10min 刷 TTL。仅 PromptAgent"
             "的 OpenAI-compat / Azure / Anthropic 路径生效（gemini SDK 自带 120s）。",
    )
    parser.add_argument(
        "--rpm", type=int, default=0,
        help="账号级 RPM（每分钟请求数）上限；0 = 不限。开启后所有 worker 共享一个"
             "60s 滑动窗口，超额时调用方阻塞等待，不打 server。每次重试都重新计入额度，"
             "和 server 端账号配额计数一致（含被拒绝的请求）",
    )
    parser.add_argument(
        "--bash_timeout", type=int, default=120,
        help="单个 ```bash``` 块（typed-action <action type=\"bash\"> 或 terminal obs 的 bash action）"
             "在 VM 上的超时秒数；超时由 server 侧 kill 并抛 SandboxExecuteHardTimeoutError。"
             "默认 120，且 pyautogui / python action 也通过 /run_bash_script 共享该超时。",
    )
    parser.add_argument(
        "--record_video", action="store_true",
        help="录制 VM 屏幕视频到 <result_dir>/.../recording.mp4。默认关闭——单个录制约 800MB-1GB，"
             "1000+ task 批量评测会产生 1TB 量级的产物，使后续 hf upload 哈希阶段极慢。"
             "需要做事故复盘 / 演示 / 标注时再打开。",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="开启后，崩溃后重跑会从 traj.jsonl 的最后一步回放：先在干净 sandbox 上重放已记录的"
             "action（GUI/CLI 每步统一 sleep 60s 让 UI 稳定），把 VM 推到中断状态，再让 agent "
             "从下一步推理。不传则维持旧行为（半成品目录整个清空、从 step 0 重跑）。"
             "traj.jsonl 损坏无法解析时自动降级为任务级重跑（记 WARNING）。"
             "前提：msh_sandbox 每次启动状态完全 deterministic（含鼠标位置、UI 初始 layout），"
             "否则 PyAutoGUI 绝对坐标会漂。",
    )


def setup_logging(args: argparse.Namespace, label: str) -> logging.Logger:
    root = logging.getLogger()
    root.setLevel(getattr(logging, args.log_level.upper()))
    log_dir = os.path.join(
        args.result_dir,
        args.eval_mode,
        args.model,
        "logs",
    )
    os.makedirs(log_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
    fmt_color = logging.Formatter(
        "\x1b[1;33m[%(asctime)s \x1b[31m%(levelname)s "
        "\x1b[32m%(module)s/%(lineno)d-%(processName)s\x1b[1;33m] \x1b[0m%(message)s"
    )
    fmt_plain = logging.Formatter(
        "[%(asctime)s %(levelname)s "
        "%(module)s/%(lineno)d-%(processName)s] %(message)s"
    )
    file_h = logging.FileHandler(
        os.path.join(log_dir, f"{label}-normal-{stamp}.log"), encoding="utf-8"
    )
    file_h.setLevel(logging.INFO)
    file_h.setFormatter(fmt_plain)
    debug_h = logging.FileHandler(
        os.path.join(log_dir, f"{label}-debug-{stamp}.log"), encoding="utf-8"
    )
    debug_h.setLevel(logging.DEBUG)
    debug_h.setFormatter(fmt_plain)
    error_h = logging.FileHandler(
        os.path.join(log_dir, f"{label}-error-{stamp}.log"), encoding="utf-8"
    )
    error_h.setLevel(logging.ERROR)
    error_h.setFormatter(fmt_plain)
    stdout_h = logging.StreamHandler(sys.stdout)
    stdout_h.setLevel(root.level)
    stdout_h.addFilter(logging.Filter("desktopenv"))
    stdout_h.setFormatter(fmt_color)
    for h in (file_h, debug_h, error_h, stdout_h):
        root.addHandler(h)
    return logging.getLogger("desktopenv.experiment")


# ---------- task loading -----------------------------------------------


def require_msh_sandbox(provider_name: str) -> None:
    if provider_name != SUPPORTED_PROVIDER:
        raise NotImplementedError(
            f"engiworld launchers only support provider_name={SUPPORTED_PROVIDER!r}; "
            f"got {provider_name!r}. Other providers are not adapted."
        )


def load_engiworld_task(base_dir: str, domain: str, example_id: str) -> Dict[str, Any]:
    cfg = os.path.join(base_dir, domain, example_id, f"{example_id}.json")
    if not os.path.isfile(cfg):
        raise FileNotFoundError(
            f"engiworld task spec not found: {cfg!r}. Expected layout: "
            "<test_config_base_dir>/<domain>/<example_id>/<example_id>.json"
        )
    with open(cfg, "r", encoding="utf-8") as f:
        task = json.load(f)
    asset_root = os.path.abspath(os.path.join(base_dir, domain))
    _absolutize_local_paths(task, asset_root, cfg)
    return task


def _absolutize_local_paths(node: Any, asset_root: str, source_cfg: str) -> None:
    if isinstance(node, dict):
        for k, v in list(node.items()):
            if k == "local_path" and isinstance(v, str):
                resolved = (
                    v if os.path.isabs(v) else os.path.abspath(os.path.join(asset_root, v))
                )
                if not os.path.exists(resolved):
                    raise FileNotFoundError(
                        f"engiworld upload_file local_path missing: {v!r} -> "
                        f"{resolved!r} (referenced by {source_cfg!r}, "
                        f"asset_root={asset_root!r})."
                    )
                node[k] = resolved
            else:
                _absolutize_local_paths(v, asset_root, source_cfg)
    elif isinstance(node, list):
        for x in node:
            _absolutize_local_paths(x, asset_root, source_cfg)


def derive_engiworld_os_type(task_config: Dict[str, Any]) -> str:
    """Pull os_type from a task spec's id suffix. Fail fast on a malformed id."""
    tid = task_config.get("id", "")
    if tid.endswith("-windows"):
        return "Windows"
    if tid.endswith("-ubuntu"):
        return "Ubuntu"
    raise ValueError(
        f"engiworld task id {tid!r} must end with '-ubuntu' or '-windows' "
        "to encode os_type."
    )


def build_engiworld_env(args: argparse.Namespace):
    require_msh_sandbox(args.provider_name)
    from desktop_env.desktop_env import DesktopEnv

    eval_mode = getattr(args, "eval_mode", "")
    observation_type = getattr(args, "observation_type", "")
    require_a11y_tree = eval_mode == "gui-a11y" or "a11y" in observation_type
    action_space = "computer_13" if eval_mode == "computer13" else "pyautogui"

    return DesktopEnv(
        action_space=action_space,
        provider_name=args.provider_name,
        screen_size=(args.screen_width, args.screen_height),
        headless=args.headless,
        require_a11y_tree=require_a11y_tree,
        enable_proxy=False,
        client_password=args.client_password,
        spec=getattr(args, "spec", None),
    )


def filter_unfinished(
    meta: Dict[str, List[str]], args: argparse.Namespace
) -> Dict[str, List[str]]:
    """Drop example_ids whose result.txt already exists.

    Half-finished dirs (no result.txt) are handled per ``args.resume``:
    - resume + traj.jsonl present: keep the dir intact so run_single can
      replay recorded actions and continue inference from where it stopped.
    - else (no resume, or no traj.jsonl to replay from): purge the dir so
      the task starts from step 0 — preserves the legacy behavior.
    """
    target_dir = os.path.join(
        args.result_dir, args.eval_mode, args.model
    )
    if not os.path.isdir(target_dir):
        return {d: list(ids) for d, ids in meta.items()}
    finished: Dict[str, set] = {d: set() for d in meta}
    resume_mode = bool(getattr(args, "resume", False))
    for d in meta:
        d_path = os.path.join(target_dir, d)
        if not os.path.isdir(d_path):
            continue
        for ex in os.listdir(d_path):
            ex_path = os.path.join(d_path, ex)
            if not os.path.isdir(ex_path):
                continue
            entries = os.listdir(ex_path)
            if "result.txt" in entries:
                finished[d].add(ex)
                continue
            if resume_mode and "traj.jsonl" in entries:
                # Leave the half-finished dir intact; run_single will detect
                # traj.jsonl and enter replay. If traj.jsonl turns out to be
                # corrupt, the runner falls back to purging + fresh run.
                continue
            for f in entries:
                os.remove(os.path.join(ex_path, f))
    return {d: [ex for ex in ids if ex not in finished[d]] for d, ids in meta.items()}


# ---------- multi-process pool ----------------------------------------


_active_environments: List[Any] = []
_processes: List[Process] = []
_is_terminating = False


def _worker(
    task_queue,
    args: argparse.Namespace,
    shared_scores,
    build_agent_fn: Callable,
    run_single_fn: Callable,
    rpm_limiter: Any = None,
):
    logger = logging.getLogger("desktopenv.experiment")
    set_active_limiter(rpm_limiter)
    env = None
    try:
        env = build_engiworld_env(args)
        logger.info("Process %s started.", current_process().name)

        while True:
            try:
                item = task_queue.get(timeout=5)
            except Exception:
                break
            domain, example_id = item
            try:
                example = load_engiworld_task(
                    args.test_config_base_dir, domain, example_id
                )
                # CLI integrity policy needs the eval-list domain to know
                # which application is the intended target. Task ids often
                # only encode task number + OS, so keep this as runner metadata.
                example["_engiworld_domain"] = domain
                task_os_type = derive_engiworld_os_type(example)
                agent = build_agent_fn(args, env, task_os_type)
                logger.info("[%s][Domain]: %s", current_process().name, domain)
                logger.info("[%s][Example ID]: %s", current_process().name, example_id)
                logger.info(
                    "[%s][OS Type]: %s", current_process().name, task_os_type
                )
                logger.info(
                    "[%s][Instruction]: %s",
                    current_process().name,
                    example["instruction"],
                )
                example_result_dir = os.path.join(
                    args.result_dir,
                    args.eval_mode,
                    args.model,
                    domain,
                    example_id,
                )
                os.makedirs(example_result_dir, exist_ok=True)
                try:
                    run_single_fn(
                        agent,
                        env,
                        example,
                        args.max_steps,
                        example["instruction"],
                        args,
                        example_result_dir,
                        shared_scores,
                    )
                except Exception as exc:
                    import traceback

                    logger.error(
                        "Exception in %s %s/%s: %s",
                        current_process().name,
                        domain,
                        example_id,
                        exc,
                    )
                    logger.error(traceback.format_exc())
                    with open(
                        os.path.join(example_result_dir, "traj.jsonl"),
                        "a",
                        encoding="utf-8",
                    ) as f:
                        f.write(
                            json.dumps({"Error": f"{domain}/{example_id} - {exc}"})
                            + "\n"
                        )
                    # Prefix with the exception class name so
                    # lib_results_logger can classify infrastructure failures
                    # (SandboxExecuteHardTimeoutError, SandboxUnavailableError,
                    # ValueError-from-parser) without re-introspecting the exc.
                    log_task_error(
                        example,
                        f"{type(exc).__name__}: {exc}",
                        example_result_dir,
                        args,
                    )
            except Exception as exc:
                import traceback

                logger.error(
                    "Task-level error in %s: %s", current_process().name, exc
                )
                logger.error(traceback.format_exc())
                stub_result_dir = os.path.join(
                    args.result_dir,
                    args.eval_mode,
                    args.model,
                    domain,
                    example_id,
                )
                log_task_error(
                    {"id": example_id},
                    f"{type(exc).__name__}: {exc}",
                    stub_result_dir,
                    args,
                )
    except Exception as exc:
        import traceback

        logger.error("Process-level error in %s: %s", current_process().name, exc)
        logger.error(traceback.format_exc())
    finally:
        logger.info("%s cleaning up environment...", current_process().name)
        try:
            if env is not None:
                env.close()
                logger.info(
                    "%s environment closed successfully", current_process().name
                )
        except Exception as exc:
            logger.error(
                "%s error during cleanup: %s", current_process().name, exc
            )


def _signal_handler(signum, _frame):
    global _is_terminating
    if _is_terminating:
        return
    _is_terminating = True
    logger = logging.getLogger("desktopenv.experiment")
    logger.info("Received signal %s. Gracefully shutting down...", signum)
    for env in _active_environments:
        try:
            env.close()
        except Exception as exc:
            logger.error("Error closing environment: %s", exc)
    for p in _processes:
        if p.is_alive():
            try:
                p.terminate()
            except Exception as exc:
                logger.error("Error terminating: %s", exc)
    time.sleep(1)
    for p in _processes:
        if p.is_alive():
            try:
                import signal as sig

                os.kill(p.pid, sig.SIGKILL)
            except Exception as exc:
                logger.error("Error force-killing: %s", exc)
    logger.info("Shutdown complete. Exiting.")
    sys.exit(0)


def _print_summary(args: argparse.Namespace, logger: logging.Logger) -> None:
    """Render overall + per-application aggregates from results.json as
    rich tables to stdout. A single anchor line is also emitted to the
    logger so log-only readers know where the JSON lives.

    Expects ``reconcile_results_from_disk`` to have run first so the file
    reflects every completed task on disk, not just this run's.
    """
    from rich.console import Console
    from rich.table import Table

    results_path = str(_model_results_dir(args) / "results.json")
    if not os.path.isfile(results_path):
        logger.info("No results.json at %s", results_path)
        return
    try:
        with open(results_path, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read %s: %s", results_path, exc)
        return

    overall = doc.get("overall") or {}
    by_app = doc.get("by_application") or {}
    # Force a min width so rich doesn't squash the wider tables (the action
    # stats sub-table is 9 columns) in non-tty contexts (CI logs, redirected
    # output) where it defaults to 80.
    try:
        term_cols = os.get_terminal_size().columns
    except OSError:
        term_cols = 0
    console = Console(width=max(160, term_cols))

    def _fnum(v: Any) -> str:
        if v is None:
            return "-"
        if isinstance(v, float):
            return f"{v:.1f}"
        return str(v)

    def _step_cells(s: Optional[Dict[str, Any]], *, include_count: bool) -> List[str]:
        s = s or {}
        n = s.get("count") or 0
        if not n:
            tail = ["-", "-", "-", "-", "-", "-"]
            return (["0"] + tail) if include_count else tail
        body = [
            _fnum(s.get("min")),
            _fnum(s.get("q1")),
            _fnum(s.get("median")),
            _fnum(s.get("q3")),
            _fnum(s.get("max")),
            _fnum(s.get("mean")),
        ]
        return ([str(n)] + body) if include_count else body

    main = Table(
        title=f"Score summary  [dim]{results_path}[/dim]",
        caption=(
            "[dim]Count = total tasks  •  "
            "Passed (score==1) + Failed (score==0) + Errors (crashed) = Count.\n"
            "min/q1/med/q3/max/mean summarize per-task step_count "
            "(all tasks, including errored).[/dim]"
        ),
        title_justify="left",
        caption_justify="left",
        header_style="bold",
    )
    main.add_column("Application", style="cyan", no_wrap=True)
    main.add_column("Count", justify="right")
    main.add_column("Passed", justify="right")
    main.add_column("Failed", justify="right")
    main.add_column("Errors", justify="right")
    for col in ("min", "q1", "med", "q3", "max", "mean"):
        main.add_column(col, justify="right")

    apps = sorted(by_app)
    for i, app in enumerate(apps):
        b = by_app[app] or {}
        main.add_row(
            app,
            str(b.get("count", 0)),
            str(b.get("passed_count", 0)),
            str(b.get("failed_count", 0)),
            str(b.get("error_count", 0)),
            *_step_cells(b.get("steps"), include_count=False),
            end_section=(i == len(apps) - 1),
        )
    main.add_row(
        "[bold]Overall[/bold]",
        f"[bold]{overall.get('count', 0)}[/bold]",
        f"[bold]{overall.get('passed_count', 0)}[/bold]",
        f"[bold]{overall.get('failed_count', 0)}[/bold]",
        f"[bold]{overall.get('error_count', 0)}[/bold]",
        *(f"[bold]{c}[/bold]" for c in _step_cells(overall.get("steps"), include_count=False)),
    )
    console.print()
    console.print(main)

    overall_breakdown = overall.get("failure_breakdown") or {}

    def _fb_get(b: Dict[str, Any], key: str) -> int:
        return int((b.get("failure_breakdown") or {}).get(key, 0) or 0)

    def _print_breakdown(title: str, caption: str, kind_keys: tuple) -> None:
        """Render one breakdown sub-table; skip silently when every cell is 0
        across every app + Overall, so an all-passed run doesn't print empty
        scaffolding."""
        any_nonzero = any(overall_breakdown.get(k, 0) for k in kind_keys)
        if not any_nonzero:
            return
        t = Table(
            title=title,
            caption=caption,
            title_justify="left",
            caption_justify="left",
            header_style="bold",
        )
        t.add_column("Application", style="cyan", no_wrap=True)
        for k in kind_keys:
            t.add_column(k, justify="right")
        for i, app in enumerate(apps):
            b = by_app[app] or {}
            t.add_row(
                app,
                *(str(_fb_get(b, k)) for k in kind_keys),
                end_section=(i == len(apps) - 1),
            )
        t.add_row(
            "[bold]Overall[/bold]",
            *(
                f"[bold]{overall_breakdown.get(k, 0)}[/bold]"
                for k in kind_keys
            ),
        )
        console.print(t)
        console.print()

    _print_breakdown(
        title="Failed breakdown  [dim](status=success, score=0)[/dim]",
        caption=(
            "[dim]wrong_score = model emitted DONE/FAIL but evaluator disagreed  •  "
            "truncated = ran out of max_steps without DONE.\n"
            "Row sum = failed_count.[/dim]"
        ),
        kind_keys=("wrong_score", "truncated"),
    )

    _print_breakdown(
        title="Error breakdown  [dim](status=error)[/dim]",
        caption=(
            "[dim]execute_timeout = sandbox /execute hard timeout (120s)  •  "
            "sandbox_error = SandboxUnavailableError\n"
            "unknown_error = uncategorized exception (see results.json "
            "err_message for the raw text).\n"
            "Row sum = error_count.[/dim]"
        ),
        kind_keys=("execute_timeout", "sandbox_error", "unknown_error"),
    )

    # Per-kind action distribution: one sub-table per action kind, rows are
    # (app × bucket), columns mirror the step distribution (count + 5-num
    # summary). Skip a kind when the overall ``all`` bucket has max==0
    # across every task — i.e. no task ever emitted that action — so an
    # all-zero kind doesn't print empty scaffolding.
    overall_actions = overall.get("actions") or {}

    def _action_cells(summary: Optional[Dict[str, Any]]) -> List[str]:
        s = summary or {}
        n = s.get("count") or 0
        if not n:
            return ["0", "-", "-", "-", "-", "-", "-"]
        return [
            str(n),
            _fnum(s.get("min")),
            _fnum(s.get("q1")),
            _fnum(s.get("median")),
            _fnum(s.get("q3")),
            _fnum(s.get("max")),
            _fnum(s.get("mean")),
        ]

    for kind in ACTION_KINDS:
        overall_all = (overall_actions.get("all") or {}).get(kind) or {}
        kind_max = overall_all.get("max")
        if not overall_all.get("count") or not kind_max:
            continue
        kind_table = Table(
            title=(
                f"Action distribution: [bold]{kind}[/bold]  "
                f"[dim](per-task count, recovered from traj.jsonl)[/dim]"
            ),
            caption=(
                "[dim]Bucket: all = every task with a traj.jsonl (errored "
                "tasks counted)  •  passed = status==success and score==1  "
                "•  failed = status==success and score==0.\n"
                "Count = tasks in the bucket  •  min/q1/med/q3/max/mean "
                f"summarize per-task '{kind}' action count.[/dim]"
            ),
            title_justify="left",
            caption_justify="left",
            header_style="bold",
        )
        kind_table.add_column("Application", style="cyan", no_wrap=True)
        kind_table.add_column("Bucket", style="cyan", no_wrap=True)
        for col in ("Count", "min", "q1", "med", "q3", "max", "mean"):
            kind_table.add_column(col, justify="right")
        # Only include apps that actually contributed a counts dict for this
        # kind. Apps with zero recoverable traj.jsonls would otherwise add
        # three all-dash rows of pure noise.
        apps_with_data = [
            app for app in apps
            if ((((by_app[app] or {}).get("actions")) or {})
                .get("all") or {}).get(kind, {}).get("count")
        ]
        for i, app in enumerate(apps_with_data):
            app_actions = ((by_app[app] or {}).get("actions")) or {}
            for bi, bucket_name in enumerate(("all", "passed", "failed")):
                kind_table.add_row(
                    app if bi == 0 else "",
                    bucket_name,
                    *_action_cells((app_actions.get(bucket_name) or {}).get(kind)),
                    end_section=(i == len(apps_with_data) - 1 and bi == 2),
                )
        for bi, bucket_name in enumerate(("all", "passed", "failed")):
            label = "[bold]Overall[/bold]" if bi == 0 else ""
            cells = _action_cells((overall_actions.get(bucket_name) or {}).get(kind))
            kind_table.add_row(
                label, bucket_name, *(f"[bold]{c}[/bold]" for c in cells)
            )
        console.print(kind_table)
        console.print()

    sbs = overall.get("steps_by_score") or {}
    if any((sbs.get(k) or {}).get("count") for k in ("score_zero", "score_one")):
        bucket = Table(
            title="Step distribution by score [dim](status==success only)[/dim]",
            caption=(
                "[dim]Count = task count in this bucket  •  "
                "min/q1/med/q3/max/mean summarize per-task step_count.[/dim]"
            ),
            title_justify="left",
            caption_justify="left",
            header_style="bold",
        )
        bucket.add_column("Bucket", style="cyan", no_wrap=True)
        for col in ("Count", "min", "q1", "med", "q3", "max", "mean"):
            bucket.add_column(col, justify="right")
        for label, key in (
            ("score == 0  (失败)", "score_zero"),
            ("score == 1  (成功)", "score_one"),
        ):
            bucket.add_row(label, *_step_cells(sbs.get(key), include_count=True))
        console.print(bucket)
        console.print()

    logger.info("Score summary printed (results.json: %s)", results_path)


def run_eval_pool(
    args: argparse.Namespace,
    *,
    build_agent_fn: Callable,
    run_single_fn: Callable,
) -> None:
    """Top-level entry. Reads meta, spawns workers; per-task os_type is derived
    inside each worker from the task id suffix."""
    require_msh_sandbox(args.provider_name)

    if not os.path.isdir(args.test_config_base_dir):
        raise FileNotFoundError(
            f"--test_config_base_dir not found: {args.test_config_base_dir!r}"
        )
    if not os.path.isfile(args.test_all_meta_path):
        raise FileNotFoundError(
            f"--test_all_meta_path not found: {args.test_all_meta_path!r}"
        )

    with open(args.test_all_meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    if args.domain != "all":
        if args.domain not in meta:
            raise KeyError(
                f"domain {args.domain!r} not in eval list (have: {sorted(meta)})"
            )
        meta = {args.domain: meta[args.domain]}

    args_dump = os.path.join(
        args.result_dir,
        args.eval_mode,
        args.model,
        "args.json",
    )
    os.makedirs(os.path.dirname(args_dump), exist_ok=True)
    with open(args_dump, "w", encoding="utf-8") as f:
        json.dump(vars(args), f, indent=2, default=str)

    # Pull any previously-finished tasks (from prior runs) into results.json
    # so the aggregates reflect the full set, not just tasks attempted now.
    reconcile_results_from_disk(args)

    todo = filter_unfinished(meta, args)
    logger = logging.getLogger("desktopenv.experiment")
    logger.info("Args: %s", args)
    logger.info("Left tasks per domain: %s", {d: len(v) for d, v in todo.items()})

    all_tasks: List[Tuple[str, str]] = [
        (d, ex) for d, ids in todo.items() for ex in ids
    ]
    if not all_tasks:
        logger.info("Nothing to do.")
        _print_summary(args, logger)
        return

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    rpm_cm: contextlib.AbstractContextManager
    if args.rpm and args.rpm > 0:
        rpm_cm = RpmManager()
    else:
        rpm_cm = contextlib.nullcontext()

    with Manager() as manager, rpm_cm as rpm_manager:
        shared_scores = manager.list()
        task_queue = manager.Queue()
        for item in all_tasks:
            task_queue.put(item)

        rpm_limiter = (
            rpm_manager.RpmLimiter(args.rpm) if rpm_manager is not None else None
        )
        if rpm_limiter is not None:
            logger.info(
                "RPM limiter active: cap=%d req/min, shared across %d worker(s)",
                args.rpm,
                args.num_envs,
            )

        worker_args = (
            task_queue,
            args,
            shared_scores,
            build_agent_fn,
            run_single_fn,
            rpm_limiter,
        )

        # Cap worker count by remaining task count so we don't spin up
        # sandboxes that will only sit idle when most tasks are already done.
        worker_count = min(args.num_envs, len(all_tasks))
        if worker_count < args.num_envs:
            logger.info(
                "Capping workers from %d -> %d (only %d task(s) remain)",
                args.num_envs,
                worker_count,
                len(all_tasks),
            )
        _processes.clear()
        for i in range(worker_count):
            p = Process(
                target=_worker,
                args=worker_args,
                name=f"EnvProcess-{i + 1}",
            )
            p.daemon = True
            p.start()
            _processes.append(p)
            logger.info("Started %s (PID=%s)", p.name, p.pid)

        try:
            while True:
                alive = sum(1 for p in _processes if p.is_alive())
                for idx, p in enumerate(_processes):
                    if not p.is_alive() and not task_queue.empty():
                        logger.warning("%s died, restarting...", p.name)
                        new_p = Process(
                            target=_worker,
                            args=worker_args,
                            name=f"EnvProcess-Restart-{idx + 1}",
                        )
                        new_p.daemon = True
                        new_p.start()
                        _processes[idx] = new_p
                        logger.info(
                            "Restarted %s (PID=%s)", new_p.name, new_p.pid
                        )

                if task_queue.empty():
                    logger.info("All tasks finished.")
                    break
                if alive == 0:
                    logger.error(
                        "All workers died with tasks remaining; exiting."
                    )
                    break
                time.sleep(5)

            for p in _processes:
                p.join()
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt; shutting down...")
            raise

        scores = list(shared_scores)

    if scores:
        logger.info(
            "This run average (new tasks only): %.4f over %d task(s)",
            sum(scores) / len(scores),
            len(scores),
        )
    _print_summary(args, logger)


__all__ = [
    "SUPPORTED_OS_TYPES",
    "SUPPORTED_PROVIDER",
    "add_common_engiworld_args",
    "build_engiworld_env",
    "derive_engiworld_os_type",
    "filter_unfinished",
    "load_engiworld_task",
    "require_msh_sandbox",
    "run_eval_pool",
    "setup_logging",
]
