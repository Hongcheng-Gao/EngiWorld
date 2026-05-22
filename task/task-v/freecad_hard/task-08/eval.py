from __future__ import annotations

from pathlib import Path

import cadquery as cq

DESKTOP = Path("/home/user/Desktop")
OUTPUT_PATH = Path('/home/user/Desktop/freecad_task-8_output.step')
EXPECTED_DESCRIPTORS = [
  {
    "volume": 192500.796839,
    "area": 35870.305685,
    "bbox": [
      0.0,
      0.0,
      0.0,
      120.0,
      70.0,
      76.0
    ],
    "center": [
      59.90065,
      34.886039,
      21.345573
    ]
  }
]
BBOX_TOL = 0.12
CENTER_TOL = 0.12
VOLUME_REL_TOL = 0.006
AREA_REL_TOL = 0.02


GUI_BYPASS_FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr",
}
GUI_BYPASS_ALLOWED_FILENAMES = {"eval.py"}
GUI_BYPASS_OUTPUT_TOKENS = (
    "result.ifc", "result.pdf", "result.osm", "workflow.osw", "summary.txt",
    "report.csv", "result.csv",
    ".dxf", ".dwg", ".step", ".stp", ".fcstd", ".scad", ".stl", ".obj",
    ".db", ".rst", ".rth", ".wbpj", ".odb", ".cae", ".inp",
    ".nc", ".gcode", ".slb", ".ipt", ".sldprt", ".sldasm",
    "autocad_result", "apdl_", "wb_",
)
GUI_BYPASS_COMMAND_TOKENS = (
    "python", "python3", "py ", "powershell", "pwsh", "cmd.exe", "cmd /c",
    "bash", " sh ", "zsh", "node", "ruby", "perl",
    "ifcopenshell", "openstudio", "energyplus",
    "blender --background", "revitbatchprocessor",
    "ansys", "mapdl", "fluent", "abaqus", "cae noGUI",
    "freecad", "freecadcmd", "openscad", "librecad",
    "ezdxf", "cadquery", "accoreconsole", "autolisp",
    "solidworks", "solvespace",
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
            writes_file = any(
                token in line for token in (">", "tee ", "cat ", "set-content", "out-file", "new-item")
            )
            if touches_output and (runs_command or writes_file):
                return True
            if ("/desktop/" in line or "\\desktop\\" in line) and any(
                ext in line for ext in GUI_BYPASS_FORBIDDEN_EXTENSIONS
            ) and runs_command:
                return True
    return False


def check_no_gui_bypass(root):
    root = Path(root)
    if _desktop_script_artifacts(root):
        return False
    if _history_contains_bypass(root):
        return False
    return True



def _rel_close(a, b, tol):
    return abs(float(a) - float(b)) / max(1.0, abs(float(b))) <= tol


def _abs_close_seq(a, b, tol):
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def _shape_descriptors(path: Path):
    wp = cq.importers.importStep(str(path))
    solids = wp.solids().vals()
    if not solids or any(not solid.isValid() for solid in solids):
        raise ValueError("invalid or empty STEP")
    desc = []
    for solid in solids:
        bbox = solid.BoundingBox()
        center = solid.Center()
        desc.append({
            "volume": float(solid.Volume()),
            "area": float(solid.Area()),
            "bbox": [float(v) for v in (bbox.xmin, bbox.ymin, bbox.zmin, bbox.xmax, bbox.ymax, bbox.zmax)],
            "center": [float(v) for v in center.toTuple()],
        })
    desc.sort(key=lambda d: (round(d["center"][0], 3), round(d["center"][1], 3), round(d["center"][2], 3), round(d["volume"], 3)))
    return desc



def _compare_descriptor_lists(actual, expected):
    if len(actual) != len(expected):
        return False
    for got, exp in zip(actual, expected):
        if not _rel_close(got["volume"], exp["volume"], VOLUME_REL_TOL):
            return False
        if not _rel_close(got["area"], exp["area"], AREA_REL_TOL):
            return False
        if not _abs_close_seq(got["bbox"], exp["bbox"], BBOX_TOL):
            return False
        if not _abs_close_seq(got["center"], exp["center"], CENTER_TOL):
            return False
    return True


def evaluate() -> bool:
    if not check_no_gui_bypass(DESKTOP):
        return False
    if not OUTPUT_PATH.exists() or OUTPUT_PATH.stat().st_size <= 0:
        return False
    actual = _shape_descriptors(OUTPUT_PATH)
    expected = EXPECTED_DESCRIPTORS
    return _compare_descriptor_lists(actual, expected)


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print("True" if ok else "False")
