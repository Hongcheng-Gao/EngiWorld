"""Run Engiworld ground-truth evaluation through OSWorld DesktopEnv.

This is the GT-only counterpart of the normal Engiworld launchers:

1. Load an Engiworld task JSON.
2. Reset the OSWorld environment, which runs the task setup config.
3. Upload every file under the task's ground_truth directory to the VM desktop.
4. Run the task's evaluator with env.evaluate().

Unlike the older remote sanity script, this entrypoint does not require a
manually supplied instance IP. The selected DesktopEnv provider is responsible
for creating or attaching to an environment and exposing its endpoint.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

LOG = logging.getLogger("engiworld.gt_check")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload Engiworld ground_truth files and run OSWorld eval.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--test_config_base_dir",
        required=True,
        help="Engiworld task split root, e.g. D:\\localwork\\Engiworld\\task\\task-v",
    )
    parser.add_argument(
        "--domain",
        required=True,
        help="Software/domain directory to run, e.g. eagle or blender.",
    )
    parser.add_argument(
        "--example_id",
        action="append",
        default=[],
        help="Task id to run, e.g. task-01. May be repeated.",
    )
    parser.add_argument(
        "--test_all_meta_path",
        default=None,
        help='Optional eval-list JSON of the form {"domain": ["task-01", ...]}.',
    )
    parser.add_argument(
        "--gt_dir",
        default=None,
        help="Override ground_truth directory. Only valid with one --example_id.",
    )
    parser.add_argument(
        "--desktop_dir",
        default=None,
        help="Override remote desktop directory. Defaults by task id suffix.",
    )
    parser.add_argument("--provider_name", default="msh-sandbox")
    parser.add_argument("--spec", default="g4il.2xlarge")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--client_password", default="")
    parser.add_argument("--screen_width", type=int, default=1920)
    parser.add_argument("--screen_height", type=int, default=1080)
    parser.add_argument("--cache_dir", default="cache")
    parser.add_argument("--continue_on_error", action="store_true")
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Only print planned ground_truth uploads; do not start DesktopEnv.",
    )
    parser.add_argument("--log_level", default="INFO")
    return parser.parse_args()


def task_os(task: dict[str, Any]) -> str:
    task_id = str(task.get("id", ""))
    if task_id.endswith("-windows"):
        return "Windows"
    if task_id.endswith("-ubuntu"):
        return "Ubuntu"
    raise ValueError(f"Cannot infer OS from task id: {task_id!r}")


def default_desktop_dir(task: dict[str, Any]) -> str:
    return "C:\\Users\\User\\Desktop" if task_os(task) == "Windows" else "/home/user/Desktop"


def remote_join(desktop_dir: str, rel: Path) -> str:
    rel_parts = rel.parts
    if "\\" in desktop_dir or ":" in desktop_dir:
        return str(PureWindowsPath(desktop_dir, *rel_parts))
    return str(PurePosixPath(desktop_dir, *rel_parts))


def ground_truth_dir(base_dir: Path, domain: str, example_id: str, override: str | None) -> Path:
    if override:
        return Path(override).resolve()
    return (base_dir / domain / example_id / "ground_truth").resolve()


def load_engiworld_task(base_dir: Path, domain: str, example_id: str) -> dict[str, Any]:
    cfg = base_dir / domain / example_id / f"{example_id}.json"
    if not cfg.is_file():
        raise FileNotFoundError(
            f"Task spec not found: {cfg}. Expected layout "
            "<test_config_base_dir>/<domain>/<example_id>/<example_id>.json"
        )
    with cfg.open("r", encoding="utf-8") as f:
        task = json.load(f)
    asset_root = (base_dir / domain).resolve()
    absolutize_local_paths(task, asset_root, cfg)
    return task


def absolutize_local_paths(node: Any, asset_root: Path, source_cfg: Path) -> None:
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if key == "local_path" and isinstance(value, str):
                path = Path(value)
                resolved = path if path.is_absolute() else (asset_root / path).resolve()
                if not resolved.exists():
                    raise FileNotFoundError(
                        f"upload_file local_path missing: {value!r} -> {resolved} "
                        f"(referenced by {source_cfg})"
                    )
                node[key] = str(resolved)
            else:
                absolutize_local_paths(value, asset_root, source_cfg)
    elif isinstance(node, list):
        for item in node:
            absolutize_local_paths(item, asset_root, source_cfg)


def build_gt_upload_steps(gt_dir: Path, desktop_dir: str) -> list[dict[str, Any]]:
    if not gt_dir.is_dir():
        raise FileNotFoundError(f"ground_truth directory not found: {gt_dir}")

    files = []
    for path in sorted(gt_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(gt_dir)
        files.append(
            {
                "local_path": str(path.resolve()),
                "path": remote_join(desktop_dir, rel),
            }
        )

    if not files:
        raise FileNotFoundError(f"ground_truth directory has no files: {gt_dir}")

    return [{"type": "upload_file", "parameters": {"files": files}}]


def load_task_ids(args: argparse.Namespace) -> list[str]:
    task_ids = list(args.example_id)
    if args.test_all_meta_path:
        with open(args.test_all_meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        task_ids.extend(meta.get(args.domain, []))
    if not task_ids:
        raise ValueError("No tasks selected. Use --example_id or --test_all_meta_path.")
    deduped = []
    seen = set()
    for task_id in task_ids:
        if task_id not in seen:
            seen.add(task_id)
            deduped.append(task_id)
    return deduped


def run_one(env: Any, args: argparse.Namespace, example_id: str) -> float:
    base_dir = Path(args.test_config_base_dir).resolve()
    if args.gt_dir and len(args.example_id) != 1:
        raise ValueError("--gt_dir override is only valid with exactly one --example_id")

    task = load_engiworld_task(base_dir, args.domain, example_id)
    os_type = task_os(task)
    desktop_dir = args.desktop_dir or default_desktop_dir(task)
    gt_dir = ground_truth_dir(base_dir, args.domain, example_id, args.gt_dir)

    LOG.info("Task %s/%s snapshot=%s os=%s", args.domain, example_id, task.get("snapshot"), os_type)
    LOG.info("Ground truth: %s -> %s", gt_dir, desktop_dir)

    env.reset(task_config=task)
    upload_steps = build_gt_upload_steps(gt_dir, desktop_dir)
    env.setup_controller.setup(upload_steps, env.current_use_proxy)
    result = float(env.evaluate())
    LOG.info("Result %s/%s: %.4f", args.domain, example_id, result)
    return result


def dry_run_one(args: argparse.Namespace, example_id: str) -> None:
    base_dir = Path(args.test_config_base_dir).resolve()
    task = load_engiworld_task(base_dir, args.domain, example_id)
    desktop_dir = args.desktop_dir or default_desktop_dir(task)
    gt_dir = ground_truth_dir(base_dir, args.domain, example_id, args.gt_dir)
    upload_steps = build_gt_upload_steps(gt_dir, desktop_dir)

    print(f"{args.domain}/{example_id}")
    print(f"  snapshot: {task.get('snapshot')}")
    print(f"  task id : {task.get('id')}")
    print(f"  gt dir  : {gt_dir}")
    for file_spec in upload_steps[0]["parameters"]["files"]:
        print(f"  upload  : {file_spec['local_path']} -> {file_spec['path']}")


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="[%(asctime)s %(levelname)s %(name)s] %(message)s",
    )

    task_ids = load_task_ids(args)
    if args.gt_dir and len(task_ids) != 1:
        raise ValueError("--gt_dir override is only valid when exactly one task is selected")

    if args.dry_run:
        for example_id in task_ids:
            dry_run_one(args, example_id)
        return 0

    if args.provider_name.lower().strip() in {"msh-sandbox", "msh_sandbox"}:
        if importlib.util.find_spec("agentgym") is None:
            raise RuntimeError(
                "provider_name=msh-sandbox still requires the 'agentgym' module at "
                "runtime. The task loading and ground_truth upload planning are ready, "
                "but this provider cannot start a no-IP sandbox after removing "
                "msh-agentgym unless another provider/launcher is wired in."
            )

    from desktop_env.desktop_env import DesktopEnv

    env = DesktopEnv(
        provider_name=args.provider_name,
        action_space="pyautogui",
        cache_dir=args.cache_dir,
        screen_size=(args.screen_width, args.screen_height),
        headless=args.headless,
        require_a11y_tree=False,
        client_password=args.client_password,
        spec=args.spec,
    )

    results: dict[str, float] = {}
    try:
        for example_id in task_ids:
            try:
                results[example_id] = run_one(env, args, example_id)
            except Exception:
                LOG.exception("Failed %s/%s", args.domain, example_id)
                results[example_id] = 0.0
                if not args.continue_on_error:
                    break
    finally:
        env.close()

    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if results and all(score == 1.0 for score in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
