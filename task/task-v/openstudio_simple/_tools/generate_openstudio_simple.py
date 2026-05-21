#!/usr/bin/env python3
import copy
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUBY = ROOT / "_tools" / "make_osm.rb"


BASE_INSTRUCTION = (
    "GUI-only requirement: Complete the task entirely in the launched OpenStudio Application graphical user interface. "
    "Do not open Terminal or a shell; do not run Ruby, Python, OpenStudio CLI, EnergyPlus command-line tools, shell commands, "
    "or helper scripts; do not edit OSM/OSW files directly outside the GUI. Use only OpenStudio Application GUI tools, dialogs, "
    "and built-in save/export commands. "
)


EVAL_TEMPLATE = r'''#!/usr/bin/env python3
import json
import math
from pathlib import Path
import subprocess
import tempfile


DESKTOP = Path("/home/user/Desktop")
SPEC = __SPEC__

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
'''


TASKS = [
    {
        "n": 1,
        "title": "Single Office Shell",
        "blank": True,
        "spaces": [{"name": "Office", "x0": 0, "y0": 0, "x1": 8, "y1": 5}],
        "height": 3.2,
        "windows": [],
        "intro": "Work in a new blank OpenStudio model with no init files. Save result.osm in the task output folder.",
        "goal": "Create a one-story rectangular office energy model with one space named Office and one thermal zone.",
    },
    {
        "n": 2,
        "title": "Two Room Suite",
        "blank": True,
        "spaces": [
            {"name": "Office-A", "x0": 0, "y0": 0, "x1": 5, "y1": 5},
            {"name": "Office-B", "x0": 5, "y0": 0, "x1": 10, "y1": 5},
        ],
        "height": 3.2,
        "intro": "Work in a new blank OpenStudio model with no init files. Save result.osm in the task output folder.",
        "goal": "Create a one-story two-room suite with spaces named Office-A and Office-B, each assigned to its own thermal zone.",
    },
    {
        "n": 3,
        "title": "Three Zone Clinic",
        "blank": True,
        "spaces": [
            {"name": "Reception", "x0": 0, "y0": 0, "x1": 6, "y1": 4},
            {"name": "Exam", "x0": 6, "y0": 0, "x1": 10, "y1": 4},
            {"name": "Storage", "x0": 0, "y0": 4, "x1": 10, "y1": 6},
        ],
        "height": 3.2,
        "intro": "Work in a new blank OpenStudio model with no init files. Save result.osm in the task output folder.",
        "goal": "Create a compact one-story clinic layout with spaces named Reception, Exam, and Storage, each assigned to its own thermal zone.",
    },
    {
        "n": 4,
        "title": "Office With Fixed Windows",
        "blank": True,
        "spaces": [{"name": "DaylitOffice", "x0": 0, "y0": 0, "x1": 10, "y1": 6}],
        "height": 3.2,
        "windows": [
            {"surface": "DaylitOffice South Wall", "name": "South Window 1", "width": 2.0, "height": 1.2, "offset": 1.0},
            {"surface": "DaylitOffice South Wall", "name": "South Window 2", "width": 2.0, "height": 1.2, "offset": 4.0},
            {"surface": "DaylitOffice North Wall", "name": "North Window 1", "width": 2.0, "height": 1.2, "offset": 1.0},
            {"surface": "DaylitOffice North Wall", "name": "North Window 2", "width": 2.0, "height": 1.2, "offset": 4.0},
        ],
        "intro": "Work in a new blank OpenStudio model with no init files. Save result.osm in the task output folder.",
        "goal": "Create a one-story space named DaylitOffice with one thermal zone and four FixedWindow subsurfaces on exterior walls.",
    },
    {
        "n": 5,
        "title": "Ideal Loads Starter",
        "blank": True,
        "spaces": [
            {"name": "OpenOffice", "x0": 0, "y0": 0, "x1": 8, "y1": 6, "thermostat": True, "ideal_loads": True},
            {"name": "Meeting", "x0": 8, "y0": 0, "x1": 12, "y1": 6, "thermostat": True, "ideal_loads": True},
        ],
        "height": 3.2,
        "min_schedules": 4,
        "intro": "Work in a new blank OpenStudio model with no init files. Save result.osm in the task output folder.",
        "goal": "Create two one-story spaces named OpenOffice and Meeting, each with a thermal zone, a dual setpoint thermostat, and an ideal loads air system.",
    },
    {
        "n": 6,
        "title": "Rename And Zone Cleanup",
        "spaces": [
            {"name": "Lobby", "x0": 0, "y0": 0, "x1": 5, "y1": 4},
            {"name": "Office", "x0": 5, "y0": 0, "x1": 10, "y1": 4},
        ],
        "init_spaces": [
            {"name": "Space-1", "x0": 0, "y0": 0, "x1": 5, "y1": 4},
            {"name": "Space-2", "x0": 5, "y0": 0, "x1": 10, "y1": 4},
        ],
        "goal": "Starting from init.osm, rename and clean up the two spaces so they are named Lobby and Office, with each space assigned to the building story and its own thermal zone.",
    },
    {
        "n": 7,
        "title": "Split Office Into Two Spaces",
        "spaces": [
            {"name": "WestOffice", "x0": 0, "y0": 0, "x1": 6, "y1": 6},
            {"name": "EastOffice", "x0": 6, "y0": 0, "x1": 12, "y1": 6},
        ],
        "init_spaces": [{"name": "OpenOffice", "x0": 0, "y0": 0, "x1": 12, "y1": 6}],
        "goal": "Starting from the one-space init.osm, split the office into two adjacent spaces named WestOffice and EastOffice, each assigned to a building story and its own thermal zone.",
    },
    {
        "n": 8,
        "title": "Add Missing Windows",
        "spaces": [{"name": "WindowOffice", "x0": 0, "y0": 0, "x1": 12, "y1": 6}],
        "init_spaces": [{"name": "WindowOffice", "x0": 0, "y0": 0, "x1": 12, "y1": 6}],
        "windows": [
            {"surface": "WindowOffice South Wall", "name": "South Window 1", "width": 2.0, "height": 1.2, "offset": 1.0},
            {"surface": "WindowOffice South Wall", "name": "South Window 2", "width": 2.0, "height": 1.2, "offset": 4.0},
            {"surface": "WindowOffice North Wall", "name": "North Window 1", "width": 2.0, "height": 1.2, "offset": 1.0},
        ],
        "goal": "Starting from init.osm, add three exterior FixedWindow subsurfaces to the existing WindowOffice space while keeping the space and thermal zone links intact.",
    },
    {
        "n": 9,
        "title": "Add Building Story Metadata",
        "spaces": [
            {"name": "StudioA", "x0": 0, "y0": 0, "x1": 5, "y1": 5},
            {"name": "StudioB", "x0": 5, "y0": 0, "x1": 10, "y1": 5},
            {"name": "Support", "x0": 0, "y0": 5, "x1": 10, "y1": 7},
        ],
        "init_spaces": [
            {"name": "StudioA", "x0": 0, "y0": 0, "x1": 5, "y1": 5},
            {"name": "StudioB", "x0": 5, "y0": 0, "x1": 10, "y1": 5},
            {"name": "Support", "x0": 0, "y0": 5, "x1": 10, "y1": 7},
        ],
        "init_no_space_links": True,
        "goal": "Starting from init.osm, make sure the spaces StudioA, StudioB, and Support are all assigned to one building story and to distinct thermal zones.",
    },
    {
        "n": 10,
        "title": "Boundary Condition Repair",
        "spaces": [
            {"name": "NorthRoom", "x0": 0, "y0": 4, "x1": 10, "y1": 8},
            {"name": "SouthRoom", "x0": 0, "y0": 0, "x1": 10, "y1": 4},
        ],
        "init_spaces": [
            {"name": "NorthRoom", "x0": 0, "y0": 4, "x1": 10, "y1": 8},
            {"name": "SouthRoom", "x0": 0, "y0": 0, "x1": 10, "y1": 4},
        ],
        "init_skip_surface_matching": True,
        "goal": "Starting from init.osm, repair the two-room model so floors are Ground, roofs and exterior walls are Outdoors, and the shared partition surfaces are Surface boundary condition.",
    },
    {
        "n": 11,
        "title": "Add Occupancy Schedule",
        "spaces": [{"name": "ScheduledOffice", "x0": 0, "y0": 0, "x1": 8, "y1": 5, "people": True}],
        "init_spaces": [{"name": "ScheduledOffice", "x0": 0, "y0": 0, "x1": 8, "y1": 5}],
        "min_schedules": 1,
        "goal": "Starting from init.osm, add one People load to ScheduledOffice and assign it a simple occupancy schedule.",
    },
    {
        "n": 12,
        "title": "Add Lighting Loads",
        "spaces": [{"name": "LightingOffice", "x0": 0, "y0": 0, "x1": 9, "y1": 5, "lights": True}],
        "init_spaces": [{"name": "LightingOffice", "x0": 0, "y0": 0, "x1": 9, "y1": 5}],
        "min_schedules": 1,
        "goal": "Starting from init.osm, add one Lights load to LightingOffice and assign it a lighting schedule.",
    },
    {
        "n": 13,
        "title": "Add Equipment Loads",
        "spaces": [{"name": "EquipmentRoom", "x0": 0, "y0": 0, "x1": 7, "y1": 5, "equipment": True}],
        "init_spaces": [{"name": "EquipmentRoom", "x0": 0, "y0": 0, "x1": 7, "y1": 5}],
        "min_schedules": 1,
        "goal": "Starting from init.osm, add one ElectricEquipment load to EquipmentRoom and assign it a schedule.",
    },
    {
        "n": 14,
        "title": "Space Type Assignment",
        "spaces": [
            {"name": "Office1", "x0": 0, "y0": 0, "x1": 5, "y1": 5, "people": True, "lights": True},
            {"name": "Office2", "x0": 5, "y0": 0, "x1": 10, "y1": 5, "people": True, "lights": True},
        ],
        "init_spaces": [
            {"name": "Office1", "x0": 0, "y0": 0, "x1": 5, "y1": 5},
            {"name": "Office2", "x0": 5, "y0": 0, "x1": 10, "y1": 5},
        ],
        "space_types": 1,
        "min_schedules": 2,
        "goal": "Starting from init.osm, create an OfficeType space type, assign both spaces to it, and provide office people and lighting load metadata.",
    },
    {
        "n": 15,
        "title": "Mixed Loads Suite",
        "spaces": [
            {"name": "Workroom", "x0": 0, "y0": 0, "x1": 7, "y1": 5, "people": True, "lights": True, "equipment": True},
            {"name": "Breakroom", "x0": 7, "y0": 0, "x1": 11, "y1": 5, "people": True, "lights": True, "equipment": True},
        ],
        "init_spaces": [
            {"name": "Workroom", "x0": 0, "y0": 0, "x1": 7, "y1": 5},
            {"name": "Breakroom", "x0": 7, "y0": 0, "x1": 11, "y1": 5},
        ],
        "min_schedules": 2,
        "goal": "Starting from init.osm, add people, lights, and electric equipment loads for both Workroom and Breakroom, using schedules for the loads.",
    },
    {
        "n": 16,
        "title": "Thermostat Retrofit",
        "spaces": [
            {"name": "ZoneA", "x0": 0, "y0": 0, "x1": 6, "y1": 5, "thermostat": True},
            {"name": "ZoneB", "x0": 6, "y0": 0, "x1": 12, "y1": 5, "thermostat": True},
        ],
        "init_spaces": [
            {"name": "ZoneA", "x0": 0, "y0": 0, "x1": 6, "y1": 5},
            {"name": "ZoneB", "x0": 6, "y0": 0, "x1": 12, "y1": 5},
        ],
        "min_schedules": 4,
        "goal": "Starting from init.osm, add one dual setpoint thermostat to each thermal zone, using simple heating and cooling setpoint schedules.",
    },
    {
        "n": 17,
        "title": "Ideal Loads Retrofit",
        "spaces": [
            {"name": "NorthOffice", "x0": 0, "y0": 5, "x1": 10, "y1": 10, "thermostat": True, "ideal_loads": True},
            {"name": "SouthOffice", "x0": 0, "y0": 0, "x1": 10, "y1": 5, "thermostat": True, "ideal_loads": True},
        ],
        "init_spaces": [
            {"name": "NorthOffice", "x0": 0, "y0": 5, "x1": 10, "y1": 10},
            {"name": "SouthOffice", "x0": 0, "y0": 0, "x1": 10, "y1": 5},
        ],
        "min_schedules": 4,
        "goal": "Starting from init.osm, add ideal loads air systems and dual setpoint thermostats for NorthOffice and SouthOffice.",
    },
    {
        "n": 18,
        "title": "South Window Retrofit",
        "spaces": [{"name": "SouthDaylit", "x0": 0, "y0": 0, "x1": 12, "y1": 6}],
        "init_spaces": [{"name": "SouthDaylit", "x0": 0, "y0": 0, "x1": 12, "y1": 6}],
        "windows": [
            {"surface": "SouthDaylit South Wall", "name": "South Fixed Window 1", "width": 2.4, "height": 1.4, "offset": 1.0},
            {"surface": "SouthDaylit South Wall", "name": "South Fixed Window 2", "width": 2.4, "height": 1.4, "offset": 4.5},
        ],
        "goal": "Starting from init.osm, add two south-facing FixedWindow subsurfaces to SouthDaylit and keep the rest of the single-zone model intact.",
    },
    {
        "n": 19,
        "title": "Simple Overhang Shading",
        "spaces": [{"name": "ShadedOffice", "x0": 0, "y0": 0, "x1": 10, "y1": 6}],
        "init_spaces": [{"name": "ShadedOffice", "x0": 0, "y0": 0, "x1": 10, "y1": 6}],
        "windows": [{"surface": "ShadedOffice South Wall", "name": "South Fixed Window", "width": 4.0, "height": 1.5, "offset": 3.0}],
        "shading": [{"name": "South Overhang", "points": [[2.5, -0.8, 2.8], [7.5, -0.8, 2.8], [7.5, 0, 2.8], [2.5, 0, 2.8]]}],
        "goal": "Starting from init.osm, add one south-facing FixedWindow and one simple exterior overhang shading surface above it.",
    },
    {
        "n": 20,
        "title": "Combined Simple Retrofit",
        "spaces": [
            {"name": "Office", "x0": 0, "y0": 0, "x1": 8, "y1": 6, "people": True, "lights": True, "equipment": True, "thermostat": True, "ideal_loads": True},
            {"name": "Conference", "x0": 8, "y0": 0, "x1": 14, "y1": 6, "people": True, "lights": True, "equipment": True, "thermostat": True, "ideal_loads": True},
        ],
        "init_spaces": [
            {"name": "Office", "x0": 0, "y0": 0, "x1": 8, "y1": 6},
            {"name": "Conference", "x0": 8, "y0": 0, "x1": 14, "y1": 6},
        ],
        "windows": [
            {"surface": "Office South Wall", "name": "Office South Window", "width": 2.0, "height": 1.2, "offset": 1.0},
            {"surface": "Conference South Wall", "name": "Conference South Window", "width": 2.0, "height": 1.2, "offset": 1.0},
        ],
        "shading": [{"name": "Shared South Overhang", "points": [[1, -0.8, 2.8], [13, -0.8, 2.8], [13, 0, 2.8], [1, 0, 2.8]]}],
        "min_schedules": 6,
        "goal": "Starting from init.osm, complete a small office retrofit by adding fixed windows, one exterior overhang, people/lights/equipment loads, thermostats, and ideal loads systems.",
    },
]


def osm_spec(task, init=False):
    spec = {
        "height": task.get("height", 3.2),
        "spaces": copy.deepcopy(task.get("init_spaces" if init else "spaces", task["spaces"])),
        "space_types": 0 if init else int(task.get("space_types", 0)),
    }
    if init and task.get("init_no_space_links"):
        spec["no_space_links"] = True
    if init and task.get("init_skip_surface_matching"):
        spec["skip_surface_matching"] = True
    if not init:
        spec["windows"] = copy.deepcopy(task.get("windows", []))
        spec["shading"] = copy.deepcopy(task.get("shading", []))
    else:
        spec["windows"] = copy.deepcopy(task.get("init_windows", []))
        spec["shading"] = copy.deepcopy(task.get("init_shading", []))
    return spec


def generate_osm_metrics(task):
    tmp = ROOT / "_tools" / f"_task_{task['n']:02d}_spec.json"
    out = ROOT / "_tools" / f"_task_{task['n']:02d}_target.osm"
    tmp.write_text(json.dumps(osm_spec(task), indent=2), encoding="utf-8")
    subprocess.run(["openstudio", "execute_ruby_script", str(RUBY), str(tmp), str(out)], check=True)
    eval_script = ROOT / "_tools" / "_inspect_eval.py"
    return out, tmp


def dump_objects(osm_path):
    ruby = ROOT / "_tools" / "_dump.rb"
    ruby.write_text(
        "require 'openstudio'\nrequire 'json'\npath=ARGV[0]\n"
        "idf=OpenStudio::IdfFile.load(path).get\nobjs=[]\n"
        "v=idf.versionObject\nobjs << v.get unless v.empty?\nobjs.concat(idf.objects)\n"
        "STDOUT.write(JSON.generate(objs.map{|o| {'type'=>o.iddObject.name.to_s,'fields'=>(0...o.numFields).map{|i| o.getField(i).to_s}}}))\n",
        encoding="utf-8",
    )
    proc = subprocess.run(["openstudio", "execute_ruby_script", str(ruby), str(osm_path)], text=True, capture_output=True, check=True)
    payload = proc.stdout
    payload = payload[payload.find("["):]
    return json.loads(payload)


def obj_name(obj):
    return obj["fields"][1] if len(obj["fields"]) > 1 else ""


def parse_vertices(fields, start_index):
    values = [float(v) for v in fields[start_index:]]
    return [(values[i], values[i + 1], values[i + 2]) for i in range(0, len(values), 3)]


def area(points):
    sx = sy = sz = 0.0
    for i, p1 in enumerate(points):
        p2 = points[(i + 1) % len(points)]
        sx += (p1[1] - p2[1]) * (p1[2] + p2[2])
        sy += (p1[2] - p2[2]) * (p1[0] + p2[0])
        sz += (p1[0] - p2[0]) * (p1[1] + p2[1])
    return 0.5 * (sx * sx + sy * sy + sz * sz) ** 0.5


def target_spec(task, osm_path):
    objects = dump_objects(osm_path)
    by_type = {}
    for obj in objects:
        by_type.setdefault(obj["type"], []).append(obj)
    surfaces = []
    for obj in by_type.get("OS:Surface", []):
        fields = obj["fields"]
        pts = parse_vertices(fields, 11)
        surfaces.append({"type": fields[2], "obc": fields[5], "points": pts, "area": area(pts)})
    subs = []
    for obj in by_type.get("OS:SubSurface", []):
        fields = obj["fields"]
        pts = parse_vertices(fields, 10)
        subs.append({"type": fields[2], "points": pts, "area": area(pts)})
    shading = []
    for obj in by_type.get("OS:ShadingSurface", []):
        pts = parse_vertices(obj["fields"], 6)
        shading.append({"points": pts, "area": area(pts)})
    points = [p for s in surfaces for p in s["points"]]
    xs, ys, zs = zip(*points)
    spec = {
        "required_outputs": {"result.osm": 500},
        "object_counts": {
            "OS:BuildingStory": len(by_type.get("OS:BuildingStory", [])),
            "OS:Space": len(by_type.get("OS:Space", [])),
            "OS:ThermalZone": len(by_type.get("OS:ThermalZone", [])),
            "OS:Surface": len(surfaces),
            "OS:SubSurface": len(subs),
        },
        "space_names": sorted(obj_name(o) for o in by_type.get("OS:Space", [])),
        "surface_counts": {
            "Floor": sum(1 for s in surfaces if s["type"] == "Floor"),
            "RoofCeiling": sum(1 for s in surfaces if s["type"] == "RoofCeiling"),
            "Wall": sum(1 for s in surfaces if s["type"] == "Wall"),
        },
        "outside_boundary_counts": {
            "Ground": sum(1 for s in surfaces if s["obc"] == "Ground"),
            "Outdoors": sum(1 for s in surfaces if s["obc"] == "Outdoors"),
            "Surface": sum(1 for s in surfaces if s["obc"] == "Surface"),
        },
        "window_count": len(subs),
        "fixed_window_count": sum(1 for s in subs if s["type"] == "FixedWindow"),
        "bbox_spans_m": [round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3), round(max(zs) - min(zs), 3)],
        "floor_area_m2": round(sum(s["area"] for s in surfaces if s["type"] == "Floor"), 3),
        "exterior_wall_area_m2": round(sum(s["area"] for s in surfaces if s["type"] == "Wall" and s["obc"] == "Outdoors"), 3),
        "window_area_m2": round(sum(s["area"] for s in subs), 3),
        "hvac": {
            "ideal_loads": len(by_type.get("OS:ZoneHVAC:IdealLoadsAirSystem", [])),
            "equipment_lists": len(by_type.get("OS:ZoneHVAC:EquipmentList", [])),
            "thermostats": len(by_type.get("OS:ThermostatSetpoint:DualSetpoint", [])),
        },
        "loads": {
            "min_schedules": int(task.get("min_schedules", 0)),
            "people": len(by_type.get("OS:People", [])),
            "lights": len(by_type.get("OS:Lights", [])),
            "electric_equipment": len(by_type.get("OS:ElectricEquipment", [])),
            "space_types": int(task.get("space_types", 0)),
        },
    }
    if shading:
        spec["object_counts"]["OS:ShadingSurface"] = len(shading)
        spec["shading_surface_count"] = len(shading)
        spec["shading_area_m2"] = round(sum(s["area"] for s in shading), 3)
    return spec


def instruction(task, spec):
    intro = task.get(
        "intro",
        "Work in the opened OpenStudio application, starting from the Desktop input file init.osm. Modify the model rather than replacing the task package with an unrelated file. Save result.osm in the task output folder.",
    )
    names = ", ".join(spec["space_names"][:-1]) + (" and " + spec["space_names"][-1] if len(spec["space_names"]) > 1 else spec["space_names"][0])
    parts = [
        BASE_INSTRUCTION,
        f"{task['title']}. {intro} {task['goal']} ",
        f"The completed model must contain {spec['object_counts']['OS:BuildingStory']} building story, {spec['object_counts']['OS:Space']} spaces and {spec['object_counts']['OS:ThermalZone']} thermal zones. ",
        f"Use these exact OS:Space names: {names}. Every space must be assigned to a building story and a thermal zone, and each space must have more than 0.05 m2 of floor area. ",
        f"Model the enclosure with {spec['object_counts']['OS:Surface']} OS:Surface objects, split into {spec['surface_counts']['Floor']} floor surfaces, {spec['surface_counts']['RoofCeiling']} roof/ceiling surfaces and {spec['surface_counts']['Wall']} wall surfaces. ",
        f"The surface outside-boundary counts should be {spec['outside_boundary_counts'].get('Ground', 0)} Ground, {spec['outside_boundary_counts'].get('Outdoors', 0)} Outdoors and {spec['outside_boundary_counts'].get('Surface', 0)} Surface. ",
    ]
    if spec["object_counts"]["OS:SubSurface"]:
        parts.append(f"Add {spec['object_counts']['OS:SubSurface']} OS:SubSurface objects, all FixedWindow windows, with total fixed-window area {spec['window_area_m2']:.2f} m2 within +/-0.75 m2. ")
    else:
        parts.append("Do not add any windows or other subsurfaces. ")
    hvac = spec["hvac"]
    loads = spec["loads"]
    if any(hvac.values()):
        parts.append(f"Include {hvac['ideal_loads']} ideal-loads air systems, {hvac['equipment_lists']} zone HVAC equipment lists and {hvac['thermostats']} dual-setpoint thermostats. ")
    if any(loads.values()):
        parts.append(f"Include simple metadata objects for schedules and loads: at least {loads['min_schedules']} schedule rulesets, {loads['people']} people loads, {loads['lights']} lights loads, {loads['electric_equipment']} electric equipment loads and {loads['space_types']} space type objects. ")
    if spec.get("shading_surface_count"):
        parts.append(f"Add {spec['shading_surface_count']} exterior shading surface with total shading area {spec['shading_area_m2']:.2f} m2 within +/-0.75 m2. ")
    parts.append(
        f"Set the geometry so the overall surface-geometry bounding box spans {spec['bbox_spans_m'][0]:.2f} m in X, {spec['bbox_spans_m'][1]:.2f} m in Y and {spec['bbox_spans_m'][2]:.2f} m in Z, each within +/-0.10 m. "
        f"The total floor surface area should be {spec['floor_area_m2']:.2f} m2 within +/-0.75 m2 and the total exterior wall gross area should be {spec['exterior_wall_area_m2']:.2f} m2 within +/-0.75 m2. "
        "Other model details may vary as long as the saved OSM satisfies these stated requirements."
    )
    return "".join(parts)


def task_json(task, spec):
    n = task["n"]
    uploads = []
    command = ["OpenStudioApp"]
    if not task.get("blank"):
        uploads.append({"local_path": f"task-{n:02d}/init_file/init.osm", "path": "/home/user/Desktop/init.osm"})
        command.append("/home/user/Desktop/init.osm")
    return {
        "id": f"v-openstudio-simple-task-{n:02d}-ubuntu",
        "snapshot": "OpenStudio-1.11.0",
        "instruction": instruction(task, spec),
        "source": "https://github.com/openstudiocoalition/OpenStudioApplication",
        "config": [
            {"type": "upload_file", "parameters": {"files": uploads}},
            {"type": "launch", "parameters": {"command": command}},
        ],
        "trajectory": "trajectories/",
        "related_apps": ["openstudio"],
        "evaluator": {
            "postconfig": [
                {"type": "upload_file", "parameters": {"files": [{"local_path": f"task-{n:02d}/eval.py", "path": "/home/user/Desktop/eval.py"}]}}
            ],
            "func": "exact_match",
            "result": {"type": "vm_command_line", "command": "python3 /home/user/Desktop/eval.py", "shell": "true"},
            "expected": {"type": "rule", "rules": {"expected": "True\n"}},
        },
        "proxy": False,
        "fixed_ip": False,
        "possibility_of_env_change": "low",
    }


def main():
    for task in TASKS:
        n = task["n"]
        task_dir = ROOT / f"task-{n:02d}"
        task_dir.mkdir(parents=True, exist_ok=True)
        target_osm, target_json = generate_osm_metrics(task)
        spec = target_spec(task, target_osm)
        eval_py = EVAL_TEMPLATE.replace("__SPEC__", repr(spec))
        (task_dir / "eval.py").write_text(eval_py, encoding="utf-8")
        (task_dir / f"task-{n:02d}.json").write_text(json.dumps(task_json(task, spec), indent=2) + "\n", encoding="utf-8")
        if not task.get("blank"):
            init_dir = task_dir / "init_file"
            init_dir.mkdir(exist_ok=True)
            init_spec_path = ROOT / "_tools" / f"_task_{n:02d}_init_spec.json"
            init_spec_path.write_text(json.dumps(osm_spec(task, init=True), indent=2), encoding="utf-8")
            subprocess.run(["openstudio", "execute_ruby_script", str(RUBY), str(init_spec_path), str(init_dir / "init.osm")], check=True)
    print("generated 20 openstudio_simple tasks")


if __name__ == "__main__":
    main()
