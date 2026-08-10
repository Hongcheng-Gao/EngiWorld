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


def _legacy_check():
    tree = parse_xml(DESKTOP / "answer.sch")
    if tree is None:
        return False
    root = tree.getroot()
    parts = parts_by_name(root)
    required_parts = {
        "U1": None, "R1": "10k", "R2": "47k", "C1": "100n", "C2": "10u", "LED1": "red",
    }
    for name, value in required_parts.items():
        part = parts.get(name)
        if part is None:
            return False
        if value is not None and part.get("value") != value:
            return False
    u1 = parts["U1"]
    if "555" not in (u1.get("deviceset") or ""):
        return False
    placed = {inst.get("part") for inst in root.findall(".//instance")}
    if not set(required_parts).issubset(placed):
        return False
    net_names = {n.get("name") for n in root.findall(".//net")}
    if not {"VCC", "GND", "TRIG_THRES", "DISCH", "OUT", "CTRL"}.issubset(net_names):
        return False
    pinrefs = {(p.get("part"), p.get("pin")) for p in root.findall(".//pinref")}
    required_u1 = {("U1", pin) for pin in ("V+", "GND", "TR", "THR", "DIS", "Q", "CV", "R")}
    return required_u1.issubset(pinrefs) and ("LED1", "A") in pinrefs


# ENGIWORLD_REPAIRED_EAGLE

def check():
    if not _legacy_check():
        return False
    tree = parse_xml(DESKTOP / "answer.sch")
    if tree is None:
        return False
    root = tree.getroot()
    parts = parts_by_name(root)
    if set(parts) != {"U1", "R1", "R2", "C1", "C2", "LED1"}:
        return False
    nets = {n.get("name"): {(p.get("part"), (p.get("pin") or "").upper())
                            for p in n.findall(".//pinref")} for n in root.findall(".//net")}
    if set(nets) != {"VCC", "GND", "TRIG_THRES", "DISCH", "OUT", "CTRL"}:
        return False
    required = {
        "VCC": {("U1", "V+"), ("U1", "R")},
        "GND": {("U1", "GND"), ("LED1", "C")},
        "TRIG_THRES": {("U1", "TR"), ("U1", "THR")},
        "DISCH": {("U1", "DIS")}, "OUT": {("U1", "Q"), ("LED1", "A")},
        "CTRL": {("U1", "CV")},
    }
    if any(not pins.issubset(nets.get(name, set())) for name, pins in required.items()):
        return False
    pin_net = {(part, pin): name for name, pins in nets.items() for part, pin in pins}
    def pn(ref): return {net for (part, _), net in pin_net.items() if part == ref}
    return (pn("R1") == {"VCC", "DISCH"} and pn("R2") == {"DISCH", "TRIG_THRES"}
            and pn("C1") == {"TRIG_THRES", "GND"} and pn("C2") == {"VCC", "GND"})

if __name__ == "__main__":
    print("True" if check_no_gui_bypass() and check() else "False")
