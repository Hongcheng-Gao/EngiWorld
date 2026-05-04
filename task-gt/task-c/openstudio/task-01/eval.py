#!/usr/bin/env python3
import json
import math
import re
from pathlib import Path
import subprocess
import tempfile


DESKTOP = Path("/home/user/Desktop")


SPEC = {
    "required_outputs": {"result.osm": 500, "kpis.json": 10},
    "openstudio_version_prefix": "3.10",
    "space_count": 1,
    "thermal_zone_count": 1,
    "building_story_count": 1,
    "floor_width_m": 12.0,
    "floor_depth_m": 8.0,
    "height_m": 3.6,
    "floor_area_m2": 96.0,
    "exterior_wall_area_m2": 144.0,
    "south_window_area_m2": 17.28,
    "east_window_area_m2": 11.52,
    "north_window_area_m2": 0.0,
    "west_window_area_m2": 0.0,
    "south_wwr": 0.40,
    "east_wwr": 0.40,
    "heating_setpoint_c": 21.0,
    "cooling_setpoint_c": 24.0,
    "window_sill_height_m": 0.90,
    "dimension_tolerance_m": 0.05,
    "area_tolerance_m2": 0.50,
    "wwr_tolerance": 0.03,
    "thermostat_tolerance_c": 0.25,
    "kpi_relative_tolerance": 0.01,
    "kpi_absolute_tolerance": 0.10,
}


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def approx(actual, expected, abs_tol, rel_tol=0.0):
    return abs(float(actual) - float(expected)) <= max(float(abs_tol), abs(float(expected)) * float(rel_tol))



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


def parse_float(value):
    text = str(value).strip()
    if text.lower() == "autosize" or text == "":
        raise ValueError(text)
    return float(text)


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


def facade_label(surface):
    cx, cy, _ = center(surface["bbox"])
    # Labels are defined by world-coordinate position for this task.
    return cx, cy


def constant_schedules(objects):
    result = {}
    for obj in by_type(objects, "OS:Schedule:Constant"):
        fields = obj["fields"]
        if len(fields) >= 4:
            try:
                result[handle(obj)] = parse_float(fields[3])
            except Exception:
                pass
    return result


def has_default_construction_set(objects):
    sets = by_type(objects, "OS:DefaultConstructionSet")
    buildings = by_type(objects, "OS:Building")
    if len(sets) < 1 or len(buildings) != 1:
        return False
    set_handles = {handle(obj) for obj in sets}
    return any(field in set_handles for field in buildings[0]["fields"])


def check_geometry(objects):
    spaces = by_type(objects, "OS:Space")
    zones = by_type(objects, "OS:ThermalZone")
    stories = by_type(objects, "OS:BuildingStory")
    if len(spaces) != SPEC["space_count"] or len(zones) != SPEC["thermal_zone_count"]:
        return None
    if len(stories) != SPEC["building_story_count"]:
        return None

    space = spaces[0]
    zone = zones[0]
    if handle(zone) not in space["fields"]:
        return None
    if handle(stories[0]) not in space["fields"]:
        return None
    if space["fields"][-1].lower() != "yes":
        return None

    surfaces = surface_data(objects)
    subsurfaces = subsurface_data(objects)
    if len(surfaces) != 6:
        return None
    floors = [s for s in surfaces if s["surface_type"] == "Floor"]
    roofs = [s for s in surfaces if s["surface_type"] == "RoofCeiling"]
    walls = [s for s in surfaces if s["surface_type"] == "Wall" and s["outside_boundary"] == "Outdoors"]
    if len(floors) != 1 or len(roofs) != 1 or len(walls) != 4:
        return None

    all_points = [point for surface in surfaces for point in surface["vertices"]]
    minx, miny, minz, maxx, maxy, maxz = bbox(all_points)
    width = maxx - minx
    depth = maxy - miny
    height = maxz - minz
    if not approx(width, SPEC["floor_width_m"], SPEC["dimension_tolerance_m"]):
        return None
    if not approx(depth, SPEC["floor_depth_m"], SPEC["dimension_tolerance_m"]):
        return None
    if not approx(height, SPEC["height_m"], SPEC["dimension_tolerance_m"]):
        return None

    floor_area = floors[0]["area"]
    exterior_wall_area = sum(w["area"] for w in walls)
    if not approx(floor_area, SPEC["floor_area_m2"], SPEC["area_tolerance_m2"]):
        return None
    if not approx(exterior_wall_area, SPEC["exterior_wall_area_m2"], SPEC["area_tolerance_m2"]):
        return None

    wall_by_handle = {s["handle"]: s for s in walls}
    window_types = {"FixedWindow", "OperableWindow", "GlassDoor", "Skylight"}
    windows = [s for s in subsurfaces if s["subsurface_type"] in window_types]
    if len(windows) != 2:
        return None

    south_wall = min(walls, key=lambda s: center(s["bbox"])[1])
    north_wall = max(walls, key=lambda s: center(s["bbox"])[1])
    east_wall = max(walls, key=lambda s: center(s["bbox"])[0])
    west_wall = min(walls, key=lambda s: center(s["bbox"])[0])
    labels = {
        south_wall["handle"]: "south",
        north_wall["handle"]: "north",
        east_wall["handle"]: "east",
        west_wall["handle"]: "west",
    }
    wall_areas = {
        "south": south_wall["area"],
        "north": north_wall["area"],
        "east": east_wall["area"],
        "west": west_wall["area"],
    }
    window_areas = {"south": 0.0, "north": 0.0, "east": 0.0, "west": 0.0}
    for win in windows:
        if win["surface_handle"] not in wall_by_handle:
            return None
        sill = win["bbox"][2]
        if not approx(sill, SPEC["window_sill_height_m"], SPEC["dimension_tolerance_m"]):
            return None
        label = labels.get(win["surface_handle"])
        if label is None:
            return None
        window_areas[label] += win["area"]

    if not approx(window_areas["south"], SPEC["south_window_area_m2"], SPEC["area_tolerance_m2"]):
        return None
    if not approx(window_areas["east"], SPEC["east_window_area_m2"], SPEC["area_tolerance_m2"]):
        return None
    if window_areas["north"] > 0.05 or window_areas["west"] > 0.05:
        return None
    if not approx(window_areas["south"] / wall_areas["south"], SPEC["south_wwr"], SPEC["wwr_tolerance"]):
        return None
    if not approx(window_areas["east"] / wall_areas["east"], SPEC["east_wwr"], SPEC["wwr_tolerance"]):
        return None

    return {
        "floor_area_m2": floor_area,
        "exterior_wall_area_m2": exterior_wall_area,
        "south_window_area_m2": window_areas["south"],
        "east_window_area_m2": window_areas["east"],
    }


def check_thermostat_and_loads(objects):
    zones = by_type(objects, "OS:ThermalZone")
    thermostats = by_type(objects, "OS:ThermostatSetpoint:DualSetpoint")
    ideal_loads = by_type(objects, "OS:ZoneHVAC:IdealLoadsAirSystem")
    equipment_lists = by_type(objects, "OS:ZoneHVAC:EquipmentList")
    if len(zones) != 1 or len(thermostats) != 1 or len(ideal_loads) != 1 or len(equipment_lists) != 1:
        return False

    zone = zones[0]
    thermostat = thermostats[0]
    ideal = ideal_loads[0]
    equipment = equipment_lists[0]
    if handle(thermostat) not in zone["fields"]:
        return False
    if handle(ideal) not in equipment["fields"]:
        return False
    if handle(zone) not in equipment["fields"]:
        return False

    schedules = constant_schedules(objects)
    if len(thermostat["fields"]) < 4:
        return False
    heat_handle = thermostat["fields"][2]
    cool_handle = thermostat["fields"][3]
    heat = schedules.get(heat_handle)
    cool = schedules.get(cool_handle)
    if heat is None or cool is None:
        return False
    if not approx(heat, SPEC["heating_setpoint_c"], SPEC["thermostat_tolerance_c"]):
        return False
    if not approx(cool, SPEC["cooling_setpoint_c"], SPEC["thermostat_tolerance_c"]):
        return False

    availability_handle = ideal["fields"][2] if len(ideal["fields"]) > 2 else ""
    if not approx(schedules.get(availability_handle), 1.0, 0.001):
        return False
    return True


def check_kpis(root, metrics):
    path = root / "kpis.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return False
    required = ["floor_area_m2", "exterior_wall_area_m2", "south_window_area_m2", "east_window_area_m2"]
    for key in required:
        if key not in payload:
            return False
        if not approx(
            float(payload[key]),
            metrics[key],
            SPEC["kpi_absolute_tolerance"],
            SPEC["kpi_relative_tolerance"],
        ):
            return False
    return True


def evaluate():
    root = DESKTOP
    if not root.is_dir():
        return False
    for rel, min_bytes in SPEC["required_outputs"].items():
        path = root / rel
        if not path.is_file() or path.stat().st_size < min_bytes:
            return False
    objects = parse_osm(root / "result.osm")
    if not objects:
        return False
    versions = by_type(objects, "OS:Version")
    if len(versions) != 1 or not versions[0]["fields"][-1].startswith(SPEC["openstudio_version_prefix"]):
        return False
    if not has_default_construction_set(objects):
        return False
    metrics = check_geometry(objects)
    if metrics is None:
        return False
    return check_thermostat_and_loads(objects) and check_kpis(root, metrics)


def main():
    try:
        finish(evaluate())
    except SystemExit:
        raise
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
