#!/usr/bin/env python3
import json
import math
from pathlib import Path
import subprocess
import tempfile


DESKTOP = Path("/home/user/Desktop")
SPEC = {'required_outputs': {'result.osm': 500}, 'object_counts': {'OS:BuildingStory': 1, 'OS:Space': 1, 'OS:ThermalZone': 1, 'OS:Surface': 6, 'OS:SubSurface': 0}, 'space_names': ['ScheduledOffice'], 'surface_counts': {'Floor': 1, 'RoofCeiling': 1, 'Wall': 4}, 'outside_boundary_counts': {'Ground': 1, 'Outdoors': 5, 'Surface': 0}, 'window_count': 0, 'fixed_window_count': 0, 'bbox_spans_m': [8.0, 5.0, 3.2], 'floor_area_m2': 40.0, 'exterior_wall_area_m2': 83.2, 'window_area_m2': 0, 'hvac': {'ideal_loads': 0, 'equipment_lists': 1, 'thermostats': 0}, 'loads': {'min_schedules': 1, 'people': 1, 'lights': 0, 'electric_equipment': 0, 'space_types': 0}}

GUI_BYPASS_FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr"
}
GUI_BYPASS_ALLOWED_FILENAMES = {"eval.py"}
GUI_BYPASS_OUTPUT_TOKENS = (
    "result.ifc", "result.pdf", "result.osm", "workflow.osw", "summary.txt",
    "report.csv", "result.csv", "kpis.json"
)
GUI_BYPASS_COMMAND_TOKENS = (
    "python", "python3", "py ", "powershell", "pwsh", "cmd.exe", "cmd /c",
    "bash", " sh ", "zsh", "node", "ruby", "perl", "ifcopenshell",
    "openstudio", "energyplus", "blender --background", "revitbatchprocessor"
)
WINDOW_TYPES = {"FixedWindow", "OperableWindow", "GlassDoor", "Skylight"}


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def approx(actual, expected, abs_tol, rel_tol=0.0):
    return abs(float(actual) - float(expected)) <= max(float(abs_tol), abs(float(expected)) * float(rel_tol))


def _read_text_safe(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _desktop_script_artifacts(root):
    if not root.exists() or not root.is_dir():
        return True
    try:
        candidates = list(root.iterdir())
        for directory in list(candidates):
            if directory.is_dir() and directory.name not in {"__pycache__", "_runtime"}:
                try:
                    candidates.extend(directory.iterdir())
                except Exception:
                    pass
        for path in candidates:
            if not path.is_file() or path.name in GUI_BYPASS_ALLOWED_FILENAMES:
                continue
            if path.suffix.lower() in GUI_BYPASS_FORBIDDEN_EXTENSIONS:
                return True
    except Exception:
        return True
    return False


def _history_contains_bypass(root):
    home = Path.home()
    paths = [
        home / ".bash_history",
        home / ".zsh_history",
        home / ".python_history",
        home / ".local/share/fish/fish_history",
        root / ".bash_history",
        root / ".zsh_history",
    ]
    for path in paths:
        if not path.is_file():
            continue
        text = _read_text_safe(path).lower()
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or "eval.py" in line:
                continue
            touches_output = any(token in line for token in GUI_BYPASS_OUTPUT_TOKENS)
            runs_command = any(token in line for token in GUI_BYPASS_COMMAND_TOKENS)
            writes_file = any(token in line for token in (">", "tee ", "cat ", "set-content", "out-file", "new-item"))
            if touches_output and (runs_command or writes_file):
                return True
            if ("/desktop/" in line or "\\desktop\\" in line) and any(ext in line for ext in GUI_BYPASS_FORBIDDEN_EXTENSIONS) and runs_command:
                return True
    return False


def check_no_gui_bypass(root):
    root = Path(root)
    return not _desktop_script_artifacts(root) and not _history_contains_bypass(root)


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
    if not text or text.lower() == "autosize":
        raise ValueError(text)
    return float(text)


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
    result = []
    for obj in by_type(objects, "OS:Surface"):
        fields = obj["fields"]
        if len(fields) < 14:
            raise ValueError("surface has too few fields")
        points = parse_vertices(fields, 11)
        result.append({
            "handle": handle(obj),
            "type": fields[2],
            "space": fields[4],
            "obc": fields[5],
            "vertices": points,
            "area": polygon_area_3d(points),
        })
    return result


def subsurface_data(objects):
    result = []
    for obj in by_type(objects, "OS:SubSurface"):
        fields = obj["fields"]
        if len(fields) < 13:
            raise ValueError("subsurface has too few fields")
        points = parse_vertices(fields, 10)
        result.append({
            "handle": handle(obj),
            "type": fields[2],
            "surface": fields[4],
            "vertices": points,
            "area": polygon_area_3d(points),
        })
    return result


def shading_surface_data(objects):
    result = []
    for obj in by_type(objects, "OS:ShadingSurface"):
        fields = obj["fields"]
        if len(fields) < 8:
            raise ValueError("shading surface has too few fields")
        points = parse_vertices(fields, 6)
        result.append({"handle": handle(obj), "vertices": points, "area": polygon_area_3d(points)})
    return result


def metrics(objects):
    surfaces = surface_data(objects)
    subsurfaces = subsurface_data(objects)
    shading = shading_surface_data(objects)
    all_points = [point for surface in surfaces for point in surface["vertices"]]
    bounds = bbox(all_points)
    spans = (bounds[3] - bounds[0], bounds[4] - bounds[1], bounds[5] - bounds[2])
    floors = [s for s in surfaces if s["type"] == "Floor"]
    exterior_walls = [s for s in surfaces if s["type"] == "Wall" and s["obc"] == "Outdoors"]
    windows = [s for s in subsurfaces if s["type"] in WINDOW_TYPES]
    floor_area_by_space = {}
    for floor in floors:
        floor_area_by_space[floor["space"]] = floor_area_by_space.get(floor["space"], 0.0) + floor["area"]
    return {
        "surfaces": surfaces,
        "subsurfaces": subsurfaces,
        "shading": shading,
        "spans": spans,
        "windows": windows,
        "floor_area": sum(s["area"] for s in floors),
        "exterior_wall_area": sum(s["area"] for s in exterior_walls),
        "window_area": sum(s["area"] for s in windows),
        "shading_area": sum(s["area"] for s in shading),
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
    if SPEC.get("space_names") is not None:
        if sorted(name(obj) for obj in by_type(objects, "OS:Space")) != sorted(SPEC["space_names"]):
            return False
    for surface_type, expected in SPEC.get("surface_counts", {}).items():
        if sum(1 for s in data["surfaces"] if s["type"] == surface_type) != int(expected):
            return False
    for obc, expected in SPEC.get("outside_boundary_counts", {}).items():
        if sum(1 for s in data["surfaces"] if s["obc"] == obc) != int(expected):
            return False
    if SPEC.get("window_count") is not None and len(data["windows"]) != int(SPEC["window_count"]):
        return False
    if SPEC.get("fixed_window_count") is not None and sum(1 for w in data["windows"] if w["type"] == "FixedWindow") != int(SPEC["fixed_window_count"]):
        return False
    if SPEC.get("shading_surface_count") is not None and len(data["shading"]) != int(SPEC["shading_surface_count"]):
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
        if not approx(actual, expected, SPEC.get("dimension_tolerance_m", 0.1)):
            return False
    for key, data_key in [
        ("floor_area_m2", "floor_area"),
        ("exterior_wall_area_m2", "exterior_wall_area"),
        ("window_area_m2", "window_area"),
        ("shading_area_m2", "shading_area"),
    ]:
        if key in SPEC and not approx(data[data_key], SPEC[key], SPEC.get("area_tolerance_m2", 0.75)):
            return False
    return True


def check_hvac(objects):
    hvac = SPEC.get("hvac", {})
    mapping = {
        "ideal_loads": "OS:ZoneHVAC:IdealLoadsAirSystem",
        "equipment_lists": "OS:ZoneHVAC:EquipmentList",
        "thermostats": "OS:ThermostatSetpoint:DualSetpoint",
    }
    return all(len(by_type(objects, object_type)) == expected for key, object_type in mapping.items() for expected in [hvac.get(key, 0)])


def check_loads(objects):
    loads = SPEC.get("loads", {})
    mapping = {
        "people": "OS:People",
        "lights": "OS:Lights",
        "electric_equipment": "OS:ElectricEquipment",
        "space_types": "OS:SpaceType",
    }
    if len(by_type(objects, "OS:Schedule:Ruleset")) < loads.get("min_schedules", 0):
        return False
    return all(len(by_type(objects, object_type)) == expected for key, object_type in mapping.items() for expected in [loads.get(key, 0)])


def evaluate():
    root = DESKTOP
    if not check_no_gui_bypass(root):
        return False
    if not root.is_dir() or not check_required_outputs(root):
        return False
    objects = parse_osm(root / "result.osm")
    data = metrics(objects)
    return (
        check_counts(objects, data)
        and check_space_links(objects, data)
        and check_geometry(data)
        and check_hvac(objects)
        and check_loads(objects)
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
