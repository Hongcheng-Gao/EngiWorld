from __future__ import annotations

from pathlib import Path

import cadquery as cq

STEP_SPECS = [{'path': '/home/user/Desktop/freecad_task-19_output.step', 'solid_count': 1, 'bbox': [70.0, 56.0, 38.0], 'volume': 83638.13402}]
BBOX_TOL = 0.05
VOLUME_REL_TOL = 0.01


def summarize_step(path: Path):
    wp = cq.importers.importStep(str(path))
    solids = wp.solids().vals()
    if not solids or any(not solid.isValid() for solid in solids):
        raise ValueError("invalid STEP")
    xs, ys, zs = [], [], []
    volume = 0.0
    for solid in solids:
        bbox = solid.BoundingBox()
        xs.extend([bbox.xmin, bbox.xmax])
        ys.extend([bbox.ymin, bbox.ymax])
        zs.extend([bbox.zmin, bbox.zmax])
        volume += solid.Volume()
    return len(solids), [max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)], volume


def evaluate() -> bool:
    for spec in STEP_SPECS:
        path = Path(spec["path"])
        if not path.exists() or path.stat().st_size <= 0:
            return False
        solid_count, bbox, volume = summarize_step(path)
        if solid_count != spec["solid_count"]:
            return False
        if any(abs(float(a) - float(b)) > BBOX_TOL for a, b in zip(bbox, spec["bbox"])):
            return False
        if abs(volume - float(spec["volume"])) / max(1.0, abs(float(spec["volume"]))) > VOLUME_REL_TOL:
            return False
    return True


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print("true" if ok else "false")
    raise SystemExit(0)
