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

REQUIRED_SPACES = ["Living", "Kitchen", "Bed 1", "Bed 2", "Bath"]
REQUIRED_HEADERS = ["SpaceName", "Level", "NetFloorArea"]
MIN_WALLS = 8
EXPECTED_STOREYS = 1


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm_text(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ").strip()).casefold()


def header_key(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


def parse_float(value):
    text = str(value).strip().replace(" ", "")
    if text.count(",") == 1 and text.count(".") == 0:
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    return float(text)


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


def check_ifc(root):
    if not check_no_gui_bypass(root):
        return False
    import ifcopenshell

    model = ifcopenshell.open(str(root / "result.ifc"))
    if model.schema.upper() != "IFC4":
        return False
    if len(model.by_type("IfcProject")) != 1 or len(model.by_type("IfcSite")) != 1:
        return False
    if len(model.by_type("IfcBuilding")) != 1:
        return False
    if len(model.by_type("IfcBuildingStorey")) != EXPECTED_STOREYS:
        return False
    if len(model.by_type("IfcWall")) < MIN_WALLS:
        return False
    if model.by_type("IfcBuildingElementProxy") or model.by_type("IfcFurniture"):
        return False
    spaces = model.by_type("IfcSpace")
    if len(spaces) != len(REQUIRED_SPACES):
        return False
    names = [norm_text(getattr(space, "Name", "") or getattr(space, "LongName", "")) for space in spaces]
    if sorted(names) != sorted(norm_text(name) for name in REQUIRED_SPACES):
        return False
    if len(model.by_type("IfcDoor")) < 1:
        return False
    if len(model.by_type("IfcRelVoidsElement")) < 1 or len(model.by_type("IfcRelFillsElement")) < 1:
        return False
    return True


def check_csv(root):
    headers, rows = read_csv(root / "result.csv")
    if not headers or len(rows) != len(REQUIRED_SPACES):
        return False
    header_map = {header_key(header): header for header in headers}
    for header in REQUIRED_HEADERS:
        if header_key(header) not in header_map:
            return False
    by_space = {}
    for row in rows:
        row_by_key = {header_key(key): value for key, value in row.items()}
        name = norm_text(row_by_key.get(header_key("SpaceName"), ""))
        if name:
            by_space.setdefault(name, []).append(row_by_key)
    for space_name in REQUIRED_SPACES:
        matches = by_space.get(norm_text(space_name), [])
        if len(matches) != 1:
            return False
        row = matches[0]
        if norm_text(row.get(header_key("Level"), "")) != norm_text("Ground Floor"):
            return False
        if parse_float(row.get(header_key("NetFloorArea"), "")) <= 0:
            return False
    return True


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
