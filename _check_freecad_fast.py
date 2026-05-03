"""In-process freecad eval-vs-gt check.

Imports cadquery once (~2 min on Windows), then runs every freecad task's
eval logic by:
  1. Reading STEP_SPECS from the eval.py
  2. Resolving each spec's expected STEP file inside the task's ground_truth/
  3. Calling cadquery on that file and checking solid_count / bbox / volume.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

print("[boot] importing cadquery (slow first time)...")
t0 = time.time()
import cadquery as cq
print(f"[boot] cadquery {cq.__version__} ready in {time.time()-t0:.1f}s")

ROOTS = [
    Path(r"d:/research/project-engiworld/Engiworld/task/task-c/freecad"),
    Path(r"d:/research/project-engiworld/Engiworld/task/task-v/freecad"),
]

BBOX_TOL_DEFAULT = 0.05
VOLUME_REL_TOL_DEFAULT = 0.01


def parse_specs(eval_src: str) -> tuple[list[dict], float, float]:
    # STEP_SPECS = [{...}, ...]
    m = re.search(r"STEP_SPECS\s*=\s*(\[.*?\])\s*\n", eval_src, re.DOTALL)
    if not m:
        return [], BBOX_TOL_DEFAULT, VOLUME_REL_TOL_DEFAULT
    specs = eval(m.group(1))

    bbox_tol = BBOX_TOL_DEFAULT
    vol_tol = VOLUME_REL_TOL_DEFAULT
    m2 = re.search(r"BBOX_TOL\s*=\s*([\d.eE+-]+)", eval_src)
    if m2:
        bbox_tol = float(m2.group(1))
    m3 = re.search(r"VOLUME_REL_TOL\s*=\s*([\d.eE+-]+)", eval_src)
    if m3:
        vol_tol = float(m3.group(1))
    return specs, bbox_tol, vol_tol


def summarize_step(path: Path) -> tuple[int, list[float], float]:
    wp = cq.importers.importStep(str(path))
    solids = wp.solids().vals()
    if not solids or any(not s.isValid() for s in solids):
        raise ValueError("invalid STEP")
    xs, ys, zs = [], [], []
    volume = 0.0
    for s in solids:
        bb = s.BoundingBox()
        xs.extend([bb.xmin, bb.xmax])
        ys.extend([bb.ymin, bb.ymax])
        zs.extend([bb.zmin, bb.zmax])
        volume += s.Volume()
    return len(solids), [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)], volume


def check_task(task_dir: Path) -> tuple[str, str]:
    eval_py = task_dir / "eval.py"
    gt_dir = task_dir / "ground_truth"
    if not eval_py.exists() or not gt_dir.exists():
        return "error", "no eval.py or ground_truth"

    src = eval_py.read_text(encoding="utf-8", errors="replace")
    specs, bbox_tol, vol_tol = parse_specs(src)
    if not specs:
        return "error", "no STEP_SPECS parsed"

    for spec in specs:
        # spec["path"] is an absolute Linux/Windows desktop path.
        # Look for the basename inside ground_truth/.
        target = gt_dir / Path(spec["path"]).name
        if not target.exists():
            # Try recursive search inside ground_truth.
            cand = list(gt_dir.rglob(target.name))
            if not cand:
                return "False", f"missing {target.name}"
            target = cand[0]
        try:
            sc, bbox, vol = summarize_step(target)
        except Exception as exc:
            return "False", f"cadquery error on {target.name}: {exc}"
        if sc != spec["solid_count"]:
            return "False", f"{target.name}: solid_count {sc} != {spec['solid_count']}"
        for a, b in zip(bbox, spec["bbox"]):
            if abs(float(a) - float(b)) > bbox_tol:
                return "False", f"{target.name}: bbox {bbox} vs {spec['bbox']}"
        rel = abs(vol - float(spec["volume"])) / max(1.0, abs(float(spec["volume"])))
        if rel > vol_tol:
            return "False", f"{target.name}: volume {vol:.2f} vs {spec['volume']:.2f}"
    return "True", ""


def main() -> None:
    grand_ok = grand_bad = grand_err = 0
    for root in ROOTS:
        if not root.exists():
            print(f"\n[skip] {root} does not exist")
            continue
        bucket = f"{root.parent.parent.name}/{root.parent.name}/{root.name}"
        tasks = sorted(p for p in root.iterdir() if p.is_dir())
        print(f"\n=== {bucket}: {len(tasks)} tasks ===")
        ok = bad = err = 0
        fails = []
        for idx, td in enumerate(tasks, 1):
            verdict, reason = check_task(td)
            marker = {"True": ".", "False": "X", "error": "?"}[verdict]
            print(f"[{idx:>3}/{len(tasks)}] {marker} {td.name}  {reason}", flush=True)
            if verdict == "True":
                ok += 1
            elif verdict == "False":
                bad += 1
                fails.append((td.name, reason))
            else:
                err += 1
        print(f"\n  {bucket}: OK={ok}  mismatch={bad}  error={err}")
        if fails:
            print(f"  --- mismatches in {bucket} ---")
            for n, r in fails:
                print(f"    {n}  ({r})")
        grand_ok += ok; grand_bad += bad; grand_err += err

    print(f"\n=== TOTAL freecad: OK={grand_ok}  mismatch={grand_bad}  error={grand_err} ===")


if __name__ == "__main__":
    main()
