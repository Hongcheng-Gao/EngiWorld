"""Build `ground_truth/answer.blend` + `ground_truth/output/city.usda` for
task KH06 - procedural city.

Opens init_file/scene.blend (ground plane + camera + sun), adds 10
`Building_00..Building_09` objects arranged in a 5x2 grid. Each
building:
  - is a scaled cube sitting on the ground; width/depth = 2.0, per-
    building height in {3, 6, 9, 12, 4, 7, 10, 5, 8, 11};
  - gets a distinct Principled BSDF material `Mat_Building_XX` with an
    HSV-stepped base color (10 hues);
  - has a POINT-domain FLOAT_COLOR `Col` vertex-color layer set to one
    of two discrete material-ID colors:
        residential (even i): (0.2, 0.6, 0.3, 1) greenish
        commercial  (odd  i): (0.6, 0.3, 0.2, 1) brownish
  - has a custom property `material_purpose` on the material, matching
    the vertex-color scheme.

Then exports the scene to `ground_truth/output/city.usda` via
`bpy.ops.wm.usd_export(..., export_mesh_colors=True,
generate_preview_surface=True)`. The `.usda` suffix forces ASCII USD.

Because Blender's USD exporter doesn't automatically map
custom-property values on materials to USDA attributes, this script
post-processes the emitted USDA text to inject a
`custom string material:purpose = "<value>"` line into each
`def Material "Mat_Building_XX"` block.

Finally, saves `ground_truth/answer.blend` and, optionally, runs
eval.py against the freshly produced city.usda for a self-check.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import colorsys
import os
import re
import sys

import bpy


HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUT_DIR    = os.path.join(TASK_DIR, "ground_truth", "output")
OUT_USDA   = os.path.join(OUT_DIR, "city.usda")
OUT_BLEND  = os.path.join(TASK_DIR, "ground_truth", "answer.blend")

os.makedirs(OUT_DIR, exist_ok=True)


# -------------------------------------------------------------------------
# Building layout.
# -------------------------------------------------------------------------
# 5 x 2 grid: X in {-8, -4, 0, 4, 8}; Y in {-4, +4}.
GRID_X     = (-8.0, -4.0, 0.0, 4.0, 8.0)
GRID_Y     = (-4.0, 4.0)
BLDG_WIDTH = 2.0   # width/depth (X and Y extents) of each building box
HEIGHTS    = (3.0, 6.0, 9.0, 12.0, 4.0, 7.0, 10.0, 5.0, 8.0, 11.0)

# Vertex colors per material-ID purpose.
PURPOSE_FOR_INDEX = {
    0: "residential", 2: "residential", 4: "residential",
    6: "residential", 8: "residential",
    1: "commercial",  3: "commercial",  5: "commercial",
    7: "commercial",  9: "commercial",
}
VCOL_FOR_PURPOSE = {
    "residential": (0.2, 0.6, 0.3, 1.0),
    "commercial":  (0.6, 0.3, 0.2, 1.0),
}


def building_index_to_grid(i):
    """10 plots = 5 columns x 2 rows. Column = i % 5, row = i // 5."""
    col = i % 5
    row = i // 5
    return GRID_X[col], GRID_Y[row]


def hsv_step_rgb(i, n=10):
    """Return an (R, G, B, 1) tuple with hue = i/n, sat=0.7, val=0.9."""
    h = (i / n) % 1.0
    r, g, b = colorsys.hsv_to_rgb(h, 0.7, 0.9)
    return (r, g, b, 1.0)


def make_building_material(name, rgba, purpose):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    principled = None
    for n in nt.nodes:
        if n.type == "BSDF_PRINCIPLED":
            principled = n
            break
    if principled is None:
        principled = nt.nodes.new("ShaderNodeBsdfPrincipled")
    principled.inputs["Base Color"].default_value = rgba
    principled.inputs["Roughness"].default_value  = 0.6
    # Viewport display color.
    mat.diffuse_color = rgba
    # Custom property tagging purpose (residential/commercial).
    mat["material_purpose"] = purpose
    return mat


def make_building(i):
    """Create Building_i as a scaled cube on the ground with its own
    material and a POINT-domain FLOAT_COLOR `Col` attribute."""
    x, y = building_index_to_grid(i)
    height = HEIGHTS[i]

    # Add unit cube at origin, then scale/translate so its base sits on
    # Z=0 and its top is at Z=height.
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, y, height / 2.0))
    obj = bpy.context.active_object
    obj.name      = f"Building_{i:02d}"
    obj.data.name = f"Building_{i:02d}Mesh"
    # Apply non-uniform scale: width x width x height.
    obj.scale = (BLDG_WIDTH, BLDG_WIDTH, height)
    # Apply scale so the exported mesh has real dimensions (not a unit
    # cube with a scale op).
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Material.
    purpose = PURPOSE_FOR_INDEX[i]
    rgba    = hsv_step_rgb(i)
    mat     = make_building_material(f"Mat_Building_{i:02d}", rgba, purpose)
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    # Vertex colors. We use a POINT-domain FLOAT_COLOR attribute named
    # "Col", with every vertex set to the purpose-specific color. This
    # matches how DM03 stores its baked Col and is what Blender's USD
    # exporter converts to `primvars:displayColor` when
    # export_mesh_colors=True.
    me      = obj.data
    vcol    = VCOL_FOR_PURPOSE[purpose]
    n_verts = len(me.vertices)
    # Remove any pre-existing Col attribute to ensure a clean insert.
    for attr in list(me.color_attributes):
        if attr.name == "Col":
            me.color_attributes.remove(attr)
    for attr in list(me.attributes):
        if attr.name == "Col":
            me.attributes.remove(attr)
    col_attr = me.color_attributes.new(
        name="Col", type="FLOAT_COLOR", domain="POINT",
    )
    # Some Blender versions create the attribute with zero entries; the
    # length is driven by the domain cardinality. `.data` is indexed by
    # vertex for POINT-domain FLOAT_COLOR.
    for k in range(n_verts):
        col_attr.data[k].color = vcol

    return obj


def load_init_scene():
    bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)


def build_city():
    buildings = []
    for i in range(10):
        buildings.append(make_building(i))
    # Deselect everything so the subsequent save/export starts clean.
    bpy.ops.object.select_all(action="DESELECT")
    return buildings


def export_usda():
    bpy.ops.wm.usd_export(
        filepath=OUT_USDA,
        selected_objects_only=False,
        export_materials=True,
        export_mesh_colors=True,
        generate_preview_surface=True,
    )
    print(f"  exported -> {OUT_USDA}")


def postprocess_usda_inject_purpose():
    """Inject `custom string material:purpose = "..."` into each
    `def Material "Mat_Building_XX"` block in the emitted USDA.

    Blender's USD exporter (4.1) does not map custom properties on
    bpy.types.Material to USDA attributes, so we do the injection via
    a regex pass over the text file.
    """
    with open(OUT_USDA, "r", encoding="utf-8") as fh:
        text = fh.read()

    # Sanity: file must start with `#usda`.
    if not text.startswith("#usda"):
        raise RuntimeError(f"{OUT_USDA} does not start with '#usda'")

    count_injected = 0
    for i in range(10):
        purpose  = PURPOSE_FOR_INDEX[i]
        mat_name = f"Mat_Building_{i:02d}"
        # Match `def Material "Mat_Building_XX" ... {` where `...` is
        # optional metadata-parenthesis block. We locate the opening
        # brace that follows the def line and insert a new line right
        # after it.
        pattern = re.compile(
            r'(def\s+Material\s+"' + re.escape(mat_name) + r'"'
            r'(?:[^{]*?))(\{)',
            re.DOTALL,
        )
        m = pattern.search(text)
        if m is None:
            raise RuntimeError(
                f"could not find Material block for {mat_name} in USDA"
            )
        inject = (
            m.group(1) + m.group(2)
            + f'\n        custom string material:purpose = "{purpose}"'
        )
        text = text[:m.start()] + inject + text[m.end():]
        count_injected += 1

    # Post-condition: the substring `material:purpose` appears at least
    # 10 times.
    n_purpose = text.count("material:purpose")
    if n_purpose < 10:
        raise RuntimeError(
            f"post-process failed: only {n_purpose} 'material:purpose' "
            f"occurrences in USDA"
        )

    with open(OUT_USDA, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"  injected 'material:purpose' into {count_injected} materials; "
          f"total occurrences in file = {n_purpose}")


def save_answer_blend():
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print(f"  saved -> {OUT_BLEND}")


def sanity_dump_scene():
    names = sorted(o.name for o in bpy.data.objects
                   if o.name.startswith("Building_"))
    print(f"  #Buildings           : {len(names)}")
    for n in names:
        ob  = bpy.data.objects[n]
        me  = ob.data
        col = me.color_attributes.get("Col")
        mats = [m.name for m in me.materials]
        z_max = max((v.co.z for v in me.vertices), default=0.0)
        print(f"    {n}: loc=({ob.location.x:.1f},{ob.location.y:.1f},"
              f"{ob.location.z:.1f}), Zmax={z_max:.1f}, mats={mats}, "
              f"Col={'yes' if col else 'no'} "
              f"(n={len(col.data) if col else 0})")


def sanity_dump_usda_head():
    size = os.path.getsize(OUT_USDA)
    print(f"  usda size            : {size} bytes")
    with open(OUT_USDA, "r", encoding="utf-8", errors="replace") as fh:
        head = fh.readlines()[:20]
    print("  first 20 lines of city.usda:")
    for l in head:
        print("    " + l.rstrip())


def self_check():
    sys.dont_write_bytecode = True
    sys.path.insert(0, TASK_DIR)
    try:
        import eval as eval_mod  # noqa: E402
        card = eval_mod._run_eval(OUT_USDA)
        print(card.render())
    except Exception as exc:
        print(f"  [warn] eval self-check failed: {exc}")


# -------------------------------------------------------------------------
# Main.
# -------------------------------------------------------------------------
load_init_scene()
build_city()
sanity_dump_scene()

export_usda()
postprocess_usda_inject_purpose()
sanity_dump_usda_head()

save_answer_blend()

self_check()
