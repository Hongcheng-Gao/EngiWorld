from __future__ import annotations

import csv
import math
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

DESKTOP = Path(os.environ.get("EVAL_DESKTOP", "/home/user/Desktop"))

GUI_BYPASS_FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr",
}
GUI_BYPASS_ALLOWED_FILENAMES = {"eval.py"}
GUI_BYPASS_OUTPUT_TOKENS = (
    "result.ifc", "result.pdf", "result.osm", "workflow.osw", "summary.txt",
    "report.csv", "result.csv", ".dxf", ".dwg", ".step", ".stp", ".fcstd",
    ".scad", ".stl", ".obj", ".blend", ".pcb", ".sch", ".brd", ".dsn",
    ".opj", ".db", ".rst", ".rth", ".wbpj", ".odb", ".cae", ".inp",
    ".nc", ".gcode", ".slb", ".ipt", ".sldprt", ".sldasm",
    "autocad_result", "apdl_", "wb_",
)
GUI_BYPASS_COMMAND_TOKENS = (
    "python", "python3", "py ", "powershell", "pwsh", "cmd.exe", "cmd /c",
    "bash", " sh ", "zsh", "node", "ruby", "perl", "ifcopenshell",
    "openstudio", "energyplus", "blender --background", "revitbatchprocessor",
    "ansys", "mapdl", "fluent", "abaqus", "cae noGUI", "freecad", "freecadcmd",
    "openscad", "librecad", "ezdxf", "cadquery", "accoreconsole", "autolisp",
    "solidworks", "solvespace", "kicad-cli", "pcbnew",
)


def _read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _desktop_script_artifacts(root: Path) -> bool:
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


def _history_paths(root: Path):
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


def _history_contains_bypass(root: Path) -> bool:
    for path in _history_paths(root):
        text = _read_text_safe(path).lower()
        if not text:
            continue
        if any(cmd in text for cmd in GUI_BYPASS_COMMAND_TOKENS) and any(tok in text for tok in GUI_BYPASS_OUTPUT_TOKENS):
            return True
    return False


def check_no_gui_bypass() -> bool:
    return not _desktop_script_artifacts(DESKTOP) and not _history_contains_bypass(DESKTOP)


def parse_xml(path: Path):
    if not path.exists():
        return None
    try:
        return ET.parse(path)
    except Exception:
        return None


def f(value, default=None):
    try:
        return float(value)
    except Exception:
        return default


def near(a, b, tol=0.35):
    return a is not None and abs(a - b) <= tol


def point_near(elem, x, y, tol=0.35):
    return near(f(elem.get("x")), x, tol) and near(f(elem.get("y")), y, tol)


def wire_matches(wire, p1, p2, tol=0.35):
    a = (f(wire.get("x1")), f(wire.get("y1")))
    b = (f(wire.get("x2")), f(wire.get("y2")))
    return ((near(a[0], p1[0], tol) and near(a[1], p1[1], tol) and near(b[0], p2[0], tol) and near(b[1], p2[1], tol)) or
            (near(a[0], p2[0], tol) and near(a[1], p2[1], tol) and near(b[0], p1[0], tol) and near(b[1], p1[1], tol)))


def all_text(root):
    return "\n".join((t.text or "") for t in root.findall(".//text"))


def elements_by_name(root):
    return {e.get("name"): e for e in root.findall(".//element")}


def parts_by_name(root):
    return {p.get("name"): p for p in root.findall(".//part")}


def norm_drill(value):
    return round(float(value), 3)


def check():
    tree = parse_xml(DESKTOP / "answer.sch")
    if tree is None:
        return False
    root = tree.getroot()
    parts = parts_by_name(root)
    if not any(p.get("library") == "frames" and p.get("deviceset") == "DINA4_L" for p in parts.values()):
        return False
    frame_parts = {p.get("name") for p in parts.values() if p.get("library") == "frames" and p.get("deviceset") == "DINA4_L"}
    if not any(inst.get("part") in frame_parts for inst in root.findall(".//instance")):
        return False
    text = all_text(root)
    required = [
        "Enviro Sensor Rev B", "Maya Chen", "ESB-CTRL-004", "2026-05-23", "B.2", "1/1",
        "Assembly: keep sensor connector on the top edge.",
        "Verification: confirm 3V3 rail before programming.",
        "ECO: replace R1 only after calibration signoff.",
    ]
    return all(item in text for item in required) and len(root.findall(".//sheet/plain/text")) >= 9


if __name__ == "__main__":
    print("True" if check_no_gui_bypass() and check() else "False")
