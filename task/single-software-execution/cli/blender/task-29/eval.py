from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")
BLENDER = os.environ.get("BLENDER_PATH", "blender")
FALLBACK_INIT = Path(__file__).resolve().parent / "init_file" / "scene.blend"
INIT_BLEND = DESKTOP / "scene.blend"


@dataclass
class CheckResult:
    name: str
    passed: bool
    msg: str


@dataclass
class ScoreCard:
    checks: list = field(default_factory=list)

    def add(self, name, passed, msg, **_kw):
        self.checks.append(CheckResult(name, passed, msg))

    @property
    def all_passed(self):
        return bool(self.checks) and all(c.passed for c in self.checks)

    @property
    def total_score(self):
        return 1.0 if self.all_passed else 0.0

    def to_dict(self):
        return {"score": self.total_score, "passed": self.all_passed,
                "checks": {c.name: {"passed": c.passed, "msg": c.msg}
                           for c in self.checks}}

    def render(self):
        lines = ["-" * 78]
        for c in self.checks:
            mark = "PASS" if c.passed else "FAIL"
            lines.append(f"  [{mark}]  {c.name:<34} {c.msg}")
        lines.append("-" * 78)
        lines.append(f"  Result: {'PASS' if self.all_passed else 'FAIL'} "
                     f"(score = {self.total_score:.1f})")
        lines.append("-" * 78)
        return "\n".join(lines)


def _run_eval(blend_path):
    import bpy
    import bmesh

    card = ScoreCard()

    if not os.path.isfile(blend_path):
        card.add("file_exists", False, f"no .blend at {blend_path}")
        return card
    init_path = INIT_BLEND if INIT_BLEND.is_file() else FALLBACK_INIT
    if not init_path.is_file():
        card.add("init_exists", False, f"no init .blend at {INIT_BLEND}")
        return card
    card.add("file_exists", True, f"blend = {blend_path}")

    bpy.ops.wm.open_mainfile(filepath=str(init_path))
    src = bpy.data.objects.get("Block")
    if src is None or src.type != "MESH":
        card.add("source_exists", False, "Block missing in init scene")
        return card

    weighted_edges = {
        i for i, item in enumerate(src.data.attributes["bevel_weight_edge"].data)
        if item.value > 0.5
    }
    card.add("weighted_edge_count", len(weighted_edges) == 4,
             f"weighted edges = {sorted(weighted_edges)}")

    bpy.ops.wm.open_mainfile(filepath=blend_path)
    obj = bpy.data.objects.get("Block")
    if obj is None or obj.type != "MESH":
        card.add("object_exists", False, "Block missing")
        return card
    card.add("object_exists", True, "Block present")
    card.add("single_mesh_object", sum(1 for o in bpy.data.objects if o.type == "MESH") == 1,
             "expected exactly one mesh object")
    card.add("modifier_stack_empty", len(obj.modifiers) == 0,
             f"{len(obj.modifiers)} modifier(s) remaining")
    card.add("world_origin", all(abs(c) < 5e-3 for c in obj.matrix_world.translation),
             f"world loc = {tuple(round(c, 4) for c in obj.matrix_world.translation)}")

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)

    tol = 5e-3
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    card.add("bbox_x", abs(min(xs) + 1.0) < tol and abs(max(xs) - 1.0) < tol,
             f"x range ({min(xs):.3f},{max(xs):.3f})")
    card.add("bbox_y", abs(min(ys) + 1.0) < tol and abs(max(ys) - 1.0) < tol,
             f"y range ({min(ys):.3f},{max(ys):.3f})")
    card.add("bbox_z", abs(min(zs) + 1.0) < tol and abs(max(zs) - 1.0) < tol,
             f"z range ({min(zs):.3f},{max(zs):.3f})")

    # Compare the final mesh against the reference bevel output shape.
    bpy.ops.wm.open_mainfile(filepath=str(init_path))
    ref_obj = bpy.data.objects["Block"]
    bpy.context.view_layer.objects.active = ref_obj
    ref_obj.select_set(True)
    mod = ref_obj.modifiers.new("Bevel", "BEVEL")
    mod.width = 0.1
    mod.segments = 2
    mod.profile = 0.5
    mod.limit_method = "WEIGHT"
    bmesh.ops.transform(bmesh.new(), matrix=ref_obj.matrix_world, verts=[])
    bpy.ops.object.modifier_apply(modifier="Bevel")
    ref_bm = bmesh.new()
    ref_bm.from_mesh(ref_obj.data)
    bmesh.ops.transform(ref_bm, matrix=ref_obj.matrix_world, verts=ref_bm.verts)

    def sorted_coords(mesh_bm):
        return sorted((round(v.co.x, 4), round(v.co.y, 4), round(v.co.z, 4)) for v in mesh_bm.verts)

    card.add("geometry_matches_reference", sorted_coords(bm) == sorted_coords(ref_bm),
             "final geometry matches reference bevel result")

    bm.free()
    ref_bm.free()
    return card


def eval_outputs(blend_path, expected=None, postconfig=None):
    return _run_eval(blend_path).to_dict()


def _emit(card):
    print(card.render())
    print("EVAL_RESULT:" + json.dumps(card.to_dict()))


def _run_via_blender(blend_path):
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        result_path = tmp / "result.json"
        runner = tmp / "runner.py"
        runner.write_text(
            "import importlib.util, json\n"
            f"spec = importlib.util.spec_from_file_location('eval_mod', {str(Path(__file__).resolve())!r})\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(mod)\n"
            f"card = mod._run_eval({str(blend_path)!r})\n"
            f"Path = __import__('pathlib').Path\n"
            f"Path({str(result_path)!r}).write_text(json.dumps({{'pass': card.all_passed}}), encoding='utf-8')\n"
            "print('True' if card.all_passed else 'False')\n",
            encoding="utf-8",
        )
        proc = subprocess.run(
            [BLENDER, "--background", "--factory-startup", "--python", str(runner)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        if result_path.exists():
            try:
                return json.loads(result_path.read_text(encoding="utf-8")).get("pass", False)
            except Exception:
                return False
        return proc.returncode == 0


def main():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = argv[1:]
    p = argparse.ArgumentParser(description="Evaluate HH02.")
    p.add_argument("--blend", default=str(DESKTOP / "answer.blend"))
    args = p.parse_args(argv)
    if "bpy" in sys.modules:
        _emit(_run_eval(args.blend))
        return
    print("True" if _run_via_blender(args.blend) else "False")


if __name__ == "__main__":
    main()
