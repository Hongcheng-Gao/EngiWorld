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

EXPECTED_TYPES = {
    "IfcWall": {
        "type_class": "IfcWallType",
        "type_name": "WallType_External",
        "count": 4,
        "summary": "Brick:0.100m | Insulation:0.050m | Gypsum:0.015m",
    },
    "IfcSlab": {
        "type_class": "IfcSlabType",
        "type_name": "SlabType_200",
        "count": 1,
        "summary": "Concrete:0.200m",
    },
    "IfcDoor": {
        "type_class": "IfcDoorType",
        "type_name": "Door Type A",
        "count": 2,
        "summary": "Timber",
    },
    "IfcWindow": {
        "type_class": "IfcWindowType",
        "type_name": "Window Type W",
        "count": 4,
        "summary": "Aluminum",
    },
}
REQUIRED_HEADERS = ["Class", "TypeName", "MaterialSummary", "OccurrenceCount"]
EXPECTED_MATERIALS = ["Brick", "Insulation", "Gypsum", "Concrete", "Timber", "Aluminum"]
LENGTH_PREFIX_SCALE = {
    "EXA": 1e18,
    "PETA": 1e15,
    "TERA": 1e12,
    "GIGA": 1e9,
    "MEGA": 1e6,
    "KILO": 1e3,
    "HECTO": 1e2,
    "DECA": 1e1,
    "DECI": 1e-1,
    "CENTI": 1e-2,
    "MILLI": 1e-3,
    "MICRO": 1e-6,
    "NANO": 1e-9,
    "PICO": 1e-12,
    "FEMTO": 1e-15,
    "ATTO": 1e-18,
}


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm_text(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def header_key(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


def parse_float(value):
    text = str(value).strip().replace(" ", "")
    if text.count(",") == 1 and text.count(".") == 0:
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    return float(text)


def canonical_summary(value):
    parts = []
    for raw in str(value or "").split("|"):
        text = raw.strip()
        if not text:
            continue
        if ":" in text:
            name, thickness = text.split(":", 1)
            thickness = thickness.strip().lower().removesuffix("m")
            parts.append(f"{norm_text(name)}:{parse_float(thickness):.3f}")
        else:
            parts.append(norm_text(text))
    return tuple(parts)


def read_csv(path):
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return None, None
    try:
        dialect = csv.Sniffer().sniff(text[:2048])
    except Exception:
        dialect = csv.excel
    rows = list(csv.reader(text.splitlines(), dialect))
    if not rows:
        return None, None
    headers = [cell.strip() for cell in rows[0]]
    body = []
    for raw in rows[1:]:
        if not any(cell.strip() for cell in raw):
            continue
        raw = raw + [""] * max(0, len(headers) - len(raw))
        body.append({headers[i]: raw[i].strip() for i in range(len(headers))})
    return headers, body


def check_outputs(root):
    if not (root / "result.ifc").is_file() or (root / "result.ifc").stat().st_size < 100:
        return False
    return True


def material_summary_for_type(model, type_obj):
    matches = []
    for rel in model.by_type("IfcRelAssociatesMaterial"):
        if type_obj in (getattr(rel, "RelatedObjects", None) or []):
            matches.append(getattr(rel, "RelatingMaterial", None))
    if len(matches) != 1:
        return None
    material = matches[0]
    if material is None:
        return None
    if material.is_a("IfcMaterial"):
        return getattr(material, "Name", "") or ""
    if material.is_a("IfcMaterialLayerSet"):
        parts = []
        for layer in material.MaterialLayers or []:
            mat = getattr(layer, "Material", None)
            name = getattr(mat, "Name", "") if mat else ""
            thickness = getattr(layer, "LayerThickness", None)
            if not name or thickness is None:
                return None
            parts.append(f"{name}:{float(thickness):.3f}m")
        return " | ".join(parts)
    return None


def length_to_metre_scale(model):
    for assignment in model.by_type("IfcUnitAssignment"):
        for unit in assignment.Units or []:
            if getattr(unit, "UnitType", None) == "LENGTHUNIT" and unit.is_a("IfcSIUnit"):
                if getattr(unit, "Name", None) == "METRE":
                    return LENGTH_PREFIX_SCALE.get(getattr(unit, "Prefix", None), 1.0)
    return 1.0


def check_ifc(root):
    if not check_no_gui_bypass(root):
        return False
    import ifcopenshell

    model = ifcopenshell.open(str(root / "result.ifc"))
    if model.schema.upper() != "IFC4":
        return False
    if len(model.by_type("IfcProject")) != 1 or len(model.by_type("IfcSite")) != 1:
        return False
    if len(model.by_type("IfcBuilding")) != 1 or len(model.by_type("IfcBuildingStorey")) != 1:
        return False
    if model.by_type("IfcBuildingElementProxy") or model.by_type("IfcFurniture"):
        return False
    scale = length_to_metre_scale(model)
    if sorted(norm_text(getattr(mat, "Name", "")) for mat in model.by_type("IfcMaterial")) != sorted(norm_text(name) for name in EXPECTED_MATERIALS):
        return False
    for class_name, expected in EXPECTED_TYPES.items():
        if len(model.by_type(class_name)) != expected["count"]:
            return False
        type_objects = model.by_type(expected["type_class"])
        if len(type_objects) != 1:
            return False
        type_obj = type_objects[0]
        if norm_text(getattr(type_obj, "Name", "")) != norm_text(expected["type_name"]):
            return False
        related = []
        rel_count = 0
        for rel in model.by_type("IfcRelDefinesByType"):
            if getattr(rel, "RelatingType", None) == type_obj:
                rel_count += 1
                related.extend(getattr(rel, "RelatedObjects", None) or [])
        if rel_count != 1 or len(related) != expected["count"] or any(not obj.is_a(class_name) for obj in related):
            return False
        summary = material_summary_for_type(model, type_obj)
        if summary and ":" in summary:
            converted = []
            for part in summary.split("|"):
                name, thickness = part.split(":", 1)
                converted.append(f"{name.strip()}:{parse_float(thickness.strip().lower().removesuffix('m')) * scale:.3f}m")
            summary = " | ".join(converted)
        if canonical_summary(summary) != canonical_summary(expected["summary"]):
            return False
    return True


def check_csv(root):
    headers, rows = read_csv(root / "result.csv")
    if not headers or len(rows) != len(EXPECTED_TYPES):
        return False
    header_map = {header_key(header): header for header in headers}
    for header in REQUIRED_HEADERS:
        if header_key(header) not in header_map:
            return False
    seen = set()
    for row in rows:
        by_key = {header_key(key): value for key, value in row.items()}
        class_name = by_key.get(header_key("Class"), "")
        if class_name not in EXPECTED_TYPES or class_name in seen:
            return False
        seen.add(class_name)
        expected = EXPECTED_TYPES[class_name]
        if norm_text(by_key.get(header_key("TypeName"), "")) != norm_text(expected["type_name"]):
            return False
        if canonical_summary(by_key.get(header_key("MaterialSummary"), "")) != canonical_summary(expected["summary"]):
            return False
        if int(parse_float(by_key.get(header_key("OccurrenceCount"), ""))) != expected["count"]:
            return False
    return seen == set(EXPECTED_TYPES)


def main():
    try:
        root = DESKTOP
        emit(root.is_dir() and check_outputs(root) and check_ifc(root))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
