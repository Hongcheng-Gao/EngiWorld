from __future__ import annotations

from pathlib import Path

import cadquery as cq

DESKTOP = Path("/home/user/Desktop")



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

from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder

TASK_NUMBER = 8
STEP_SPEC = {'path': '/home/user/Desktop/freecad_task-8_output.step', 'solid_count': 1, 'bounds': [0.0, 120.0, 0.0, 80.0, 0.0, 50.0], 'volume': 336000.0}
GEOM_TOL = 0.12
VOLUME_REL_TOL = 0.01


def _close(actual, expected, tol=GEOM_TOL):
    return abs(float(actual) - float(expected)) <= float(tol)


def _load_solids(path):
    if not path.is_file() or path.stat().st_size <= 0:
        raise ValueError("missing STEP")
    solids = cq.importers.importStep(str(path)).solids().vals()
    if not solids or any(not solid.isValid() for solid in solids):
        raise ValueError("invalid STEP")
    return solids


def _bounds(solids):
    boxes = [solid.BoundingBox() for solid in solids]
    return [
        min(box.xmin for box in boxes), max(box.xmax for box in boxes),
        min(box.ymin for box in boxes), max(box.ymax for box in boxes),
        min(box.zmin for box in boxes), max(box.zmax for box in boxes),
    ]


def _cylinders(solids):
    result = []
    for solid in solids:
        for face in solid.Faces():
            surface = BRepAdaptor_Surface(face.wrapped, True)
            if surface.GetType() != GeomAbs_Cylinder:
                continue
            cylinder = surface.Cylinder()
            direction = cylinder.Axis().Direction()
            point = cylinder.Axis().Location()
            box = face.BoundingBox()
            result.append({
                "radius": cylinder.Radius(),
                "axis": (direction.X(), direction.Y(), direction.Z()),
                "axis_point": (point.X(), point.Y(), point.Z()),
                "mid": (
                    (box.xmin + box.xmax) / 2.0,
                    (box.ymin + box.ymax) / 2.0,
                    (box.zmin + box.zmax) / 2.0,
                ),
                "span": (box.xlen, box.ylen, box.zlen),
            })
    return result


def _axis_matches(record, axis):
    index = {"x": 0, "y": 1, "z": 2}[axis]
    return abs(abs(record["axis"][index]) - 1.0) <= 0.01


def _match_cylinders(records, radius, axis, expected, span=None):
    unused = list(records)
    for target in expected:
        match = None
        for index, record in enumerate(unused):
            if not _close(record["radius"], radius, 0.06) or not _axis_matches(record, axis):
                continue
            if span is not None:
                axis_index = {"x": 0, "y": 1, "z": 2}[axis]
                if not _close(record["span"][axis_index], span, 0.10):
                    continue
            if any(not _close(record["mid"][i], value, 0.15) for i, value in target.items()):
                continue
            match = index
            break
        if match is None:
            return False
        unused.pop(match)
    return True


def _inside(solid, point):
    return bool(solid.isInside(cq.Vector(*point), 1e-6))


def _feature_check(solids):
    solid = solids[0]
    cylinders = _cylinders(solids)
    if TASK_NUMBER == 1:
        return _match_cylinders(cylinders, 10.0, "z", [{0: 60.0, 1: 40.0, 2: 5.0}], 10.0)
    if TASK_NUMBER == 2:
        return _match_cylinders(cylinders, 4.0, "y", [{0: 30.0, 2: 30.0}, {0: 70.0, 2: 30.0}], 8.0)
    if TASK_NUMBER == 3:
        return _match_cylinders(cylinders, 5.0, "z", [
            {0: 15.0, 1: 15.0, 2: 16.0}, {0: 75.0, 1: 15.0, 2: 16.0},
            {0: 15.0, 1: 45.0, 2: 16.0}, {0: 75.0, 1: 45.0, 2: 16.0},
        ], 16.0)
    if TASK_NUMBER == 4:
        centers = [
            {0: 38.0, 1: 0.0, 2: 6.0}, {0: 19.0, 1: 32.908965, 2: 6.0},
            {0: -19.0, 1: 32.908965, 2: 6.0}, {0: -38.0, 1: 0.0, 2: 6.0},
            {0: -19.0, 1: -32.908965, 2: 6.0}, {0: 19.0, 1: -32.908965, 2: 6.0},
        ]
        return (
            _match_cylinders(cylinders, 4.0, "z", centers, 12.0)
            and _match_cylinders(cylinders, 15.0, "z", [{0: 0.0, 1: 0.0, 2: 6.0}], 12.0)
        )
    if TASK_NUMBER == 5:
        r5 = [r for r in cylinders if _close(r["radius"], 5.0, 0.06) and _axis_matches(r, "z")]
        r3 = [r for r in cylinders if _close(r["radius"], 3.0, 0.06)]
        return len(r5) == 4 and len(r3) == 8
    if TASK_NUMBER == 6:
        return _match_cylinders(cylinders, 20.0, "x", [{0: 30.0}, {0: 90.0}], 10.0)
    if TASK_NUMBER == 7:
        return _match_cylinders(cylinders, 3.0, "z", [
            {0: 15.0, 1: 15.0}, {0: 145.0, 1: 15.0},
            {0: 15.0, 1: 85.0}, {0: 145.0, 1: 85.0},
        ], 6.0)
    if TASK_NUMBER == 8:
        voids = [
            (20.2, 40.0, 25.0), (99.8, 40.0, 25.0),
            (60.0, 20.2, 25.0), (60.0, 59.8, 25.0),
            (60.0, 40.0, 5.2), (60.0, 40.0, 49.8),
        ]
        material = [
            (19.8, 40.0, 25.0), (100.2, 40.0, 25.0),
            (60.0, 19.8, 25.0), (60.0, 60.2, 25.0),
            (60.0, 40.0, 4.8),
        ]
        return all(not _inside(solid, point) for point in voids) and all(_inside(solid, point) for point in material)
    if TASK_NUMBER == 9:
        for center_x in (35.0, 70.0, 105.0):
            material = [(center_x, 15.0, 14.0), (center_x - 11.0, 15.0, 35.0), (center_x + 11.0, 15.0, 8.5)]
            voids = [(center_x, 11.8, 14.0), (center_x, 18.2, 14.0), (center_x + 11.0, 15.0, 12.0)]
            if not all(_inside(solid, point) for point in material):
                return False
            if not all(not _inside(solid, point) for point in voids):
                return False
        return True
    if TASK_NUMBER == 10:
        voids = [(0.0, 0.0, 4.0), (20.2, 0.0, 4.0), (30.0, 8.8, 4.0)]
        material = [(-25.0, 0.0, 4.0), (19.8, 0.0, 4.0), (25.0, 9.2, 4.0), (25.0, -9.2, 4.0)]
        return all(not _inside(solid, point) for point in voids) and all(_inside(solid, point) for point in material)
    if TASK_NUMBER == 11:
        return (
            _match_cylinders(cylinders, 9.0, "z", [{0: 50.0, 1: 30.0}], 8.0)
            and _match_cylinders(cylinders, 4.0, "z", [{0: 20.0, 1: 20.0}, {0: 20.0, 1: 40.0}], 8.0)
        )
    if TASK_NUMBER == 12:
        if len(solids) != 6:
            return False
        actual = sorted(tuple(round(value, 3) for value in solid.Center().toTuple()) for solid in solids)
        expected = sorted((x, y, 6.0) for x in (6.0, 26.0, 46.0) for y in (6.0, 26.0))
        boxes_ok = all(
            _close(s.BoundingBox().xlen, 12.0) and _close(s.BoundingBox().ylen, 12.0) and _close(s.BoundingBox().zlen, 12.0)
            for s in solids
        )
        return boxes_ok and actual == expected
    if TASK_NUMBER == 14:
        return _match_cylinders(cylinders, 5.0, "x", [{0: 40.0, 1: 15.0, 2: 40.0}], 50.0)
    if TASK_NUMBER == 15:
        return (
            len(solids) == 1
            and _match_cylinders(cylinders, 25.0, "x", [{0: -4.0, 1: 0.0, 2: 0.0}], 8.0)
            and _match_cylinders(cylinders, 25.0, "y", [{0: 35.0, 1: -74.0, 2: 0.0}], 8.0)
        )
    if TASK_NUMBER == 16:
        return _match_cylinders(cylinders, 1.5, "z", [
            {0: 20.0, 1: 15.0, 2: 24.0}, {0: 70.0, 1: 15.0, 2: 24.0},
            {0: 20.0, 1: 45.0, 2: 24.0}, {0: 70.0, 1: 45.0, 2: 24.0},
        ], 8.0)
    if TASK_NUMBER == 17:
        voids = [(20.2, 0.0, 27.5), (79.8, 0.0, 27.5), (50.0, 3.8, 27.5)]
        material = [(19.8, 0.0, 27.5), (80.2, 0.0, 27.5), (50.0, 4.2, 27.5), (50.0, 0.0, 24.8)]
        return all(not _inside(solid, point) for point in voids) and all(_inside(solid, point) for point in material)
    if TASK_NUMBER == 19:
        return _match_cylinders(cylinders, 3.0, "z", [{0: 10.0, 1: -9.0}, {0: 60.0, 1: -9.0}], 6.0)
    return False


def evaluate():
    if not check_no_gui_bypass(DESKTOP):
        return False
    solids = _load_solids(Path(STEP_SPEC["path"]))
    if len(solids) != int(STEP_SPEC["solid_count"]):
        return False
    if any(not _close(actual, expected) for actual, expected in zip(_bounds(solids), STEP_SPEC["bounds"])):
        return False
    volume = sum(solid.Volume() for solid in solids)
    if abs(volume - float(STEP_SPEC["volume"])) / max(1.0, abs(float(STEP_SPEC["volume"]))) > VOLUME_REL_TOL:
        return False
    return _feature_check(solids)


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print("True" if ok else "False")
    raise SystemExit(0)
