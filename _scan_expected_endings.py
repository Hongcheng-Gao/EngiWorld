"""Scan all task-XX.json files for the line-ending used in evaluator.expected.rules.expected.

The VM stdout-over-HTTP normalises line endings to '\n', but a lot of task
jsons still expect '\r\n'.  Tasks whose expected ends in '\r\n' will fail
exact_match no matter what the eval prints.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOTS = [
    Path(r"d:/research/project-engiworld/Engiworld/task/task-c"),
    Path(r"d:/research/project-engiworld/Engiworld/task/task-v"),
    Path(r"d:/research/project-engiworld/Engiworld/task-gt/task-c"),
    Path(r"d:/research/project-engiworld/Engiworld/task-gt/task-v"),
]


def get_expected(data):
    try:
        return data["evaluator"]["expected"]["rules"]["expected"]
    except Exception:
        return None


def classify(s):
    if not isinstance(s, str):
        return "n/a"
    if s.endswith("\r\n"):
        return "CRLF"
    if s.endswith("\n"):
        return "LF"
    return "no-newline"


for root in ROOTS:
    bucket = f"{root.parent.name}/{root.name}"
    print(f"\n=== {bucket} ===")
    cls_total: Counter = Counter()
    cls_by_app: dict[str, Counter] = defaultdict(Counter)
    json_files = [j for j in root.rglob("task-*.json") if j.parent.name.startswith("task-")]
    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        exp = get_expected(data)
        cls = classify(exp)
        cls_total[cls] += 1
        cls_by_app[jf.parent.parent.name][cls] += 1

    print(f"Overall: {dict(cls_total)}")
    print(f"{'app':<20}  {'CRLF':>5}  {'LF':>5}  {'no-newline':>10}  {'n/a':>4}")
    for app, c in sorted(cls_by_app.items()):
        total = sum(c.values())
        print(f"{app:<20}  {c['CRLF']:>5}  {c['LF']:>5}  {c['no-newline']:>10}  {c['n/a']:>4}  (total {total})")
