"""Build ground_truth/answer.blend for task BH04.

Construct a Geometry Nodes tree entirely in Python on the `Array` object:

  Mesh Line (Count=20, Offset=(0,0,0.2))
      -> Instance on Points (.Points)
  Mesh Cube (Size=(0.1,0.1,0.1))
      -> Instance on Points (.Instance)
  Instance on Points.Instances
      -> Realize Instances.Geometry
  Realize Instances.Geometry
      -> Group Output.Geometry

The modifier is NOT applied; base mesh stays empty (0 verts).

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


bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

arr = bpy.data.objects["Array"]

# --- Add GN modifier -------------------------------------------------------
mod = arr.modifiers.new(name="GeometryNodes", type="NODES")

# --- Build the GN tree entirely via Python --------------------------------
tree = bpy.data.node_groups.new(name="ArrayGN", type="GeometryNodeTree")
mod.node_group = tree

# Interface sockets (Blender 4.x API).
tree.interface.new_socket(name="Geometry",
                          in_out="INPUT",
                          socket_type="NodeSocketGeometry")
tree.interface.new_socket(name="Geometry",
                          in_out="OUTPUT",
                          socket_type="NodeSocketGeometry")

# Group Input / Group Output boundary nodes.
n_in  = tree.nodes.new("NodeGroupInput")
n_out = tree.nodes.new("NodeGroupOutput")
n_in.location  = (-900.0, 0.0)
n_out.location = ( 600.0, 0.0)

# Three REQUIRED nodes (plus a Mesh Cube primitive as the instance source).
n_line = tree.nodes.new("GeometryNodeMeshLine")
n_iop  = tree.nodes.new("GeometryNodeInstanceOnPoints")
n_ri   = tree.nodes.new("GeometryNodeRealizeInstances")
n_cube = tree.nodes.new("GeometryNodeMeshCube")

n_line.location = (-600.0,  150.0)
n_cube.location = (-600.0, -200.0)
n_iop.location  = (-250.0,   50.0)
n_ri.location   = ( 150.0,   50.0)

# Mesh Line configuration.
n_line.inputs["Count"].default_value          = 20
n_line.inputs["Start Location"].default_value = (0.0, 0.0, 0.0)
n_line.inputs["Offset"].default_value         = (0.0, 0.0, 0.2)

# Mesh Cube configuration.
n_cube.inputs["Size"].default_value = (0.1, 0.1, 0.1)

# --- Links ---------------------------------------------------------------
tree.links.new(n_line.outputs["Mesh"],    n_iop.inputs["Points"])
tree.links.new(n_cube.outputs["Mesh"],    n_iop.inputs["Instance"])
tree.links.new(n_iop.outputs["Instances"], n_ri.inputs["Geometry"])
tree.links.new(n_ri.outputs["Geometry"],   n_out.inputs["Geometry"])

# Sanity: base mesh MUST remain empty (modifier NOT applied).
me = arr.data
print(f"  base mesh vertices: {len(me.vertices)} (expect 0)")
print(f"  modifiers: {[(m.name, m.type) for m in arr.modifiers]}")
print(f"  nodes in tree: {[n.bl_idname for n in tree.nodes]}")

# Evaluated-mesh sanity (should be 160 = 20 * 8).
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = arr.evaluated_get(dg).to_mesh()
print(f"  evaluated vertices: {len(ev.vertices)} (expect 160)")
zs = [v.co.z for v in ev.vertices]
if zs:
    print(f"  evaluated Z-extent: [{min(zs):.3f}, {max(zs):.3f}]")
arr.evaluated_get(dg).to_mesh_clear()

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
