"""Build ground_truth/answer.blend for task AH03 -- Menger Sponge (GN Repeat Zone).

Adds a Geometry Nodes modifier to the `Sponge` object. The GN tree uses a
Repeat Zone to recursively subdivide a unit cube into a Menger sponge of
depth `Iterations` (default 3). On each iteration, each current "cube"
(represented by a point with a `size` attribute) is replaced by 20 child
cubes corresponding to a 3x3x3 subdivision minus the 7 "bad" positions
(the 6 face-centers and the volume center). Child size = parent size / 3.

After the Repeat Zone finishes, each resulting point is replaced by a
real Mesh Cube of the corresponding `size`, yielding the final Menger
sponge mesh (8000 cuboids at depth 3 -> 64000 verts, 48000 faces).

Architecture:
    GroupInput (Geometry, Iterations)
      Points node (1 point at (0.5,0.5,0.5))
      Store Named Attribute 'size' = 1.0
        -> RepeatInput (Iterations, Geometry)
            [ body:
              current geometry (points carrying 'size' attr)
              sub-grid (20 points at offsets (i-1,j-1,k-1)/3 for i,j,k in 0..2
                         excluding 7 bad positions)
              Instance on Points with Scale = (size,size,size)
              Realize Instances
              Store Named Attribute 'size' = old size / 3
            ]
        -> RepeatOutput (Geometry)
      After the zone: Mesh Cube (size=1) instanced at each point with
        Scale = (size,size,size), realized
      Group Output (Geometry)

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bpy

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUT_PATH   = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)


DEF_ITERATIONS = 3


# ---------------------------------------------------------------------------
# Open init and fetch the Sponge object.
# ---------------------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)
sponge = bpy.data.objects["Sponge"]

# Add NODES modifier with a fresh node group.
mod = sponge.modifiers.new(name="MengerGN", type="NODES")
tree = bpy.data.node_groups.new(name="MengerSpongeGN", type="GeometryNodeTree")
mod.node_group = tree

# ---------------------------------------------------------------------------
# Interface: Geometry input/output + Iterations (int, default 3).
# ---------------------------------------------------------------------------
tree.interface.new_socket(name="Geometry",
                          in_out="INPUT",
                          socket_type="NodeSocketGeometry")
tree.interface.new_socket(name="Geometry",
                          in_out="OUTPUT",
                          socket_type="NodeSocketGeometry")
s_iter = tree.interface.new_socket(name="Iterations",
                                   in_out="INPUT",
                                   socket_type="NodeSocketInt")
s_iter.default_value = DEF_ITERATIONS
s_iter.min_value = 0
s_iter.max_value = 5


def mknode(bl_idname, x, y, name=None):
    n = tree.nodes.new(bl_idname)
    n.location = (x, y)
    if name is not None:
        n.name = name
        n.label = name
    return n


# ---------------------------------------------------------------------------
# Boundary.
# ---------------------------------------------------------------------------
n_in  = mknode("NodeGroupInput",  -2400.0,   0.0, "Group Input")
n_out = mknode("NodeGroupOutput",  2200.0,   0.0, "Group Output")


# ---------------------------------------------------------------------------
# Initial geometry: a single point at (0.5, 0.5, 0.5) with size=1.0.
# ---------------------------------------------------------------------------
n_pts_init = mknode("GeometryNodePoints", -2100.0, 0.0, "Seed Point")
n_pts_init.inputs["Count"].default_value = 1
n_pts_init.inputs["Position"].default_value = (0.5, 0.5, 0.5)
n_pts_init.inputs["Radius"].default_value = 0.01

n_sna_init = mknode("GeometryNodeStoreNamedAttribute",
                    -1850.0, 0.0, "Init size")
n_sna_init.data_type = "FLOAT"
n_sna_init.domain = "POINT"
n_sna_init.inputs["Name"].default_value = "size"
n_sna_init.inputs["Value"].default_value = 1.0
tree.links.new(n_pts_init.outputs["Geometry"], n_sna_init.inputs["Geometry"])


# ---------------------------------------------------------------------------
# Build the 20-point Menger sub-grid (pure GN, no external object).
# Strategy:
#   * three Mesh Line nodes with count=3 and offsets along each axis
#     (unit spacing 1/3) -> three separate 3-point lines.
#   * compose them into a 3x3x3 grid via nested Instance on Points + Realize.
#   * Set Position offset by (-1/3,-1/3,-1/3) to center the grid on origin.
#   * Delete Geometry points where at least 2 of {|x|,|y|,|z|} are ~0 (the
#     volume-center + 6 face-center positions).
# Result: a 20-point mesh at offsets (i-1,j-1,k-1)/3 for Menger-valid (i,j,k).
# ---------------------------------------------------------------------------
THIRD = 1.0 / 3.0

lx = mknode("GeometryNodeMeshLine", -2100.0,  650.0, "Sub Line X")
lx.mode = "OFFSET"
lx.count_mode = "TOTAL"
lx.inputs["Count"].default_value = 3
lx.inputs["Offset"].default_value = (THIRD, 0.0, 0.0)

ly = mknode("GeometryNodeMeshLine", -2100.0,  450.0, "Sub Line Y")
ly.mode = "OFFSET"
ly.count_mode = "TOTAL"
ly.inputs["Count"].default_value = 3
ly.inputs["Offset"].default_value = (0.0, THIRD, 0.0)

lz = mknode("GeometryNodeMeshLine", -2100.0,  250.0, "Sub Line Z")
lz.mode = "OFFSET"
lz.count_mode = "TOTAL"
lz.inputs["Count"].default_value = 3
lz.inputs["Offset"].default_value = (0.0, 0.0, THIRD)

# 3x3 XY plane: instance X-line on each Y-point, realize.
iop_xy = mknode("GeometryNodeInstanceOnPoints",
                -1800.0, 550.0, "XY instances")
tree.links.new(ly.outputs["Mesh"], iop_xy.inputs["Points"])
tree.links.new(lx.outputs["Mesh"], iop_xy.inputs["Instance"])
rea_xy = mknode("GeometryNodeRealizeInstances",
                -1600.0, 550.0, "Realize XY")
tree.links.new(iop_xy.outputs["Instances"], rea_xy.inputs["Geometry"])

# 3x3x3 volume: instance XY plane on Z-line, realize.
iop_xyz = mknode("GeometryNodeInstanceOnPoints",
                 -1400.0, 400.0, "XYZ instances")
tree.links.new(lz.outputs["Mesh"], iop_xyz.inputs["Points"])
tree.links.new(rea_xy.outputs["Geometry"], iop_xyz.inputs["Instance"])
rea_xyz = mknode("GeometryNodeRealizeInstances",
                 -1200.0, 400.0, "Realize XYZ")
tree.links.new(iop_xyz.outputs["Instances"], rea_xyz.inputs["Geometry"])

# Shift centered: add offset (-1/3,-1/3,-1/3) so positions lie in
# {-1/3, 0, +1/3}^3.
n_shift = mknode("GeometryNodeSetPosition", -1000.0, 400.0, "Center grid")
n_shift.inputs["Offset"].default_value = (-THIRD, -THIRD, -THIRD)
tree.links.new(rea_xyz.outputs["Geometry"], n_shift.inputs["Geometry"])

# Build a boolean selection: "at least 2 of {|x|,|y|,|z|} are ~0" -> DELETE.
n_pos = mknode("GeometryNodeInputPosition", -1000.0,  750.0, "Position")
n_sep = mknode("ShaderNodeSeparateXYZ",      -800.0,  750.0, "Split pos")
tree.links.new(n_pos.outputs["Position"], n_sep.inputs["Vector"])

def _abs_lt_epsilon(yc, src_sock, label):
    """Build |src| < 0.01 sub-chain.  Returns the socket of the bool result."""
    abs_n = mknode("ShaderNodeMath", -600.0, yc, f"abs {label}")
    abs_n.operation = "ABSOLUTE"
    tree.links.new(src_sock, abs_n.inputs[0])
    cmp = mknode("ShaderNodeMath", -420.0, yc, f"eps {label}")
    cmp.operation = "LESS_THAN"
    cmp.inputs[1].default_value = 0.01
    tree.links.new(abs_n.outputs[0], cmp.inputs[0])
    return cmp.outputs[0]

b_x = _abs_lt_epsilon( 900.0, n_sep.outputs["X"], "x")
b_y = _abs_lt_epsilon( 750.0, n_sep.outputs["Y"], "y")
b_z = _abs_lt_epsilon( 600.0, n_sep.outputs["Z"], "z")

# sum = b_x + b_y + b_z   (as floats).
n_add1 = mknode("ShaderNodeMath", -220.0, 800.0, "sum xy")
n_add1.operation = "ADD"
tree.links.new(b_x, n_add1.inputs[0])
tree.links.new(b_y, n_add1.inputs[1])
n_add2 = mknode("ShaderNodeMath",  -40.0, 750.0, "sum xyz")
n_add2.operation = "ADD"
tree.links.new(n_add1.outputs[0], n_add2.inputs[0])
tree.links.new(b_z, n_add2.inputs[1])

# Threshold: sum > 1.5  (i.e. at least 2 of the three |coord|==0 flags).
n_ge = mknode("ShaderNodeMath", 140.0, 750.0, "drop mask")
n_ge.operation = "GREATER_THAN"
n_ge.inputs[1].default_value = 1.5
tree.links.new(n_add2.outputs[0], n_ge.inputs[0])

# Delete those 7 points.
n_del = mknode("GeometryNodeDeleteGeometry", 340.0, 500.0, "Drop 7")
n_del.domain = "POINT"
tree.links.new(n_shift.outputs["Geometry"], n_del.inputs["Geometry"])
tree.links.new(n_ge.outputs[0],             n_del.inputs["Selection"])
# The 20-point sub-grid output (each vert at offsets (i-1,j-1,k-1)/3
# for Menger-valid i,j,k in {0,1,2}).


# ---------------------------------------------------------------------------
# Repeat Zone.  Body: each iteration expands each current point into 20
# children (via IOP with the sub-grid) and divides `size` by 3.
# ---------------------------------------------------------------------------
n_rep_in  = mknode("GeometryNodeRepeatInput",  -700.0, -50.0, "Repeat In")
n_rep_out = mknode("GeometryNodeRepeatOutput", 1400.0, -50.0, "Repeat Out")
n_rep_in.pair_with_output(n_rep_out)

# Drive Iterations from the Group Input.
tree.links.new(n_in.outputs["Iterations"], n_rep_in.inputs["Iterations"])
# Feed the seeded points into the zone body's geometry input.
tree.links.new(n_sna_init.outputs["Geometry"], n_rep_in.inputs["Geometry"])


# --- Inside the zone body -------------------------------------------------
# Read current `size` attribute for the IOP scale.
n_na_size = mknode("GeometryNodeInputNamedAttribute",
                   -400.0, -350.0, "Read size")
n_na_size.data_type = "FLOAT"
n_na_size.inputs["Name"].default_value = "size"

n_cv_scale = mknode("ShaderNodeCombineXYZ", -200.0, -350.0, "size -> vec3")
tree.links.new(n_na_size.outputs["Attribute"], n_cv_scale.inputs["X"])
tree.links.new(n_na_size.outputs["Attribute"], n_cv_scale.inputs["Y"])
tree.links.new(n_na_size.outputs["Attribute"], n_cv_scale.inputs["Z"])

# Instance the 20-point sub-grid on each current point, scaled by `size`.
n_iop = mknode("GeometryNodeInstanceOnPoints",
               200.0, -150.0, "Expand x20")
tree.links.new(n_rep_in.outputs["Geometry"], n_iop.inputs["Points"])
tree.links.new(n_del.outputs["Geometry"],    n_iop.inputs["Instance"])
tree.links.new(n_cv_scale.outputs["Vector"], n_iop.inputs["Scale"])

n_rea = mknode("GeometryNodeRealizeInstances",
               420.0, -150.0, "Realize")
tree.links.new(n_iop.outputs["Instances"], n_rea.inputs["Geometry"])

# Update size: new_size = old_size / 3.
n_na_size2 = mknode("GeometryNodeInputNamedAttribute",
                    420.0, -400.0, "Read size 2")
n_na_size2.data_type = "FLOAT"
n_na_size2.inputs["Name"].default_value = "size"

n_div3 = mknode("ShaderNodeMath", 620.0, -400.0, "size / 3")
n_div3.operation = "DIVIDE"
n_div3.inputs[1].default_value = 3.0
tree.links.new(n_na_size2.outputs["Attribute"], n_div3.inputs[0])

n_sna_new = mknode("GeometryNodeStoreNamedAttribute",
                   820.0, -150.0, "Write new size")
n_sna_new.data_type = "FLOAT"
n_sna_new.domain = "POINT"
n_sna_new.inputs["Name"].default_value = "size"
tree.links.new(n_rea.outputs["Geometry"], n_sna_new.inputs["Geometry"])
tree.links.new(n_div3.outputs[0],         n_sna_new.inputs["Value"])

# Feed back into the zone output.
tree.links.new(n_sna_new.outputs["Geometry"], n_rep_out.inputs["Geometry"])


# ---------------------------------------------------------------------------
# After the repeat zone: instance a unit Mesh Cube at each final point
# with Scale = (size, size, size), then realize.
# ---------------------------------------------------------------------------
n_cube = mknode("GeometryNodeMeshCube", 1500.0, -350.0, "Unit Cube")
n_cube.inputs["Size"].default_value = (1.0, 1.0, 1.0)

n_na_final = mknode("GeometryNodeInputNamedAttribute",
                    1500.0, -550.0, "Final size")
n_na_final.data_type = "FLOAT"
n_na_final.inputs["Name"].default_value = "size"

n_cv_final = mknode("ShaderNodeCombineXYZ", 1700.0, -550.0, "Final scale vec")
tree.links.new(n_na_final.outputs["Attribute"], n_cv_final.inputs["X"])
tree.links.new(n_na_final.outputs["Attribute"], n_cv_final.inputs["Y"])
tree.links.new(n_na_final.outputs["Attribute"], n_cv_final.inputs["Z"])

n_iop_cube = mknode("GeometryNodeInstanceOnPoints",
                    1900.0, -150.0, "Cubes")
tree.links.new(n_rep_out.outputs["Geometry"], n_iop_cube.inputs["Points"])
tree.links.new(n_cube.outputs["Mesh"],        n_iop_cube.inputs["Instance"])
tree.links.new(n_cv_final.outputs["Vector"],  n_iop_cube.inputs["Scale"])

n_rea_final = mknode("GeometryNodeRealizeInstances",
                     2100.0, -150.0, "Realize Cubes")
tree.links.new(n_iop_cube.outputs["Instances"], n_rea_final.inputs["Geometry"])

tree.links.new(n_rea_final.outputs["Geometry"], n_out.inputs["Geometry"])


# ---------------------------------------------------------------------------
# Set the modifier's stored default for the Iterations socket so the
# modifier property panel shows the correct value.
# ---------------------------------------------------------------------------
gn_mod = mod
gn_mod[s_iter.identifier] = DEF_ITERATIONS
gn_mod.node_group = gn_mod.node_group
sponge.update_tag()


# ---------------------------------------------------------------------------
# Sanity: evaluate the mesh and print counts.
# ---------------------------------------------------------------------------
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev_obj = sponge.evaluated_get(dg)
ev_mesh = ev_obj.to_mesh()
print(f"  base mesh verts:      {len(sponge.data.vertices)} (expect 0)")
print(f"  base mesh faces:      {len(sponge.data.polygons)} (expect 0)")
print(f"  evaluated verts:      {len(ev_mesh.vertices)} (expect 64000)")
print(f"  evaluated polygons:   {len(ev_mesh.polygons)} (expect 48000)")
if len(ev_mesh.vertices) > 0:
    xs = [v.co.x for v in ev_mesh.vertices]
    ys = [v.co.y for v in ev_mesh.vertices]
    zs = [v.co.z for v in ev_mesh.vertices]
    print(f"  bbox X: [{min(xs):.4f}, {max(xs):.4f}]  (expect [0,1])")
    print(f"  bbox Y: [{min(ys):.4f}, {max(ys):.4f}]  (expect [0,1])")
    print(f"  bbox Z: [{min(zs):.4f}, {max(zs):.4f}]  (expect [0,1])")
ev_obj.to_mesh_clear()

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
