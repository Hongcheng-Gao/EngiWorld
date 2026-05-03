"""Analyse the JSON report produced by _check_eval_vs_gt.py."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REPORT = Path(r"d:/research/project-engiworld/Engiworld/_eval_vs_gt_report.json")

data = json.loads(REPORT.read_text(encoding="utf-8"))

for bucket, rows in data.items():
    print(f"\n========== {bucket} ==========")
    by_app = {}
    for r in rows:
        app = r["task"].split("/", 1)[0]
        by_app.setdefault(app, Counter())[r["verdict"]] += 1
    print(f"{'app':<20}{'True':>6}{'False':>7}{'error':>7}")
    for app, c in sorted(by_app.items()):
        print(f"{app:<20}{c['True']:>6}{c['False']:>7}{c['error']:>7}")

    print(f"\n--- Mismatches (verdict=False) in {bucket} ---")
    for r in rows:
        if r["verdict"] == "False":
            print(f"  {r['task']}")

    print(f"\n--- Error reasons in {bucket} (top patterns) ---")
    err_msgs = Counter()
    for r in rows:
        if r["verdict"] == "error":
            stderr = r["stderr_tail"] or ""
            stdout = r["stdout_tail"] or ""
            line = (stderr or stdout).splitlines()[-1] if (stderr or stdout) else "(no output)"
            err_msgs[line[:120]] += 1
    for msg, n in err_msgs.most_common(20):
        print(f"  {n:>3}x  {msg}")
