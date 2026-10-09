"""Build ground_truth/answer.blend for task AH05 - Proximity Vertex Group.

Adds a Geometry Nodes modifier on `Skin` that:

  1. Reads the Bone object's geometry via Object Info
     (transform_space='RELATIVE' so Bone's world position is honored in
     Skin's local frame; Skin is at the origin so this matches world space).
  2. Feeds it to `GeometryNodeProximity` (target_element='FACES'); Source
     Position defaults to the evaluating geometry's Position, so we get
     distance from each Skin vertex to the Bone surface.
  3. Remaps the distance with Map Range (interpolation_type='SMOOTHSTEP',
     clamp=True), from_min=0.3 -> to_min=1.0, from_max=1.0 -> to_max=0.0.
     This yields 1 for distance <= 0.3, 0 for distance >= 1.0, and a
     smooth fade in between.
  4. Stores the remapped float as a POINT-domain FLOAT attribute
     `Influence` via Store Named Attribute.
  5. Passes geometry to Group Output.

The modifier is NOT applied; the base Skin carries no Influence attribute.

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


def main():
    bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

    skin = bpy.data.objects["Skin"]
    bone = bpy.data.objects["Bone"]

    # --- Add GN modifier --------------------------------------------------
    mod = skin.modifiers.new(name="ProximityInfluenceGN", type="NODES")

    # --- Build the GN tree ------------------------------------------------
    tree = bpy.data.node_groups.new(name="ProximityInfluenceGN",
                                    type="GeometryNodeTree")
    mod.node_group = tree

    tree.interface.new_socket(name="Geometry",
                              in_out="INPUT",
                              socket_type="NodeSocketGeometry")
    tree.interface.new_socket(name="Geometry",
                              in_out="OUTPUT",
                              socket_type="NodeSocketGeometry")

    n_in  = tree.nodes.new("NodeGroupInput")
    n_out = tree.nodes.new("NodeGroupOutput")
    n_in.location  = (-1400.0, 0.0)
    n_out.location = ( 1400.0, 0.0)

    # Object Info for Bone. transform_space='RELATIVE' transforms Bone's
    # geometry into Skin's local space; Skin is at world origin so this is
    # equivalent to world space.
    n_oi = tree.nodes.new("GeometryNodeObjectInfo")
    n_oi.location = (-1200.0, 200.0)
    n_oi.inputs["Object"].default_value = bone
    n_oi.transform_space = "RELATIVE"

    # Proximity node: Target = Bone geometry; Source Position defaults to
    # Position (per-point). target_element 'FACES' (default) measures
    # distance to the nearest surface point on the target mesh.
    n_prox = tree.nodes.new("GeometryNodeProximity")
    n_prox.location = (-900.0, 100.0)
    n_prox.target_element = "FACES"

    # Map Range with SMOOTHSTEP: from [0.3, 1.0] to [1.0, 0.0], clamped.
    #   distance <= 0.3 -> 1.0
    #   distance >= 1.0 -> 0.0
    #   between         -> smoothstep fade
    n_map = tree.nodes.new("ShaderNodeMapRange")
    n_map.location = (-600.0, 100.0)
    n_map.data_type = "FLOAT"
    n_map.interpolation_type = "SMOOTHSTEP"
    n_map.clamp = True
    n_map.inputs["From Min"].default_value = 0.3
    n_map.inputs["From Max"].default_value = 1.0
    n_map.inputs["To Min"].default_value   = 1.0
    n_map.inputs["To Max"].default_value   = 0.0

    # Store Named Attribute: FLOAT / POINT / 'Influence'.
    n_store = tree.nodes.new("GeometryNodeStoreNamedAttribute")
    n_store.location = (200.0, 0.0)
    n_store.data_type = "FLOAT"
    n_store.domain = "POINT"
    n_store.inputs["Name"].default_value = "Influence"

    # --- Links -----------------------------------------------------------
    L = tree.links.new

    # Geometry pipe: GroupInput -> StoreAttr -> GroupOutput.
    L(n_in.outputs["Geometry"], n_store.inputs["Geometry"])
    L(n_store.outputs["Geometry"], n_out.inputs["Geometry"])

    # Proximity target = Bone geometry (from Object Info).
    L(n_oi.outputs["Geometry"], n_prox.inputs["Target"])

    # Proximity Distance -> Map Range input.
    # The Map Range node (ShaderNodeMapRange) FLOAT data_type input key is
    # "Value"; resolve by name + type to be safe.
    prox_dist_out = n_prox.outputs["Distance"]
    map_value_in = next(
        (s for s in n_map.inputs if s.name == "Value" and s.enabled),
        None,
    )
    assert map_value_in is not None, "Map Range has no enabled Value input"
    L(prox_dist_out, map_value_in)

    # Map Range Result -> Store Named Attribute Value (FLOAT).
    map_result_out = next(
        (s for s in n_map.outputs
         if s.name == "Result" and s.enabled),
        None,
    )
    assert map_result_out is not None, "Map Range has no enabled Result output"

    # For data_type=FLOAT, Store Named Attribute's active Value input has
    # socket .type 'VALUE'. Find by (name, type).
    store_value_in = next(
        (s for s in n_store.inputs
         if s.name == "Value" and s.type == "VALUE"),
        None,
    )
    assert store_value_in is not None, \
        "Store Named Attribute has no VALUE Value socket with data_type=FLOAT"
    L(map_result_out, store_value_in)

    # --- Sanity check: base mesh must NOT have Influence ----------------
    me = skin.data
    base_has = any(a.name == "Influence" for a in me.attributes)
    print(f"  base Skin has Influence? {base_has} (expect False)")
    print(f"  Skin base verts: {len(me.vertices)}")
    print(f"  Skin modifiers:  {[(m.name, m.type) for m in skin.modifiers]}")

    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev_obj = skin.evaluated_get(dg)
    ev_mesh = ev_obj.to_mesh()

    eval_has = any(a.name == "Influence" for a in ev_mesh.attributes)
    print(f"  evaluated Skin has Influence? {eval_has} (expect True)")
    if eval_has:
        attr = ev_mesh.attributes["Influence"]
        print(f"    domain: {attr.domain} (expect POINT)")
        print(f"    type:   {attr.data_type} (expect FLOAT)")
        vals = [attr.data[i].value for i in range(len(ev_mesh.vertices))]
        print(f"    min/max:   {min(vals):.4f} / {max(vals):.4f}")
        # Compute some stats for close/far bands for debugging.
        import math
        n_close = n_far = 0
        close_min = 1.0
        far_max = 0.0
        for i, v in enumerate(ev_mesh.vertices):
            # Distance to Bone surface: sphere at (0,0,0.5) radius 0.3.
            d_center = math.sqrt(v.co.x ** 2 + v.co.y ** 2
                                 + (v.co.z - 0.5) ** 2)
            d_surf = max(0.0, d_center - 0.3)
            if d_surf <= 0.3:
                n_close += 1
                close_min = min(close_min, vals[i])
            elif d_surf > 1.0:
                n_far += 1
                far_max = max(far_max, vals[i])
        print(f"    close verts (d_surf <= 0.3): {n_close}, "
              f"min Influence = {close_min:.4f} (expect >= 0.9)")
        print(f"    far verts   (d_surf >  1.0): {n_far}, "
              f"max Influence = {far_max:.4f} (expect <= 0.1)")

    ev_obj.to_mesh_clear()

    bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
    print(f"  saved -> {OUT_PATH}")


if __name__ == "__main__":
    main()
