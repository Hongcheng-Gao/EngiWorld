"""Scan every task-c log to determine VM software health.

For each task we look for the eval result line:
  {'error': '...', 'output': '...', 'returncode': N, 'status': 'success'}

Then classify:
  - 'True\\n'   -> software launched AND eval accepted GT  (DEFINITE: software OK)
  - 'False\\n'  -> EITHER software-not-installed OR eval rejected GT (ambiguous)
  - 'true\\n'   -> same as True (some apps print lowercase)
  - 'false\\n'  -> ambiguous
  - other / no-output -> infra error (APIError, sandbox failed, timeout)

We also pull out the "Smoke-tests that ..." doc-string from check_and_eval.py
so we know exactly which command/file each app's smoke test looks for.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

BATCH = Path(r"d:/research/project-engiworld/Engiworld/batch-20260503-202633/task-c")
GT_ROOT = Path(r"d:/research/project-engiworld/Engiworld/task-gt/task-c")

OUTPUT_RE = re.compile(r"\{'error': '[^']*', 'output': '([^']*)', 'returncode': (\d+), 'status': '([^']*)'\}")


def classify(out: str | None) -> str:
    if out is None:
        return "no_output"
    norm = out.replace("\\n", "\n").strip().lower()
    if norm in {"true", "1", "ok", "pass"}:
        return "TRUE"
    if norm in {"false", "0", "fail"}:
        return "FALSE"
    return "other"


def parse_log(log_path: Path) -> tuple[str, str | None]:
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    m = OUTPUT_RE.search(text)
    if m:
        return classify(m.group(1)), m.group(1)
    # No eval line at all -> see whether it's APIError / failed reset
    if "APIError" in text:
        return "infra_apierror", None
    if "FileNotFoundError" in text:
        return "infra_filenotfound", None
    if "timeout" in text.lower():
        return "infra_timeout", None
    return "infra_other", None


def find_smoke_check(app: str) -> str:
    # Use task-21 (or any first task) check_and_eval.py to extract the smoke logic.
    app_dir = GT_ROOT / app
    if not app_dir.exists():
        return "(app dir missing)"
    for task_dir in sorted(app_dir.iterdir()):
        cae = task_dir / "check_and_eval.py"
        if cae.exists():
            txt = cae.read_text(encoding="utf-8", errors="ignore")
            # find check_software body
            m = re.search(r"def check_software[^:]*:\n(.*?)\ndef ", txt, re.DOTALL)
            if m:
                body = m.group(1).strip()
                # collapse whitespace and shorten
                body = re.sub(r"\s+", " ", body)
                return body[:200]
    return "(no check_and_eval.py)"


def main() -> None:
    by_app: dict[str, Counter] = defaultdict(Counter)
    sample_outputs: dict[str, dict[str, str]] = defaultdict(dict)
    if not BATCH.exists():
        print(f"Batch dir not found: {BATCH}")
        return

    for app_dir in sorted(BATCH.iterdir()):
        if not app_dir.is_dir():
            continue
        for task_dir in sorted(app_dir.iterdir()):
            log = next(task_dir.glob("*.log"), None)
            if not log:
                continue
            cat, raw = parse_log(log)
            by_app[app_dir.name][cat] += 1
            if raw and cat not in sample_outputs[app_dir.name]:
                sample_outputs[app_dir.name][cat] = raw

    # Print
    print(f"{'app':<20}  {'TRUE':>4}  {'FALSE':>5}  {'other':>5}  {'apierr':>6}  {'fnf':>4}  {'timeout':>7}  {'infraX':>6}  {'noout':>5}  {'tot':>4}")
    grand = Counter()
    for app in sorted(by_app):
        c = by_app[app]
        total = sum(c.values())
        grand.update(c)
        print(f"{app:<20}  "
              f"{c['TRUE']:>4}  {c['FALSE']:>5}  {c['other']:>5}  "
              f"{c['infra_apierror']:>6}  {c['infra_filenotfound']:>4}  "
              f"{c['infra_timeout']:>7}  {c['infra_other']:>6}  {c['no_output']:>5}  "
              f"{total:>4}")

    print()
    print("=== Software-launch verdict (only counts tasks where check_and_eval actually ran) ===")
    print(f"{'app':<20}  {'launched':>9}  {'False(?)':>9}  {'total_ran':>9}  {'launch%':>7}  smoke-check")
    for app in sorted(by_app):
        c = by_app[app]
        ran = c["TRUE"] + c["FALSE"] + c["other"]
        launched = c["TRUE"]
        if ran == 0:
            verdict = "n/a (infra)"
            pct = "-"
        else:
            pct = f"{100 * launched / ran:.0f}%"
            verdict = launched
        smoke = find_smoke_check(app)
        print(f"{app:<20}  {str(launched):>9}  {str(c['FALSE']):>9}  {str(ran):>9}  {str(pct):>7}  {smoke[:80]}")

    print(f"\nGrand totals: {dict(grand)}")


if __name__ == "__main__":
    main()
