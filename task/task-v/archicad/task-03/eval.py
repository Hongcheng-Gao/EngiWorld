#!/usr/bin/env python3
import os
import re
from pathlib import Path

DESKTOP = Path(os.environ.get("ENGIWORLD_DESKTOP", "C:/Users/user/Desktop"))

GUI_BYPASS_FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr",
}
GUI_BYPASS_ALLOWED_FILENAMES = {"eval.py"}
GUI_BYPASS_OUTPUT_TOKENS = ("result.ifc", "result.pdf", "result.osm", "workflow.osw", "summary.txt", "report.csv", "result.csv")
GUI_BYPASS_COMMAND_TOKENS = (
    "python", "python3", "py ", "powershell", "pwsh", "cmd.exe", "cmd /c",
    "bash", " sh ", "zsh", "node", "ruby", "perl", "ifcopenshell",
    "openstudio", "energyplus", "blender --background", "revitbatchprocessor",
)

SPEC = {'ifc_file': 'result.ifc', 'min_ifc_bytes': 500, 'schema': 'IFC4', 'space_names': ['CAFE', 'COUNTER', 'KITCHEN', 'STORE', 'STAFF', 'WC'], 'exact_counts': {'projects': 1, 'sites': 1, 'buildings': 1, 'storeys': 1, 'spaces': 6}, 'min_counts': {'walls': 12, 'slabs': 1, 'roofs': 1, 'doors': 6, 'windows': 5}, 'overall_span_ranges_m': {'x': [13.0, 15.2], 'y': [7.0, 9.2], 'z': [2.9000000000000004, 4.5]}, 'roof_min_z': 2.8}


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
    return [
        home / ".bash_history",
        home / ".zsh_history",
        home / ".python_history",
        home / ".local/share/fish/fish_history",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/Visual Studio Code Host_history.txt",
        root / ".bash_history",
        root / ".zsh_history",
    ]


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
    return not _desktop_script_artifacts(root) and not _history_contains_bypass(root)


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ").strip()).lower()


def entity_count(model, classes):
    if isinstance(classes, str):
        classes = [classes]
    return sum(len(model.by_type(name)) for name in classes)


def unique_global_ids(model):
    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]
    return bool(gids) and len(gids) == len(set(gids))


def check_counts(model):
    class_map = {
        "projects": "IfcProject",
        "sites": "IfcSite",
        "buildings": "IfcBuilding",
        "storeys": "IfcBuildingStorey",
        "spaces": "IfcSpace",
        "walls": ["IfcWall", "IfcWallStandardCase"],
        "slabs": "IfcSlab",
        "roofs": "IfcRoof",
        "doors": "IfcDoor",
        "windows": "IfcWindow",
        "stairs": "IfcStair",
        "columns": "IfcColumn",
        "beams": "IfcBeam",
        "curtain_walls": "IfcCurtainWall",
    }
    for key, exact in SPEC.get("exact_counts", {}).items():
        if entity_count(model, class_map[key]) != exact:
            return False
    for key, minimum in SPEC.get("min_counts", {}).items():
        if entity_count(model, class_map[key]) < minimum:
            return False
    alt = SPEC.get("alternative_min_counts")
    if alt:
        if not any(entity_count(model, class_map[key]) >= minimum for key, minimum in alt):
            return False
    return True


def check_forbidden(model):
    return entity_count(model, "IfcBuildingElementProxy") == 0


def check_space_names(model):
    actual = [norm(getattr(space, "Name", "") or getattr(space, "LongName", "")) for space in model.by_type("IfcSpace")]
    required = [norm(name) for name in SPEC["space_names"]]
    return sorted(actual) == sorted(required)


def product_bbox(product):
    import ifcopenshell.geom

    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    shape = ifcopenshell.geom.create_shape(settings, product)
    verts = list(shape.geometry.verts)
    if not verts:
        return None
    xs, ys, zs = verts[0::3], verts[1::3], verts[2::3]
    return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)


def shaped_product_bbox(model):
    products = []
    for ifc_class in ("IfcWall", "IfcWallStandardCase", "IfcSlab", "IfcRoof", "IfcDoor", "IfcWindow", "IfcStair", "IfcColumn", "IfcBeam", "IfcCurtainWall"):
        products.extend(model.by_type(ifc_class))
    mins = [None, None, None]
    maxs = [None, None, None]
    shaped = 0
    for product in products:
        try:
            bbox = product_bbox(product)
        except Exception:
            continue
        if bbox is None:
            continue
        shaped += 1
        for i, value in enumerate(bbox[:3]):
            mins[i] = value if mins[i] is None else min(mins[i], value)
        for i, value in enumerate(bbox[3:]):
            maxs[i] = value if maxs[i] is None else max(maxs[i], value)
    if shaped == 0:
        return None
    return (*mins, *maxs)


def check_overall_size(model):
    ranges = SPEC.get("overall_span_ranges_m") or {}
    if not ranges:
        return True
    bbox = shaped_product_bbox(model)
    if bbox is None:
        return False
    minx, miny, minz, maxx, maxy, maxz = bbox
    spans = {"x": maxx - minx, "y": maxy - miny, "z": maxz - minz}
    for axis, limits in ranges.items():
        low, high = limits
        if not (low <= spans[axis] <= high):
            return False
    return True


def check_roof_height(model):
    roof_min = SPEC.get("roof_min_z")
    if roof_min is None or entity_count(model, "IfcRoof") == 0:
        return True
    for roof in model.by_type("IfcRoof"):
        try:
            bbox = product_bbox(roof)
        except Exception:
            continue
        if bbox and bbox[2] >= roof_min:
            return True
    return False


def evaluate(root):
    root = Path(root)
    if not check_no_gui_bypass(root):
        return False
    path = root / SPEC["ifc_file"]
    if not path.is_file() or path.stat().st_size < SPEC["min_ifc_bytes"]:
        return False
    import ifcopenshell

    model = ifcopenshell.open(str(path))
    schema = str(getattr(model, "schema", "")).upper()
    return (
        schema.startswith(SPEC["schema"])
        and unique_global_ids(model)
        and check_counts(model)
        and check_forbidden(model)
        and check_space_names(model)
        and check_overall_size(model)
        and check_roof_height(model)
    )


def main():
    try:
        finish(evaluate(DESKTOP))
    except SystemExit:
        raise
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
