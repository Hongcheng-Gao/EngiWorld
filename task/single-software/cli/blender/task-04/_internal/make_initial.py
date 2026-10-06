"""Build init_file/scene.blend for task AH04 - Procedural Tree with LOD.

An empty scene with a single mesh object named `Tree` at the world
origin. `Tree.data` is a minimal mesh with a single vertex at origin.
A Geometry Nodes modifier named `GN_Tree` is attached as a pass-through
placeholder: its node tree has only a Group Input connected directly to
a Group Output (no sub-node-groups, no LOD input). The testee must
rebuild the tree to add three named sub-node-groups (Trunk, Branches,
Leaves) and expose an Integer `LOD` input.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import os

import bpy

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
OUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)


def clean_scene():
    """Remove every object and purge common data-blocks for a minimal file."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.node_groups, bpy.data.materials,
                bpy.data.armatures, bpy.data.objects):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


def build_tree_object():
    """Create the empty Tree mesh with a single vertex at origin."""
    me = bpy.data.meshes.new("TreeMesh")
    # Single vertex at origin so evaluated mesh isn't pathologically empty.
    me.from_pydata([(0.0, 0.0, 0.0)], [], [])
    me.update()
    obj = bpy.data.objects.new("Tree", me)
    bpy.context.collection.objects.link(obj)
    obj.location = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale = (1.0, 1.0, 1.0)
    return obj


def build_passthrough_gn(tree_obj):
    """Attach a GN modifier with a minimal pass-through graph."""
    mod = tree_obj.modifiers.new(name="GN_Tree", type="NODES")
    ng = bpy.data.node_groups.new(name="GN_Tree", type="GeometryNodeTree")
    mod.node_group = ng

    # Only Geometry IO - no LOD input.
    ng.interface.new_socket(name="Geometry",
                            in_out="INPUT",
                            socket_type="NodeSocketGeometry")
    ng.interface.new_socket(name="Geometry",
                            in_out="OUTPUT",
                            socket_type="NodeSocketGeometry")

    n_in = ng.nodes.new("NodeGroupInput")
    n_out = ng.nodes.new("NodeGroupOutput")
    n_in.location = (-300.0, 0.0)
    n_out.location = (300.0, 0.0)

    # Pass-through link.
    ng.links.new(n_in.outputs["Geometry"], n_out.inputs["Geometry"])

    return mod


def main():
    clean_scene()

    # Scene units: meters.
    scn = bpy.context.scene
    scn.unit_settings.system = "METRIC"
    scn.unit_settings.length_unit = "METERS"
    scn.unit_settings.scale_length = 1.0

    tree_obj = build_tree_object()
    mod = build_passthrough_gn(tree_obj)

    # Sanity prints.
    print(f"  Tree verts:      {len(tree_obj.data.vertices)} (expect 1)")
    print(f"  Tree modifiers:  {len(tree_obj.modifiers)} (expect 1)")
    print(f"  Modifier name:   {mod.name} (expect GN_Tree)")
    print(f"  Modifier type:   {mod.type} (expect NODES)")
    print(f"  Node group:      {mod.node_group.name} "
          f"({len(mod.node_group.nodes)} node(s))")
    print(f"  Interface sockets: "
          f"{[(s.name, s.in_out) for s in mod.node_group.interface.items_tree]}")
    print(f"  node_groups in file: "
          f"{[(ng.name, ng.type) for ng in bpy.data.node_groups]}")

    bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
    print(f"  saved -> {OUT_PATH}")


if __name__ == "__main__":
    main()
