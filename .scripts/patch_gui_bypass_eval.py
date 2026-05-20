"""Inject _gui_bypass checks into task-v eval.py for the nine gap apps."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TASK_V = REPO / "task" / "task-v"

APPS = (
    "ansys",
    "autocad",
    "freecad",
    "freecad-path",
    "librecad",
    "openscad",
    "solidcam",
    "solidworks",
    "solvespace",
)

IMPORT_BLOCK = """
import sys

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass
""".strip()

BYPASS_LINE_TPL = "    if not check_no_gui_bypass({root}):\n        return False\n"

DESKTOP_PATTERNS = [
    re.compile(r"^DESKTOP\s*=\s*(.+)$", re.M),
    re.compile(r"^OUTPUT_ROOT\s*=\s*(.+)$", re.M),
    re.compile(r"^TARGET\s*=\s*(.+)$", re.M),
]


def detect_root_expr(src: str) -> str | None:
    for pat in DESKTOP_PATTERNS:
        m = pat.search(src)
        if m:
            return m.group(1).strip()
    if re.search(r"/home/user/Desktop", src):
        return 'Path("/home/user/Desktop")'
    if re.search(r"C:\\\\Users\\\\user\\\\Desktop", src, re.I):
        return r'Path(r"C:\Users\user\Desktop")'
    return None


def ensure_desktop_const(src: str, root_expr: str) -> str:
    if re.search(r"^DESKTOP\s*=", src, re.M):
        return src
    if root_expr == 'Path("/home/user/Desktop")' or "Desktop" in root_expr:
        lines = src.splitlines(keepends=True)
        insert_at = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith(("#", '"""', "'''")):
                if line.startswith("from ") or line.startswith("import "):
                    continue
                insert_at = i
                break
        const = f"DESKTOP = {root_expr}\n\n"
        return "".join(lines[:insert_at]) + const + "".join(lines[insert_at:])
    return src


def already_patched(src: str) -> bool:
    return (
        "check_no_gui_bypass" in src
        or "GUI_BYPASS_FORBIDDEN_EXTENSIONS" in src
        or "from _gui_bypass import" in src
    )


def insert_imports(src: str) -> str:
    lines = src.splitlines(keepends=True)
    last_import = -1
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("import ") or s.startswith("from "):
            last_import = i
    insert_at = last_import + 1 if last_import >= 0 else 0
    block = IMPORT_BLOCK + "\n\n"
    if "Path(__file__)" in block and not any("from pathlib import Path" in l for l in lines):
        block = "from pathlib import Path\n" + block
    return "".join(lines[:insert_at]) + block + "".join(lines[insert_at:])


def patch_evaluate_fn(src: str, root_expr: str) -> str | None:
    bypass = BYPASS_LINE_TPL.format(root=root_expr)
    patterns = [
        (r"(def evaluate\([^)]*\)\s*(?:->\s*bool)?\s*:\n)", bypass),
        (r"(def main\(\)\s*->\s*bool:\n)", bypass),
    ]
    for pat, ins in patterns:
        m = re.search(pat, src)
        if m:
            return src[: m.end()] + ins + src[m.end() :]
    return None


def patch_solidcam_main(src: str, root_expr: str) -> str | None:
    bypass = (
        f"        if not check_no_gui_bypass({root_expr}):\n"
        "            ok = False\n"
        "        else:\n"
    )
    pat = r"(if __name__ == [\"']__main__[\"']:\n\s+try:\n)"
    m = re.search(pat, src)
    if not m:
        return None
    return src[: m.end()] + bypass + "            " + src[m.end() :].lstrip()


def patch_file(path: Path) -> str:
    src = path.read_text(encoding="utf-8")
    if already_patched(src):
        return "skip"
    root_expr = detect_root_expr(src)
    if not root_expr:
        return "no_root"
    src = ensure_desktop_const(src, root_expr)
    if root_expr.startswith("Path(") and "DESKTOP" not in src.split("def ")[0]:
        root_expr = "DESKTOP"
    src = insert_imports(src)
    new_src = patch_evaluate_fn(src, root_expr)
    if new_src is None and path.parts[-3] == "solidcam":
        new_src = patch_solidcam_main(src, root_expr)
    if new_src is None:
        return "no_eval"
    path.write_text(new_src, encoding="utf-8")
    return "patched"


def fix_ansys_task01() -> None:
    path = TASK_V / "ansys" / "task-01" / "eval.py"
    body = r'''from pathlib import Path
import subprocess
import sys

DESKTOP = Path(r"C:\Users\user\Desktop")
DB_FILE = DESKTOP / "apdl_solid_beam.db"
RESULT_FILE = DESKTOP / "apdl_solid_beam.rst"
REQUIRED_FILES = [DB_FILE, RESULT_FILE]
EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
JOBNAME = "eval_apdl_solid_beam"
MAPDL_PORT = 50110

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass

GROUND_TRUTH = {
    "load_point_UY_mm": -0.18762852462477883,
    "load_point_USUM_mm": 0.18815225868694857,
    "max_UY_mm": -0.18762852462477883,
    "max_USUM_mm": 0.18815225868694857,
    "max_von_mises_MPa": 52.70123620816831,
    "reaction_FY_N": -100.00001525878906,
}

TOLERANCE = {
    "default": {"rel": 0.01, "abs": 1e-4},
    "max_von_mises_MPa": {"rel": 0.01, "abs": 0.05},
    "reaction_FY_N": {"rel": 0.01, "abs": 0.10},
}


def is_nonempty_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def within_tolerance(name: str, truth: float, pred: float) -> bool:
    tol = TOLERANCE.get(name, TOLERANCE["default"])
    rel = tol["rel"]
    abs_tol = tol["abs"]
    if truth == 0:
        return abs(pred - truth) <= abs_tol
    return abs(pred - truth) <= max(abs(truth) * rel, abs_tol)


def allsel(mapdl) -> None:
    mapdl.run("ALLSEL,ALL")


def node_at(mapdl, x: float, y: float, z: float, tol: float = 1e-3) -> int:
    allsel(mapdl)
    mapdl.nsel("S", "LOC", "X", x - tol, x + tol)
    mapdl.nsel("R", "LOC", "Y", y - tol, y + tol)
    mapdl.nsel("R", "LOC", "Z", z - tol, z + tol)
    node = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
    allsel(mapdl)
    if node < 1:
        raise RuntimeError("Node not found.")
    return node


def sort_max(mapdl, item: str, comp: str = "") -> float:
    if comp:
        mapdl.run(f"NSORT,{item},{comp},0,1,ALL")
    else:
        mapdl.run(f"NSORT,{item},,0,1,ALL")
    return float(mapdl.get_value("SORT", 0, "MAX"))


def reaction_fy_on_z(mapdl, z: float, tol: float = 1e-3) -> float:
    allsel(mapdl)
    mapdl.nsel("S", "LOC", "Z", z - tol, z + tol)
    if int(mapdl.get_value("NODE", 0, "COUNT")) < 1:
        raise RuntimeError("No support nodes selected.")
    mapdl.fsum()
    fy = float(mapdl.get_value("FSUM", 0, "ITEM", "FY"))
    allsel(mapdl)
    return fy


def extract_predictions(mapdl) -> dict:
    mapdl.resume(DB_FILE.stem, "db")
    mapdl.post1()
    mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip("."))
    mapdl.set(1, 1)

    load_node = node_at(mapdl, x=5.0, y=10.0, z=100.0)
    return {
        "load_point_UY_mm": float(mapdl.get_value("NODE", load_node, "U", "Y")),
        "load_point_USUM_mm": float(mapdl.get_value("NODE", load_node, "U", "SUM")),
        "max_UY_mm": sort_max(mapdl, "U", "Y"),
        "max_USUM_mm": sort_max(mapdl, "U", "SUM"),
        "max_von_mises_MPa": sort_max(mapdl, "S", "EQV"),
        "reaction_FY_N": reaction_fy_on_z(mapdl, z=0.0),
    }


def _kill_ansys_related() -> None:
    for target in (
        "ANSYS261.exe",
        "ansys261.exe",
        "ANSYS.exe",
        "ansys.exe",
        "fluent.exe",
        "Fluent.exe",
        "cortex.exe",
        "Cortex.exe",
    ):
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", target],
                capture_output=True,
                creationflags=0x08000000,
            )
        except Exception:
            pass


def evaluate() -> bool:
    if not check_no_gui_bypass(DESKTOP):
        return False
    _kill_ansys_related()

    if any(not is_nonempty_file(p) for p in REQUIRED_FILES):
        return False

    mapdl = None
    try:
        from ansys.mapdl.core import launch_mapdl

        mapdl = launch_mapdl(
            exec_file=EXEC_FILE,
            jobname=JOBNAME,
            run_location=str(DESKTOP),
            nproc=1,
            port=MAPDL_PORT,
            override=True,
        )
        pred = extract_predictions(mapdl)
    except Exception:
        return False
    finally:
        if mapdl is not None:
            try:
                mapdl.exit()
            except Exception:
                pass

    for name, truth in GROUND_TRUTH.items():
        if name not in pred or not within_tolerance(name, truth, pred[name]):
            return False
    return True


def main() -> None:
    print("True" if evaluate() else "False")


if __name__ == "__main__":
    main()
'''
    path.write_text(body, encoding="utf-8")
    return "fixed_task01"


def main() -> None:
    stats: dict[str, int] = {}
    for app in APPS:
        app_root = TASK_V / app
        if not app_root.is_dir():
            continue
        for task_dir in sorted(app_root.glob("task-*/eval.py")):
            if app == "ansys" and task_dir.parent.name == "task-01":
                fix_ansys_task01()
                stats["fixed_task01"] = stats.get("fixed_task01", 0) + 1
                continue
            status = patch_file(task_dir)
            stats[status] = stats.get(status, 0) + 1
    print(stats)


if __name__ == "__main__":
    main()
