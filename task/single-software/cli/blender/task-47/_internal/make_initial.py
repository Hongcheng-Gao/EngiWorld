"""Build `init_file/scene.blend` for task LH03.

Creates two mesh objects:
  - `Source`: a cube at location (2.0, 0.0, 0.0).
  - `Driven`: a cube with a driver on `location[1]` (y) whose data_path
    on the SINGLE_PROP variable target is intentionally typo'd (the
    attribute name is misspelled, so RNA fails to resolve it). The
    expression is simply `var`.

Because the driver variable's data_path is invalid, the driver evaluates
to the default 0.0 rather than picking up Source.location.x = 2.0.
A scene frame update does not raise; Driven.location.y stays 0.0.

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
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.actions):
        for d in list(blk):
            blk.remove(d)


def add_cube(name, location):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.name = name + "Mesh"
    return obj


def add_broken_driver(obj, source_name):
    """Add a driver on obj.location.y that references source.location with
    a *typo'd* data path ('location.xx'). The driver variable is
    SINGLE_PROP; the expression is the variable itself."""
    fcurve = obj.driver_add("location", 1)   # index 1 == y
    drv = fcurve.driver
    drv.type = 'SCRIPTED'
    drv.expression = "var"

    var = drv.variables.new()
    var.name = "var"
    var.type = 'SINGLE_PROP'
    tgt = var.targets[0]
    tgt.id_type = 'OBJECT'
    tgt.id = bpy.data.objects[source_name]
    # Typo: should be 'location.x'. 'locaton' is a misspelling of
    # 'location', so RNA path resolution fails and the driver evaluates
    # to its default (0.0). This is the intentional bug.
    tgt.data_path = "locaton.x"
    return fcurve


clean_scene()

source = add_cube("Source", (2.0, 0.0, 0.0))
driven = add_cube("Driven", (0.0, 0.0, 0.0))

fcurve = add_broken_driver(driven, "Source")

# Force an evaluation so the driver's error state is resolved before save.
bpy.context.view_layer.update()
bpy.context.scene.frame_set(bpy.context.scene.frame_current)

print(f"  Source.location = {tuple(source.location)}")
print(f"  Driven.location = {tuple(driven.location)}")
print(f"  Driven drivers  = "
      f"{len(driven.animation_data.drivers) if driven.animation_data else 0}")
print(f"  driver expression = {fcurve.driver.expression!r}")
print(f"  driver var[0].data_path = "
      f"{fcurve.driver.variables[0].targets[0].data_path!r} (typo'd)")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
