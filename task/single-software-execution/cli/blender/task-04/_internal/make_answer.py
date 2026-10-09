"""Build ground_truth/answer.blend for task AH04 - Procedural Tree with LOD.

Starting from init_file/scene.blend (Tree object with a pass-through
GN_Tree modifier), rebuild the GN node tree so that it:

    1. Exposes an Integer input socket `LOD` (default 3, range 0..3).
    2. Pulls trunk geometry from a sub-node-group named `Trunk`.
    3. Switches in branches from a sub-node-group `Branches` when LOD>=1.
    4. Switches in leaves from a sub-node-group `Leaves` when LOD>=2.

Sub-node-groups (all type `GeometryNodeTree`):

  `Trunk`
      Input  : (none in; trunk is self-seeded)
      Output : Geometry (a vertical tube from z=0 to z=3 with radius 0.15)
      Body   : Mesh Line (count=10, offset=(0,0,0.3333)) -> Curve Line
               Fill -> Curve to Mesh with a Curve Circle (radius 0.15)
               profile.  We use Mesh Line converted to a curve via
               Mesh to Curve, then Curve to Mesh with a circle profile.

  `Branches`
      Input  : Geometry (trunk)
      Output : Geometry (trunk + 4 branches protruding from upper trunk)
      Body   : Builds 4 branch curves that start on the upper trunk
               and extend outward+upward; convert each via Curve to Mesh
               with a thinner circle profile.  Joined with the trunk
               geometry.

  `Leaves`
      Input  : Geometry (trunk + branches)
      Output : Geometry (trunk + branches + leaf cubes)
      Body   : Distribute Points on Faces (density 200) on the incoming
               geometry -> Instance on Points with a small cube (0.1).
               Realize Instances -> Join with the incoming geometry so
               the scene contains trunk+branches+leaves as one mesh.

Main graph:

    [Group Input: Geometry, LOD]
         |
         v
    Trunk (sub-group)  --- produces trunk geometry
         |
         +---> Switch(GEOMETRY, condition = LOD>=1)
                 False -> trunk
                 True  -> Branches(trunk)
                   |
                   v
                 Switch(GEOMETRY, condition = LOD>=2)
                   False -> (above)
                   True  -> Leaves(above)
                               |
                               v
                        [Group Output: Geometry]

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


TRUNK_HEIGHT = 3.0
TRUNK_RADIUS = 0.15
BRANCH_RADIUS = 0.06
LEAF_SIZE = 0.1
LEAF_DENSITY = 200.0
DEFAULT_LOD = 3


def mknode(tree, bl_idname, x, y, name=None):
    n = tree.nodes.new(bl_idname)
    n.location = (float(x), float(y))
    if name is not None:
        n.name = name
        n.label = name
    return n


def _find_iface_socket(tree, name, in_out):
    for item in tree.interface.items_tree:
        if getattr(item, "item_type", "SOCKET") != "SOCKET":
            continue
        if getattr(item, "in_out", None) != in_out:
            continue
        if getattr(item, "name", "") == name:
            return item
    return None


# --------------------------------------------------------------------------
# Sub-node-group: Trunk
# Builds a cylinder-ish trunk from a vertical Mesh Line -> curve -> Curve
# to Mesh with a circular profile.
# --------------------------------------------------------------------------
def build_trunk_group():
    ng = bpy.data.node_groups.get("Trunk")
    if ng is not None:
        bpy.data.node_groups.remove(ng, do_unlink=True)
    ng = bpy.data.node_groups.new(name="Trunk", type="GeometryNodeTree")

    # Interface: only a Geometry output (self-seeded).
    ng.interface.new_socket(name="Geometry",
                            in_out="OUTPUT",
                            socket_type="NodeSocketGeometry")

    n_in = mknode(ng, "NodeGroupInput", -1200.0, 0.0, "Group Input")
    n_out = mknode(ng, "NodeGroupOutput", 800.0, 0.0, "Group Output")

    # 1. Vertical spine: Mesh Line along +Z, 10 segments, total length TRUNK_HEIGHT.
    n_line = mknode(ng, "GeometryNodeMeshLine", -900.0, 0.0, "Trunk Spine")
    n_line.mode = "OFFSET"
    n_line.count_mode = "TOTAL"
    n_line.inputs["Count"].default_value = 10
    # Offset per step so last point sits at z=TRUNK_HEIGHT.
    n_line.inputs["Offset"].default_value = (0.0, 0.0, TRUNK_HEIGHT / 9.0)
    n_line.inputs["Start Location"].default_value = (0.0, 0.0, 0.0)

    # 2. Mesh to Curve so we can sweep a circle profile.
    n_m2c = mknode(ng, "GeometryNodeMeshToCurve", -650.0, 0.0, "Mesh to Curve")
    ng.links.new(n_line.outputs["Mesh"], n_m2c.inputs["Mesh"])

    # 3. Circle profile.
    n_circle = mknode(ng, "GeometryNodeCurvePrimitiveCircle",
                      -650.0, -300.0, "Trunk Profile")
    n_circle.mode = "RADIUS"
    n_circle.inputs["Resolution"].default_value = 12
    n_circle.inputs["Radius"].default_value = TRUNK_RADIUS

    # 4. Curve to Mesh -> trunk tube.
    n_c2m = mknode(ng, "GeometryNodeCurveToMesh", -350.0, 0.0, "Trunk Tube")
    n_c2m.inputs["Fill Caps"].default_value = True
    ng.links.new(n_m2c.outputs["Curve"], n_c2m.inputs["Curve"])
    ng.links.new(n_circle.outputs["Curve"], n_c2m.inputs["Profile Curve"])

    ng.links.new(n_c2m.outputs["Mesh"], n_out.inputs["Geometry"])

    return ng


# --------------------------------------------------------------------------
# Sub-node-group: Branches
# Takes trunk geometry as input, adds a handful of branch tubes attached
# to the upper 2/3 of the trunk.  We build branches as 4 Mesh Line curves
# at specific anchor positions, converted to thin tubes, and join with
# the incoming trunk.
# --------------------------------------------------------------------------
def build_branches_group():
    ng = bpy.data.node_groups.get("Branches")
    if ng is not None:
        bpy.data.node_groups.remove(ng, do_unlink=True)
    ng = bpy.data.node_groups.new(name="Branches", type="GeometryNodeTree")

    ng.interface.new_socket(name="Geometry",
                            in_out="INPUT",
                            socket_type="NodeSocketGeometry")
    ng.interface.new_socket(name="Geometry",
                            in_out="OUTPUT",
                            socket_type="NodeSocketGeometry")

    n_in = mknode(ng, "NodeGroupInput", -1800.0, 300.0, "Group Input")
    n_out = mknode(ng, "NodeGroupOutput", 1200.0, 0.0, "Group Output")

    # Shared circle profile for branches.
    n_bp = mknode(ng, "GeometryNodeCurvePrimitiveCircle",
                  -1800.0, -900.0, "Branch Profile")
    n_bp.mode = "RADIUS"
    n_bp.inputs["Resolution"].default_value = 8
    n_bp.inputs["Radius"].default_value = BRANCH_RADIUS

    # Build 4 branches at z in {1.5, 2.0, 2.4, 2.7} with outward xy offsets.
    # Each is a 4-point line from (ax, ay, az) to (bx, by, bz).
    anchors = [
        ((0.0, 0.0, 1.5), (0.9, 0.0, 2.0)),
        ((0.0, 0.0, 2.0), (-0.8, 0.2, 2.5)),
        ((0.0, 0.0, 2.4), (0.2, 0.85, 2.8)),
        ((0.0, 0.0, 2.7), (-0.2, -0.75, 3.0)),
    ]

    # We'll build each branch with a Mesh Line in END_POINTS mode.
    branch_geoms = []
    y_base = -300.0
    for i, (a, b) in enumerate(anchors):
        yi = y_base - i * 300.0

        n_ml = mknode(ng, "GeometryNodeMeshLine", -1500.0, yi, f"Branch Line {i}")
        n_ml.mode = "END_POINTS"
        n_ml.count_mode = "TOTAL"
        n_ml.inputs["Count"].default_value = 4
        n_ml.inputs["Start Location"].default_value = a
        # In END_POINTS mode, the "Offset" socket is reinterpreted as the
        # end-point location (same socket slot, different semantics).
        n_ml.inputs["Offset"].default_value = b

        n_m2c = mknode(ng, "GeometryNodeMeshToCurve",
                       -1200.0, yi, f"Branch Curve {i}")
        ng.links.new(n_ml.outputs["Mesh"], n_m2c.inputs["Mesh"])

        n_c2m = mknode(ng, "GeometryNodeCurveToMesh",
                       -900.0, yi, f"Branch Tube {i}")
        n_c2m.inputs["Fill Caps"].default_value = True
        ng.links.new(n_m2c.outputs["Curve"], n_c2m.inputs["Curve"])
        ng.links.new(n_bp.outputs["Curve"], n_c2m.inputs["Profile Curve"])

        branch_geoms.append(n_c2m)

    # Join branches together.
    n_join = mknode(ng, "GeometryNodeJoinGeometry", -500.0, -900.0,
                    "Join Branches")
    for bg in branch_geoms:
        ng.links.new(bg.outputs["Mesh"], n_join.inputs["Geometry"])

    # Join with trunk input.
    n_join_all = mknode(ng, "GeometryNodeJoinGeometry", 200.0, 0.0,
                        "Join Trunk+Branches")
    # Order: trunk first, branches second.
    ng.links.new(n_in.outputs["Geometry"], n_join_all.inputs["Geometry"])
    ng.links.new(n_join.outputs["Geometry"], n_join_all.inputs["Geometry"])

    ng.links.new(n_join_all.outputs["Geometry"], n_out.inputs["Geometry"])

    return ng


# --------------------------------------------------------------------------
# Sub-node-group: Leaves
# Takes trunk+branches geometry, distributes points on faces, instances a
# small cube at each point, realizes, joins with the incoming geometry.
# --------------------------------------------------------------------------
def build_leaves_group():
    ng = bpy.data.node_groups.get("Leaves")
    if ng is not None:
        bpy.data.node_groups.remove(ng, do_unlink=True)
    ng = bpy.data.node_groups.new(name="Leaves", type="GeometryNodeTree")

    ng.interface.new_socket(name="Geometry",
                            in_out="INPUT",
                            socket_type="NodeSocketGeometry")
    ng.interface.new_socket(name="Geometry",
                            in_out="OUTPUT",
                            socket_type="NodeSocketGeometry")

    n_in = mknode(ng, "NodeGroupInput", -1400.0, 200.0, "Group Input")
    n_out = mknode(ng, "NodeGroupOutput", 1100.0, 0.0, "Group Output")

    # Distribute Points on Faces.
    n_dist = mknode(ng, "GeometryNodeDistributePointsOnFaces",
                    -1000.0, -100.0, "Distribute Leaf Points")
    n_dist.distribute_method = "RANDOM"
    n_dist.inputs["Density"].default_value = LEAF_DENSITY
    n_dist.inputs["Seed"].default_value = 42
    ng.links.new(n_in.outputs["Geometry"], n_dist.inputs["Mesh"])

    # Mesh Cube for a leaf instance.
    n_cube = mknode(ng, "GeometryNodeMeshCube", -1000.0, -500.0, "Leaf Cube")
    n_cube.inputs["Size"].default_value = (LEAF_SIZE, LEAF_SIZE, LEAF_SIZE)

    # Instance on Points.
    n_iop = mknode(ng, "GeometryNodeInstanceOnPoints", -600.0, -200.0,
                   "Leaves on Points")
    ng.links.new(n_dist.outputs["Points"], n_iop.inputs["Points"])
    ng.links.new(n_cube.outputs["Mesh"], n_iop.inputs["Instance"])

    # Realize so downstream sees real mesh verts.
    n_real = mknode(ng, "GeometryNodeRealizeInstances", -250.0, -200.0,
                    "Realize Leaves")
    ng.links.new(n_iop.outputs["Instances"], n_real.inputs["Geometry"])

    # Join with incoming.
    n_join = mknode(ng, "GeometryNodeJoinGeometry", 200.0, 0.0,
                    "Join with Input")
    ng.links.new(n_in.outputs["Geometry"], n_join.inputs["Geometry"])
    ng.links.new(n_real.outputs["Geometry"], n_join.inputs["Geometry"])

    ng.links.new(n_join.outputs["Geometry"], n_out.inputs["Geometry"])

    return ng


# --------------------------------------------------------------------------
# Main graph on the Tree object's modifier.
# --------------------------------------------------------------------------
def build_main_graph(tree_obj, ng_trunk, ng_branches, ng_leaves):
    mod = None
    for m in tree_obj.modifiers:
        if m.type == "NODES":
            mod = m
            break
    if mod is None:
        mod = tree_obj.modifiers.new(name="TreeLOD", type="NODES")
    else:
        # Rename the init's pass-through modifier so the checks can find it.
        mod.name = "TreeLOD"

    # Remove/rebuild the main node group (the existing GN_Tree).
    old = mod.node_group
    mod.node_group = None
    if old is not None:
        try:
            bpy.data.node_groups.remove(old, do_unlink=True)
        except Exception:
            pass

    main = bpy.data.node_groups.new(name="TreeLOD", type="GeometryNodeTree")
    mod.node_group = main

    # Interface: Geometry in/out + LOD integer.
    main.interface.new_socket(name="Geometry",
                              in_out="INPUT",
                              socket_type="NodeSocketGeometry")
    main.interface.new_socket(name="Geometry",
                              in_out="OUTPUT",
                              socket_type="NodeSocketGeometry")
    sock_lod = main.interface.new_socket(name="LOD",
                                         in_out="INPUT",
                                         socket_type="NodeSocketInt")
    sock_lod.default_value = DEFAULT_LOD
    sock_lod.min_value = 0
    sock_lod.max_value = 3

    n_in = mknode(main, "NodeGroupInput", -1600.0, 0.0, "Group Input")
    n_out = mknode(main, "NodeGroupOutput", 1800.0, 0.0, "Group Output")

    # 1. Trunk sub-group (always present).
    n_trunk = mknode(main, "GeometryNodeGroup", -1100.0, 0.0, "Trunk")
    n_trunk.node_tree = ng_trunk

    # 2. Branches sub-group (evaluated lazily; fed by the Switch's False
    #    branch bypassing it).
    n_branches = mknode(main, "GeometryNodeGroup", -500.0, -300.0, "Branches")
    n_branches.node_tree = ng_branches
    main.links.new(n_trunk.outputs["Geometry"], n_branches.inputs["Geometry"])

    # 3. Compare LOD >= 1 -> boolean for Switch.
    n_cmp1 = mknode(main, "FunctionNodeCompare", -900.0, -600.0,
                    "LOD >= 1")
    n_cmp1.data_type = "INT"
    n_cmp1.operation = "GREATER_EQUAL"
    # FunctionNodeCompare with data_type=INT exposes A/B as integers.
    # Find the correct integer sockets (only those .enabled == True).
    # We'll iterate and set B=1 on the second enabled integer input.
    int_inputs = [s for s in n_cmp1.inputs if s.enabled and s.type == "INT"]
    if len(int_inputs) >= 2:
        # inputs[0]=A, inputs[1]=B after filtering.
        int_inputs[1].default_value = 1
    main.links.new(n_in.outputs["LOD"], n_cmp1.inputs[2])  # A (INT)

    # 4. Switch: branches if LOD >= 1.
    n_sw1 = mknode(main, "GeometryNodeSwitch", -100.0, -100.0,
                   "Switch Branches")
    n_sw1.input_type = "GEOMETRY"
    # Switch sockets for GEOMETRY type: [Switch(bool), False(Geom), True(Geom)]
    # but only the corresponding-type sockets are enabled. We link by name.
    main.links.new(n_cmp1.outputs["Result"], n_sw1.inputs["Switch"])
    main.links.new(n_trunk.outputs["Geometry"], n_sw1.inputs["False"])
    main.links.new(n_branches.outputs["Geometry"], n_sw1.inputs["True"])

    # 5. Leaves sub-group (takes the switch-1 output so leaves populate
    #    the trunk+branches when LOD >= 2).
    n_leaves = mknode(main, "GeometryNodeGroup", 400.0, -300.0, "Leaves")
    n_leaves.node_tree = ng_leaves
    main.links.new(n_sw1.outputs["Output"], n_leaves.inputs["Geometry"])

    # 6. Compare LOD >= 3 -> boolean for Switch (leaves only at LOD=3).
    n_cmp2 = mknode(main, "FunctionNodeCompare", 100.0, -600.0,
                    "LOD >= 3")
    n_cmp2.data_type = "INT"
    n_cmp2.operation = "GREATER_EQUAL"
    int_inputs2 = [s for s in n_cmp2.inputs if s.enabled and s.type == "INT"]
    if len(int_inputs2) >= 2:
        int_inputs2[1].default_value = 3
    main.links.new(n_in.outputs["LOD"], n_cmp2.inputs[2])

    # 7. Switch: leaves if LOD >= 2.
    n_sw2 = mknode(main, "GeometryNodeSwitch", 1000.0, -100.0,
                   "Switch Leaves")
    n_sw2.input_type = "GEOMETRY"
    main.links.new(n_cmp2.outputs["Result"], n_sw2.inputs["Switch"])
    main.links.new(n_sw1.outputs["Output"], n_sw2.inputs["False"])
    main.links.new(n_leaves.outputs["Geometry"], n_sw2.inputs["True"])

    # 8. Group Output.
    main.links.new(n_sw2.outputs["Output"], n_out.inputs["Geometry"])

    # Set the modifier's stored default for the LOD socket.
    iface_lod = _find_iface_socket(main, "LOD", "INPUT")
    assert iface_lod is not None, "LOD interface socket missing"
    mod[iface_lod.identifier] = DEFAULT_LOD

    # Nudge modifier to rebuild.
    mod.node_group = mod.node_group
    tree_obj.update_tag()

    return mod, main, iface_lod


def _eval_vertex_count(obj, mod, iface_lod, lod_value):
    mod[iface_lod.identifier] = int(lod_value)
    obj.update_tag()
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    ev_obj = obj.evaluated_get(dg)
    ev_mesh = ev_obj.to_mesh()
    n = len(ev_mesh.vertices)
    # Bounding box in Z.
    if n:
        zs = [v.co.z for v in ev_mesh.vertices]
        zmin, zmax = min(zs), max(zs)
    else:
        zmin, zmax = 0.0, 0.0
    ev_obj.to_mesh_clear()
    return n, zmin, zmax


def main():
    bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

    tree_obj = bpy.data.objects.get("Tree")
    assert tree_obj is not None, "Tree object missing"

    # Build sub-node-groups first.
    ng_trunk = build_trunk_group()
    ng_branches = build_branches_group()
    ng_leaves = build_leaves_group()

    # Rebuild main graph.
    mod, main, iface_lod = build_main_graph(
        tree_obj, ng_trunk, ng_branches, ng_leaves)

    # Sanity prints across LODs.
    for lod in (0, 1, 2, 3):
        n, zmin, zmax = _eval_vertex_count(tree_obj, mod, iface_lod, lod)
        print(f"  LOD={lod}: verts={n}, Z range=[{zmin:.4f}, {zmax:.4f}]")

    # Final: set LOD=3 and save.
    mod[iface_lod.identifier] = DEFAULT_LOD
    tree_obj.update_tag()
    bpy.context.view_layer.update()

    geom_ng_names = [ng.name for ng in bpy.data.node_groups
                     if ng.type == "GEOMETRY"]
    print(f"  Geometry node_groups in file: {geom_ng_names}")

    bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
    print(f"  saved -> {OUT_PATH}")


if __name__ == "__main__":
    main()
