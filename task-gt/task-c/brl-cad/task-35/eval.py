from __future__ import annotations

from pathlib import Path

import trimesh


TASK_ID = 'task-35'
STL_SPECS = [{'path': 'out.stl', 'bbox': [115.0, 45.0, 23.0], 'vertices': 8, 'faces': 12}]
OUTPUT_PATH = Path('/home/user/Desktop/out.stl')
BBOX_TOL = 0.05


def summarize_stl(path: Path) -> dict[str, object]:
    mesh = trimesh.load(str(path), force="mesh")
    if getattr(mesh, "is_empty", True) or len(mesh.vertices) == 0 or len(mesh.faces) == 0:
        raise ValueError("invalid_stl")
    bounds = mesh.bounds
    extents = bounds[1] - bounds[0]
    return {
        "bbox": [round(float(value), 4) for value in extents],
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
    }


def evaluate() -> bool:
    if not STL_SPECS or not OUTPUT_PATH.exists() or OUTPUT_PATH.stat().st_size <= 0:
        return False
    spec = STL_SPECS[0]
    actual = summarize_stl(OUTPUT_PATH)
    if actual["faces"] != spec["faces"] or actual["vertices"] != spec["vertices"]:
        return False
    if any(abs(float(a) - float(b)) > BBOX_TOL for a, b in zip(actual["bbox"], spec["bbox"])):
        return False
    return True


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
