"""Build ground_truth/answer.blend for task AH01 - GN Cable Sag.

Architecture:
  - Object Info (A) -> location (OUT_A)
  - Object Info (B) -> location (OUT_B)
  - Curve Line (start=OUT_A, end=OUT_B) -> Resample Curve (count=60)
  - Spline Parameter (factor t in [0,1])
  - Vector Math SUBTRACT: A - B
  - Vector Math LENGTH:   |A - B|
  - Math MULTIPLY by pi:  pi * t
  - Math SINE:            sin(pi * t)
  - Group Input -> sag_factor (float)
  - Math MULTIPLY: |A - B| * sag_factor
  - Math MULTIPLY: (|A - B| * sag_factor) * sin(pi * t)   -> sag_amount (scalar)
  - Combine XYZ: (0, 0, -sag_amount) -> offset vector
  - Set Position (Offset=offset) on resampled curve
  - Curve Circle (resolution=6) as profile
  - Curve to Mesh -> Group Output.Geometry

The Cable object's base mesh remains empty; GN modifier is NOT applied.
sag_factor default on the modifier is 0.1.

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

bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

cable = bpy.data.objects["Cable"]
empty_a = bpy.data.objects["A"]
empty_b = bpy.data.objects["B"]

# --- Add GN modifier -------------------------------------------------------
mod = cable.modifiers.new(name="CableGN", type="NODES")

# --- Build the GN tree entirely via Python --------------------------------
tree = bpy.data.node_groups.new(name="CableSagGN", type="GeometryNodeTree")
mod.node_group = tree

# Interface sockets (Blender 4.x API).
tree.interface.new_socket(name="Geometry",
                          in_out="INPUT",
                          socket_type="NodeSocketGeometry")
sag_sock = tree.interface.new_socket(name="sag_factor",
                                     in_out="INPUT",
                                     socket_type="NodeSocketFloat")
sag_sock.default_value = 0.1
sag_sock.min_value = 0.0
sag_sock.max_value = 10.0
tree.interface.new_socket(name="Geometry",
                          in_out="OUTPUT",
                          socket_type="NodeSocketGeometry")

# Group Input / Group Output boundary nodes.
n_in  = tree.nodes.new("NodeGroupInput")
n_out = tree.nodes.new("NodeGroupOutput")
n_in.location  = (-1400.0, 0.0)
n_out.location = ( 1400.0, 0.0)

# Object Info nodes for A and B.
n_oi_a = tree.nodes.new("GeometryNodeObjectInfo")
n_oi_a.location = (-1400.0, 500.0)
n_oi_a.inputs["Object"].default_value = empty_a
n_oi_a.transform_space = "RELATIVE"

n_oi_b = tree.nodes.new("GeometryNodeObjectInfo")
n_oi_b.location = (-1400.0, 250.0)
n_oi_b.inputs["Object"].default_value = empty_b
n_oi_b.transform_space = "RELATIVE"

# Curve Line (from A to B).
n_line = tree.nodes.new("GeometryNodeCurvePrimitiveLine")
n_line.location = (-1000.0, 400.0)

# Resample curve with count = 60.
n_resample = tree.nodes.new("GeometryNodeResampleCurve")
n_resample.location = (-700.0, 400.0)
n_resample.mode = "COUNT"
n_resample.inputs["Count"].default_value = 60

# Spline Parameter (gives factor t along resampled curve).
n_param = tree.nodes.new("GeometryNodeSplineParameter")
n_param.location = (-700.0, 100.0)

# Vector Math: A - B (difference).
n_sub = tree.nodes.new("ShaderNodeVectorMath")
n_sub.operation = "SUBTRACT"
n_sub.location = (-1000.0, 0.0)

# Vector Math: LENGTH of (A - B).
n_len = tree.nodes.new("ShaderNodeVectorMath")
n_len.operation = "LENGTH"
n_len.location = (-800.0, 0.0)

# Math: pi * t.
n_mul_pi = tree.nodes.new("ShaderNodeMath")
n_mul_pi.operation = "MULTIPLY"
n_mul_pi.location = (-500.0, 100.0)
n_mul_pi.inputs[1].default_value = math.pi

# Math: sin(pi * t).
n_sin = tree.nodes.new("ShaderNodeMath")
n_sin.operation = "SINE"
n_sin.location = (-300.0, 100.0)

# Math: |A - B| * sag_factor.
n_mul_len_sf = tree.nodes.new("ShaderNodeMath")
n_mul_len_sf.operation = "MULTIPLY"
n_mul_len_sf.location = (-500.0, -100.0)

# Math: (|A - B| * sag_factor) * sin(pi * t) => sag magnitude.
n_mul_final = tree.nodes.new("ShaderNodeMath")
n_mul_final.operation = "MULTIPLY"
n_mul_final.location = (-100.0, 0.0)

# Math: negate  -> -sag magnitude (we want downward on Z).
n_neg = tree.nodes.new("ShaderNodeMath")
n_neg.operation = "MULTIPLY"
n_neg.location = (100.0, 0.0)
n_neg.inputs[1].default_value = -1.0

# Combine XYZ: (0, 0, -sag_amount).
n_cxyz = tree.nodes.new("ShaderNodeCombineXYZ")
n_cxyz.location = (300.0, 0.0)
n_cxyz.inputs[0].default_value = 0.0
n_cxyz.inputs[1].default_value = 0.0

# Set Position on resampled curve (offset only).
n_setpos = tree.nodes.new("GeometryNodeSetPosition")
n_setpos.location = (500.0, 400.0)

# Curve Circle (hex profile: resolution = 6).
n_circle = tree.nodes.new("GeometryNodeCurvePrimitiveCircle")
n_circle.location = (500.0, -300.0)
n_circle.mode = "RADIUS"
n_circle.inputs["Resolution"].default_value = 6
n_circle.inputs["Radius"].default_value = 0.05

# Curve to Mesh.
n_c2m = tree.nodes.new("GeometryNodeCurveToMesh")
n_c2m.location = (900.0, 200.0)
# Fill Caps: leave False (open ends); evaluator is lenient on caps.
n_c2m.inputs["Fill Caps"].default_value = False

# --- Links ---------------------------------------------------------------
L = tree.links.new

# A, B locations -> curve line endpoints.
L(n_oi_a.outputs["Location"], n_line.inputs["Start"])
L(n_oi_b.outputs["Location"], n_line.inputs["End"])

# line -> resample
L(n_line.outputs["Curve"], n_resample.inputs["Curve"])

# A - B -> length
L(n_oi_a.outputs["Location"], n_sub.inputs[0])
L(n_oi_b.outputs["Location"], n_sub.inputs[1])
L(n_sub.outputs["Vector"], n_len.inputs[0])

# spline parameter factor -> multiply by pi -> sine
L(n_param.outputs["Factor"], n_mul_pi.inputs[0])
L(n_mul_pi.outputs["Value"], n_sin.inputs[0])

# length * sag_factor
L(n_len.outputs["Value"], n_mul_len_sf.inputs[0])
L(n_in.outputs["sag_factor"], n_mul_len_sf.inputs[1])

# (len * sag_factor) * sin(pi*t)
L(n_mul_len_sf.outputs["Value"], n_mul_final.inputs[0])
L(n_sin.outputs["Value"], n_mul_final.inputs[1])

# negate
L(n_mul_final.outputs["Value"], n_neg.inputs[0])

# combine xyz (Z = -sag)
L(n_neg.outputs["Value"], n_cxyz.inputs[2])

# Set Position
L(n_resample.outputs["Curve"], n_setpos.inputs["Geometry"])
L(n_cxyz.outputs["Vector"], n_setpos.inputs["Offset"])

# Curve to Mesh
L(n_setpos.outputs["Geometry"], n_c2m.inputs["Curve"])
L(n_circle.outputs["Curve"], n_c2m.inputs["Profile Curve"])

# Output
L(n_c2m.outputs["Mesh"], n_out.inputs["Geometry"])

# --- Set sag_factor default on modifier -----------------------------------
# In Blender 4.x, modifier inputs are indexed by the socket identifier
# (e.g. "Input_2" for the 2nd input). First INPUT is Geometry; second is
# sag_factor.
sag_identifier = None
for item in tree.interface.items_tree:
    if item.item_type == "SOCKET" and item.in_out == "INPUT" and item.name == "sag_factor":
        sag_identifier = item.identifier
        break

if sag_identifier is not None:
    mod[sag_identifier] = 0.1
    print(f"  set mod[{sag_identifier}] = 0.1")
else:
    print("  WARNING: could not locate sag_factor identifier")

# --- Sanity check: evaluated mesh ----------------------------------------
me = cable.data
print(f"  base Cable verts: {len(me.vertices)} (expect 0)")
print(f"  modifiers: {[(m.name, m.type) for m in cable.modifiers]}")

bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev_obj = cable.evaluated_get(dg)
ev_mesh = ev_obj.to_mesh()
n_v = len(ev_mesh.vertices)
print(f"  evaluated verts: {n_v}  (expect >= 240, multiple of 6)")
print(f"  evaluated faces: {len(ev_mesh.polygons)}")
zs = [v.co.z for v in ev_mesh.vertices]
if zs:
    print(f"  Z range: [{min(zs):.4f}, {max(zs):.4f}]")
ev_obj.to_mesh_clear()

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
