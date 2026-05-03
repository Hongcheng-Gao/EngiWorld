"""Check every eval.py against its ground_truth folder.

For each task in task-gt/task-c and task/task-c we patch the Desktop output
path inside eval.py so it points at the task's local ground_truth/ folder,
then run the patched script with the *same* Python interpreter we are using
right now.  If eval prints "True" we count it as a match, otherwise as a
mismatch (or an error if the script crashed before printing anything).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOTS = [
    Path(r"d:/research/project-engiworld/Engiworld/task-gt/task-c"),
    Path(r"d:/research/project-engiworld/Engiworld/task/task-c"),
]

WIN_DESKTOP = r"C:\\Users\\Administrator\\Desktop"
WIN_DESKTOP_FWD = "C:/Users/Administrator/Desktop"
LIN_DESKTOP = "/home/user/Desktop"

# Regex helpers - we want to be permissive about quoting style
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


def run_eval(eval_path: Path, gt_dir: Path, init_dir: Path | None) -> tuple[str, str, str]:
    """Return (verdict, stdout, stderr).  verdict is True/False/error.

    We build a fake "Desktop" by copying init_file/* and ground_truth/* into a
    fresh temp directory, patch the eval.py path constants to point at it, and
    run the patched script.
    """
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
                    # Many GT files use an `answer.*` prefix as a convention.
                    # Also expose them under their plain name so eval.py's
                    # `result.*` / `audit.csv` lookups can find them.
                    name = src.name
                    if name.startswith("answer."):
                        alt = work / rel.parent / name[len("answer."):]
                        shutil.copy2(src, alt)
                        alt2 = work / rel.parent / ("result." + name[len("answer."):])
                        shutil.copy2(src, alt2)

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


def main() -> None:
    summary: dict[str, list[dict]] = {}
    for root in ROOTS:
        bucket = root.parent.name + "/" + root.name
        results = []
        tasks = list(collect_tasks(root))
        print(f"=== {bucket}: {len(tasks)} tasks ===", flush=True)
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
            if verdict != "True":
                if stderr:
                    print(f"    stderr: {stderr.splitlines()[-1][:200]}", flush=True)
        summary[bucket] = results

    out_path = Path(r"d:/research/project-engiworld/Engiworld/_eval_vs_gt_report.json")
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nReport written to: {out_path}")

    # quick statistics
    for bucket, rows in summary.items():
        good = sum(1 for r in rows if r["verdict"] == "True")
        bad = sum(1 for r in rows if r["verdict"] == "False")
        err = sum(1 for r in rows if r["verdict"] == "error")
        print(f"{bucket}: True={good}, False={bad}, error={err}, total={len(rows)}")


if __name__ == "__main__":
    main()
