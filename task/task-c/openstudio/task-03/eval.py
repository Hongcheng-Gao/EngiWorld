#!/usr/bin/env python3
import csv
import json
import math
import re
from pathlib import Path
import subprocess
import tempfile


DESKTOP = Path("/home/user/Desktop")

SPEC = {'required_outputs': {'result.osm': 500, 'result.csv': 10}, 'openstudio_version_prefix': '3.10', 'object_counts': {'OS:Building': 1, 'OS:BuildingStory': 1, 'OS:Space': 6, 'OS:ThermalZone': 6, 'OS:Surface': 42, 'OS:SubSurface': 0}, 'space_names': ['Classroom-1', 'Classroom-2', 'Corridor', 'Restroom', 'Office', 'Storage'], 'surface_counts': {'Floor': 6, 'RoofCeiling': 6, 'Wall': 30}, 'outside_boundary_counts': {'Ground': 6, 'Outdoors': 20, 'Surface': 16}, 'bbox_spans_m': [22.0, 10.0, 3.4], 'floor_area_m2': 176.0, 'exterior_wall_area_m2': 217.6, 'window_area_m2': 0.0, 'dimension_tolerance_m': 0.05, 'area_tolerance_m2': 0.5, 'require_default_construction_set': True, 'require_space_links': True, 'csv': {'mode': 'space_summary', 'headers': ['space_name', 'floor_area_m2', 'space_type_name', 'thermal_zone_name'], 'order': ['Classroom-1', 'Classroom-2', 'Corridor', 'Office', 'Restroom', 'Storage'], 'rows': [{}, {}, {}, {}, {}, {}], 'numeric_tolerance': 0.2}}


def finish(ok):
    print("true" if ok else "false")
    raise SystemExit(0)


def approx(actual, expected, abs_tol, rel_tol=0.0):
    return abs(float(actual) - float(expected)) <= max(float(abs_tol), abs(float(expected)) * float(rel_tol))


def norm_name(value):
    return re.sub(r"\s+", " ", str(value or "").strip())



def parse_float(value):
    text = str(value).strip()
    if text == "" or text.lower() == "autosize":
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


def object_by_handle(objects, object_type):
    return {handle(obj): obj for obj in by_type(objects, object_type)}


def parse_vertices(fields, start_index):
    values = [parse_float(v) for v in fields[start_index:]]
    if len(values) % 3 != 0 or not values:
        raise ValueError("invalid vertices")
    return [(values[i], values[i + 1], values[i + 2]) for i in range(0, len(values), 3)]


def polygon_area_3d(points):
    if len(points) < 3:
        return 0.0
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
            "surface_handle": fields[4],
            "vertices": points,
            "area": polygon_area_3d(points),
            "bbox": bbox(points),
        })
    return subsurfaces


def parse_csv_file(path):
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


def model_metrics(objects):
    surfaces = surface_data(objects)
    subsurfaces = subsurface_data(objects)
    all_points = [point for surface in surfaces for point in surface["vertices"]]
    bounds = bbox(all_points)
    spans = (bounds[3] - bounds[0], bounds[4] - bounds[1], bounds[5] - bounds[2])
    surface_by_handle = {surface["handle"]: surface for surface in surfaces}
    floors = [s for s in surfaces if s["surface_type"] == "Floor"]
    exterior_walls = [s for s in surfaces if s["surface_type"] == "Wall" and s["outside_boundary"] == "Outdoors"]
    windows = [s for s in subsurfaces if s["subsurface_type"] in {"FixedWindow", "OperableWindow", "GlassDoor", "Skylight"}]
    floor_area_by_space = {}
    window_area_by_space = {}
    for floor in floors:
        floor_area_by_space[floor["space_handle"]] = floor_area_by_space.get(floor["space_handle"], 0.0) + floor["area"]
    for window in windows:
        parent = surface_by_handle.get(window["surface_handle"])
        if parent is None:
            raise ValueError("window without parent surface")
        space_handle = parent["space_handle"]
        window_area_by_space[space_handle] = window_area_by_space.get(space_handle, 0.0) + window["area"]
    return {
        "bounds": bounds,
        "spans": spans,
        "surfaces": surfaces,
        "subsurfaces": subsurfaces,
        "floors": floors,
        "exterior_walls": exterior_walls,
        "windows": windows,
        "floor_area": sum(s["area"] for s in floors),
        "exterior_wall_area": sum(s["area"] for s in exterior_walls),
        "window_area": sum(s["area"] for s in windows),
        "floor_area_by_space": floor_area_by_space,
        "window_area_by_space": window_area_by_space,
    }


def check_required_outputs(root):
    for rel, min_bytes in SPEC["required_outputs"].items():
        path = root / rel
        if not path.is_file() or path.stat().st_size < min_bytes:
            return False
    return True


def check_counts(objects, metrics):
    for object_type, expected in SPEC.get("object_counts", {}).items():
        if len(by_type(objects, object_type)) != int(expected):
            return False
    for object_type, minimum in SPEC.get("object_min_counts", {}).items():
        if len(by_type(objects, object_type)) < int(minimum):
            return False
    if SPEC.get("space_names") is not None:
        actual = sorted(name(obj) for obj in by_type(objects, "OS:Space"))
        if actual != sorted(SPEC["space_names"]):
            return False
    surface_counts = SPEC.get("surface_counts", {})
    for surface_type, expected in surface_counts.items():
        if sum(1 for s in metrics["surfaces"] if s["surface_type"] == surface_type) != int(expected):
            return False
    obc_counts = SPEC.get("outside_boundary_counts", {})
    for obc, expected in obc_counts.items():
        if sum(1 for s in metrics["surfaces"] if s["outside_boundary"] == obc) != int(expected):
            return False
    if SPEC.get("window_count") is not None and len(metrics["windows"]) != int(SPEC["window_count"]):
        return False
    if SPEC.get("fixed_window_count") is not None:
        fixed = [w for w in metrics["windows"] if w["subsurface_type"] == "FixedWindow"]
        if len(fixed) != int(SPEC["fixed_window_count"]):
            return False
    return True


def check_version(objects):
    versions = by_type(objects, "OS:Version")
    return len(versions) == 1 and versions[0]["fields"] and versions[0]["fields"][-1].startswith(SPEC["openstudio_version_prefix"])


def check_building_default_set(objects):
    if not SPEC.get("require_default_construction_set"):
        return True
    sets = by_type(objects, "OS:DefaultConstructionSet")
    buildings = by_type(objects, "OS:Building")
    if len(sets) < 1 or len(buildings) != 1:
        return False
    handles = {handle(obj) for obj in sets}
    return any(field in handles for field in buildings[0]["fields"])


def check_space_links(objects, metrics):
    if not SPEC.get("require_space_links"):
        return True
    stories = {handle(obj) for obj in by_type(objects, "OS:BuildingStory")}
    zones = {handle(obj) for obj in by_type(objects, "OS:ThermalZone")}
    for space in by_type(objects, "OS:Space"):
        fields = space["fields"]
        if len(fields) < 12:
            return False
        if fields[9] not in stories or fields[10] not in zones:
            return False
        if fields[11].lower() != "yes":
            return False
        if metrics["floor_area_by_space"].get(handle(space), 0.0) <= 0.05:
            return False
    return True


def check_geometry(metrics):
    tol = float(SPEC.get("dimension_tolerance_m", 0.05))
    for actual, expected in zip(metrics["spans"], SPEC.get("bbox_spans_m", [])):
        if not approx(actual, expected, tol):
            return False
    area_tol = float(SPEC.get("area_tolerance_m2", 0.5))
    if SPEC.get("floor_area_m2") is not None and not approx(metrics["floor_area"], SPEC["floor_area_m2"], area_tol):
        return False
    if SPEC.get("exterior_wall_area_m2") is not None and not approx(metrics["exterior_wall_area"], SPEC["exterior_wall_area_m2"], area_tol):
        return False
    if SPEC.get("window_area_m2") is not None and not approx(metrics["window_area"], SPEC["window_area_m2"], area_tol):
        return False
    return True


def check_hvac(objects):
    hvac = SPEC.get("hvac")
    if not hvac:
        return True
    zones = by_type(objects, "OS:ThermalZone")
    thermostats = by_type(objects, "OS:ThermostatSetpoint:DualSetpoint")
    ideal_loads = by_type(objects, "OS:ZoneHVAC:IdealLoadsAirSystem")
    equipment_lists = by_type(objects, "OS:ZoneHVAC:EquipmentList")
    if len(thermostats) != hvac.get("thermostats", len(thermostats)):
        return False
    if len(ideal_loads) != hvac.get("ideal_loads", len(ideal_loads)):
        return False
    if len(equipment_lists) != hvac.get("equipment_lists", len(equipment_lists)):
        return False
    thermostat_handles = {handle(obj) for obj in thermostats}
    ideal_handles = {handle(obj) for obj in ideal_loads}
    for zone in zones:
        if not any(handle(zone) in eq["fields"] for eq in equipment_lists):
            return False
        if thermostat_handles and not any(field in thermostat_handles for field in zone["fields"]):
            return False
    for eq in equipment_lists:
        if ideal_handles and not any(field in ideal_handles for field in eq["fields"]):
            return False
    return True


def check_kpis(root, metrics, objects):
    spec = SPEC.get("kpis")
    if not spec:
        return True
    payload = json.loads((root / "kpis.json").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return False
    values = {
        "total_floor_area_m2": metrics["floor_area"],
        "floor_area_m2": metrics["floor_area"],
        "total_exterior_wall_area_m2": metrics["exterior_wall_area"],
        "exterior_wall_area_m2": metrics["exterior_wall_area"],
        "total_window_area_m2": metrics["window_area"],
        "zone_count": len(by_type(objects, "OS:ThermalZone")),
    }
    for key in spec:
        if key not in payload or key not in values:
            return False
        if not approx(float(payload[key]), values[key], SPEC.get("kpi_absolute_tolerance", 0.10), SPEC.get("kpi_relative_tolerance", 0.01)):
            return False
    return True


def check_csv(root, metrics, objects):
    csv_spec = SPEC.get("csv")
    if not csv_spec:
        return True
    headers, rows = parse_csv_file(root / "result.csv")
    if headers != csv_spec["headers"] or len(rows) != len(csv_spec["rows"]):
        return False
    spaces = object_by_handle(objects, "OS:Space")
    zones = object_by_handle(objects, "OS:ThermalZone")
    space_types = object_by_handle(objects, "OS:SpaceType")
    expected_rows = []
    if csv_spec["mode"] == "space_summary":
        for space_name in csv_spec["order"]:
            space = next((sp for sp in spaces.values() if name(sp) == space_name), None)
            if space is None:
                return False
            fields = space["fields"]
            expected_rows.append({
                "space_name": space_name,
                "floor_area_m2": metrics["floor_area_by_space"].get(handle(space), 0.0),
                "space_type_name": name(space_types.get(fields[2], {"fields": []})),
                "thermal_zone_name": name(zones.get(fields[10], {"fields": []})),
            })
    elif csv_spec["mode"] == "zone_summary":
        space_by_zone = {}
        window_by_zone = {}
        for space in spaces.values():
            zone_handle = space["fields"][10]
            space_by_zone[zone_handle] = space_by_zone.get(zone_handle, 0.0) + metrics["floor_area_by_space"].get(handle(space), 0.0)
            window_by_zone[zone_handle] = window_by_zone.get(zone_handle, 0.0) + metrics["window_area_by_space"].get(handle(space), 0.0)
        for row_spec in csv_spec["rows"]:
            zone = next((z for z in zones.values() if name(z) == row_spec["zone_name"]), None)
            if zone is None:
                return False
            expected_rows.append({
                "zone_name": row_spec["zone_name"],
                "floor_area_m2": space_by_zone.get(handle(zone), 0.0),
                "ext_window_area_m2": window_by_zone.get(handle(zone), 0.0),
                "use_type": row_spec["use_type"],
            })
    else:
        expected_rows = csv_spec["rows"]
    for actual, expected in zip(rows, expected_rows):
        for key in csv_spec["headers"]:
            if isinstance(expected[key], (int, float)):
                if not approx(float(actual[key]), float(expected[key]), csv_spec.get("numeric_tolerance", 0.20)):
                    return False
            else:
                if actual[key] != str(expected[key]):
                    return False
    return True


def evaluate():
    root = DESKTOP
    if not root.is_dir() or not check_required_outputs(root):
        return False
    objects = parse_osm(root / "result.osm")
    if not objects or not check_version(objects):
        return False
    metrics = model_metrics(objects)
    return (
        check_building_default_set(objects)
        and check_counts(objects, metrics)
        and check_space_links(objects, metrics)
        and check_geometry(metrics)
        and check_hvac(objects)
        and check_kpis(root, metrics, objects)
        and check_csv(root, metrics, objects)
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
