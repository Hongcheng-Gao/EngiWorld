"""Evaluator for SK-C-01 - Parametric Straight-Run Staircase.

Submission format: a native SketchUp model saved as `answer.skp`.

The evaluator launches the local SketchUp desktop application, installs a
temporary Ruby bridge plugin, opens the submitted `.skp`, dumps the model's
world-space face polygons to JSON, and then verifies that the model contains
exactly N disconnected cuboid treads placed at the required positions.

Usage:

    python eval.py --dir path/to/output_dir

or programmatically:

    from eval import eval_outputs
    eval_outputs(output_dir)
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field


HERE = os.path.dirname(os.path.abspath(__file__))
BRIDGE_RB = os.path.join(HERE, "_internal", "sketchup_bridge.rb")

# Expected values derived from init_file/params.json (fixed for this task).
SPEC = {
    "total_rise_m": 3.0,
    "total_run_m": 3.2,
    "max_rise_per_step_mm": 190,
    "tread_thickness_mm": 50,
    "tread_width_m": 1.0,
}
EXPECTED_N = math.ceil(SPEC["total_rise_m"] * 1000 / SPEC["max_rise_per_step_mm"])  # 16
RISE_PER_STEP = SPEC["total_rise_m"] / EXPECTED_N
RUN_PER_STEP = SPEC["total_run_m"] / EXPECTED_N
THICKNESS = SPEC["tread_thickness_mm"] / 1000.0
WIDTH = SPEC["tread_width_m"]

POS_TOL = 0.002
SIZE_TOL = 0.01
GRID_TOL = 1e-4


@dataclass
class Check:
    name: str
    passed: bool
    msg: str


@dataclass
class ScoreCard:
    checks: list = field(default_factory=list)

    def add(self, name, passed, msg, **_):
        self.checks.append(Check(name, passed, msg))

    @property
    def all_passed(self):
        return bool(self.checks) and all(c.passed for c in self.checks)

    @property
    def total_score(self):
        return 1.0 if self.all_passed else 0.0

    def to_dict(self):
        return {
            "score": self.total_score,
            "passed": self.all_passed,
            "checks": {c.name: {"passed": c.passed, "msg": c.msg} for c in self.checks},
        }

    def render(self):
        lines = ["-" * 78]
        for c in self.checks:
            mark = "PASS" if c.passed else "FAIL"
            lines.append(f"  [{mark}]  {c.name:<32} {c.msg}")
        lines.append("-" * 78)
        lines.append(
            f"  Result: {'PASS' if self.all_passed else 'FAIL'}  "
            f"(score = {self.total_score:.1f})"
        )
        return "\n".join(lines)


def _find_sketchup_exe():
    candidates = []
    env_path = os.environ.get("ENGIWORLD_SKETCHUP_EXE")
    if env_path:
        candidates.append(env_path)
    candidates.append(r"D:\sketchup\SketchUp\SketchUp.exe")

    for base in filter(None, [os.environ.get("ProgramW6432"), os.environ.get("ProgramFiles")]):
        candidates.extend(
            sorted(
                glob.glob(os.path.join(base, "SketchUp", "SketchUp *", "SketchUp.exe")),
                reverse=True,
            )
        )

    for path in candidates:
        if path and os.path.exists(path):
            return os.path.normpath(path)
    return None


def _find_plugins_dir():
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    roots = sorted(
        glob.glob(os.path.join(appdata, "SketchUp", "SketchUp *", "SketchUp")),
        reverse=True,
    )
    if not roots:
        return None
    return os.path.join(roots[0], "Plugins")


def _quantize(value, tol=GRID_TOL):
    return int(round(float(value) / tol))


def _qpoint(pt, tol=GRID_TOL):
    return tuple(_quantize(v, tol) for v in pt)


def _collect_components(faces):
    point_to_faces = defaultdict(set)
    face_points = []

    for idx, face in enumerate(faces):
        pts = [_qpoint(p) for p in face]
        face_points.append(pts)
        for pt in set(pts):
            point_to_faces[pt].add(idx)

    neighbors = [set() for _ in face_points]
    for ids in point_to_faces.values():
        ids = list(ids)
        for i in ids:
            neighbors[i].update(j for j in ids if j != i)

    seen = set()
    comps = []
    for start in range(len(face_points)):
        if start in seen:
            continue
        stack = [start]
        comp = set()
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            comp.add(cur)
            stack.extend(neighbors[cur] - seen)
        comps.append(sorted(comp))
    return comps


def _bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def _close(a, b, tol):
    return abs(a - b) <= tol


def _run_sketchup_extract(skp_path):
    sketchup_exe = _find_sketchup_exe()
    if not sketchup_exe:
        raise RuntimeError("SketchUp.exe not found")

    plugins_dir = _find_plugins_dir()
    if not plugins_dir:
        raise RuntimeError("SketchUp plugins directory not found under %APPDATA%")

    os.makedirs(plugins_dir, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="skc01_eval_") as tmpdir:
        summary_path = os.path.join(tmpdir, "summary.json")
        error_path = os.path.join(tmpdir, "bridge_error.txt")
        plugin_name = f"engiworld_skc01_{uuid.uuid4().hex}.rb"
        plugin_path = os.path.join(plugins_dir, plugin_name)

        shutil.copy2(BRIDGE_RB, plugin_path)
        env = os.environ.copy()
        env["ENGIWORLD_TASK01_MODE"] = "extract_faces"
        env["ENGIWORLD_TASK01_SUMMARY_JSON"] = summary_path
        env["ENGIWORLD_TASK01_ERROR_LOG"] = error_path

        proc = None
        try:
            proc = subprocess.Popen([sketchup_exe, skp_path], env=env)
            deadline = time.time() + 120.0
            while time.time() < deadline:
                if os.path.exists(summary_path):
                    with open(summary_path, "r", encoding="utf-8") as fh:
                        return json.load(fh)
                if os.path.exists(error_path):
                    with open(error_path, "r", encoding="utf-8", errors="ignore") as fh:
                        raise RuntimeError(fh.read().strip() or "SketchUp bridge failed")
                time.sleep(1.0)
            raise RuntimeError("Timed out waiting for SketchUp bridge output")
        finally:
            try:
                if proc is not None and proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=10)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            try:
                os.remove(plugin_path)
            except OSError:
                pass


def eval_outputs(output_dir):
    sc = ScoreCard()
    skp_path = os.path.join(output_dir, "answer.skp")

    if not os.path.exists(skp_path):
        sc.add("file_exists", False, f"answer.skp not found at {skp_path}")
        return sc
    sc.add("file_exists", True, f"found {os.path.basename(skp_path)}")

    try:
        data = _run_sketchup_extract(skp_path)
    except Exception as e:
        sc.add("sketchup_extract", False, f"extract failed: {e!r}")
        return sc

    faces = data.get("faces") or []
    if not faces:
        sc.add("sketchup_extract", False, "no faces extracted from SketchUp model")
        return sc
    sc.add("sketchup_extract", True, f"{len(faces)} face polygons extracted")

    comps = _collect_components(faces)
    sc.add(
        "tread_count",
        len(comps) == EXPECTED_N,
        f"found {len(comps)} disconnected solids; expected {EXPECTED_N}",
    )

    all_points = [tuple(pt) for face in faces for pt in face]
    x0, y0, z0, x1, y1, z1 = _bbox(all_points)
    sc.add(
        "overall_bbox",
        _close(x1 - x0, SPEC["total_run_m"], SIZE_TOL)
        and _close(y1 - y0, WIDTH, SIZE_TOL)
        and _close(z1, SPEC["total_rise_m"], POS_TOL)
        and _close(z0, RISE_PER_STEP - THICKNESS, POS_TOL),
        (
            f"bbox spans=({x1 - x0:.4f}, {y1 - y0:.4f}, {z1 - z0:.4f}) "
            f"z-range=({z0:.4f}, {z1:.4f})"
        ),
    )

    matched = 0
    cuboids_ok = 0
    used_indices = set()

    for comp in comps:
        comp_points = [tuple(pt) for face_idx in comp for pt in faces[face_idx]]
        unique_points = sorted({_qpoint(pt): pt for pt in comp_points}.values())
        bx0, by0, bz0, bx1, by1, bz1 = _bbox(unique_points)
        ux = sorted({_quantize(pt[0]) for pt in unique_points})
        uy = sorted({_quantize(pt[1]) for pt in unique_points})
        uz = sorted({_quantize(pt[2]) for pt in unique_points})

        is_cuboid = (
            len(comp) == 6
            and len(unique_points) == 8
            and len(ux) == 2
            and len(uy) == 2
            and len(uz) == 2
            and _close(bx1 - bx0, RUN_PER_STEP, POS_TOL)
            and _close(by1 - by0, WIDTH, POS_TOL)
            and _close(bz1 - bz0, THICKNESS, POS_TOL)
            and _close(by0, 0.0, POS_TOL)
        )
        if is_cuboid:
            cuboids_ok += 1

        found_idx = None
        for i in range(EXPECTED_N):
            ex0 = i * RUN_PER_STEP
            ex1 = (i + 1) * RUN_PER_STEP
            ez1 = (i + 1) * RISE_PER_STEP
            ez0 = ez1 - THICKNESS
            if (
                _close(bx0, ex0, POS_TOL)
                and _close(bx1, ex1, POS_TOL)
                and _close(bz0, ez0, POS_TOL)
                and _close(bz1, ez1, POS_TOL)
            ):
                found_idx = i
                break

        if found_idx is not None and found_idx not in used_indices:
            used_indices.add(found_idx)
            matched += 1

    sc.add(
        "cuboid_solids",
        cuboids_ok == EXPECTED_N,
        f"{cuboids_ok}/{EXPECTED_N} components are axis-aligned 6-face cuboids",
    )
    sc.add(
        "tread_positions",
        matched == EXPECTED_N,
        f"{matched}/{EXPECTED_N} expected tread bounding boxes matched",
    )

    return sc


def _main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default=os.path.join(HERE, "ground_truth"))
    args = parser.parse_args(argv)

    sc = eval_outputs(args.dir)
    print(sc.render())
    print(json.dumps(sc.to_dict(), indent=2))
    return 0 if sc.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(_main())

