#!/usr/bin/env python3
import re
from pathlib import Path

import ifcopenshell


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
import ifcopenshell.geom
import ifcopenshell.util.unit


SPEC = {
    "ifc_file": "result.ifc",
    "min_ifc_bytes": 500,
    "schema": "IFC4",
    "counts": {
        "IfcProject": 1,
        "IfcSite": 1,
        "IfcBuilding": 1,
        "IfcBuildingStorey": 1,
        "IfcSpace": 5,
        "IfcWall": 7,
        "IfcSlab": 3,
        "IfcDoor": 1,
        "IfcWindow": 4,
        "IfcOpeningElement": 5,
        "IfcRelVoidsElement": 5,
        "IfcRelFillsElement": 5,
    },
    "forbidden_counts": {
        "IfcBuildingElementProxy": 0,
        "IfcFurniture": 0,
        "IfcRoof": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcStair": 0,
        "IfcFlowTerminal": 0,
    },
    "storey_names": ["Bungalow Level"],
    "space_dimensions": {
        "Living": (5.80, 3.00),
        "Kitchen": (2.80, 3.00),
        "Bed 1": (2.80, 2.60),
        "Bed 2": (3.00, 2.60),
        "Bath": (2.80, 2.60),
    },
    "space_tolerance_m": 0.10,
    "slab_names": ["Main Slab", "Main Roof", "Porch Canopy"],
    "roof_slab_min_z": {"Main Roof": 3.00, "Porch Canopy": 2.50},
    "porch_canopy_max_y": 0.00,
    "wall_height_m": 3.00,
    "wall_height_tolerance_m": 0.10,
    "door_widths": {"Entrance Door": 0.90},
    "window_widths": {
        "Kitchen Window": 1.20,
        "Bed1 Window": 1.20,
        "Bed2 Window": 1.20,
        "Bath Window": 1.20,
    },
    "opening_hosts": {
        "Entrance Door": ("IfcDoor", "South Wall"),
        "Kitchen Window": ("IfcWindow", "East Wall"),
        "Bed1 Window": ("IfcWindow", "North Wall"),
        "Bed2 Window": ("IfcWindow", "North Wall"),
        "Bath Window": ("IfcWindow", "North Wall"),
    },
    "width_tolerance_m": 0.05,
}


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def one_space(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def approx(actual, expected, tolerance):
    return abs(float(actual) - float(expected)) <= float(tolerance)


def unit_scale(model):
    try:
        return float(ifcopenshell.util.unit.calculate_unit_scale(model))
    except Exception:
        return 1.0


def entity_count(model, ifc_class):
    return len(model.by_type(ifc_class))


def check_counts(model):
    for ifc_class, expected in SPEC["counts"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    for ifc_class, expected in SPEC["forbidden_counts"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    return True


def check_global_ids(model):
    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]
    return len(gids) == len(set(gids))


def shape_bbox(entity):
    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    shape = ifcopenshell.geom.create_shape(settings, entity)
    verts = list(shape.geometry.verts)
    if not verts:
        return None
    xs = verts[0::3]
    ys = verts[1::3]
    zs = verts[2::3]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def span(bbox):
    minx, miny, minz, maxx, maxy, maxz = bbox
    return (maxx - minx, maxy - miny, maxz - minz)


def named_entities(model, ifc_class):
    return {one_space(getattr(e, "Name", "")): e for e in model.by_type(ifc_class)}


def scaled_width(entity, model):
    value = getattr(entity, "OverallWidth", None)
    if value in (None, ""):
        return None
    raw = float(value)
    scaled = raw * unit_scale(model)
    if 0.05 <= scaled <= 50.0:
        return scaled
    return raw


def filling_opening(fill):
    rels = getattr(fill, "FillsVoids", None) or []
    if len(rels) != 1:
        return None
    return getattr(rels[0], "RelatingOpeningElement", None)


def opening_host(opening):
    rels = getattr(opening, "VoidsElements", None) or []
    if len(rels) != 1:
        return None
    return getattr(rels[0], "RelatingBuildingElement", None)


def check_storeys(model):
    names = sorted(one_space(getattr(s, "Name", "")) for s in model.by_type("IfcBuildingStorey"))
    return names == sorted(SPEC["storey_names"])


def check_space_geometry(model):
    spaces = named_entities(model, "IfcSpace")
    if set(spaces) != set(SPEC["space_dimensions"]):
        return False
    for name, (expected_x, expected_y) in SPEC["space_dimensions"].items():
        bbox = shape_bbox(spaces[name])
        if bbox is None:
            return False
        sx, sy, _ = span(bbox)
        tol = SPEC["space_tolerance_m"]
        if not approx(sx, expected_x, tol) or not approx(sy, expected_y, tol):
            return False
    return True


def check_slabs(model):
    slabs = named_entities(model, "IfcSlab")
    if set(slabs) != set(SPEC["slab_names"]):
        return False
    for name, min_z in SPEC["roof_slab_min_z"].items():
        bbox = shape_bbox(slabs[name])
        if bbox is None or bbox[2] < min_z:
            return False
    porch_bbox = shape_bbox(slabs["Porch Canopy"])
    return porch_bbox is not None and porch_bbox[1] < SPEC["porch_canopy_max_y"]


def check_wall_geometry(model):
    for wall in model.by_type("IfcWall"):
        bbox = shape_bbox(wall)
        if bbox is None:
            return False
        _, _, sz = span(bbox)
        if not approx(sz, SPEC["wall_height_m"], SPEC["wall_height_tolerance_m"]):
            return False
    return True


def check_widths(model):
    doors = named_entities(model, "IfcDoor")
    windows = named_entities(model, "IfcWindow")
    tol = SPEC["width_tolerance_m"]
    for name, expected in SPEC["door_widths"].items():
        if name not in doors or not approx(scaled_width(doors[name], model), expected, tol):
            return False
    for name, expected in SPEC["window_widths"].items():
        if name not in windows or not approx(scaled_width(windows[name], model), expected, tol):
            return False
    return True


def check_openings(model):
    walls = named_entities(model, "IfcWall")
    fills = {}
    for ifc_class in ("IfcDoor", "IfcWindow"):
        fills.update({name: (ifc_class, entity) for name, entity in named_entities(model, ifc_class).items()})
    used_openings = set()
    for fill_name, (ifc_class, host_name) in SPEC["opening_hosts"].items():
        if fill_name not in fills or fills[fill_name][0] != ifc_class or host_name not in walls:
            return False
        opening = filling_opening(fills[fill_name][1])
        if opening is None or opening.id() in used_openings:
            return False
        host = opening_host(opening)
        if host is None or host.id() != walls[host_name].id():
            return False
        used_openings.add(opening.id())
    return True


def check_ifc(root):
    if not check_no_gui_bypass(root):
        return False
    path = root / SPEC["ifc_file"]
    if not path.is_file() or path.stat().st_size < SPEC["min_ifc_bytes"]:
        return False
    model = ifcopenshell.open(str(path))
    if not str(getattr(model, "schema", "")).upper().startswith(SPEC["schema"]):
        return False
    return (
        check_counts(model)
        and check_global_ids(model)
        and check_storeys(model)
        and check_space_geometry(model)
        and check_slabs(model)
        and check_wall_geometry(model)
        and check_widths(model)
        and check_openings(model)
    )


def main():
    try:
        root = DESKTOP
        finish(root.is_dir() and check_ifc(root))
    except SystemExit:
        raise
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
