import json
import math
import sys
from pathlib import Path

import bmesh
import bpy


BORE_CENTERS = (
    (-1.2, -0.5),
    (0.0, -0.5),
    (1.2, -0.5),
    (-1.2, 0.5),
    (0.0, 0.5),
    (1.2, 0.5),
)


def apply_difference(plate, cutter, name):
    modifier = plate.modifiers.new(name=name, type="BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.context.view_layer.objects.active = plate
    plate.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def mesh_stats(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    boundary_edges = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    nonmanifold_edges = sum(1 for edge in bm.edges if len(edge.link_faces) != 2)
    stats = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "euler": len(bm.verts) - len(bm.edges) + len(bm.faces),
        "boundary_edges": boundary_edges,
        "nonmanifold_edges": nonmanifold_edges,
        "volume": abs(bm.calc_volume(signed=True)),
    }
    bm.free()
    return stats


def main():
    output = Path(sys.argv[sys.argv.index("--") + 1])
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.0, 0.0))
    plate = bpy.context.object
    plate.name = "Plate"
    plate.data.name = "PlateMesh"
    plate.dimensions = (4.0, 2.0, 0.2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    for index, (x, y) in enumerate(BORE_CENTERS, start=1):
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=64,
            radius=0.15,
            depth=0.4,
            location=(x, y, 0.0),
        )
        apply_difference(plate, bpy.context.object, f"ThroughBore{index:02d}")

    # Top is Z=0.1. The cutter bottom at Z=0.02 leaves a 0.12-thick floor.
    bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.0, 0.07))
    pocket = bpy.context.object
    pocket.dimensions = (2.0, 0.8, 0.10)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    apply_difference(plate, pocket, "CenteredPocket")

    bpy.context.view_layer.objects.active = plate
    plate.select_set(True)
    bpy.ops.object.shade_flat()
    plate["engiworld_task"] = "reverse-cli-blender-task-04"
    plate["bore_centers"] = json.dumps(BORE_CENTERS)
    plate["bore_diameter"] = 0.30
    plate["pocket_dimensions"] = "2.0 x 0.8 x 0.08"
    plate["generator"] = f"Blender {bpy.app.version_string} Exact Boolean"

    stats = mesh_stats(plate)
    dimensions = tuple(float(value) for value in plate.dimensions)
    if any(abs(actual - expected) > 1e-6 for actual, expected in zip(dimensions, (4.0, 2.0, 0.2))):
        raise RuntimeError(f"unexpected dimensions: {dimensions}")
    if stats["euler"] != -10 or stats["boundary_edges"] or stats["nonmanifold_edges"]:
        raise RuntimeError(f"invalid closed topology: {stats}")
    expected_volume = 1.6 - 6.0 * math.pi * 0.15**2 * 0.2 - 2.0 * 0.8 * 0.08
    if abs(stats["volume"] - expected_volume) > 0.003:
        raise RuntimeError(f"unexpected volume: {stats['volume']} vs {expected_volume}")

    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), check_existing=False)
    print("TASK04_GENERATION=" + json.dumps({
        "blender_version": bpy.app.version_string,
        "output": str(output),
        "dimensions": dimensions,
        "bore_centers": BORE_CENTERS,
        "pocket": {"size_xy": [2.0, 0.8], "depth": 0.08, "floor_z": 0.02},
        "mesh": stats,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
