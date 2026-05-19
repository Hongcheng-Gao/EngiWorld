#!/usr/bin/env python3
import json
import math
from pathlib import Path
import subprocess
import tempfile


DESKTOP = Path("/home/user/Desktop")


GUI_BYPASS_FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr"
}
GUI_BYPASS_ALLOWED_FILENAMES = {"eval.py"}
GUI_BYPASS_OUTPUT_TOKENS = (
    "result.ifc", "result.pdf", "result.osm", "workflow.osw", "summary.txt",
    "report.csv", "result.csv"
)
GUI_BYPASS_COMMAND_TOKENS = (
    "python", "python3", "py ", "powershell", "pwsh", "cmd.exe", "cmd /c",
    "bash", " sh ", "zsh", "node", "ruby", "perl", "ifcopenshell",
    "openstudio", "energyplus", "blender --background", "revitbatchprocessor"
)


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
            if not path.is_file():
                continue
            if path.name in GUI_BYPASS_ALLOWED_FILENAMES:
                continue
            if path.suffix.lower() in GUI_BYPASS_FORBIDDEN_EXTENSIONS:
                return True
    except Exception:
        return True
    return False


def _history_paths(root):
    home = Path.home()
    paths = [
        home / ".bash_history",
        home / ".zsh_history",
        home / ".python_history",
        home / ".local/share/fish/fish_history",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/Visual Studio Code Host_history.txt",
        root / ".bash_history",
        root / ".zsh_history",
    ]
    return paths


def _history_contains_bypass(root):
    for path in _history_paths(root):
        if not path.is_file():
            continue
        text = _read_text_safe(path).lower()
        if not text:
            continue
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
    if _desktop_script_artifacts(root):
        return False
    if _history_contains_bypass(root):
        return False
    return True

SPEC = {'required_outputs': {'result.osm': 500}, 'object_counts': {'OS:BuildingStory': 2, 'OS:Space': 10, 'OS:ThermalZone': 10, 'OS:Surface': 68, 'OS:SubSurface': 16, 'OS:ZoneHVAC:IdealLoadsAirSystem': 10, 'OS:ZoneHVAC:EquipmentList': 10, 'OS:ThermostatSetpoint:DualSetpoint': 10}, 'space_names': ['V11-F1-North', 'V11-F1-South', 'V11-F1-West', 'V11-F1-East', 'V11-F1-Core', 'V11-F2-North', 'V11-F2-South', 'V11-F2-West', 'V11-F2-East', 'V11-F2-Core'], 'surface_counts': {'Floor': 10, 'RoofCeiling': 10, 'Wall': 48}, 'outside_boundary_counts': {'Ground': 5, 'Outdoors': 21, 'Surface': 42}, 'window_count': 16, 'fixed_window_count': 16, 'bbox_spans_m': [28.0, 20.0, 8.0], 'floor_area_m2': 1120.0, 'exterior_wall_area_m2': 768.0, 'window_area_m2': 245.76, 'hvac': {'ideal_loads': 10, 'equipment_lists': 10, 'thermostats': 10}}
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




def metrics(objects):
    surfaces = surface_data(objects)
    subsurfaces = subsurface_data(objects)
    shading_surfaces = shading_surface_data(objects)
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
        "shading_surfaces": shading_surfaces,
        "bounds": bounds,
        "spans": spans,
        "floors": floors,
        "exterior_walls": exterior_walls,
        "windows": windows,
        "floor_area": sum(s["area"] for s in floors),
        "exterior_wall_area": sum(s["area"] for s in exterior_walls),
        "window_area": sum(s["area"] for s in windows),
        "shading_area": sum(s["area"] for s in shading_surfaces),
        "floor_area_by_space": floor_area_by_space,
    }


def check_required_outputs(root):
    for rel, min_bytes in SPEC["required_outputs"].items():
        path = root / rel
        if not path.is_file() or path.stat().st_size < min_bytes:
            return False
    return True


def check_version(objects):
    prefix = SPEC.get("openstudio_version_prefix")
    if not prefix:
        return True
    versions = by_type(objects, "OS:Version")
    return len(versions) == 1 and versions[0]["fields"] and versions[0]["fields"][-1].startswith(prefix)


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
    if SPEC.get("fixed_window_count") is not None and sum(1 for w in data["windows"] if w["subsurface_type"] == "FixedWindow") != int(SPEC["fixed_window_count"]):
        return False
    if SPEC.get("shading_surface_count") is not None and len(data["shading_surfaces"]) != int(SPEC["shading_surface_count"]):
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
    if SPEC.get("shading_area_m2") is not None and not approx(data["shading_area"], SPEC["shading_area_m2"], SPEC.get("area_tolerance_m2", 0.5)):
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




def check_workflow(root):
    workflow = SPEC.get("workflow")
    if not workflow:
        return True
    payload = json.loads((root / "workflow.osw").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return False
    for key in workflow["required_keys"]:
        if key not in payload:
            return False
    if len(payload.get("steps", [])) < workflow.get("min_steps", 0):
        return False
    return True


def evaluate():
    root = DESKTOP
    if not check_no_gui_bypass(root):
        return False
    if not root.is_dir() or not check_required_outputs(root):
        return False
    objects = parse_osm(root / "result.osm")
    if not objects:
        return False
    data = metrics(objects)
    return (
        check_counts(objects, data)
        and check_space_links(objects, data)
        and check_geometry(data)
        and check_hvac(objects)
        and check_workflow(root)
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
