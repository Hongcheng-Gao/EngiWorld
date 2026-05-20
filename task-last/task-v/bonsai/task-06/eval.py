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

REQUIRED_FILES = ("result.ifc",)
EXPECTED_SPACES = {"LIVING", "KITCHEN", "BEDROOM", "BATH"}
EXPECTED_COUNTS = {
    "IfcProject": 1,
    "IfcBuildingStorey": 1,
    "IfcSpace": 4,
    "IfcWall": 7,
    "IfcDoor": 3,
    "IfcWindow": 4,
    "IfcSlab": 1,
    "IfcBuildingElementProxy": 0,
}
EXPECTED_CSV_HEADER = ["GlobalId", "Class", "TypeName", "MaterialSummary", "Storey"]
EXPECTED_CSV_CLASS_COUNTS = {"IfcWall": 7, "IfcDoor": 3, "IfcWindow": 4}
EXPECTED_CSV_MATERIAL_COUNTS = {
    "Brick | Insulation | Gypsum": 7,
    "Timber": 3,
    "Aluminium": 4,
}
WALL_MATERIALS = ["BRICK", "INSULATION", "GYPSUM"]


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    text = str(value or "").replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text.strip()).upper()


def require_files(root):
    for rel in REQUIRED_FILES:
        path = root / rel
        if not path.is_file():
            return False
        if rel.endswith(".ifc") and path.stat().st_size < 100:
            return False
        if rel.endswith(".csv") and path.stat().st_size < 1:
            return False
    return True


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return None, None
    header = [cell.strip() for cell in rows[0]]
    body = []
    for row in rows[1:]:
        if not any(str(cell).strip() for cell in row):
            continue
        padded = row + [""] * max(0, len(header) - len(row))
        body.append({header[i]: padded[i].strip() for i in range(len(header))})
    return header, body


def material_sequences(product):
    sequences = []
    for rel in getattr(product, "HasAssociations", []) or []:
        if not rel.is_a("IfcRelAssociatesMaterial"):
            continue
        mat = rel.RelatingMaterial
        if mat.is_a("IfcMaterial"):
            sequences.append([norm(mat.Name)])
        elif mat.is_a("IfcMaterialLayerSetUsage"):
            layers = mat.ForLayerSet.MaterialLayers or []
            sequences.append([norm(layer.Material.Name) for layer in layers if layer.Material])
        elif mat.is_a("IfcMaterialLayerSet"):
            layers = mat.MaterialLayers or []
            sequences.append([norm(layer.Material.Name) for layer in layers if layer.Material])
        elif mat.is_a("IfcMaterialList"):
            sequences.append([norm(item.Name) for item in mat.Materials if item])
    return sequences


def has_sequence(product, expected):
    return any(sequence == expected for sequence in material_sequences(product))


def has_material(product, expected):
    wanted = norm(expected)
    return any(wanted in sequence for sequence in material_sequences(product))


def check_ifc(root):
    if not check_no_gui_bypass(root):
        return False
    import ifcopenshell

    model = ifcopenshell.open(str(root / "result.ifc"))
    if str(model.schema).upper() != "IFC4":
        return None
    for cls, count in EXPECTED_COUNTS.items():
        if len(model.by_type(cls)) != count:
            return None

    storey = model.by_type("IfcBuildingStorey")[0]
    if getattr(storey, "Name", None) != "Level 00":
        return None

    space_names = {norm(getattr(space, "Name", "") or getattr(space, "LongName", "")) for space in model.by_type("IfcSpace")}
    if space_names != EXPECTED_SPACES:
        return None

    for wall in model.by_type("IfcWall"):
        if not has_sequence(wall, WALL_MATERIALS):
            return None
    for door in model.by_type("IfcDoor"):
        if not has_material(door, "Timber"):
            return None
    for window in model.by_type("IfcWindow"):
        if not has_material(window, "Aluminium"):
            return None

    return {
        element.GlobalId: element.is_a()
        for cls in EXPECTED_CSV_CLASS_COUNTS
        for element in model.by_type(cls)
    }


def check_csv(root, ifc_elements):
    header, rows = read_csv(root / "result.csv")
    if header != EXPECTED_CSV_HEADER:
        return False
    if len(rows) != 14:
        return False

    row_ids = [row.get("GlobalId", "") for row in rows]
    if len(set(row_ids)) != len(row_ids):
        return False
    if set(row_ids) != set(ifc_elements):
        return False

    if Counter(row.get("Class", "") for row in rows) != EXPECTED_CSV_CLASS_COUNTS:
        return False
    if Counter(row.get("MaterialSummary", "") for row in rows) != EXPECTED_CSV_MATERIAL_COUNTS:
        return False
    for row in rows:
        if row.get("Class") != ifc_elements[row["GlobalId"]]:
            return False
        if row.get("Storey") != "Level 00":
            return False
    return True


def main():
    try:
        root = DESKTOP
        if not root.is_dir() or not require_files(root):
            emit(False)
        ifc_elements = check_ifc(root)
        emit(bool(ifc_elements))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
