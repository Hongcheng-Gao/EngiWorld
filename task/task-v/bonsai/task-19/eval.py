#!/usr/bin/env python3
import csv
import re
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
CSV_HEADERS = ("RoomNumber", "SpaceName", "FloorFinish", "WallFinish", "CeilingFinish", "NetFloorArea")
EXPECTED_SPACES = {
    "Lobby": {
        "RoomNumber": "101",
        "FloorFinish": "Polished Concrete",
        "WallFinish": "Painted GWB",
        "CeilingFinish": "Acoustic Tile",
        "NetFloorArea": 10.08,
    },
    "Office A": {
        "RoomNumber": "102",
        "FloorFinish": "Carpet Tile",
        "WallFinish": "Painted GWB",
        "CeilingFinish": "Acoustic Tile",
        "NetFloorArea": 23.04,
    },
    "Office B": {
        "RoomNumber": "103",
        "FloorFinish": "Carpet Tile",
        "WallFinish": "Painted GWB",
        "CeilingFinish": "Acoustic Tile",
        "NetFloorArea": 33.84,
    },
    "Meeting": {
        "RoomNumber": "104",
        "FloorFinish": "Vinyl Plank",
        "WallFinish": "Painted GWB",
        "CeilingFinish": "Acoustic Tile",
        "NetFloorArea": 14.96,
    },
    "WC": {
        "RoomNumber": "105",
        "FloorFinish": "Ceramic Tile",
        "WallFinish": "Moisture Board",
        "CeilingFinish": "Painted Ceiling",
        "NetFloorArea": 15.64,
    },
}
AREA_TOLERANCE = 0.05
FORBIDDEN_CLASSES = ("IfcBuildingElementProxy", "IfcFurnishingElement")


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ").strip()).upper()


def parse_float(value):
    text = str(value).strip().replace(" ", "")
    if text.count(",") == 1 and text.count(".") == 0:
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    return float(text)


def class_count(model, ifc_class):
    return len(model.by_type(ifc_class))


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(CSV_HEADERS):
            return None
        return [row for row in reader if any(str(value).strip() for value in row.values())]


def nominal_value(value):
    return getattr(value, "wrappedValue", value)


def space_properties(space):
    data = {}
    for rel in getattr(space, "IsDefinedBy", []) or []:
        pdef = getattr(rel, "RelatingPropertyDefinition", None)
        if pdef is None:
            continue
        if pdef.is_a("IfcPropertySet") and getattr(pdef, "Name", "") == "EPset_FMFinish":
            for prop in getattr(pdef, "HasProperties", []) or []:
                value = getattr(prop, "NominalValue", None)
                data[getattr(prop, "Name", "")] = str(nominal_value(value))
        if pdef.is_a("IfcElementQuantity") and getattr(pdef, "Name", "") == "Qto_SpaceBaseQuantities":
            for quantity in getattr(pdef, "Quantities", []) or []:
                if getattr(quantity, "Name", "") == "NetFloorArea" and hasattr(quantity, "AreaValue"):
                    data["NetFloorArea"] = float(quantity.AreaValue)
    return data


def filled_element_count(model):
    filled_ids = set()
    opening_ids = set()
    for rel in model.by_type("IfcRelFillsElement"):
        element = getattr(rel, "RelatedBuildingElement", None)
        opening = getattr(rel, "RelatingOpeningElement", None)
        if element is None or opening is None:
            return None
        if not (element.is_a("IfcDoor") or element.is_a("IfcWindow")):
            return None
        filled_ids.add(element.id())
        opening_ids.add(opening.id())

    void_opening_ids = set()
    for rel in model.by_type("IfcRelVoidsElement"):
        wall = getattr(rel, "RelatingBuildingElement", None)
        opening = getattr(rel, "RelatedOpeningElement", None)
        if wall is None or opening is None or not wall.is_a("IfcWall"):
            return None
        void_opening_ids.add(opening.id())
    if opening_ids != void_opening_ids:
        return None
    return len(filled_ids)


def check_expected_record(actual, expected):
    for key in ("RoomNumber", "FloorFinish", "WallFinish", "CeilingFinish"):
        if str(actual.get(key, "")).strip() != expected[key]:
            return False
    try:
        area = parse_float(actual.get("NetFloorArea"))
    except Exception:
        return False
    return abs(area - expected["NetFloorArea"]) <= AREA_TOLERANCE


def check_ifc(path):
    import ifcopenshell

    model = ifcopenshell.open(str(path))
    if model.schema.upper() != "IFC4":
        return None
    expected_counts = {
        "IfcProject": 1,
        "IfcBuildingStorey": 1,
        "IfcSpace": 5,
        "IfcWall": 7,
        "IfcSlab": 1,
        "IfcDoor": 4,
        "IfcWindow": 3,
        "IfcOpeningElement": 7,
        "IfcRelVoidsElement": 7,
        "IfcRelFillsElement": 7,
    }
    for ifc_class, expected in expected_counts.items():
        if class_count(model, ifc_class) != expected:
            return None
    for ifc_class in FORBIDDEN_CLASSES:
        if class_count(model, ifc_class) != 0:
            return None
    if filled_element_count(model) != 7:
        return None

    actual_spaces = {}
    for space in model.by_type("IfcSpace"):
        name = getattr(space, "Name", "")
        actual_spaces[norm(name)] = space_properties(space)
    if set(actual_spaces) != {norm(name) for name in EXPECTED_SPACES}:
        return None
    for name, expected in EXPECTED_SPACES.items():
        if not check_expected_record(actual_spaces[norm(name)], expected):
            return None
    return model


def check_csv(rows):
    if rows is None or len(rows) != len(EXPECTED_SPACES):
        return False
    seen = set()
    for row in rows:
        name = row.get("SpaceName", "")
        key = norm(name)
        if key in seen:
            return False
        seen.add(key)
        expected_name = next((item for item in EXPECTED_SPACES if norm(item) == key), None)
        if expected_name is None:
            return False
        if not check_expected_record(row, EXPECTED_SPACES[expected_name]):
            return False
    return seen == {norm(name) for name in EXPECTED_SPACES}


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
        emit(model is not None)
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
