#!/usr/bin/env python3
import csv
import math
import json
from pathlib import Path
import subprocess
import tempfile


DESKTOP = Path("/home/user/Desktop")

SPEC = {'required_outputs': {'result.osm': 500, 'result.csv': 10}, 'object_counts': {'OS:BuildingStory': 1, 'OS:Space': 4, 'OS:ThermalZone': 4, 'OS:Surface': 24, 'OS:SubSurface': 8, 'OS:ZoneHVAC:IdealLoadsAirSystem': 0, 'OS:ZoneHVAC:EquipmentList': 4, 'OS:ThermostatSetpoint:DualSetpoint': 4, 'OS:People': 3, 'OS:Lights': 3, 'OS:ElectricEquipment': 3}, 'space_names': ['Classroom-A', 'Classroom-B', 'TeacherOffice', 'Storage'], 'surface_counts': {'Floor': 4, 'RoofCeiling': 4, 'Wall': 16}, 'outside_boundary_counts': {'Ground': 4, 'Outdoors': 12, 'Surface': 8}, 'window_count': 8, 'fixed_window_count': 8, 'bbox_spans_m': [16.0, 12.0, 3.2], 'floor_area_m2': 192.0, 'exterior_wall_area_m2': 179.2, 'window_area_m2': 34.56, 'csv': {'headers': ['space_name', 'resolved_schedule_set', 'resolved_space_type', 'occupied_flag'], 'rows': [{'space_name': 'Classroom-A', 'resolved_schedule_set': 'School Defaults', 'resolved_space_type': 'ClassroomType', 'occupied_flag': '1'}, {'space_name': 'Classroom-B', 'resolved_schedule_set': 'School Defaults', 'resolved_space_type': 'ClassroomType', 'occupied_flag': '1'}, {'space_name': 'Storage', 'resolved_schedule_set': 'Support Defaults', 'resolved_space_type': 'StorageType', 'occupied_flag': '1'}, {'space_name': 'TeacherOffice', 'resolved_schedule_set': 'Support Defaults', 'resolved_space_type': 'OfficeType', 'occupied_flag': '1'}]}}
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
    all_points = [point for surface in surfaces for point in surface["vertices"]]
    bounds = bbox(all_points)
    spans = (bounds[3] - bounds[0], bounds[4] - bounds[1], bounds[5] - bounds[2])
    floors = [s for s in surfaces if s["surface_type"] == "Floor"]
    exterior_walls = [s for s in surfaces if s["surface_type"] == "Wall" and s["outside_boundary"] == "Outdoors"]
    windows = [s for s in subsurfaces if s["subsurface_type"] in WINDOW_TYPES]
    floor_area_by_space = {}
    for floor in floors:
        floor_area_by_space[floor["space_handle"]] = floor_area_by_space.get(floor["space_handle"], 0.0) + floor["area"]
    return {
        "surfaces": surfaces,
        "subsurfaces": subsurfaces,
        "bounds": bounds,
        "spans": spans,
        "floors": floors,
        "exterior_walls": exterior_walls,
        "windows": windows,
        "floor_area": sum(s["area"] for s in floors),
        "exterior_wall_area": sum(s["area"] for s in exterior_walls),
        "window_area": sum(s["area"] for s in windows),
        "floor_area_by_space": floor_area_by_space,
    }


def check_required_outputs(root):
    for rel, min_bytes in SPEC["required_outputs"].items():
        path = root / rel
        if not path.is_file() or path.stat().st_size < min_bytes:
            return False
    return True



def check_counts(objects, data):
    for object_type, expected in SPEC.get("object_counts", {}).items():
        if len(by_type(objects, object_type)) != int(expected):
            return False
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
    if SPEC.get("fixed_window_count") is not None and sum(1 for w in data["windows"] if w["subsurface_type"] == "FixedWindow") != int(SPEC["fixed_window_count"]):
        return False
    return True


def check_space_links(objects, data):
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
    for actual, expected in zip(data["spans"], SPEC["bbox_spans_m"]):
        if not approx(actual, expected, SPEC.get("dimension_tolerance_m", 0.05)):
            return False
    if not approx(data["floor_area"], SPEC["floor_area_m2"], SPEC.get("area_tolerance_m2", 0.5)):
        return False
    if not approx(data["exterior_wall_area"], SPEC["exterior_wall_area_m2"], SPEC.get("area_tolerance_m2", 0.5)):
        return False
    if not approx(data["window_area"], SPEC["window_area_m2"], SPEC.get("area_tolerance_m2", 0.5)):
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
                if not approx(float(actual[key]), float(expected[key]), csv_spec.get("numeric_tolerance", 0.001)):
                    return False
            elif actual[key] != str(expected[key]):
                return False
    return True


def evaluate():
    root = DESKTOP
    if not root.is_dir() or not check_required_outputs(root):
        return False
    objects = parse_osm(root / "result.osm")
    if not objects:
        return False
    data = metrics(objects)
    return check_counts(objects, data) and check_space_links(objects, data) and check_geometry(data) and check_csv(root)


def main():
    try:
        finish(evaluate())
    except SystemExit:
        raise
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
