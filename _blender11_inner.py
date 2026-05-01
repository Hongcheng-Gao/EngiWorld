"""Evaluator for task HM05 - Three-Operation Machining of a Casting.

Runs inside Blender's Python:
    blender --background --python eval.py -- --blend <path/to/answer.blend>

Also exposes `eval_outputs(blend_path)` for external harnesses.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field


SPEC = {
    "object_name":    "Casting",
    "x_half":         1.0,       # x in [-1, +1]
    "y_half":         0.7,       # y in [-0.7, +0.7]
    "z_min":          0.0,
    "z_max_after":    0.9,       # after face-off
    "through_radius": 0.25,
    "pin_radius":     0.05,
    "pin_center_yz":  (0.0, 0.45),
    "pin_depth":      0.45,
    "tolerance":      0.02,
}


@dataclass
class CheckResult:
    name: str
    passed: bool
    msg: str


@dataclass
class ScoreCard:
    checks: list = field(default_factory=list)

    def add(self, name, passed, msg):
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


def _run_eval(blend_path):
    import bpy
    import bmesh
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    bpy.ops.wm.open_mainfile(filepath=blend_path)
    card = ScoreCard()

    name = SPEC["object_name"]
    tol  = SPEC["tolerance"]

    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        card.add("single_casting_object", False,
                 f"'{name}' missing or not a mesh")
        return card

    n_mesh = sum(1 for o in bpy.data.objects if o.type == "MESH")
    card.add("single_casting_object",
             n_mesh == 1 and obj.type == "MESH",
             f"{n_mesh} mesh object(s), '{name}' type={obj.type}")

    # Modifier stack must be empty.
    card.add("modifier_stack_empty", len(obj.modifiers) == 0,
             f"{len(obj.modifiers)} modifier(s) remaining")

    # Location / rotation unchanged (input: loc=(0,0,0.5), rot=(0,0,0)).
    loc = obj.location
    rot = obj.rotation_euler
    loc_ok = (abs(loc.x) < tol and abs(loc.y) < tol
              and abs(loc.z - 0.5) < tol)
    rot_ok = (abs(rot.x) < tol and abs(rot.y) < tol and abs(rot.z) < tol)
    card.add("transform_unchanged", loc_ok and rot_ok,
             f"loc=({loc.x:.4f},{loc.y:.4f},{loc.z:.4f}), "
             f"rot=({rot.x:.4f},{rot.y:.4f},{rot.z:.4f})")

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)

    non_manifold = [e for e in bm.edges if not e.is_manifold]
    loose_verts  = [v for v in bm.verts if not v.link_edges]
    card.add("closed_manifold_mesh",
             len(non_manifold) == 0 and len(loose_verts) == 0,
             "closed-manifold" if (not non_manifold and not loose_verts)
             else f"{len(non_manifold)} non-manifold edge(s), "
                  f"{len(loose_verts)} loose vert(s)")

    if not bm.verts:
        card.add("envelope", False, "no verts")
        bm.free()
        return card

    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]

    env_ok = (
        abs(min(xs) + SPEC["x_half"]) < tol
        and abs(max(xs) - SPEC["x_half"]) < tol
        and abs(min(ys) + SPEC["y_half"]) < tol
        and abs(max(ys) - SPEC["y_half"]) < tol
        and abs(min(zs) - SPEC["z_min"]) < tol
        and abs(max(zs) - SPEC["z_max_after"]) < tol
    )
    card.add("envelope",
             env_ok,
             f"x=[{min(xs):.4f},{max(xs):.4f}] "
             f"y=[{min(ys):.4f},{max(ys):.4f}] "
             f"z=[{min(zs):.4f},{max(zs):.4f}]")

    bvh = BVHTree.FromBMesh(bm)

    # Op 2: central through-hole. Vertical ray on axis must pass through.
    ray_origin = Vector((0.0, 0.0, 1.5))
    hit, *_ = bvh.ray_cast(ray_origin, Vector((0.0, 0.0, -1.0)), 3.0)
    # Off-axis ray (x=0.4) must hit the faced-off top at z=0.9.
    ray_near = Vector((0.40, 0.0, 1.5))
    hit_near, *_ = bvh.ray_cast(ray_near, Vector((0.0, 0.0, -1.0)), 3.0)
    near_ok = (hit_near is not None
               and abs(hit_near.z - SPEC["z_max_after"]) < tol)

    # Probe through-hole radius by increasing offset; first-hit offset is an
    # upper bound on radius, previous offset is lower.
    def through_hole_radius_probe():
        for offset in [0.05 * i for i in range(1, 10)]:  # 0.05 .. 0.45
            r_ray = Vector((offset, 0.0, 1.5))
            h, *_ = bvh.ray_cast(r_ray, Vector((0.0, 0.0, -1.0)), 3.0)
            if h is not None:
                return offset
        return None

    hole_edge = through_hole_radius_probe()
    radius_ok = (hole_edge is not None
                 and abs((hole_edge - 0.025) - SPEC["through_radius"]) < 0.05)

    card.add("central_through_hole",
             hit is None and near_ok and radius_ok,
             f"axis ray {'through' if hit is None else 'BLOCKED'}; "
             f"near-ray top z="
             f"{f'{hit_near.z:.3f}' if hit_near is not None else 'None'}; "
             f"radius edge near offset="
             f"{f'{hole_edge:.3f}' if hole_edge is not None else 'None'}")

    # Op 3: pin holes. First hit on the +X ray at (y=0, z=0.45) heading -X
    # must be the blind end at x = +1 - 0.45 = +0.55 (outer face is drilled).
    py_, pz_ = SPEC["pin_center_yz"]
    origin_plus  = Vector((+2.0, py_, pz_))
    hit_plus,  *_ = bvh.ray_cast(origin_plus,  Vector((-1.0, 0.0, 0.0)), 4.0)
    origin_minus = Vector((-2.0, py_, pz_))
    hit_minus, *_ = bvh.ray_cast(origin_minus, Vector((+1.0, 0.0, 0.0)), 4.0)
    exp_blind_plus  =  SPEC["x_half"] - SPEC["pin_depth"]
    exp_blind_minus = -(SPEC["x_half"] - SPEC["pin_depth"])
    plus_ok  = hit_plus  is not None and abs(hit_plus.x  - exp_blind_plus)  < tol
    minus_ok = hit_minus is not None and abs(hit_minus.x - exp_blind_minus) < tol

    # Off-axis ray (y=0.3) at same z must hit the outer +X face at x=+1.
    off_plus = Vector((+2.0, 0.3, pz_))
    hit_off, *_ = bvh.ray_cast(off_plus, Vector((-1.0, 0.0, 0.0)), 4.0)
    off_ok = (hit_off is not None
              and abs(hit_off.x - SPEC["x_half"]) < tol)

    card.add("pin_holes",
             plus_ok and minus_ok and off_ok,
             f"+X blind x="
             f"{f'{hit_plus.x:.4f}' if hit_plus is not None else 'None'}, "
             f"-X blind x="
             f"{f'{hit_minus.x:.4f}' if hit_minus is not None else 'None'}, "
             f"off-axis +X face x="
             f"{f'{hit_off.x:.4f}' if hit_off is not None else 'None'}")

    bm.free()
    return card


def _emit(card):
    print(card.render())
    print("EVAL_RESULT:" + json.dumps(card.to_dict()))


def eval_outputs(blend_path, expected=None, postconfig=None):
    """Harness entry point. Runs the full evaluation on ``blend_path`` and
    returns a dict with keys ``score``, ``passed``, and per-check details."""
    return _run_eval(blend_path).to_dict()


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser(description="Evaluate HM05.")
    p.add_argument("--blend", required=True)
    args = p.parse_args(argv)
    _emit(_run_eval(args.blend))


if __name__ == "__main__":
    main()
