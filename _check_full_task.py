"""Run eval-vs-gt check across task/task-c and task/task-v.

For each task we:
  1. Build a temp dir mimicking the agent's Desktop
  2. Copy init_file/* and ground_truth/* into it (also expose `answer.X` as both `X` and `result.X`)
  3. Patch the eval.py path constants (Desktop hard-codes) to point at that temp dir
  4. Run the patched eval.py via subprocess
  5. Categorise the last line of stdout as True / False / error
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOTS = [
    Path(r"d:/research/project-engiworld/Engiworld/task/task-c"),
    Path(r"d:/research/project-engiworld/Engiworld/task/task-v"),
]

PATH_PATTERNS = [
    re.compile(r"C:\\\\Users\\\\Administrator\\\\Desktop"),
    re.compile(r"C:\\Users\\Administrator\\Desktop"),
    re.compile(r"C:/Users/Administrator/Desktop"),
    re.compile(r"/home/user/Desktop"),
]


def patch_eval_source(src: str, gt_dir: Path) -> str:
    gt = str(gt_dir).replace("\\", "/")
    out = src
    for pat in PATH_PATTERNS:
        out = pat.sub(gt, out)
    return out


def run_eval(eval_path: Path, gt_dir: Path, init_dir: Path | None):
    try:
        original = eval_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return "error", "", f"read_eval: {exc}"

    work = Path(tempfile.mkdtemp(prefix="eval_check_"))
    try:
        if init_dir and init_dir.exists():
            for src in init_dir.rglob("*"):
                if src.is_file():
                    rel = src.relative_to(init_dir)
                    dst = work / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
        if gt_dir.exists():
            for src in gt_dir.rglob("*"):
                if src.is_file():
                    rel = src.relative_to(gt_dir)
                    dst = work / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    name = src.name
                    if name.startswith("answer."):
                        plain = work / rel.parent / name[len("answer."):]
                        result = work / rel.parent / ("result." + name[len("answer."):])
                        shutil.copy2(src, plain)
                        shutil.copy2(src, result)

        patched = patch_eval_source(original, work)
        tmp = work / "_patched_eval.py"
        tmp.write_text(patched, encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(tmp)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(work),
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        last_line = stdout.splitlines()[-1].strip() if stdout else ""
        norm = last_line.strip().lower().rstrip(".")
        if norm in {"true", "1", "ok", "pass", "passed"}:
            verdict = "True"
        elif norm in {"false", "0", "fail", "failed"}:
            verdict = "False"
        else:
            verdict = "error"
        return verdict, stdout, stderr
    except subprocess.TimeoutExpired:
        return "error", "", "timeout"
    except Exception as exc:
        return "error", "", f"run: {exc}"
    finally:
        try:
            shutil.rmtree(work, ignore_errors=True)
        except OSError:
            pass


def collect_tasks(root: Path):
    for app_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for task_dir in sorted(p for p in app_dir.iterdir() if p.is_dir()):
            eval_py = task_dir / "eval.py"
            gt_dir = task_dir / "ground_truth"
            init_dir = task_dir / "init_file"
            if eval_py.exists() and gt_dir.exists():
                yield task_dir, eval_py, gt_dir, init_dir


def err_reason(stderr: str) -> str:
    if "cadquery" in stderr:
        return "missing cadquery (STEP)"
    if "pymupdf" in stderr or "fitz" in stderr:
        return "missing pymupdf"
    if "ifcopenshell" in stderr:
        return "missing ifcopenshell"
    if "trimesh" in stderr:
        return "missing trimesh"
    if "ezdxf" in stderr:
        return "missing ezdxf"
    if "collada" in stderr:
        return "missing collada"
    return stderr.splitlines()[-1][:120] if stderr else "(no stderr)"


def main() -> None:
    summary: dict[str, list[dict]] = {}
    for root in ROOTS:
        bucket = root.parent.name + "/" + root.name
        tasks = list(collect_tasks(root))
        print(f"\n=== {bucket}: {len(tasks)} tasks ===", flush=True)
        results: list[dict] = []
        for idx, (task_dir, eval_py, gt_dir, init_dir) in enumerate(tasks, 1):
            verdict, stdout, stderr = run_eval(eval_py, gt_dir, init_dir)
            tag = task_dir.relative_to(root).as_posix()
            row = {
                "task": tag,
                "verdict": verdict,
                "stdout_tail": stdout[-400:],
                "stderr_tail": stderr[-400:],
            }
            results.append(row)
            marker = {"True": ".", "False": "X", "error": "?"}[verdict]
            print(f"[{idx:>3}/{len(tasks)}] {marker} {tag}", flush=True)
        summary[bucket] = results

    out = Path(r"d:/research/project-engiworld/Engiworld/_full_task_report.json")
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nReport written to: {out}\n")

    # Pretty per-app summary
    for bucket, rows in summary.items():
        print("=" * 78)
        print(bucket)
        print("=" * 78)
        by_app: dict[str, Counter] = defaultdict(Counter)
        for r in rows:
            by_app[r["task"].split("/", 1)[0]][r["verdict"]] += 1

        width = max((len(a) for a in by_app), default=10)
        print(f"{'app':<{width}}  {'OK':>4}  {'mismatch':>8}  {'cli_skip':>8}  {'total':>5}")
        tot_ok = tot_mis = tot_err = 0
        for app in sorted(by_app):
            c = by_app[app]
            t = c["True"] + c["False"] + c["error"]
            tot_ok += c["True"]
            tot_mis += c["False"]
            tot_err += c["error"]
            print(f"{app:<{width}}  {c['True']:>4}  {c['False']:>8}  {c['error']:>8}  {t:>5}")
        print(f"{'TOTAL':<{width}}  {tot_ok:>4}  {tot_mis:>8}  {tot_err:>8}  {tot_ok+tot_mis+tot_err:>5}")

        miss = [r["task"] for r in rows if r["verdict"] == "False"]
        if miss:
            print(f"\n--- mismatches ({len(miss)}) ---")
            for t in miss:
                print(f"  {t}")
        cli = [(r["task"], err_reason(r["stderr_tail"] or "")) for r in rows if r["verdict"] == "error"]
        if cli:
            print(f"\n--- cli_skip ({len(cli)}) ---")
            rc = Counter(r for _, r in cli)
            for reason, n in rc.most_common():
                print(f"  {n:>3}x  {reason}")
        print()


if __name__ == "__main__":
    main()
