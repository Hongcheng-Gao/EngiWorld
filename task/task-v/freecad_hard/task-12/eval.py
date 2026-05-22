from __future__ import annotations

from pathlib import Path

import cadquery as cq

DESKTOP = Path("/home/user/Desktop")
OUTPUT_PATH = Path('/home/user/Desktop/freecad_task-12_output.step')
EXPECTED_DESCRIPTORS = [
  {
    "volume": 3240.0,
    "area": 1368.0,
    "bbox": [
      0.0,
      0.0,
      0.0,
      18.0,
      18.0,
      10.0
    ],
    "center": [
      9.0,
      9.0,
      5.0
    ]
  },
  {
    "volume": 1413.716694,
    "area": 722.56631,
    "bbox": [
      7.0,
      37.0,
      0.0,
      17.0,
      47.0,
      18.0
    ],
    "center": [
      12.0,
      42.0,
      9.0
    ]
  },
  {
    "volume": 5184.0,
    "area": 1800.0,
    "bbox": [
      24.0,
      0.0,
      0.0,
      42.0,
      18.0,
      16.0
    ],
    "center": [
      33.0,
      9.0,
      8.0
    ]
  },
  {
    "volume": 1995.696733,
    "area": 915.774259,
    "bbox": [
      36.5,
      44.5,
      0.0,
      47.5,
      55.5,
      21.0
    ],
    "center": [
      42.0,
      50.0,
      10.5
    ]
  },
  {
    "volume": 7128.0,
    "area": 2232.0,
    "bbox": [
      48.0,
      0.0,
      0.0,
      66.0,
      18.0,
      22.0
    ],
    "center": [
      57.0,
      9.0,
      11.0
    ]
  },
  {
    "volume": 2714.336053,
    "area": 1130.973355,
    "bbox": [
      66.0,
      36.0,
      0.0,
      78.0,
      48.0,
      24.0
    ],
    "center": [
      72.0,
      42.0,
      12.0
    ]
  },
  {
    "volume": 9072.0,
    "area": 2664.0,
    "bbox": [
      72.0,
      0.0,
      0.0,
      90.0,
      18.0,
      28.0
    ],
    "center": [
      81.0,
      9.0,
      14.0
    ]
  },
  {
    "volume": 3583.77182,
    "area": 1368.163601,
    "bbox": [
      95.5,
      43.5,
      0.0,
      108.5,
      56.5,
      27.0
    ],
    "center": [
      102.0,
      50.0,
      13.5
    ]
  },
  {
    "volume": 11016.0,
    "area": 3096.0,
    "bbox": [
      96.0,
      0.0,
      0.0,
      114.0,
      18.0,
      34.0
    ],
    "center": [
      105.0,
      9.0,
      17.0
    ]
  },
  {
    "volume": 4618.141201,
    "area": 1627.344995,
    "bbox": [
      125.0,
      35.0,
      0.0,
      139.0,
      49.0,
      30.0
    ],
    "center": [
      132.0,
      42.0,
      15.0
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
