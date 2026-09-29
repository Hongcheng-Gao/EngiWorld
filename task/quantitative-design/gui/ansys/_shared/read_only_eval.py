from __future__ import annotations

import hashlib
import math
import os
import re
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(os.environ.get("EVAL_ROOT", str(Path(os.environ.get("USERPROFILE", r"C:\Users\user")) / "Desktop")))
LICENSE_FILE = ROOT / "license.py"
ANSYS_EXEC = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"


class InvalidArtifact(RuntimeError):
    pass


def debug(message: str) -> None:
    if os.environ.get("EVAL_DEBUG") == "1":
        print("debug: " + message)


def clamp(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, value))


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def required_paths(names: list[str]) -> list[Path]:
    paths = [ROOT / name for name in names]
    for path in paths:
        if not path.is_file() or path.stat().st_size <= 0:
            raise FileNotFoundError(path.name)
    return paths


def hashes(paths: list[Path]) -> dict[str, str]:
    return {str(path.resolve()): digest(path) for path in paths}


def artifacts_identical(left: list[Path], right: list[Path]) -> bool:
    left_by_suffix = {path.suffix.lower(): path for path in left if path.suffix.lower() in {".db", ".rst", ".rth"}}
    right_by_suffix = {path.suffix.lower(): path for path in right if path.suffix.lower() in {".db", ".rst", ".rth"}}
    if left_by_suffix.keys() != right_by_suffix.keys():
        return False
    return all(digest(left_by_suffix[key]) == digest(right_by_suffix[key]) for key in left_by_suffix)


def check_license() -> None:
    result = subprocess.run(
        ["python", str(LICENSE_FILE)], cwd=ROOT, capture_output=True, text=True,
        timeout=120, creationflags=0x08000000,
    )
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0 or "[SUCCESS]" not in output:
        raise InvalidArtifact("ANSYS license setup failed")


def free_port(start: int) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise InvalidArtifact("no MAPDL port available")


def checked(mapdl, command: str) -> str:
    output = str(mapdl.run(command) or "")
    upper = output.upper()
    if "*** ERROR ***" in upper or "COMMAND IS IGNORED" in upper or "UNKNOWN LABEL" in upper:
        raise InvalidArtifact(command)
    return output


def close(value: float, target: float, absolute: float, relative: float = 0.0) -> bool:
    return math.isfinite(value) and abs(value - target) <= max(absolute, relative * abs(target))


def parse_constraints(text: str) -> set[tuple[int, str]]:
    return {
        (int(node), label.upper())
        for node, label in re.findall(r"(?m)^\s*(\d+)\s+(UX|UY|UZ|ROTX|ROTY|ROTZ|TEMP)\s+" + FLOAT, text)
    }


def parse_forces(text: str) -> dict[tuple[int, str], float]:
    values = {}
    for node, label, value in re.findall(r"(?m)^\s*(\d+)\s+(FX|FY|FZ|HEAT)\s+(" + FLOAT + r")", text):
        values[(int(node), label.upper())] = float(value)
    return values


def material_values(text: str) -> dict[str, float]:
    upper = text.upper()
    values = {}
    for label in ("EX", "PRXY", "DENS", "KXX"):
        match = re.search(rf"\b{label}\b\s*[=:]?\s*({FLOAT})", upper)
        if match:
            values[label] = float(match.group(1))
    return values


def require_material(text: str, expected: dict[str, float]) -> None:
    actual = material_values(text)
    for label, target in expected.items():
        if label not in actual or not close(actual[label], target, max(abs(target) * 0.005, 1.0e-12)):
            raise InvalidArtifact("material " + label)


def mesh_data(mapdl):
    numbers = [int(value) for value in mapdl.mesh.nnum]
    coordinates = [[float(item) for item in row] for row in mapdl.mesh.nodes]
    if not numbers or len(numbers) != len(coordinates):
        raise InvalidArtifact("mesh nodes")
    return numbers, coordinates, dict(zip(numbers, coordinates)), mapdl.mesh.grid


def bounds(coordinates) -> list[tuple[float, float]]:
    return [(min(row[index] for row in coordinates), max(row[index] for row in coordinates)) for index in range(3)]


def nodes_at(coordinate_by_node: dict[int, list[float]], axis: int, value: float, tolerance: float = 1.0e-5) -> set[int]:
    return {node for node, xyz in coordinate_by_node.items() if abs(xyz[axis] - value) <= tolerance}


def complete_interval(coordinate_by_node, nodes: set[int], axis: int, lo: float, hi: float, max_gap: float) -> bool:
    values = sorted({round(coordinate_by_node[node][axis], 8) for node in nodes})
    if not values or abs(values[0] - lo) > 1.0e-5 or abs(values[-1] - hi) > 1.0e-5:
        return False
    return all(right - left <= max_gap * 1.01 for left, right in zip(values, values[1:]))


def connected(grid) -> bool:
    cells = [int(value) for value in grid.cells]
    point_count = int(grid.n_points)
    parent = list(range(point_count))

    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left, right):
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    used = set()
    index = 0
    while index < len(cells):
        count = cells[index]
        points = cells[index + 1:index + 1 + count]
        if count <= 0 or len(points) != count:
            raise InvalidArtifact("cell connectivity")
        used.update(points)
        for point in points[1:]:
            union(points[0], point)
        index += count + 1
    return bool(used) and len({find(point) for point in used}) == 1


def maximum_mesh_edge(grid) -> float:
    edges = grid.extract_all_edges().compute_cell_sizes(length=True, area=False, volume=False)
    lengths = edges.cell_data.get("Length")
    if lengths is None or len(lengths) == 0:
        raise InvalidArtifact("mesh edge lengths")
    return max(float(value) for value in lengths)


def geometric_measure(grid, dimension: int) -> float:
    sized = grid.compute_cell_sizes(length=True, area=True, volume=True)
    key = {1: "Length", 2: "Area", 3: "Volume"}[dimension]
    values = sized.cell_data.get(key)
    if values is None:
        raise InvalidArtifact("geometric measure")
    total = sum(float(value) for value in values)
    if not math.isfinite(total) or total <= 0:
        raise InvalidArtifact("geometric measure")
    return total


def raster_occupancy(grid, ranges: tuple[tuple[float, float], ...], spacing: float):
    import numpy as np
    from vtkmodules.vtkCommonDataModel import vtkStaticCellLocator

    axes = [np.arange(lo + spacing / 2.0, hi, spacing) for lo, hi in ranges]
    locator = vtkStaticCellLocator()
    locator.SetDataSet(grid)
    locator.BuildLocator()
    occupied = np.zeros(tuple(len(axis) for axis in axes), dtype=bool)
    if len(ranges) == 2:
        for x_index, x_value in enumerate(axes[0]):
            for y_index, y_value in enumerate(axes[1]):
                occupied[x_index, y_index] = locator.FindCell(
                    (float(x_value), float(y_value), 0.0)
                ) >= 0
    else:
        for x_index, x_value in enumerate(axes[0]):
            for y_index, y_value in enumerate(axes[1]):
                for z_index, z_value in enumerate(axes[2]):
                    occupied[x_index, y_index, z_index] = locator.FindCell(
                        (float(x_value), float(y_value), float(z_value))
                    ) >= 0
    return axes, occupied


def require_2d_width_path(grid, ranges, minimum_width: float, spacing: float = 0.5) -> None:
    import numpy as np
    from scipy.ndimage import distance_transform_edt, label

    axes, occupied = raster_occupancy(grid, ranges, spacing)
    distance = distance_transform_edt(np.pad(occupied, 1), sampling=spacing)[1:-1, 1:-1]
    core = distance >= minimum_width / 2.0 - spacing * 0.1
    groups, count = label(core, structure=np.ones((3, 3), dtype=int))
    left_limit = ranges[0][0] + minimum_width / 2.0 + spacing
    right_limit = ranges[0][1] - minimum_width / 2.0 - spacing
    for group in range(1, count + 1):
        x_indices = np.where(groups == group)[0]
        if (
            len(x_indices)
            and axes[0][int(x_indices.min())] <= left_limit
            and axes[0][int(x_indices.max())] >= right_limit
        ):
            return
    raise InvalidArtifact("minimum two-dimensional path width")


def require_3d_width_path(
    grid,
    ranges,
    minimum_width: float,
    preserved_depth: float,
    spacing: float = 1.0,
) -> None:
    import numpy as np
    from scipy.ndimage import distance_transform_edt, label

    axes, occupied = raster_occupancy(grid, ranges, spacing)
    left = axes[0] < ranges[0][0] + preserved_depth
    right = axes[0] > ranges[0][1] - preserved_depth
    if not occupied[left].all() or not occupied[right].all():
        raise InvalidArtifact("preserved end-interface volume")

    core = np.zeros_like(occupied)
    for x_index in range(occupied.shape[0]):
        transverse_distance = distance_transform_edt(
            np.pad(occupied[x_index], 1), sampling=spacing
        )[1:-1, 1:-1]
        core[x_index] = transverse_distance >= minimum_width / 2.0 - spacing * 0.1
    groups, count = label(core, structure=np.ones((3, 3, 3), dtype=int))
    for group in range(1, count + 1):
        x_indices = np.where(groups == group)[0]
        if len(x_indices) and int(x_indices.min()) == 0 and int(x_indices.max()) == len(axes[0]) - 1:
            return
    raise InvalidArtifact("minimum three-dimensional path width")


def plane_thickness_by_real_set(text: str) -> dict[int, float]:
    return {
        int(set_number): float(value)
        for set_number, value in re.findall(
            r"REAL CONSTANT SET\s+(\d+)\s+ITEMS\s+1(?:\s+TO\s+\d+)?\s*\n\s*(" + FLOAT + r")",
            text,
            flags=re.S,
        )
    }


def require_plane_thickness(text: str, expected: float, grid=None) -> None:
    thicknesses = plane_thickness_by_real_set(text)
    if not thicknesses:
        raise InvalidArtifact("plane thickness")
    used_sets = set(thicknesses)
    if grid is not None:
        values = grid.cell_data.get("ansys_real_constant")
        if values is None or len(values) == 0:
            raise InvalidArtifact("plane real-constant assignment")
        used_sets = {int(value) for value in values}
    if any(
        set_number not in thicknesses
        or not close(thicknesses[set_number], expected, 1.0e-6)
        for set_number in used_sets
    ):
        raise InvalidArtifact("plane thickness")


def face_axis_weights(values: list[float]) -> dict[float, float]:
    ordered = sorted(set(values))
    if len(ordered) < 2:
        return {}
    weights = {}
    for index, value in enumerate(ordered):
        left = value if index == 0 else (ordered[index - 1] + value) / 2.0
        right = value if index == len(ordered) - 1 else (value + ordered[index + 1]) / 2.0
        weights[value] = right - left
    return weights


def tensor_face_tributary_weights(
    coordinate_by_node: dict[int, list[float]],
    nodes: set[int],
    axes: tuple[int, int],
) -> dict[int, float]:
    coordinate_keys = {
        node: tuple(round(coordinate_by_node[node][axis], 8) for axis in axes)
        for node in nodes
    }
    if len(set(coordinate_keys.values())) != len(nodes):
        return {}
    axis_values = [sorted({key[index] for key in coordinate_keys.values()}) for index in range(2)]
    if len(nodes) != len(axis_values[0]) * len(axis_values[1]):
        return {}
    if set(coordinate_keys.values()) != {
        (first, second) for first in axis_values[0] for second in axis_values[1]
    }:
        return {}
    first_weights = face_axis_weights(axis_values[0])
    second_weights = face_axis_weights(axis_values[1])
    return {
        node: first_weights[key[0]] * second_weights[key[1]]
        for node, key in coordinate_keys.items()
    }


def triangular_face_tributary_weights(
    coordinate_by_node: dict[int, list[float]],
    nodes: set[int],
    axes: tuple[int, int],
) -> dict[int, float]:
    import numpy as np
    from scipy.spatial import Delaunay

    ordered_nodes = sorted(nodes)
    points = np.asarray(
        [[coordinate_by_node[node][axis] for axis in axes] for node in ordered_nodes],
        dtype=float,
    )
    if len(points) < 3 or not np.isfinite(points).all():
        return {}
    try:
        triangles = Delaunay(points).simplices
    except Exception:
        return {}
    weights = {node: 0.0 for node in ordered_nodes}
    for triangle in triangles:
        first, second, third = points[triangle]
        first_edge = second - first
        second_edge = third - first
        area = abs(float(first_edge[0] * second_edge[1] - first_edge[1] * second_edge[0])) / 2.0
        for point_index in triangle:
            weights[ordered_nodes[int(point_index)]] += area / 3.0
    span_area = float(np.ptp(points[:, 0]) * np.ptp(points[:, 1]))
    if span_area <= 0 or not close(sum(weights.values()), span_area, span_area * 1.0e-4):
        return {}
    return weights


def distribution_matches(
    magnitudes: dict[int, float],
    weights: dict[int, float],
    relative_tolerance: float = 0.2,
    absolute_fraction_tolerance: float = 0.0025,
) -> bool:
    if magnitudes.keys() != weights.keys():
        return False
    magnitude_total = sum(magnitudes.values())
    weight_total = sum(weights.values())
    if magnitude_total <= 0 or weight_total <= 0:
        return False
    for node, magnitude in magnitudes.items():
        actual = magnitude / magnitude_total
        target = weights[node] / weight_total
        if abs(actual - target) > max(absolute_fraction_tolerance, relative_tolerance * target):
            return False
    return True


def require_uniform_face_force(
    forces: dict[tuple[int, str], float],
    coordinate_by_node: dict[int, list[float]],
    nodes: set[int],
    label: str,
    total: float,
    axes: tuple[int, int],
) -> None:
    if any(not math.isfinite(value) for value in forces.values()):
        raise InvalidArtifact("finite force values")
    nonzero = {
        (node, force_label): value
        for (node, force_label), value in forces.items()
        if math.isfinite(value) and abs(value) > 1.0e-12
    }
    if any(node not in nodes or force_label != label for node, force_label in nonzero):
        raise InvalidArtifact("loaded-face-only force")
    values = {node: forces.get((node, label)) for node in nodes}
    if any(value is None or not math.isfinite(value) or value * total <= 0 for value in values.values()):
        raise InvalidArtifact("complete loaded-face force")
    if not close(sum(values.values()), total, max(abs(total) * 0.005, 1.0e-6)):
        raise InvalidArtifact("distributed end load total")
    magnitudes = {node: abs(value) for node, value in values.items()}
    candidates = [
        {node: 1.0 for node in nodes},
        tensor_face_tributary_weights(coordinate_by_node, nodes, axes),
        triangular_face_tributary_weights(coordinate_by_node, nodes, axes),
    ]
    if not any(weights and distribution_matches(magnitudes, weights) for weights in candidates):
        raise InvalidArtifact("uniform loaded-face distribution")


def require_plate_result(displacement: float, stress: float) -> None:
    if (
        not 0.0001 < displacement <= 0.8
        or not math.isfinite(stress)
        or not 0.0 <= stress <= 160.0
    ):
        raise InvalidArtifact("plate result")


def result_input_forces(result, result_set: int = 0) -> dict[tuple[int, str], float]:
    labels = {1: "FX", 2: "FY", 3: "FZ", 4: "MX", 5: "MY", 6: "MZ"}
    node_numbers, dof_numbers, values = result.nodal_input_force(result_set)
    forces = {}
    for node, dof, value in zip(node_numbers, dof_numbers, values):
        label = labels.get(int(dof))
        if label is not None:
            key = (int(node), label)
            forces[key] = forces.get(key, 0.0) + float(value)
    return forces


def section_data(text: str) -> dict[str, float | str | list[float]]:
    upper = text.upper()
    if "HOLLOW RECTANGLE" in upper or " HREC" in upper:
        section_type = "HREC"
    elif "RECTANGLE" in upper or " RECT" in upper:
        section_type = "RECT"
    else:
        section_type = ""
    named = {}
    for label in ("AREA", "IYY", "IZZ", "IYZ"):
        match = re.search(rf"\b{label}\b\s*[=:]?\s*({FLOAT})", upper)
        if match:
            named[label.lower()] = abs(float(match.group(1)))
    dimensions = []
    coordinate_match = re.search(
        r"BEAM SECTION CELLS NODAL COORDINATES(.*?)BEAM SECTION CELL CONNECTIVITY",
        upper,
        flags=re.S,
    )
    if coordinate_match:
        points = []
        for line in coordinate_match.group(1).splitlines():
            match = re.match(rf"\s*\d+\s+({FLOAT})\s+({FLOAT})\s*$", line)
            if match:
                points.append((float(match.group(1)), float(match.group(2))))
        if points:
            width = max(point[0] for point in points) - min(point[0] for point in points)
            height = max(point[1] for point in points) - min(point[1] for point in points)
            dimensions = [width, height]
            if section_type == "HREC" and named.get("area", 0.0) > 0:
                discriminant = (width + height) ** 2 - 4.0 * float(named["area"])
                if discriminant >= 0:
                    dimensions.append(((width + height) - math.sqrt(discriminant)) / 4.0)
    return {"type": section_type, "dimensions": dimensions, **named}


def section_inertia(section: dict) -> float:
    if section.get("iyy", 0.0) > 0 and section.get("izz", 0.0) > 0:
        return min(float(section["iyy"]), float(section["izz"]))
    dimensions = section.get("dimensions", [])
    if len(dimensions) < 2:
        raise InvalidArtifact("section inertia")
    width, height = abs(dimensions[0]), abs(dimensions[1])
    if section.get("type") == "RECT":
        return min(width * height**3, height * width**3) / 12.0
    if len(dimensions) < 3:
        raise InvalidArtifact("HREC dimensions")
    thickness = min(abs(value) for value in dimensions[2:])
    inner_width = width - 2.0 * thickness
    inner_height = height - 2.0 * thickness
    if inner_width <= 0 or inner_height <= 0:
        raise InvalidArtifact("HREC thickness")
    return min(width * height**3 - inner_width * inner_height**3, height * width**3 - inner_height * inner_width**3) / 12.0


def section_area(section: dict) -> float:
    if section.get("area", 0.0) > 0:
        return float(section["area"])
    dimensions = section.get("dimensions", [])
    if len(dimensions) < 2:
        raise InvalidArtifact("section area")
    width, height = abs(dimensions[0]), abs(dimensions[1])
    if section.get("type") == "RECT":
        return width * height
    if len(dimensions) < 3:
        raise InvalidArtifact("HREC dimensions")
    walls = [abs(value) for value in dimensions[2:]]
    if len(walls) == 1:
        left = right = top = bottom = walls[0]
    elif len(walls) >= 4:
        top, bottom, left, right = walls[:4]
    else:
        left = right = walls[0]
        top = bottom = walls[1]
    inner_width = width - left - right
    inner_height = height - top - bottom
    if inner_width <= 0 or inner_height <= 0:
        raise InvalidArtifact("HREC area")
    return width * height - inner_width * inner_height


def validate_section(section: dict, area: float, config: dict) -> None:
    if section.get("type") not in {"RECT", "HREC"}:
        raise InvalidArtifact("section type")
    if not config["area"][0] <= area <= config["area"][1]:
        raise InvalidArtifact("section area")
    dimensions = section.get("dimensions", [])
    if len(dimensions) < 2:
        raise InvalidArtifact("section dimensions")
    for value in dimensions[:2]:
        if not config["outer"][0] <= abs(value) <= config["outer"][1]:
            raise InvalidArtifact("outer section dimension")
    if section.get("type") == "HREC":
        if len(dimensions) < 3:
            raise InvalidArtifact("wall thickness")
        walls = [abs(value) for value in dimensions[2:]]
        if any(not config["wall"][0] <= value <= config["wall"][1] for value in walls):
            raise InvalidArtifact("wall thickness")


def reaction(mapdl, nodes: set[int], label: str) -> float:
    values = []
    for node in nodes:
        value = float(mapdl.get_value("NODE", node, "RF", label))
        if math.isfinite(value):
            values.append(value)
    if not values:
        raise InvalidArtifact("reaction " + label)
    return sum(values)


def result_pair(mapdl, root: Path, suffix: str, database_nodes: set[int], mode: bool = False) -> None:
    mapdl.finish()
    mapdl.post1()
    mapdl.file(str((root / "case").resolve()), suffix.lstrip("."))
    if mode:
        mapdl.set(1, 1)
    else:
        mapdl.set("LAST")
    result_nodes = set(int(value) for value in mapdl.result.mesh.nnum)
    if result_nodes != database_nodes:
        raise InvalidArtifact("database/result node mismatch")


def verify_result_metadata(mapdl, database_materials: str, database_section: dict | None = None) -> None:
    result_materials = mapdl.result.materials
    if not isinstance(result_materials, dict) or not result_materials:
        raise InvalidArtifact("result material metadata")
    result_material = next(iter(result_materials.values()))
    if not isinstance(result_material, dict):
        raise InvalidArtifact("result material metadata")
    database_values = material_values(database_materials)
    aliases = {"PRXY": ("PRXY", "NUXY")}
    for label, target in database_values.items():
        keys = aliases.get(label, (label,))
        matches = [float(result_material[key]) for key in keys if key in result_material]
        tolerance = max(abs(target) * 1.0e-6, 1.0e-12)
        if not matches or not any(close(value, target, tolerance) for value in matches):
            raise InvalidArtifact("database/result material mismatch")

    if database_section is None:
        return
    result_sections = mapdl.result.section_data
    if not isinstance(result_sections, dict) or not result_sections:
        raise InvalidArtifact("result section metadata")
    values = next(iter(result_sections.values()))
    if len(values) < 14:
        raise InvalidArtifact("result section metadata")
    area = section_area(database_section)
    if not close(float(values[6]), area, max(area * 1.0e-5, 1.0e-6)):
        raise InvalidArtifact("database/result section area mismatch")
    for label, index in (("iyy", 11), ("izz", 13)):
        target = float(database_section.get(label, 0.0))
        if target > 0 and not close(float(values[index]), target, max(target * 1.0e-5, 1.0e-6)):
            raise InvalidArtifact("database/result section inertia mismatch")


def validate_plate(mapdl, common: dict, constraints: set, forces: dict, config: dict) -> dict:
    numbers, coordinates, by_node, grid = common["mesh"]
    model_bounds = bounds(coordinates)
    if not all(close(model_bounds[index][side], target, 1.0e-4) for index, expected in enumerate(((0.0, 100.0), (0.0, 200.0))) for side, target in enumerate(expected)):
        raise InvalidArtifact("plate envelope")
    if int(mapdl.get_value("ELEM", 0, "COUNT")) < 400 or "PLANE183" not in common["elements"] or not any(label in common["elements"] for label in ("PLANE STRESS", "PLANE STRS")):
        raise InvalidArtifact("plate elements")
    require_material(common["materials"], {"EX": 210000.0, "PRXY": 0.3, "DENS": 7.85e-9})
    require_plane_thickness(common["real_constants"], 1.0, grid)
    if not connected(grid) or maximum_mesh_edge(grid) > 5.25:
        raise InvalidArtifact("plate mesh")
    require_2d_width_path(grid, ((0.0, 100.0), (0.0, 200.0)), 10.0)
    left, right = nodes_at(by_node, 0, 0.0), nodes_at(by_node, 0, 100.0)
    if not complete_interval(by_node, left, 1, 0.0, 200.0, 5.0) or not complete_interval(by_node, right, 1, 0.0, 200.0, 5.0):
        raise InvalidArtifact("plate interfaces")
    left_force = sum(value for (node, label), value in forces.items() if node in left and label == "FX")
    right_force = sum(value for (node, label), value in forces.items() if node in right and label == "FX")
    if not close(left_force, -2000.0, 20.0) or not close(right_force, 2000.0, 20.0):
        raise InvalidArtifact("plate traction")
    constrained_nodes = {node for node, _ in constraints}
    if len(constrained_nodes) < 2 or not any((node, "UX") in constraints and (node, "UY") in constraints for node in constrained_nodes):
        raise InvalidArtifact("rigid-body constraints")
    volume = geometric_measure(grid, 2)
    result_pair(mapdl, common["root"], ".rst", set(numbers))
    require_plane_thickness(common["real_constants"], 1.0, mapdl.result.grid)
    verify_result_metadata(mapdl, common["materials"])
    displacement = max(abs(float(value)) for value in mapdl.post_processing.nodal_displacement("NORM"))
    stress = max(abs(float(value)) for value in mapdl.post_processing.nodal_eqv_stress())
    require_plate_result(displacement, stress)
    return {"mass": volume * 7.85e-9, "displacement": displacement, "stress": stress}


def validate_beam_buckling(mapdl, common: dict, constraints: set, forces: dict, config: dict) -> dict:
    numbers, coordinates, by_node, grid = common["mesh"]
    model_bounds = bounds(coordinates)
    if not (close(model_bounds[0][0], 0.0, 1.0e-6) and close(model_bounds[0][1], 0.0, 1.0e-6) and close(model_bounds[1][0], 0.0, 1.0e-6) and close(model_bounds[1][1], 1000.0, 1.0e-4)):
        raise InvalidArtifact("buckling axis")
    if len(numbers) != 41 or int(mapdl.get_value("ELEM", 0, "COUNT")) != 40 or "BEAM188" not in common["elements"] or not connected(grid):
        raise InvalidArtifact("buckling mesh")
    require_material(common["materials"], {"EX": 210000.0, "PRXY": 0.3, "DENS": 7.85e-9})
    section = section_data(common["sections"])
    area = section_area(section)
    validate_section(section, area, config["section"])
    bottom, top = nodes_at(by_node, 1, 0.0), nodes_at(by_node, 1, 1000.0)
    if len(bottom) != 1 or len(top) != 1:
        raise InvalidArtifact("buckling endpoints")
    bottom_node, top_node = next(iter(bottom)), next(iter(top))
    if any((bottom_node, dof) not in constraints for dof in ("UX", "UY", "UZ")):
        raise InvalidArtifact("bottom pin")
    if (top_node, "UX") not in constraints or (top_node, "UZ") not in constraints or (top_node, "UY") in constraints:
        raise InvalidArtifact("top pin")
    if not close(forces.get((top_node, "FY"), float("nan")), -1.0, 1.0e-4):
        raise InvalidArtifact("buckling load")
    result_pair(mapdl, common["root"], ".rst", set(numbers), mode=True)
    verify_result_metadata(mapdl, common["materials"], section)
    factor = float(mapdl.get_value("MODE", 1, "FREQ"))
    inertia = section_inertia(section)
    expected = math.pi**2 * 210000.0 * inertia / 1000.0**2
    if factor <= 0 or abs(factor - expected) > 0.12 * expected:
        raise InvalidArtifact("buckling result")
    lateral = max(
        max(abs(float(value)) for value in mapdl.post_processing.nodal_displacement("X")),
        max(abs(float(value)) for value in mapdl.post_processing.nodal_displacement("Z")),
    )
    if lateral <= 1.0e-9:
        raise InvalidArtifact("buckling mode shape")
    return {"mass": area * 1000.0 * 7.85e-9, "factor": factor}


def validate_beam_modal(mapdl, common: dict, constraints: set, forces: dict, config: dict) -> dict:
    numbers, coordinates, by_node, grid = common["mesh"]
    model_bounds = bounds(coordinates)
    if not (close(model_bounds[0][0], 0.0, 1.0e-6) and close(model_bounds[0][1], 500.0, 1.0e-4) and close(model_bounds[1][0], 0.0, 1.0e-6) and close(model_bounds[1][1], 0.0, 1.0e-6)):
        raise InvalidArtifact("modal axis")
    if len(numbers) != 21 or int(mapdl.get_value("ELEM", 0, "COUNT")) != 20 or "BEAM188" not in common["elements"] or not connected(grid):
        raise InvalidArtifact("modal mesh")
    require_material(common["materials"], {"EX": 210000.0, "PRXY": 0.3, "DENS": 7.85e-9})
    section = section_data(common["sections"])
    area = section_area(section)
    validate_section(section, area, config["section"])
    for endpoint in (next(iter(nodes_at(by_node, 0, 0.0))), next(iter(nodes_at(by_node, 0, 500.0)))):
        if any((endpoint, dof) not in constraints for dof in ("UX", "UY", "UZ", "ROTX", "ROTY", "ROTZ")):
            raise InvalidArtifact("fixed modal end")
    if forces:
        raise InvalidArtifact("modal load")
    result_pair(mapdl, common["root"], ".rst", set(numbers), mode=True)
    verify_result_metadata(mapdl, common["materials"], section)
    frequency = float(mapdl.get_value("MODE", 1, "FREQ"))
    inertia = section_inertia(section)
    expected = 4.730040744862704**2 / (2.0 * math.pi * 500.0**2) * math.sqrt(210000.0 * inertia / (7.85e-9 * area))
    if frequency <= 0 or abs(frequency - expected) > 0.15 * expected:
        raise InvalidArtifact("modal result")
    return {"mass": area * 500.0 * 7.85e-9, "frequency": frequency}


def validate_thermal(mapdl, common: dict, constraints: set, forces: dict, config: dict) -> dict:
    numbers, coordinates, by_node, grid = common["mesh"]
    model_bounds = bounds(coordinates)
    if not all(close(model_bounds[index][side], target, 1.0e-4) for index, expected in enumerate(((0.0, 100.0), (0.0, 60.0))) for side, target in enumerate(expected)):
        raise InvalidArtifact("thermal envelope")
    if not any(name in common["elements"] for name in ("PLANE55", "PLANE77")) or not connected(grid):
        raise InvalidArtifact("thermal elements")
    require_material(common["materials"], {"KXX": 0.05})
    require_plane_thickness(common["real_constants"], 1.0, grid)
    area = geometric_measure(grid, 2)
    if area > 1500.0 or maximum_mesh_edge(grid) > 2.1:
        raise InvalidArtifact("thermal material or mesh")
    require_2d_width_path(grid, ((0.0, 100.0), (0.0, 60.0)), 5.0)
    sink = {node for node in nodes_at(by_node, 0, 0.0) if -1.0e-5 <= by_node[node][1] <= 10.00001}
    source = {node for node in nodes_at(by_node, 0, 100.0) if 49.99999 <= by_node[node][1] <= 60.00001}
    if not complete_interval(by_node, sink, 1, 0.0, 10.0, 2.0) or not complete_interval(by_node, source, 1, 50.0, 60.0, 2.0):
        raise InvalidArtifact("thermal interfaces")
    if any((node, "TEMP") not in constraints for node in sink):
        raise InvalidArtifact("sink temperature")
    source_heat = sum(value for (node, label), value in forces.items() if node in source and label == "HEAT")
    if not close(source_heat, 1.0, 0.005):
        raise InvalidArtifact("source heat")
    result_pair(mapdl, common["root"], ".rth", set(numbers))
    require_plane_thickness(common["real_constants"], 1.0, mapdl.result.grid)
    verify_result_metadata(mapdl, common["materials"])
    source_temperature = sum(float(mapdl.get_value("NODE", node, "TEMP")) for node in source) / len(source)
    sink_temperature = sum(float(mapdl.get_value("NODE", node, "TEMP")) for node in sink) / len(sink)
    heat_reaction = reaction(mapdl, sink, "HEAT")
    if not close(sink_temperature, 20.0, 0.05) or source_temperature <= sink_temperature or not close(abs(heat_reaction), 1.0, 0.02):
        raise InvalidArtifact("thermal result or balance")
    return {"area": area, "resistance": source_temperature - 20.0}


def validate_cantilever(mapdl, common: dict, constraints: set, forces: dict, config: dict) -> dict:
    numbers, coordinates, by_node, grid = common["mesh"]
    model_bounds = bounds(coordinates)
    expected = ((0.0, 100.0), (0.0, 20.0), (0.0, 20.0))
    if any(not close(model_bounds[index][side], target, 1.0e-4) for index, pair in enumerate(expected) for side, target in enumerate(pair)):
        raise InvalidArtifact("cantilever envelope")
    if "SOLID185" not in common["elements"] or not connected(grid) or maximum_mesh_edge(grid) > 5.25:
        raise InvalidArtifact("cantilever mesh")
    require_3d_width_path(
        grid,
        ((0.0, 100.0), (0.0, 20.0), (0.0, 20.0)),
        minimum_width=4.0,
        preserved_depth=10.0,
    )
    require_material(common["materials"], {"EX": 210000.0, "PRXY": 0.3, "DENS": 7.85e-9})
    fixed, loaded = nodes_at(by_node, 0, 0.0), nodes_at(by_node, 0, 100.0)
    for face in (fixed, loaded):
        if not complete_interval(by_node, face, 1, 0.0, 20.0, 5.0) or not complete_interval(by_node, face, 2, 0.0, 20.0, 5.0):
            raise InvalidArtifact("cantilever interface")
    if any(any((node, dof) not in constraints for dof in ("UX", "UY", "UZ")) for node in fixed):
        raise InvalidArtifact("cantilever support")
    require_uniform_face_force(forces, by_node, loaded, "FY", -500.0, (1, 2))
    volume = geometric_measure(grid, 3)
    result_pair(mapdl, common["root"], ".rst", set(numbers))
    result_forces = result_input_forces(mapdl.result)
    require_uniform_face_force(result_forces, by_node, loaded, "FY", -500.0, (1, 2))
    if any(
        key not in result_forces or not close(result_forces[key], value, max(abs(value) * 1.0e-5, 1.0e-8))
        for key, value in forces.items()
        if abs(value) > 1.0e-12
    ):
        raise InvalidArtifact("database/result force mismatch")
    verify_result_metadata(mapdl, common["materials"])
    average_uy = sum(float(mapdl.get_value("NODE", node, "U", "Y")) for node in loaded) / len(loaded)
    stress = max(abs(float(value)) for value in mapdl.post_processing.nodal_eqv_stress())
    support_reaction = reaction(mapdl, fixed, "FY")
    if not -10.0 < average_uy < -1.0e-5 or stress <= 0 or stress > 160.0 or not close(abs(support_reaction), 500.0, 10.0):
        raise InvalidArtifact("cantilever result")
    return {"mass": volume * 7.85e-9, "average_uy": average_uy, "stress": stress}


VALIDATORS = {
    "plate_mass": validate_plate,
    "beam_buckling": validate_beam_buckling,
    "beam_modal": validate_beam_modal,
    "thermal_path": validate_thermal,
    "solid_cantilever": validate_cantilever,
}


def inspect(paths: list[Path], config: dict, port_seed: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="ansys_read_only_eval_", ignore_cleanup_errors=True) as temp:
        case_root = Path(temp)
        result_suffix = config["result_suffix"]
        for path in paths:
            if path.suffix.lower() == ".db":
                shutil.copy2(path, case_root / "case.db")
            elif path.suffix.lower() == result_suffix:
                shutil.copy2(path, case_root / ("case" + result_suffix))
        if not (case_root / "case.db").is_file() or not (case_root / ("case" + result_suffix)).is_file():
            raise InvalidArtifact("native pair")

        check_license()
        from ansys.mapdl.core import launch_mapdl

        mapdl = launch_mapdl(
            exec_file=ANSYS_EXEC, run_location=str(case_root), jobname="read_only_eval", nproc=1,
            port=free_port(port_seed), override=True, cleanup_on_exit=True,
        )
        try:
            mapdl.resume(str((case_root / "case").resolve()), "db")
            mapdl.prep7()
            mapdl.allsel()
            common = {
                "root": case_root,
                "mesh": mesh_data(mapdl),
                "elements": checked(mapdl, "ETLIST,ALL").upper(),
                "materials": checked(mapdl, "MPLIST,ALL").upper(),
                "sections": checked(mapdl, "SLIST,ALL,,,FULL").upper() if config["kind"].startswith("beam_") else "",
                "real_constants": checked(mapdl, "RLIST,ALL").upper()
                if config["kind"] in {"plate_mass", "thermal_path"}
                else "",
            }
            constraints = parse_constraints(checked(mapdl, "DLIST,ALL,ALL"))
            force_output = checked(mapdl, "FLIST,ALL,ALL")
            forces = parse_forces(force_output)
            return VALIDATORS[config["kind"]](mapdl, common, constraints, forces, config)
        finally:
            try:
                mapdl.exit(force=True)
            except Exception:
                pass


def raw_metric(metrics: dict, config: dict) -> float:
    kind = config["kind"]
    if kind == "plate_mass":
        return metrics["mass"]
    if kind == "beam_buckling":
        return metrics["factor"] / metrics["mass"]
    if kind == "beam_modal":
        return metrics["frequency"] / metrics["mass"]
    if kind == "thermal_path":
        return metrics["resistance"]
    if kind == "solid_cantilever":
        stiffness = 500.0 / abs(metrics["average_uy"])
        return stiffness / metrics["mass"]
    raise InvalidArtifact("metric kind")


def score(submitted: float, baseline: float, direction: str) -> float:
    if submitted <= 0 or baseline <= 0 or not math.isfinite(submitted) or not math.isfinite(baseline):
        return 0.0
    if direction == "minimize":
        return clamp(1.0 - submitted / baseline)
    return clamp(1.0 - baseline / submitted)


def evaluate(config: dict) -> float:
    baseline_paths = required_paths(config["baseline_files"])
    submission_paths = required_paths(config["submission_files"])
    observed_paths = baseline_paths + submission_paths
    before = hashes(observed_paths)
    try:
        if artifacts_identical(baseline_paths, submission_paths):
            result = 0.0
        else:
            base_metrics = inspect(baseline_paths, config, config["port_seed"])
            submitted_metrics = inspect(submission_paths, config, config["port_seed"] + 100)
            result = score(raw_metric(submitted_metrics, config), raw_metric(base_metrics, config), config["direction"])
    finally:
        after = hashes(observed_paths)
        if before != after:
            raise InvalidArtifact("artifact hash changed")
    return result


def main(config: dict) -> int:
    try:
        value = evaluate(config)
    except Exception as exc:
        debug(str(exc))
        value = 0.0
    print(f"{clamp(float(value)):.6f}")
    return 0
