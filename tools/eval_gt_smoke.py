#!/usr/bin/env python3
"""
Smoke-test task eval.py using local ground_truth/ as simulated VM Desktop.

默认完全串行、每条结果立即落盘，尽量降低内存峰值（避免大批量并行子进程）。

Run:
  python tools/eval_gt_smoke.py
  python tools/eval_gt_smoke.py --timeout 12 --max-tasks 100
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _oneline(text: str, limit: int = 200) -> str:
    if not text:
        return ""
    return " ".join(text.replace("\t", " ").split())[:limit]


def patch_eval_source(text: str, sim: Path) -> str:
    posix = sim.as_posix()
    win = str(sim)
    text = text.replace("/home/user/Desktop", posix)
    text = text.replace(r"C:\Users\Administrator\Desktop", win)
    text = text.replace("C:/Users/Administrator/Desktop", posix)
    text = text.replace(r"C:\\Users\\Administrator\\Desktop", win.replace("\\", "\\\\"))
    return text


def copy_ground_truth(gt_dir: Path, sim: Path) -> None:
    sim.mkdir(parents=True, exist_ok=True)
    for p in gt_dir.iterdir():
        if p.name.startswith("."):
            continue
        dest = sim / p.name
        if p.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(p, dest)
        else:
            shutil.copy2(p, dest)


def clear_sim(sim: Path) -> None:
    if not sim.exists():
        return
    for p in sim.iterdir():
        try:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)
        except OSError:
            pass


def run_eval_patched(eval_py: Path, sim: Path, timeout: float) -> tuple[int, str, str]:
    src = eval_py.read_text(encoding="utf-8", errors="replace")
    patched = patch_eval_source(src, sim)
    with tempfile.NamedTemporaryFile(
        "w", suffix="_eval_patched.py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(patched)
        tmp_path = Path(tmp.name)
    try:
        proc = subprocess.run(
            [sys.executable, str(tmp_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
        raw = (proc.stdout or b"")[:512]
        out = raw.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0 and not out:
            err = f"exitcode:{proc.returncode}"
        else:
            err = ""
        return proc.returncode, out, err
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    finally:
        tmp_path.unlink(missing_ok=True)


def classify(stdout: str) -> str:
    t = stdout.strip().splitlines()
    last = t[-1].strip() if t else ""
    if last == "True":
        return "true"
    if last == "False":
        return "false"
    if not last:
        return "empty"
    return "other:" + last[:80]


def find_tasks(task_roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in task_roots:
        if not root.is_dir():
            continue
        for eval_py in root.rglob("eval.py"):
            gt = eval_py.parent / "ground_truth"
            if gt.is_dir():
                found.append(eval_py)
    return sorted(found, key=lambda p: str(p))


def process_one(
    eval_py: Path, task_root: Path, sim_root: Path, timeout: float, skip_neg: bool
) -> dict:
    rel = eval_py.relative_to(task_root)
    h = hashlib.sha1(str(rel).encode("utf-8")).hexdigest()[:16]
    sim = sim_root / h
    r: dict = {"task": str(rel), "with_gt": "", "no_gt": "", "note": ""}

    clear_sim(sim)
    gt = eval_py.parent / "ground_truth"
    try:
        copy_ground_truth(gt, sim)
    except OSError as e:
        r["note"] = _oneline(f"copy_gt:{e}")
        return r

    code, out, err = run_eval_patched(eval_py, sim, timeout)
    r["with_gt"] = classify(out)
    if code != 0 and r["with_gt"] == "empty":
        r["note"] = _oneline(err or f"exitcode:{code}")

    if skip_neg:
        r["no_gt"] = "-"
        clear_sim(sim)
        return r

    clear_sim(sim)
    code2, out2, err2 = run_eval_patched(eval_py, sim, timeout)
    r["no_gt"] = classify(out2)
    if code2 != 0 and r["no_gt"] == "empty" and not r["note"]:
        r["note"] = _oneline(err2 or f"exitcode:{code2}")

    clear_sim(sim)
    return r


def _append_tsv_row(path: Path, row: dict) -> None:
    line = "\t".join(
        [
            row["task"],
            row["with_gt"],
            row.get("no_gt", ""),
            _oneline(row.get("note", "")),
        ]
    )
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--task-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "task",
        help="Path to .../Engiworld/task",
    )
    ap.add_argument(
        "--timeout",
        type=float,
        default=12.0,
        help="Per eval subprocess timeout (seconds).",
    )
    ap.add_argument(
        "--gc-every",
        type=int,
        default=3,
        help="Call gc.collect() every N completed tasks (1 = every task).",
    )
    ap.add_argument("--only", choices=("task-c", "task-v", "both"), default="both")
    ap.add_argument("--max-tasks", type=int, default=0, help="0 = no limit")
    ap.add_argument("--skip-negative", action="store_true", help="Only run with-GT case")
    args = ap.parse_args()

    roots: list[Path] = []
    if args.only in ("task-c", "both"):
        roots.append(args.task_root / "task-c")
    if args.only in ("task-v", "both"):
        roots.append(args.task_root / "task-v")

    tasks = find_tasks(roots)
    if args.max_tasks:
        tasks = tasks[: args.max_tasks]

    sim_root = Path(tempfile.mkdtemp(prefix="engiworld_eval_sim_"))
    out_path = Path(__file__).resolve().parent / "eval_gt_smoke_report.tsv"

    summary = {"with_true": 0, "with_false": 0, "with_other": 0, "neg_fail": 0, "neg_ok": 0}
    bad_neg_sample: list[str] = []
    false_pos_sample: list[tuple[str, str, str]] = []

    out_path.write_text("task\twith_gt\tno_gt\tnote\n", encoding="utf-8")

    try:
        for i, ep in enumerate(tasks, 1):
            row = process_one(ep, args.task_root, sim_root, args.timeout, args.skip_negative)
            _append_tsv_row(out_path, row)

            wg, ng = row["with_gt"], row["no_gt"]
            if wg == "true":
                summary["with_true"] += 1
            elif wg == "false":
                summary["with_false"] += 1
            else:
                summary["with_other"] += 1
            if not args.skip_negative:
                if ng == "false":
                    summary["neg_ok"] += 1
                elif ng == "true":
                    summary["neg_fail"] += 1
                    if len(bad_neg_sample) < 25:
                        bad_neg_sample.append(row["task"])
            if wg != "true" and len(false_pos_sample) < 30:
                false_pos_sample.append((row["task"], wg, row.get("note", "")))

            if args.gc_every > 0 and i % args.gc_every == 0:
                gc.collect()

            if i % 40 == 0 or i == len(tasks):
                print(f"progress {i}/{len(tasks)}", file=sys.stderr)
    except KeyboardInterrupt:
        print("interrupted (partial report already on disk)", file=sys.stderr)
    finally:
        shutil.rmtree(sim_root, ignore_errors=True)

    print("=== summary ===")
    print(f"tasks: {len(tasks)}")
    print(f"with_gt True:  {summary['with_true']}")
    print(f"with_gt False: {summary['with_false']}")
    print(f"with_gt other: {summary['with_other']}")
    if not args.skip_negative:
        print(f"no_gt expected False -> got False: {summary['neg_ok']}")
        print(f"no_gt expected False -> got True (bad): {summary['neg_fail']}")
    print(f"report: {out_path}")

    if bad_neg_sample:
        print("\n=== no_gt still True (sample) ===")
        for t in bad_neg_sample:
            print(t)

    print(f"\n=== with_gt not True (sample {len(false_pos_sample)}) ===")
    for task, wg, note in false_pos_sample:
        print(f"{task}\t{wg}\t{note[:100]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
