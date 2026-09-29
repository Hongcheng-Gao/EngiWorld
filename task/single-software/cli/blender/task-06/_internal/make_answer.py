"""Build ground_truth/answer.blend for task AH06 - Field-Driven Instance
Rotation.

Adds a Geometry Nodes modifier on `Globe` that scatters ~500 `Spike`
instances across the sphere's surface with each spike's local +Z axis
aligned to the surface normal at the base, plus a small (+/- 5 deg)
per-instance random twist around that normal seeded from Seed=42.

GN tree:
    Group Input (Geometry)
      -> Distribute Points on Faces (POISSON, distance_min, density_max,
                                     seed=42)
      -> Align Euler to Vector (axis=Z, factor=1, vector=normal)
      -> Random Value (FLOAT, -5 deg .. +5 deg, seed=42)
      -> Rotate Euler (AXIS_ANGLE, axis=normal, angle=random_tilt)
      -> Instance on Points (Instance = Object Info(Spike), Rotation = ...)
      -> Group Output (Geometry)

Do NOT realize the instances - leave them as true instances so the
depsgraph exposes their transforms.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import math
import os

import bpy

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUT_PATH   = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

# Spec constants.
SEED        = 42
TARGET_CNT  = 500
TILT_DEG    = 5.0

# Poisson tuning for a sphere of surface area 4*pi*r^2 = 28.274 BU^2.
# The caller can tune these params to land near TARGET_CNT. We'll start
# with a reasonable guess and iterate.
DISTANCE_MIN = 0.14
DENSITY_MAX  = 50.0


def mknode(tree, bl_idname, x, y, name=None):
    n = tree.nodes.new(bl_idname)
    n.location = (x, y)
    if name is not None:
        n.name = name
        n.label = name
    return n


def build_gn_tree(globe, spike, distance_min, density_max):
    """Build (or rebuild) the GN modifier + node tree. Returns
    (modifier, node_tree, distribute_node). Any existing modifier on
    Globe is removed first."""
    # Purge any pre-existing GN modifier + node group.
    for m in list(globe.modifiers):
        globe.modifiers.remove(m)
    old = bpy.data.node_groups.get("FieldSpikeGN")
    if old is not None:
        bpy.data.node_groups.remove(old, do_unlink=True)

    mod = globe.modifiers.new(name="FieldSpikeGN", type="NODES")
    tree = bpy.data.node_groups.new(name="FieldSpikeGN",
                                    type="GeometryNodeTree")
    mod.node_group = tree

    tree.interface.new_socket(name="Geometry",
                              in_out="INPUT",
                              socket_type="NodeSocketGeometry")
    tree.interface.new_socket(name="Geometry",
                              in_out="OUTPUT",
                              socket_type="NodeSocketGeometry")

    n_in  = mknode(tree, "NodeGroupInput",  -1400.0,   0.0, "Group Input")
    n_out = mknode(tree, "NodeGroupOutput",  1400.0,   0.0, "Group Output")

    # 1. Distribute Points on Faces (POISSON).
    n_dist = mknode(tree, "GeometryNodeDistributePointsOnFaces",
                    -1100.0, 0.0, "Distribute Points (Poisson)")
    n_dist.distribute_method = "POISSON"
    n_dist.inputs["Distance Min"].default_value = distance_min
    n_dist.inputs["Density Max"].default_value  = density_max
    n_dist.inputs["Seed"].default_value         = SEED

    tree.links.new(n_in.outputs["Geometry"], n_dist.inputs["Mesh"])

    # 2. Align Euler to Vector: aligns local +Z to the normal field.
    n_align = mknode(tree, "FunctionNodeAlignEulerToVector",
                     -700.0, -250.0, "Align Z to Normal")
    n_align.axis = "Z"
    n_align.pivot_axis = "AUTO"
    n_align.inputs["Factor"].default_value = 1.0
    # Feed the Normal field from the distribute node into Vector input.
    tree.links.new(n_dist.outputs["Normal"], n_align.inputs["Vector"])

    # 3. Random Value (FLOAT) for per-instance tilt angle in radians.
    n_rand = mknode(tree, "FunctionNodeRandomValue",
                    -700.0, -550.0, "Random Tilt (radians)")
    n_rand.data_type = "FLOAT"
    # Socket layout for FunctionNodeRandomValue with data_type=FLOAT:
    #   inputs: Min(Vec), Max(Vec), Min(Float2), Max(Float3),
    #           Min(Int5), Max(Int6), Probability(Float7), ID(Int8),
    #           Seed(Int9)
    # We set the float Min/Max (indices 2/3) and Seed (index 9).
    tilt_rad = math.radians(TILT_DEG)
    # Assign via sockets by enabled flag — iterate and pick the ones
    # that are actually visible given the data_type.
    floats_set = 0
    for sock in n_rand.inputs:
        if not sock.enabled:
            continue
        if sock.type == "VALUE":  # float socket
            if floats_set == 0:
                sock.default_value = -tilt_rad
                floats_set += 1
            elif floats_set == 1:
                sock.default_value = +tilt_rad
                floats_set += 1
    n_rand.inputs["Seed"].default_value = SEED

    # 4. Build axis vector (0,0,1) for the local-Z rotate. BUT since
    # Align Euler rotates local +Z to the normal, we then want to rotate
    # AROUND the normal. Use axis = Normal.
    # We'll use Rotate Euler in AXIS_ANGLE mode with axis = normal.
    n_rot = mknode(tree, "FunctionNodeRotateEuler",
                   -400.0, -350.0, "Tilt around Normal")
    # Rotation type in 4.1: EULER or AXIS_ANGLE. The property is
    # called `rotation_type` (not `type`).
    n_rot.rotation_type = "AXIS_ANGLE"
    n_rot.space = "OBJECT"
    tree.links.new(n_align.outputs["Rotation"], n_rot.inputs["Rotation"])
    tree.links.new(n_dist.outputs["Normal"],    n_rot.inputs["Axis"])
    tree.links.new(n_rand.outputs["Value"],     n_rot.inputs["Angle"])

    # 5. Object Info -> Spike.
    n_objinfo = mknode(tree, "GeometryNodeObjectInfo",
                       -400.0, -650.0, "Spike Object Info")
    n_objinfo.transform_space = "RELATIVE"
    n_objinfo.inputs["Object"].default_value = spike

    # 6. Instance on Points.
    n_iop = mknode(tree, "GeometryNodeInstanceOnPoints",
                   0.0, 0.0, "Instance on Points")
    tree.links.new(n_dist.outputs["Points"],     n_iop.inputs["Points"])
    tree.links.new(n_objinfo.outputs["Geometry"], n_iop.inputs["Instance"])
    tree.links.new(n_rot.outputs["Rotation"],    n_iop.inputs["Rotation"])

    # 7. Group Output.
    tree.links.new(n_iop.outputs["Instances"], n_out.inputs["Geometry"])

    # Nudge modifier to rebuild.
    mod.node_group = mod.node_group
    globe.update_tag()
    return mod, tree, n_dist


def count_instances(globe):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    n = 0
    for oi in dg.object_instances:
        if (oi.is_instance
                and oi.parent is not None
                and oi.parent.original == globe):
            n += 1
    return n


def main():
    bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)
    globe = bpy.data.objects["Globe"]
    spike = bpy.data.objects["Spike"]

    # --- Empirical tune: bisect distance_min so count == 500 with
    # seed=42. For a sphere of surface area ~28.27 BU^2 and a fixed
    # density_max that's well above saturation, distance_min is the
    # dominant knob. Smaller distance_min -> more points. We'll search
    # a reasonable range and lock to exactly 500 if possible; otherwise
    # accept a count in [480, 520].
    distance_min = DISTANCE_MIN
    density_max  = DENSITY_MAX

    # Adaptive search: if count too low, lower distance_min; if too
    # high, raise distance_min. Use a bisection over a bounded range.
    lo, hi = 0.05, 0.30
    best = None
    best_diff = None
    # First, a simple bisection in distance_min with seed=42 fixed.
    # We iterate up to ~20 steps to land on 500.
    for it in range(24):
        dm = 0.5 * (lo + hi)
        build_gn_tree(globe, spike, dm, density_max)
        n = count_instances(globe)
        print(f"    iter {it:02d}: distance_min={dm:.6f} -> count={n}")
        if best is None or abs(n - TARGET_CNT) < best_diff:
            best = (dm, n)
            best_diff = abs(n - TARGET_CNT)
            if n == TARGET_CNT:
                break
        # Smaller distance_min -> more points. So if n < target, decrease dm.
        if n < TARGET_CNT:
            hi = dm   # want smaller dm -> move hi down
        else:
            lo = dm   # want bigger dm -> move lo up

    distance_min, final_count = best
    print(f"  Tuned distance_min={distance_min:.6f} -> count={final_count}")

    # Final rebuild at the tuned value.
    mod, tree, n_dist = build_gn_tree(
        globe, spike, distance_min, density_max)

    # Sanity re-count.
    n_instances = count_instances(globe)
    print(f"  Final instance count: {n_instances} (target {TARGET_CNT})")

    # Verify alignment on a few samples.
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    max_angle = 0.0
    from mathutils import Vector
    for oi in dg.object_instances:
        if (oi.is_instance and oi.parent is not None
                and oi.parent.original == globe):
            M = oi.matrix_world
            pos = M.translation
            spike_z = (M.to_3x3() @ Vector((0, 0, 1))).normalized()
            # Globe is at origin with radius r, so the outward normal
            # at the base is pos.normalized().
            normal = pos.normalized()
            d = max(-1.0, min(1.0, spike_z.dot(normal)))
            ang = math.degrees(math.acos(d))
            if ang > max_angle:
                max_angle = ang
    print(f"  Max angle(spike+Z, normal) = {max_angle:.4f} deg")

    # Save answer.blend.
    bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
    print(f"  saved -> {OUT_PATH}")


if __name__ == "__main__":
    main()
