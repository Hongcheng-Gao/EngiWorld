"""Scan all task JSON + eval.py integrity."""
from __future__ import annotations

import ast
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TASK = REPO / "task"

json_err: list[str] = []
eval_issues: list[str] = []
truncated: list[str] = []

for jpath in sorted(TASK.rglob("task-*/task-*.json")):
    if "ground_truth" in jpath.parts or "init_file" in jpath.parts:
        continue
    try:
        json.loads(jpath.read_text(encoding="utf-8"))
    except Exception as e:
        json_err.append(f"{jpath.relative_to(REPO)}: {e}")

for epath in sorted(TASK.rglob("task-*/eval.py")):
    if "ground_truth" in epath.parts:
        continue
    rel = str(epath.relative_to(REPO))
    try:
        src = epath.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        eval_issues.append(f"{rel}: read error {e}")
        continue
    if not src.strip():
        eval_issues.append(f"{rel}: empty")
        continue
    try:
        ast.parse(src)
    except SyntaxError as e:
        eval_issues.append(f"{rel}: syntax {e}")
        continue
    has_eval = "def evaluate(" in src
    has_main = 'if __name__' in src and "main" in src
    # abaqus evals run via abaqus noGUI, may only print true/false
    is_abaqus = "/abaqus/" in rel.replace("\\", "/")
    if not has_eval and not is_abaqus:
        if not has_main:
            eval_issues.append(f"{rel}: no evaluate()/main")

out = REPO / ".scripts" / "integrity_scan_result.txt"
out.write_text(
    f"json_errors={len(json_err)}\n"
    + "\n".join(json_err)
    + f"\n\neval_issues={len(eval_issues)}\n"
    + "\n".join(eval_issues),
    encoding="utf-8",
)
print(out.read_text(encoding="utf-8"))
