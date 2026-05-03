"""Pretty per-app report for the full task/ run."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

REPORT = Path(r"d:/research/project-engiworld/Engiworld/_full_task_report.json")
data = json.loads(REPORT.read_text(encoding="utf-8"))


def classify(row):
    if row["verdict"] == "True":
        return "True"
    if row["verdict"] == "False":
        return "mismatch"
    return "cli_skip"


def err_reason(row):
    err = row.get("stderr_tail") or ""
    if "cadquery" in err:
        return "missing cadquery (STEP)"
    if "pymupdf" in err or "fitz" in err:
        return "missing pymupdf"
    if "ifcopenshell" in err:
        return "missing ifcopenshell"
    if "trimesh" in err:
        return "missing trimesh"
    if "ezdxf" in err:
        return "missing ezdxf"
    return err.splitlines()[-1][:120] if err else "(no stderr)"


def header(s):
    print("\n" + "=" * 78)
    print(s)
    print("=" * 78)


for bucket, rows in data.items():
    header(bucket)
    by_app = defaultdict(Counter)
    for r in rows:
        by_app[r["task"].split("/", 1)[0]][classify(r)] += 1

    width = max(len(a) for a in by_app)
    print(f"{'app':<{width}}  {'OK':>4}  {'mismatch':>8}  {'cli_skip':>8}  {'total':>5}")
    tot_ok = tot_mis = tot_err = 0
    for app in sorted(by_app):
        c = by_app[app]
        tot = c["True"] + c["mismatch"] + c["cli_skip"]
        tot_ok += c["True"]; tot_mis += c["mismatch"]; tot_err += c["cli_skip"]
        print(f"{app:<{width}}  {c['True']:>4}  {c['mismatch']:>8}  {c['cli_skip']:>8}  {tot:>5}")
    print(f"{'TOTAL':<{width}}  {tot_ok:>4}  {tot_mis:>8}  {tot_err:>8}  {tot_ok+tot_mis+tot_err:>5}")

    miss = [r["task"] for r in rows if classify(r) == "mismatch"]
    if miss:
        print(f"\n--- mismatches ({len(miss)}) ---")
        for t in miss:
            print(f"  {t}")

    cli = [(r["task"], err_reason(r)) for r in rows if classify(r) == "cli_skip"]
    if cli:
        print(f"\n--- cli_skip ({len(cli)}) ---")
        rc = Counter(r for _, r in cli)
        for reason, n in rc.most_common():
            print(f"  {n:>3}x  {reason}")
