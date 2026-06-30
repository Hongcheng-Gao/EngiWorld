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
            lines.append(f"  [{mark}]  {c.name:<32} {c.msg}")
        lines.append("-" * 78)
        lines.append(f"  Result: {'PASS' if self.all_passed else 'FAIL'} "
                     f"(score = {self.total_score:.1f})")
        lines.append("-" * 78)
        return "\n".join(lines)


def _vec_close(a, b, tol):
    return all(abs(x - y) < tol for x, y in zip(a, b))


def _snapshot(obj):
    mw = obj.matrix_world
    rot = mw.to_euler()
    return {
        "world_loc": tuple(mw.translation),
        "world_rot": tuple(rot),
        "local_loc": tuple(obj.location),
        "local_rot": tuple(obj.rotation_euler),
    }


def _run_eval(blend_path):
    import bpy

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
    init = {}
    for name in ("Arm1", "Arm2", "Arm3"):
        ob = bpy.data.objects.get(name)
        card.add(f"init_{name}_exists", ob is not None,
                 f"{name}: {'present' if ob else 'MISSING'}")
        if ob is None:
            return card
        init[name] = _snapshot(ob)

    bpy.ops.wm.open_mainfile(filepath=blend_path)
    a1 = bpy.data.objects.get("Arm1")
    a2 = bpy.data.objects.get("Arm2")
    a3 = bpy.data.objects.get("Arm3")
    for name, ob in (("arm1", a1), ("arm2", a2), ("arm3", a3)):
        card.add(f"{name}_exists", ob is not None,
                 f"{name}: {'present' if ob else 'MISSING'}")
    if not (a1 and a2 and a3):
        return card

    card.add("arm1_has_no_parent", a1.parent is None,
             f"Arm1.parent = {a1.parent.name if a1.parent else 'None'}")
    card.add("arm2_parent_is_arm1", a2.parent is a1,
             f"Arm2.parent = {a2.parent.name if a2.parent else 'None'}")
    card.add("arm3_parent_is_arm2", a3.parent is a2,
             f"Arm3.parent = {a3.parent.name if a3.parent else 'None'}")

    tol = 5e-3
    w1 = a1.matrix_world
    i1 = init["Arm1"]["world_loc"]
    r1 = init["Arm1"]["world_rot"]
    card.add("arm1_world_loc", _vec_close(w1.translation, i1, tol),
             f"Arm1 world loc = ({w1.translation.x:.4f},{w1.translation.y:.4f},{w1.translation.z:.4f})")
    r1_now = w1.to_euler()
    card.add("arm1_world_rot", _vec_close((r1_now.x, r1_now.y, r1_now.z), r1, tol),
             f"Arm1 world rot = ({r1_now.x:.4f},{r1_now.y:.4f},{r1_now.z:.4f})")

    w2 = a2.matrix_world
    i2 = init["Arm2"]
    card.add("arm2_world_loc", _vec_close(w2.translation, i2["world_loc"], tol),
             f"Arm2 world loc = ({w2.translation.x:.4f},{w2.translation.y:.4f},{w2.translation.z:.4f})")
    card.add("arm2_local_xy_unchanged",
             _vec_close((a2.rotation_euler.x, a2.rotation_euler.y),
                        (i2["local_rot"][0], i2["local_rot"][1]), tol),
             f"Arm2 local XY = ({a2.rotation_euler.x:.4f},{a2.rotation_euler.y:.4f})")
    target_z = i2["local_rot"][2] + math.radians(30.0)
    card.add("arm2_local_z_rotated", abs(a2.rotation_euler.z - target_z) < tol,
             f"Arm2 local Z = {a2.rotation_euler.z:.4f} rad (target {target_z:.4f})")

    w3 = a3.matrix_world
    i3 = init["Arm3"]["world_loc"]
    d3 = math.sqrt(sum((w3.translation[i] - i3[i]) ** 2 for i in range(3)))
    card.add("arm3_world_loc_preserved", d3 < tol,
             f"Arm3 world loc = ({w3.translation.x:.4f},{w3.translation.y:.4f},{w3.translation.z:.4f}); err = {d3:.5f}")

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
    p = argparse.ArgumentParser(description="Evaluate HH01.")
    p.add_argument("--blend", required=True)
    args = p.parse_args(argv)
    if "bpy" in sys.modules:
        _emit(_run_eval(args.blend))
        return
    print("True" if _run_via_blender(args.blend) else "False")


if __name__ == "__main__":
    main()
