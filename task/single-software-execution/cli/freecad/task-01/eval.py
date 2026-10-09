from __future__ import annotations

import os
from pathlib import Path
import cadquery as cq

DEFAULT_OUTPUT = Path('/home/user/Desktop/freecad_task-01_output.step')
SOLID_COUNT = 5
GLOBAL_BBOX = [0.0, 120.0, 0.0, 70.0, 0.0, 32.0]
TOTAL_VOLUME = 89814.318109
SOLID_BBOXES = [[0.0, 120.0, 0.0, 70.0, 0.0, 8.0], [12.0, 77.0, 12.0, 22.0, 8.0, 20.0], [84.0, 96.0, 18.0, 58.0, 8.0, 20.0], [24.0, 36.0, 40.0, 64.0, 8.0, 32.0], [87.0, 105.0, 43.0, 61.0, 8.0, 30.0]]
SOLID_VOLUMES = [67200.0, 7800.0, 5760.0, 3456.0, 5598.318109]
SOLID_PROBES = [[60, 35, 4], [30, 17, 14], [90, 40, 14], [30, 45, 12], [96, 52, 20]]
EMPTY_PROBES = [[80, 17, 14], [90, 14, 14], [30, 62, 30], [96, 52, 31], [130, 20, 5]]
BBOX_TOL = 0.15
POINT_TOL = 1.0e-4
VOLUME_REL_TOL = 0.01
SOLID_VOLUME_REL_TOL = 0.015


def _bbox(solid):
    bb = solid.BoundingBox()
    return [bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax]


def _all_bbox(solids):
    xs, ys, zs = [], [], []
    for solid in solids:
        bb = solid.BoundingBox()
        xs.extend([bb.xmin, bb.xmax]); ys.extend([bb.ymin, bb.ymax]); zs.extend([bb.zmin, bb.zmax])
    return [min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)]


def _close_list(actual, expected, tol):
    return all(abs(float(a) - float(e)) <= tol for a, e in zip(actual, expected))


def _close_volume(actual, expected, rel_tol):
    return abs(float(actual) - float(expected)) / max(1.0, abs(float(expected))) <= rel_tol


def _contains(solids, point):
    return any(solid.isInside(tuple(point), POINT_TOL) for solid in solids)


def evaluate() -> bool:
    path = Path(os.environ.get('FREECAD_EVAL_OUTPUT', str(DEFAULT_OUTPUT)))
    if not path.exists() or path.stat().st_size <= 0:
        return False
    wp = cq.importers.importStep(str(path))
    solids = wp.solids().vals()
    if len(solids) != SOLID_COUNT:
        return False
    if not solids or any(not solid.isValid() for solid in solids):
        return False
    if not _close_list(_all_bbox(solids), GLOBAL_BBOX, BBOX_TOL):
        return False
    if not _close_volume(sum(solid.Volume() for solid in solids), TOTAL_VOLUME, VOLUME_REL_TOL):
        return False
    actual_bboxes = sorted([_bbox(s) for s in solids], key=lambda b: (round(b[0], 3), round(b[2], 3), round(b[4], 3)))
    expected_bboxes = sorted(SOLID_BBOXES, key=lambda b: (round(b[0], 3), round(b[2], 3), round(b[4], 3)))
    for got, want in zip(actual_bboxes, expected_bboxes):
        if not _close_list(got, want, BBOX_TOL):
            return False
    for got, want in zip(sorted([s.Volume() for s in solids]), sorted(SOLID_VOLUMES)):
        if not _close_volume(got, want, SOLID_VOLUME_REL_TOL):
            return False
    for point in SOLID_PROBES:
        if not _contains(solids, point):
            return False
    for point in EMPTY_PROBES:
        if _contains(solids, point):
            return False
    return True


if __name__ == '__main__':
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
    raise SystemExit(0)
