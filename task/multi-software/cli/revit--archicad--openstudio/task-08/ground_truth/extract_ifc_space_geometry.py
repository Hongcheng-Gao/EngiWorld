from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any


def mesh(space: Any, settings: Any) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    import ifcopenshell.geom  # type: ignore

    shape = ifcopenshell.geom.create_shape(settings, space)
    values = list(shape.geometry.verts)
    points = [tuple(round(float(values[i + j]), 6) for j in range(3)) for i in range(0, len(values), 3)]
    faces = list(shape.geometry.faces)
    triangles = [tuple(int(faces[i + j]) for j in range(3)) for i in range(0, len(faces), 3)]
    if not points or not triangles:
        raise ValueError(f"IfcSpace {space.GlobalId} has empty geometry")
    return points, triangles


def facts(space: Any, settings: Any) -> dict[str, Any]:
    points, triangles = mesh(space, settings)
    edges: Counter[tuple[int, int]] = Counter()
    area = 0.0
    volume6 = 0.0
    for indices in triangles:
        a, b, c = (points[index] for index in indices)
        u = tuple(b[i] - a[i] for i in range(3))
        v = tuple(c[i] - a[i] for i in range(3))
        cross = (
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        )
        area += math.sqrt(sum(value * value for value in cross)) / 2.0
        volume6 += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            + a[1] * (b[2] * c[0] - b[0] * c[2])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        )
        for left, right in ((indices[0], indices[1]), (indices[1], indices[2]), (indices[2], indices[0])):
            edges[tuple(sorted((left, right)))] += 1

    bounds = [
        min(point[0] for point in points), max(point[0] for point in points),
        min(point[1] for point in points), max(point[1] for point in points),
        min(point[2] for point in points), max(point[2] for point in points),
    ]
    storeys = {
        (str(rel.RelatingObject.GlobalId), str(rel.RelatingObject.Name))
        for rel in getattr(space, "Decomposes", [])
        if getattr(rel, "RelatingObject", None) and rel.RelatingObject.is_a("IfcBuildingStorey")
    }
    if len(storeys) != 1:
        raise ValueError(f"IfcSpace {space.GlobalId} must have exactly one building-storey container")
    storey_guid, storey_name = next(iter(storeys))
    name = str(space.LongName or space.Name or "")
    width, depth, height = bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]
    return {
        "name": name,
        "ifc_guid": str(space.GlobalId),
        "storey": storey_name,
        "storey_ifc_guid": storey_guid,
        "bbox_m": bounds,
        "x_m": bounds[0],
        "y_m": bounds[2],
        "z_m": bounds[4],
        "width_m": width,
        "depth_m": depth,
        "height_m": height,
        "floor_area_m2": width * depth,
        "volume_m3": abs(volume6) / 6.0,
        "surface_area_m2": area,
        "closed": bool(edges) and all(count == 2 for count in edges.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ifc", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    import ifcopenshell  # type: ignore
    import ifcopenshell.geom  # type: ignore

    model = ifcopenshell.open(str(args.ifc))
    if model.schema != "IFC4":
        raise ValueError(f"Expected IFC4, found {model.schema}")
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    spaces = [facts(space, settings) for space in model.by_type("IfcSpace")]
    if len(spaces) != 4 or len({space["name"] for space in spaces}) != 4:
        raise ValueError("stage2.ifc must contain four uniquely named IfcSpace products")
    if not all(space["closed"] and space["volume_m3"] > 0 and space["floor_area_m2"] > 0 for space in spaces):
        raise ValueError("Every stage2 IfcSpace must be a closed, positive-volume solid")
    output = {
        "source": "stage2.ifc",
        "source_sha256": hashlib.sha256(args.ifc.read_bytes()).hexdigest(),
        "parser": "IfcOpenShell structured IFC4 geometry",
        "spaces": sorted(spaces, key=lambda space: space["name"]),
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
