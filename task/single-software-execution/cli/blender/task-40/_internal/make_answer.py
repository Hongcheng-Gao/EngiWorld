"""Build ground_truth/answer.blend for task KH02.

Pipeline:
  1. Open init_file/scene.blend.
  2. Parse init_file/bricks.csv (100 rows of x, y, z, hue).
  3. Create `BrickPoints` - a mesh with exactly 100 vertices at the CSV
     positions and a POINT-domain FLOAT attribute `hue` carrying the
     CSV's hue column.
  4. Create `Brick` - a small cuboid (0.8 x 0.5 x 0.3) to use as the
     per-brick instance source.
  5. Add a Geometry Nodes modifier on BrickPoints that:
       - Instances Brick at every vertex via Instance on Points
         (Instance = Object Info(Brick).Geometry).
       - Realizes the instances (Realize Instances node).
       - Carries the `hue` attribute from the points onto the realized
         geometry so the shader can read it per-instance.
  6. Build a material `Mat_Brick` whose color is driven by the `hue`
     attribute via a ColorRamp feeding Principled BSDF Base Color.
  7. Assign Mat_Brick to the Brick object (instance source) so the
     material propagates to every instance.
  8. Parent the Camera to a new `TurnPivot` empty at the origin and
     keyframe the pivot's Z rotation 0 -> 2pi over frames 1..30.
  9. Configure Cycles render (256x256, 16 samples, denoise on) and
     render the 30-frame sequence to
     `<task>/ground_truth/output/frame_0001.png` .. `frame_0030.png`.
 10. Save answer.blend.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import csv
import math
import os

import bmesh
import bpy
from mathutils import Vector

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_BLEND = os.path.join(TASK_DIR, "init_file", "scene.blend")
CSV_PATH    = os.path.join(TASK_DIR, "init_file", "bricks.csv")
OUT_BLEND   = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
FRAME_DIR   = os.path.join(TASK_DIR, "ground_truth", "output")
os.makedirs(FRAME_DIR, exist_ok=True)

BRICK_SIZE = (0.8, 0.5, 0.3)   # x, y, z full extents

# ---------------------------------------------------------------------------
# CSV


def read_bricks_csv(path):
    """Return list of (x, y, z, hue) floats from the CSV."""
    rows = []
    with open(path) as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append((float(row["x"]), float(row["y"]),
                         float(row["z"]), float(row["hue"])))
    return rows


# ---------------------------------------------------------------------------
# Meshes


def make_brick_points(rows):
    """Create a Mesh named BrickPoints with one vertex per row and a
    POINT-domain FLOAT attribute `hue`."""
    bm = bmesh.new()
    for (x, y, z, _hue) in rows:
        bm.verts.new((x, y, z))
    bm.verts.ensure_lookup_table()

    me  = bpy.data.meshes.new("BrickPointsMesh")
    obj = bpy.data.objects.new("BrickPoints", me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me)
    bm.free()

    # Add the `hue` attribute.
    attr = me.attributes.new(name="hue", type="FLOAT", domain="POINT")
    for i, (_x, _y, _z, hue) in enumerate(rows):
        attr.data[i].value = float(hue)

    obj.location = (0.0, 0.0, 0.0)
    return obj


def make_brick():
    """Create a small cuboid mesh named Brick (0.8 x 0.5 x 0.3) centered
    at its origin."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    # Scale verts to (sx, sy, sz) / 2 so full extents match BRICK_SIZE.
    sx, sy, sz = BRICK_SIZE
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    me  = bpy.data.meshes.new("BrickMesh")
    obj = bpy.data.objects.new("Brick", me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me)
    bm.free()

    # Keep the Brick source at the world origin and hide it from
    # render. We cannot park the source far below the scene because
    # Object Info(RELATIVE) in a GN modifier running on BrickPoints
    # (at origin) would pull that translation into every realized
    # instance, stuffing all 100 bricks down at z=-100 and out of the
    # camera's view. Placing the source at the origin means instances
    # land exactly at the CSV-specified vertex positions of BrickPoints.
    # `hide_render` only hides THIS object's own render pass and does
    # not affect the realized-instances geometry emitted by the GN
    # modifier on BrickPoints, so the 100 visible copies still render.
    obj.location = (0.0, 0.0, 0.0)
    obj.hide_render = True
    return obj


# ---------------------------------------------------------------------------
# Material


def build_brick_material():
    """Create Mat_Brick with Attribute('hue') -> ColorRamp -> Principled
    BSDF Base Color."""
    mat = bpy.data.materials.new("Mat_Brick")
    mat.use_nodes = True
    nt = mat.node_tree
    # Clear default nodes.
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    n_attr = nt.nodes.new("ShaderNodeAttribute")
    n_attr.location = (-700, 0)
    n_attr.attribute_name = "hue"
    # Default attribute_type is 'GEOMETRY' which reads from mesh
    # attributes and propagates through instances / realized geometry.

    n_ramp = nt.nodes.new("ShaderNodeValToRGB")
    n_ramp.location = (-400, 0)
    ramp = n_ramp.color_ramp
    ramp.interpolation = "LINEAR"
    # Replace default 2-stop ramp with a 5-stop rainbow.
    # Blender's default ramp has 2 elements already; we add 3 more.
    # Desired stops: red, yellow, green, blue, purple.
    stops = [
        (0.00, (1.00, 0.00, 0.00, 1.0)),
        (0.25, (1.00, 1.00, 0.00, 1.0)),
        (0.50, (0.00, 1.00, 0.00, 1.0)),
        (0.75, (0.00, 0.30, 1.00, 1.0)),
        (1.00, (0.60, 0.00, 0.80, 1.0)),
    ]
    # Adjust the existing 2 elements first, then add remaining.
    for i, (pos, col) in enumerate(stops[:2]):
        ramp.elements[i].position = pos
        ramp.elements[i].color    = col
    for (pos, col) in stops[2:]:
        e = ramp.elements.new(pos)
        e.color = col

    n_bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    n_bsdf.location = (0, 0)
    # Make it slightly rough for clearer color visibility.
    if "Roughness" in n_bsdf.inputs:
        n_bsdf.inputs["Roughness"].default_value = 0.5
    # Specular defaults are fine; we just drive Base Color.

    n_out = nt.nodes.new("ShaderNodeOutputMaterial")
    n_out.location = (300, 0)

    nt.links.new(n_attr.outputs["Fac"],    n_ramp.inputs["Fac"])
    nt.links.new(n_ramp.outputs["Color"],  n_bsdf.inputs["Base Color"])
    nt.links.new(n_bsdf.outputs["BSDF"],   n_out.inputs["Surface"])

    return mat


def assign_material(obj, mat):
    me = obj.data
    if me.materials:
        me.materials[0] = mat
    else:
        me.materials.append(mat)


# ---------------------------------------------------------------------------
# Geometry Nodes modifier


def build_gn_modifier(brick_points, brick):
    """Add a GN modifier on BrickPoints that:
      Group Input(Geometry) -> Instance on Points(Instance=ObjectInfo(Brick))
      -> Realize Instances -> Store Named Attribute('hue' propagation)
      -> Group Output.
    The `hue` attribute on the POINT domain of the input mesh propagates
    through Instance on Points' capture; to make it trivially visible on
    the realized geometry we also explicitly capture and store it.
    """
    # Clear any prior modifier.
    for m in list(brick_points.modifiers):
        brick_points.modifiers.remove(m)

    mod = brick_points.modifiers.new(name="BrickInstancer", type="NODES")
    tree = bpy.data.node_groups.new(name="BrickInstancerGN",
                                    type="GeometryNodeTree")
    mod.node_group = tree

    tree.interface.new_socket(name="Geometry",
                              in_out="INPUT",
                              socket_type="NodeSocketGeometry")
    tree.interface.new_socket(name="Geometry",
                              in_out="OUTPUT",
                              socket_type="NodeSocketGeometry")

    nodes = tree.nodes
    links = tree.links

    n_in  = nodes.new("NodeGroupInput")
    n_out = nodes.new("NodeGroupOutput")
    n_in.location  = (-1400.0, 0.0)
    n_out.location = ( 1200.0, 0.0)

    # Named Attribute (read `hue` from points) so we can re-store it on
    # the realized geometry later.
    n_named = nodes.new("GeometryNodeInputNamedAttribute")
    n_named.location = (-1200.0, -300.0)
    n_named.data_type = "FLOAT"
    n_named.inputs["Name"].default_value = "hue"

    # Capture Attribute: capture `hue` on POINT domain of input so it
    # rides along with instances.
    n_cap = nodes.new("GeometryNodeCaptureAttribute")
    n_cap.location = (-900.0, 0.0)
    n_cap.data_type = "FLOAT"
    n_cap.domain    = "POINT"
    # The capture node's second input ("Value") is the attribute we're
    # capturing. Wire from Named Attribute.
    links.new(n_in.outputs["Geometry"], n_cap.inputs["Geometry"])
    # The "Value" socket on capture is indexed; prefer by name when
    # available.
    if "Value" in n_cap.inputs:
        links.new(n_named.outputs["Attribute"], n_cap.inputs["Value"])
    else:
        links.new(n_named.outputs["Attribute"], n_cap.inputs[1])

    # Object Info for Brick (instance source).
    n_objinfo = nodes.new("GeometryNodeObjectInfo")
    n_objinfo.location = (-600.0, -350.0)
    n_objinfo.transform_space = "RELATIVE"
    n_objinfo.inputs["Object"].default_value = brick

    # Instance on Points.
    n_iop = nodes.new("GeometryNodeInstanceOnPoints")
    n_iop.location = (-300.0, 0.0)
    links.new(n_cap.outputs["Geometry"], n_iop.inputs["Points"])
    links.new(n_objinfo.outputs["Geometry"], n_iop.inputs["Instance"])

    # Realize instances so shader/attribute read is trivial.
    n_real = nodes.new("GeometryNodeRealizeInstances")
    n_real.location = (100.0, 0.0)
    links.new(n_iop.outputs["Instances"], n_real.inputs["Geometry"])

    # Store Named Attribute: write `hue` back onto the realized geometry
    # (POINT domain) so the shader Attribute node finds it. On realized
    # instances, captured-attribute values propagate to the POINT domain
    # of the expanded geometry, but we store explicitly to be safe.
    n_store = nodes.new("GeometryNodeStoreNamedAttribute")
    n_store.location = (500.0, 0.0)
    n_store.data_type = "FLOAT"
    n_store.domain    = "POINT"
    n_store.inputs["Name"].default_value = "hue"
    links.new(n_real.outputs["Geometry"], n_store.inputs["Geometry"])
    # Route captured attribute value through as the stored value.
    # The capture node exposes its captured attribute on an output named
    # "Attribute" (Blender 4.x).
    cap_out = None
    for so in n_cap.outputs:
        if so.name == "Attribute":
            cap_out = so
            break
    if cap_out is None:
        # Fallback: second output index.
        cap_out = n_cap.outputs[1]
    if "Value" in n_store.inputs:
        links.new(cap_out, n_store.inputs["Value"])
    else:
        # index-3 is typically the Value socket when the Selection
        # (index 2) is unused.
        for inp in n_store.inputs:
            if inp.type == "VALUE":
                links.new(cap_out, inp)
                break

    links.new(n_store.outputs["Geometry"], n_out.inputs["Geometry"])

    # Nudge rebuild.
    mod.node_group = mod.node_group
    brick_points.update_tag()
    return mod


# ---------------------------------------------------------------------------
# Turntable


def build_turntable(scene, cam):
    """Create `TurnPivot` empty at origin, parent Camera to it
    preserving the camera's world transform, and keyframe the empty's
    Z rotation from 0 at frame 1 to 2*pi at frame 30."""
    # Remove any leftover empty from a prior run.
    old = bpy.data.objects.get("TurnPivot")
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)

    empty = bpy.data.objects.new("TurnPivot", None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = 2.0
    empty.location = (0.0, 0.0, 0.0)
    empty.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.collection.objects.link(empty)

    bpy.context.view_layer.update()
    # Use operator-style parenting to preserve the camera's current
    # world transform. `KEEP_TRANSFORM` sets matrix_parent_inverse so
    # that world(cam) stays the same after reparenting. Doing the
    # matrix math by hand with `empty.matrix_world.inverted() @
    # cam.matrix_world` is unreliable here because `cam.matrix_world`
    # is read lazily through the parent chain: after `cam.parent =
    # empty` Blender returns the already-parented world, and when the
    # pivot is identity that equals cam.matrix_basis, so plugging that
    # in as matrix_parent_inverse double-applies the camera's
    # translation and rotation.
    bpy.ops.object.select_all(action="DESELECT")
    cam.select_set(True)
    empty.select_set(True)
    bpy.context.view_layer.objects.active = empty
    bpy.ops.object.parent_set(type="OBJECT", keep_transform=True)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.update()

    # Clear any prior animation on the empty.
    if empty.animation_data is not None:
        empty.animation_data_clear()

    keyframes = [(1, 0.0), (30, 2.0 * math.pi)]
    for f, z in keyframes:
        scene.frame_set(f)
        empty.rotation_euler = (0.0, 0.0, z)
        empty.keyframe_insert(data_path="rotation_euler", index=2, frame=f)

    # Force LINEAR so f(frame) is exact at each key.
    action = empty.animation_data.action
    fc_z = action.fcurves.find("rotation_euler", index=2)
    for kp in fc_z.keyframe_points:
        kp.interpolation = "LINEAR"
    fc_z.update()

    scene.frame_set(1)
    bpy.context.view_layer.update()
    return empty


# ---------------------------------------------------------------------------
# Render


def render_sequence(scene):
    scene.render.engine        = "CYCLES"
    scene.cycles.device        = "CPU"
    scene.cycles.samples       = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x  = 256
    scene.render.resolution_y  = 256
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode  = 'RGBA'

    # Use the #### token; Blender substitutes frame numbers 0001..0030.
    filepath_template = os.path.join(FRAME_DIR, "frame_####.png")
    scene.render.filepath = filepath_template
    scene.frame_start = 1
    scene.frame_end   = 30

    # Render the full animation.
    bpy.ops.render.render(animation=True)


# ---------------------------------------------------------------------------


def main():
    bpy.ops.wm.open_mainfile(filepath=INPUT_BLEND)
    scene = bpy.context.scene

    # Parse CSV.
    rows = read_bricks_csv(CSV_PATH)
    assert len(rows) == 100, f"expected 100 CSV rows, got {len(rows)}"

    # Distribution mesh + brick instance source.
    brick_points = make_brick_points(rows)
    brick = make_brick()

    # Material.
    mat = build_brick_material()
    assign_material(brick, mat)

    # GN modifier.
    mod = build_gn_modifier(brick_points, brick)

    # Turntable.
    cam = bpy.data.objects["Camera"]
    pivot = build_turntable(scene, cam)

    # Sanity prints.
    print("-" * 60)
    print(f"  BrickPoints verts         = {len(brick_points.data.vertices)}")
    print(f"  Brick mesh verts          = {len(brick.data.vertices)}")
    print(f"  Material                  = "
          f"{brick.data.materials[0].name if brick.data.materials else None}")
    print(f"  GN modifier on points     = "
          f"{[m.name for m in brick_points.modifiers]}")
    print(f"  Camera.parent             = "
          f"{cam.parent.name if cam.parent else None}")
    print(f"  TurnPivot keyframes       = "
          f"{len(pivot.animation_data.action.fcurves.find('rotation_euler', index=2).keyframe_points)}")
    # Evaluate pivot rotation at frames 1 and 30 for sanity.
    for f in (1, 30):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        ev = pivot.evaluated_get(dg)
        print(f"    frame {f}: pivot.z_rot_eval = "
              f"{ev.rotation_euler.z:+.4f} rad "
              f"({math.degrees(ev.rotation_euler.z):+.1f} deg)")

    # Evaluated BrickPoints mesh after GN modifier - should now have
    # realized brick geometry (100 instances x 8 verts = 800 verts,
    # 6 quads each = 600 faces).
    scene.frame_set(1)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev_bp = brick_points.evaluated_get(dg)
    ev_me = ev_bp.data
    print(f"  Evaluated BrickPoints verts = {len(ev_me.vertices)} "
          f"(expect ~800)")
    print(f"  Evaluated BrickPoints polys = {len(ev_me.polygons)} "
          f"(expect ~600)")
    print(f"  Evaluated BrickPoints mats  = "
          f"{[m.name if m else None for m in ev_me.materials]}")
    print(f"  Evaluated attrs             = "
          f"{[a.name for a in ev_me.attributes]}")
    print(f"  BrickPoints.visible_get     = {brick_points.visible_get()}")
    print(f"  Brick.visible_get           = {brick.visible_get()}")
    print(f"  BrickPoints.hide_render     = {brick_points.hide_render}")
    print(f"  Brick.hide_render           = {brick.hide_render}")
    print("-" * 60)

    # Render sequence BEFORE saving so we don't leave a stale absolute
    # filepath baked into the blend.
    render_sequence(scene)

    # Reset filepath so the saved blend doesn't lock into an absolute
    # host-specific path.
    scene.render.filepath = "//frame_####.png"
    scene.frame_set(1)
    bpy.context.view_layer.update()

    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print(f"  saved -> {OUT_BLEND}")


if __name__ == "__main__":
    main()
