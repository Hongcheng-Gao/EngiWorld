#!/usr/bin/env python3
import csv
import json
import math
from pathlib import Path
import subprocess
import tempfile


DESKTOP = Path("/home/user/Desktop")

SPEC = {'required_outputs': {'result.osm': 500, 'result.csv': 10}, 'openstudio_version_prefix': '3.10', 'object_counts': {'OS:BuildingStory': 1, 'OS:Space': 5, 'OS:ThermalZone': 5, 'OS:Surface': 33, 'OS:SubSurface': 8, 'OS:ZoneHVAC:IdealLoadsAirSystem': 5, 'OS:ZoneHVAC:EquipmentList': 5, 'OS:ThermostatSetpoint:DualSetpoint': 5, 'OS:People': 4, 'OS:Lights': 4}, 'space_names': ['Classroom-A', 'Classroom-B', 'Teacher-Office', 'Restroom', 'Corridor'], 'surface_counts': {'Floor': 5, 'RoofCeiling': 5, 'Wall': 23}, 'outside_boundary_counts': {'Ground': 5, 'Outdoors': 18, 'Surface': 10}, 'window_count': 8, 'fixed_window_count': 8, 'bbox_spans_m': [24.0, 10.0, 3.2], 'floor_area_m2': 208.0, 'exterior_wall_area_m2': 268.8, 'window_area_m2': 56.32, 'require_space_links': True, 'hvac': {'ideal_loads': 5, 'equipment_lists': 5, 'thermostats': 5}, 'csv': {'headers': ['space_name', 'thermal_zone_name', 'floor_area_m2', 'people_per_m2'], 'rows': [{'space_name': 'Classroom-A', 'thermal_zone_name': 'Classroom-A Zone', 'floor_area_m2': 64.0, 'people_per_m2': 0.055}, {'space_name': 'Classroom-B', 'thermal_zone_name': 'Classroom-B Zone', 'floor_area_m2': 64.0, 'people_per_m2': 0.055}, {'space_name': 'Teacher-Office', 'thermal_zone_name': 'Teacher-Office Zone', 'floor_area_m2': 16.0, 'people_per_m2': 0.05}, {'space_name': 'Corridor', 'thermal_zone_name': 'Corridor Zone', 'floor_area_m2': 48.0, 'people_per_m2': 0.005}, {'space_name': 'Restroom', 'thermal_zone_name': 'Restroom Zone', 'floor_area_m2': 16.0, 'people_per_m2': 0.02}], 'numeric_tolerance': 0.001}}
WINDOW_TYPES = {"FixedWindow", "OperableWindow", "GlassDoor", "Skylight"}


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def approx(actual, expected, abs_tol, rel_tol=0.0):
    return abs(float(actual) - float(expected)) <= max(float(abs_tol), abs(float(expected)) * float(rel_tol))



def parse_float(value):
    text = str(value).strip()
    if not text or text.lower() == "autosize":
        raise ValueError(text)
    return float(text)


OPENSTUDIO_DUMP_RUBY = r"""
require 'openstudio'
require 'json'

path = ARGV[0]
loaded = OpenStudio::IdfFile.load(path)
if loaded.empty?
  STDERR.puts("OpenStudio could not load #{path}")
  exit 2
end
idf = loaded.get
objects = []
version = idf.versionObject
objects << version.get unless version.empty?
objects.concat(idf.objects)
objects = objects.map do |object|
  fields = []
  (0...object.numFields).each do |index|
    fields << object.getField(index).to_s
  end
  {"type" => object.iddObject.name.to_s, "fields" => fields}
end
STDOUT.write(JSON.generate(objects))
"""


def parse_osm(path):
    with tempfile.NamedTemporaryFile("w", suffix=".rb", delete=False, encoding="utf-8") as script:
        script.write(OPENSTUDIO_DUMP_RUBY)
        script_path = Path(script.name)
    try:
        proc = subprocess.run(
            ["openstudio", "execute_ruby_script", str(script_path), str(path)],
            text=True,
            capture_output=True,
            timeout=30,
        )
    finally:
        script_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise ValueError(proc.stderr.strip() or proc.stdout.strip() or "OpenStudio failed to parse OSM")
    payload = proc.stdout.strip()
    start = payload.find("[")
    if start > 0:
        payload = payload[start:]
    return json.loads(payload)


def by_type(objects, object_type):
    return [obj for obj in objects if obj["type"] == object_type]


def handle(obj):
    return obj["fields"][0] if obj["fields"] else ""


def name(obj):
    return obj["fields"][1] if len(obj["fields"]) > 1 else ""


def parse_vertices(fields, start_index):
    values = [parse_float(v) for v in fields[start_index:]]
    if len(values) % 3 != 0 or not values:
        raise ValueError("invalid vertices")
    return [(values[i], values[i + 1], values[i + 2]) for i in range(0, len(values), 3)]


def polygon_area_3d(points):
    sx = sy = sz = 0.0
    for i, p1 in enumerate(points):
        p2 = points[(i + 1) % len(points)]
        sx += (p1[1] - p2[1]) * (p1[2] + p2[2])
        sy += (p1[2] - p2[2]) * (p1[0] + p2[0])
        sz += (p1[0] - p2[0]) * (p1[1] + p2[1])
    return 0.5 * math.sqrt(sx * sx + sy * sy + sz * sz)


def bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)


def center(bounds):
    return ((bounds[0] + bounds[3]) / 2.0, (bounds[1] + bounds[4]) / 2.0, (bounds[2] + bounds[5]) / 2.0)


def surface_data(objects):
    surfaces = []
    for obj in by_type(objects, "OS:Surface"):
        fields = obj["fields"]
        if len(fields) < 14:
            raise ValueError("surface has too few fields")
        points = parse_vertices(fields, 11)
        surfaces.append({
            "handle": handle(obj),
            "name": name(obj),
            "surface_type": fields[2],
            "construction_handle": fields[3],
            "space_handle": fields[4],
            "outside_boundary": fields[5],
            "vertices": points,
            "area": polygon_area_3d(points),
            "bbox": bbox(points),
        })
    return surfaces


def subsurface_data(objects):
    subsurfaces = []
    for obj in by_type(objects, "OS:SubSurface"):
        fields = obj["fields"]
        if len(fields) < 13:
            raise ValueError("subsurface has too few fields")
        points = parse_vertices(fields, 10)
        subsurfaces.append({
            "handle": handle(obj),
            "name": name(obj),
            "subsurface_type": fields[2],
            "construction_handle": fields[3],
            "surface_handle": fields[4],
            "vertices": points,
            "area": polygon_area_3d(points),
            "bbox": bbox(points),
        })
    return subsurfaces


def shading_surface_data(objects):
    result = []
    for obj in by_type(objects, "OS:ShadingSurface"):
        fields = obj["fields"]
        if len(fields) < 8:
            raise ValueError("shading surface has too few fields")
        points = parse_vertices(fields, 6)
        result.append({
            "handle": handle(obj),
            "name": name(obj),
            "group_handle": fields[3],
            "vertices": points,
            "area": polygon_area_3d(points),
            "bbox": bbox(points),
        })
    return result


def parse_csv_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return [], []
    headers = [cell.strip() for cell in rows[0]]
    body = []
    for row in rows[1:]:
        if not any(cell.strip() for cell in row):
            continue
        padded = row + [""] * max(0, len(headers) - len(row))
        body.append({headers[i]: padded[i].strip() for i in range(len(headers))})
    return headers, body


def metrics(objects):
    surfaces = surface_data(objects)
    subsurfaces = subsurface_data(objects)
    shading_surfaces = shading_surface_data(objects)
    all_points = [point for surface in surfaces for point in surface["vertices"]]
    bounds = bbox(all_points)
    spans = (bounds[3] - bounds[0], bounds[4] - bounds[1], bounds[5] - bounds[2])
    surface_by_handle = {surface["handle"]: surface for surface in surfaces}
    floors = [s for s in surfaces if s["surface_type"] == "Floor"]
    exterior_walls = [s for s in surfaces if s["surface_type"] == "Wall" and s["outside_boundary"] == "Outdoors"]
    windows = [s for s in subsurfaces if s["subsurface_type"] in WINDOW_TYPES]
    doors = [s for s in subsurfaces if s["subsurface_type"] == "Door"]
    floor_area_by_space = {}
    window_area_by_space = {}
    for floor in floors:
        floor_area_by_space[floor["space_handle"]] = floor_area_by_space.get(floor["space_handle"], 0.0) + floor["area"]
    for window in windows:
        parent = surface_by_handle.get(window["surface_handle"])
        if parent is None:
            raise ValueError("window without parent")
        window_area_by_space[parent["space_handle"]] = window_area_by_space.get(parent["space_handle"], 0.0) + window["area"]
    return {
        "surfaces": surfaces,
        "subsurfaces": subsurfaces,
        "shading_surfaces": shading_surfaces,
        "floors": floors,
        "exterior_walls": exterior_walls,
        "windows": windows,
        "doors": doors,
        "bounds": bounds,
        "spans": spans,
        "floor_area": sum(s["area"] for s in floors),
        "exterior_wall_area": sum(s["area"] for s in exterior_walls),
        "window_area": sum(s["area"] for s in windows),
        "shading_area": sum(s["area"] for s in shading_surfaces),
        "floor_area_by_space": floor_area_by_space,
        "window_area_by_space": window_area_by_space,
    }


def facade_wwrs(data):
    walls = data["exterior_walls"]
    min_y = min(center(w["bbox"])[1] for w in walls)
    max_y = max(center(w["bbox"])[1] for w in walls)
    min_x = min(center(w["bbox"])[0] for w in walls)
    max_x = max(center(w["bbox"])[0] for w in walls)
    wall_area = {"south": 0.0, "north": 0.0, "west": 0.0, "east": 0.0}
    window_area = {"south": 0.0, "north": 0.0, "west": 0.0, "east": 0.0}
    labels = {}
    for wall in walls:
        cx, cy, _ = center(wall["bbox"])
        if approx(cy, min_y, 0.05):
            label = "south"
        elif approx(cy, max_y, 0.05):
            label = "north"
        elif approx(cx, min_x, 0.05):
            label = "west"
        else:
            label = "east"
        labels[wall["handle"]] = label
        wall_area[label] += wall["area"]
    for window in data["windows"]:
        label = labels.get(window["surface_handle"])
        if label:
            window_area[label] += window["area"]
    return {key: (window_area[key] / wall_area[key] if wall_area[key] else 0.0) for key in wall_area}


def check_required_outputs(root):
    for rel, min_bytes in SPEC["required_outputs"].items():
        path = root / rel
        if not path.is_file() or path.stat().st_size < min_bytes:
            return False
    return True


def check_version(objects):
    versions = by_type(objects, "OS:Version")
    return len(versions) == 1 and versions[0]["fields"] and versions[0]["fields"][-1].startswith(SPEC["openstudio_version_prefix"])


def check_counts(objects, data):
    for object_type, expected in SPEC.get("object_counts", {}).items():
        if len(by_type(objects, object_type)) != int(expected):
            return False
    if SPEC.get("space_names") is not None:
        if sorted(name(obj) for obj in by_type(objects, "OS:Space")) != sorted(SPEC["space_names"]):
            return False
    for surface_type, expected in SPEC.get("surface_counts", {}).items():
        if sum(1 for s in data["surfaces"] if s["surface_type"] == surface_type) != int(expected):
            return False
    for obc, expected in SPEC.get("outside_boundary_counts", {}).items():
        if sum(1 for s in data["surfaces"] if s["outside_boundary"] == obc) != int(expected):
            return False
    if SPEC.get("window_count") is not None and len(data["windows"]) != int(SPEC["window_count"]):
        return False
    if SPEC.get("fixed_window_count") is not None:
        if sum(1 for w in data["windows"] if w["subsurface_type"] == "FixedWindow") != int(SPEC["fixed_window_count"]):
            return False
    if SPEC.get("door_count") is not None and len(data["doors"]) != int(SPEC["door_count"]):
        return False
    if SPEC.get("shading_surface_count") is not None and len(data["shading_surfaces"]) != int(SPEC["shading_surface_count"]):
        return False
    return True


def check_space_links(objects, data):
    if not SPEC.get("require_space_links"):
        return True
    stories = {handle(obj) for obj in by_type(objects, "OS:BuildingStory")}
    zones = {handle(obj) for obj in by_type(objects, "OS:ThermalZone")}
    for space in by_type(objects, "OS:Space"):
        fields = space["fields"]
        if len(fields) < 11 or fields[9] not in stories or fields[10] not in zones:
            return False
        if data["floor_area_by_space"].get(handle(space), 0.0) <= 0.05:
            return False
    return True


def check_geometry(data):
    dim_tol = SPEC.get("dimension_tolerance_m", 0.05)
    for actual, expected in zip(data["spans"], SPEC.get("bbox_spans_m", [])):
        if not approx(actual, expected, dim_tol):
            return False
    area_tol = SPEC.get("area_tolerance_m2", 0.5)
    for key, actual_key in [("floor_area_m2", "floor_area"), ("exterior_wall_area_m2", "exterior_wall_area"), ("window_area_m2", "window_area"), ("shading_area_m2", "shading_area")]:
        if key in SPEC and not approx(data[actual_key], SPEC[key], area_tol):
            return False
    return True


def check_hvac(objects):
    hvac = SPEC.get("hvac")
    if not hvac:
        return True
    if len(by_type(objects, "OS:ZoneHVAC:IdealLoadsAirSystem")) != hvac.get("ideal_loads", 0):
        return False
    if len(by_type(objects, "OS:ZoneHVAC:EquipmentList")) != hvac.get("equipment_lists", 0):
        return False
    if len(by_type(objects, "OS:ThermostatSetpoint:DualSetpoint")) != hvac.get("thermostats", 0):
        return False
    return True


def expected_kpi_value(key, objects, data):
    if key in SPEC.get("fixed_kpis", {}):
        return SPEC["fixed_kpis"][key]
    space_lookup = {name(obj): obj for obj in by_type(objects, "OS:Space")}
    if key == "reading_area_m2":
        return data["floor_area_by_space"].get(handle(space_lookup["Reading"]), 0.0)
    if key == "stacks_area_m2":
        return data["floor_area_by_space"].get(handle(space_lookup["Stacks"]), 0.0)
    if key == "south_overhang_area_m2":
        return data["shading_area"]
    if key in {"north_wwr", "east_wwr", "south_wwr", "west_wwr"}:
        return facade_wwrs(data)[key.removesuffix("_wwr")]
    values = {
        "total_floor_area_m2": data["floor_area"],
        "zone_count": len(by_type(objects, "OS:ThermalZone")),
        "total_window_area_m2": data["window_area"],
    }
    return values[key]


def check_kpis(root, objects, data):
    keys = SPEC.get("kpis")
    if not keys:
        return True
    payload = json.loads((root / "kpis.json").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return False
    for key in keys:
        if key not in payload:
            return False
        if not approx(float(payload[key]), expected_kpi_value(key, objects, data), SPEC.get("kpi_absolute_tolerance", 0.10), SPEC.get("kpi_relative_tolerance", 0.01)):
            return False
    return True


def check_csv(root):
    csv_spec = SPEC.get("csv")
    if not csv_spec:
        return True
    headers, rows = parse_csv_rows(root / "result.csv")
    if headers != csv_spec["headers"] or len(rows) != len(csv_spec["rows"]):
        return False
    for actual, expected in zip(rows, csv_spec["rows"]):
        for key in csv_spec["headers"]:
            if isinstance(expected[key], (int, float)):
                if not approx(float(actual[key]), float(expected[key]), csv_spec.get("numeric_tolerance", 0.20)):
                    return False
            elif actual[key] != str(expected[key]):
                return False
    return True


def evaluate():
    root = DESKTOP
    if not root.is_dir() or not check_required_outputs(root):
        return False
    objects = parse_osm(root / "result.osm")
    if not objects or not check_version(objects):
        return False
    data = metrics(objects)
    return (
        check_counts(objects, data)
        and check_space_links(objects, data)
        and check_geometry(data)
        and check_hvac(objects)
        and check_kpis(root, objects, data)
        and check_csv(root)
    )


def main():
    try:
        finish(evaluate())
    except SystemExit:
        raise
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
