from __future__ import annotations

from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
TOL = 0.08


def load_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or not solids[0].isValid():
        raise ValueError("expected one valid split solid")
    return solids[0]


def bbox_tuple(solid):
    bb = solid.BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def close_tuple(actual, expected) -> bool:
    return all(abs(float(a) - float(e)) <= TOL for a, e in zip(actual, expected))


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def check_core(core) -> bool:
    return (
        close_tuple(bbox_tuple(core), (-50.0, 50.0, -35.0, 35.0, 0.0, 20.0))
        and inside(core, 39.0, 0.0, 1.0)
        and not inside(core, 41.0, 0.0, 1.0)
        and inside(core, 49.0, 0.0, 19.5)
    )


def check_cavity(cavity) -> bool:
    return (
        close_tuple(bbox_tuple(cavity), (-50.0, 50.0, -35.0, 35.0, 20.0, 40.0))
        and inside(cavity, 49.0, 0.0, 20.5)
        and inside(cavity, 39.0, 0.0, 39.0)
        and not inside(cavity, 41.0, 0.0, 39.0)
    )


def evaluate() -> bool:
    core = load_single_solid(OUTPUT_ROOT / "cli_036_core_side.step")
    cavity = load_single_solid(OUTPUT_ROOT / "cli_036_cavity_side.step")
    return (
        check_core(core)
        and check_cavity(cavity)
        and abs(core.Volume() - 108666.7) <= 150.0
        and abs(cavity.Volume() - 108666.7) <= 150.0
    )


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
