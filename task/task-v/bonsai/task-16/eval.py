#!/usr/bin/env python3
import csv
import re
from collections import Counter
from pathlib import Path


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

REQUIRED_OUTPUTS = ("result.ifc",)
CSV_HEADERS = ("GlobalId", "Class", "TypeName", "Width", "Height", "HostWall")
EXPECTED_ROWS = [
    {"Class": "IfcDoor", "TypeName": "DoorType-1000", "Width": 1.0, "Height": 2.1, "HostWall": "Wall-S"},
    {"Class": "IfcDoor", "TypeName": "DoorType-1000", "Width": 1.0, "Height": 2.1, "HostWall": "Wall-N"},
    {"Class": "IfcWindow", "TypeName": "WindowType-1200", "Width": 1.2, "Height": 1.2, "HostWall": "Wall-N"},
    {"Class": "IfcWindow", "TypeName": "WindowType-1200", "Width": 1.2, "Height": 1.2, "HostWall": "Wall-N"},
    {"Class": "IfcWindow", "TypeName": "WindowType-1000", "Width": 1.0, "Height": 1.2, "HostWall": "Wall-E"},
]
WIDTH_HEIGHT_TOLERANCE = 0.05
FORBIDDEN_CLASSES = ("IfcBuildingElementProxy", "IfcFurnishingElement")


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def parse_float(value):
    text = str(value).strip().replace(" ", "")
    if text.count(",") == 1 and text.count(".") == 0:
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    return float(text)


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(CSV_HEADERS):
            return None
        return [row for row in reader if any(str(value).strip() for value in row.values())]


def class_count(model, ifc_class):
    return len(model.by_type(ifc_class))


def wall_name_for_filled_element(model):
    opening_to_wall = {}
    for rel in model.by_type("IfcRelVoidsElement"):
        wall = getattr(rel, "RelatingBuildingElement", None)
        opening = getattr(rel, "RelatedOpeningElement", None)
        if wall is not None and opening is not None and wall.is_a("IfcWall"):
            opening_to_wall[opening.id()] = norm(getattr(wall, "Name", ""))

    element_to_wall = {}
    for rel in model.by_type("IfcRelFillsElement"):
        element = getattr(rel, "RelatedBuildingElement", None)
        opening = getattr(rel, "RelatingOpeningElement", None)
        if element is not None and opening is not None:
            host = opening_to_wall.get(opening.id())
            if host:
                element_to_wall[getattr(element, "GlobalId", "")] = host
    return element_to_wall


def check_ifc(path):
    import ifcopenshell

    model = ifcopenshell.open(str(path))
    if model.schema.upper() != "IFC4":
        return None
    expected_counts = {
        "IfcProject": 1,
        "IfcBuildingStorey": 1,
        "IfcWall": 4,
        "IfcSlab": 1,
        "IfcDoor": 2,
        "IfcWindow": 3,
        "IfcOpeningElement": 5,
        "IfcRelVoidsElement": 5,
        "IfcRelFillsElement": 5,
    }
    for ifc_class, expected in expected_counts.items():
        if class_count(model, ifc_class) != expected:
            return None
    for ifc_class in FORBIDDEN_CLASSES:
        if class_count(model, ifc_class) != 0:
            return None
    host_counts = Counter()
    element_to_wall = wall_name_for_filled_element(model)
    for ifc_class in ("IfcDoor", "IfcWindow"):
        for product in model.by_type(ifc_class):
            host_counts[(ifc_class, element_to_wall.get(getattr(product, "GlobalId", "")))] += 1
    expected_hosts = Counter({
        ("IfcDoor", "Wall-S"): 1,
        ("IfcDoor", "Wall-N"): 1,
        ("IfcWindow", "Wall-N"): 2,
        ("IfcWindow", "Wall-E"): 1,
    })
    if host_counts != expected_hosts:
        return None
    return model


def check_csv(rows, model):
    if rows is None or len(rows) != len(EXPECTED_ROWS):
        return False

    products = {}
    for ifc_class in ("IfcDoor", "IfcWindow"):
        for product in model.by_type(ifc_class):
            products[getattr(product, "GlobalId", "")] = product
    element_to_wall = wall_name_for_filled_element(model)

    actual_signatures = []
    seen_global_ids = set()
    for row in rows:
        gid = norm(row.get("GlobalId"))
        if gid in seen_global_ids or gid not in products:
            return False
        seen_global_ids.add(gid)
        product = products[gid]
        if row.get("Class") != product.is_a():
            return False
        if norm(row.get("HostWall")) != element_to_wall.get(gid):
            return False
        try:
            width = parse_float(row.get("Width"))
            height = parse_float(row.get("Height"))
        except Exception:
            return False
        actual_signatures.append(
            {
                "Class": product.is_a(),
                "TypeName": norm(row.get("TypeName")),
                "Width": width,
                "Height": height,
                "HostWall": norm(row.get("HostWall")),
            }
        )

    unmatched = actual_signatures[:]
    for expected in EXPECTED_ROWS:
        found_at = None
        for index, actual in enumerate(unmatched):
            if actual["Class"] != expected["Class"]:
                continue
            if actual["TypeName"] != expected["TypeName"]:
                continue
            if actual["HostWall"] != expected["HostWall"]:
                continue
            if abs(actual["Width"] - expected["Width"]) > WIDTH_HEIGHT_TOLERANCE:
                continue
            if abs(actual["Height"] - expected["Height"]) > WIDTH_HEIGHT_TOLERANCE:
                continue
            found_at = index
            break
        if found_at is None:
            return False
        unmatched.pop(found_at)
    return not unmatched


def main():
    try:
        root = DESKTOP
        if not check_no_gui_bypass(root):
            emit(False)
        if not root.is_dir():
            emit(False)
        for name in REQUIRED_OUTPUTS:
            path = root / name
            if not path.is_file() or path.stat().st_size == 0:
                emit(False)
        model = check_ifc(root / "result.ifc")
        if model is None:
            emit(False)
        emit(model is not None)
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
