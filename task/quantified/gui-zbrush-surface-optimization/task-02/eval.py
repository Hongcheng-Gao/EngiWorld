from __future__ import annotations

import json
import math
import os
from pathlib import Path


DESKTOP = Path(os.environ.get("ENGIWORLD_DESKTOP", Path.home() / "Desktop"))
TASK = json.loads(r"""{
  "instruction_tail": "Optimize a weathered-rock planar-break surface. The opened `seed.obj` is the starting mesh. Use ZBrush sculpting/modeling tools to optimize the shape, then export `C:\\Users\\user\\Desktop\\optimized.obj`. Create strong, coherent planar breaks by fitting the specified height field; this task scores the open surface geometry and does not use or infer enclosed volume.",
  "kind": "rock",
  "metric": "planar-break height-field RMSE with span, mean-height, and face-count penalties",
  "target": {
    "amp": 0.42,
    "freq": 5.0,
    "ridge": 0.08,
    "smooth": 0.2
  },
  "title": "Optimize weathered rock facet balance"
}""")
BASELINE = json.loads(r"""{
  "mean_abs_height": 0.08164,
  "rmse": 0.12123,
  "score": 84.8892
}""")


def z_target(kind, x, y, target):
    amp = target["amp"]
    freq = target["freq"]
    ridge = target["ridge"]
    if kind == "grip":
        return amp * math.sin(freq * math.pi * (x + 1) / 2) * (1 - 0.25 * y * y) + ridge * math.exp(-8 * x * x)
    if kind == "rock":
        return amp * (0.55 * math.sin(freq * x + 1.7 * y) + 0.45 * math.sin(2.2 * x - freq * y)) + ridge * math.cos(4 * x * y)
    if kind == "gasket":
        ring = math.exp(-18 * (math.hypot(x, y) - 0.62) ** 2)
        return amp * ring + ridge * math.exp(-12 * (x * x + y * y))
    if kind == "thumb":
        pocket = -amp * math.exp(-4.5 * (x * x + 0.65 * y * y))
        shoulders = 0.16 * math.exp(-16 * (abs(x) - 0.55) ** 2) * (1 - y * y * 0.3)
        return pocket + shoulders + ridge * math.exp(-8 * y * y)
    if kind == "turbine":
        return amp * math.sin(freq * (x + 0.25 * y)) * (0.45 + 0.55 * (y + 1) / 2) + ridge * x
    return 0.0


def parse_obj(path):
    verts = []
    faces = 0
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("v "):
            parts = line.split()
            if len(parts) >= 4:
                verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif line.startswith("f "):
            faces += 1
    return verts, faces


def score(verts, faces):
    if not verts:
        return {"score": 0.0, "error": "no vertices"}
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)
    bbox_penalty = abs(span_x - 2.0) * 8.0 + abs(span_y - 2.0) * 8.0
    mse = 0.0
    for x, y, z in verts:
        nx = 0.0 if span_x == 0 else 2 * (x - min(xs)) / span_x - 1
        ny = 0.0 if span_y == 0 else 2 * (y - min(ys)) / span_y - 1
        nz = z
        mse += (nz - z_target(TASK["kind"], nx, ny, TASK["target"])) ** 2
    mse /= len(verts)
    rmse = math.sqrt(mse)
    mean_abs_height = sum(abs(z) for z in zs) / len(zs)
    smooth_penalty = abs(mean_abs_height - TASK["target"]["smooth"]) * 15.0
    face_penalty = 0.0
    if faces < 300:
        face_penalty += (300 - faces) * 0.03
    if faces > 8000:
        face_penalty += (faces - 8000) * 0.002
    score_value = max(0.0, 100.0 - rmse * 110.0 - smooth_penalty - bbox_penalty - face_penalty)
    return {
        "score": round(score_value, 4),
        "rmse": round(rmse, 5),
        "mean_abs_height": round(mean_abs_height, 5),
        "face_count": faces,
        "vertex_count": len(verts),
        "bbox_penalty": round(bbox_penalty, 5),
    }


def main():
    obj = DESKTOP / "optimized.obj"
    if not obj.exists():
        print(json.dumps({"score": 0.0, "error": "missing optimized.obj", "baseline_score": BASELINE["score"]}, sort_keys=True))
        return
    verts, faces = parse_obj(obj)
    result = score(verts, faces)
    result.update({"metric_direction": "maximize", "metric_name": TASK["metric"], "baseline_score": BASELINE["score"]})
    notes = DESKTOP / "optimization_notes.json"
    if notes.exists():
        try:
            result["submitted_notes"] = json.loads(notes.read_text(encoding="utf-8"))
        except Exception:
            result["notes_parse_error"] = True
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
