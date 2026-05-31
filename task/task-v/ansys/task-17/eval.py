from pathlib import Path
from shutil import which
import subprocess
import tempfile
import os
import glob
import re

FLUENT_EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\fluent\ntbin\win64\fluent.exe"

DESKTOP = Path(r"C:\Users\user\Desktop")
CASE_FILE = DESKTOP / "couette.cas"
DATA_FILE = DESKTOP / "couette.dat"
REQUIRED_FILES = [CASE_FILE, DATA_FILE]


def is_nonempty_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def _is_known_generated_script(name: str) -> bool:
    return (
        (name.startswith("eval_") and name.endswith((".bat", ".cmd")))
        or (name.startswith("tmp") and name.endswith((".jou", ".wbjn")))
    )


def _cleanup_known_generated_scripts(desktop_path: Path) -> None:
    try:
        entries = list(desktop_path.iterdir())
    except Exception:
        return

    for entry in entries:
        try:
            if not entry.is_file():
                continue
        except Exception:
            continue

        name = entry.name.lower()
        if not _is_known_generated_script(name):
            continue

        try:
            entry.unlink()
        except Exception:
            pass


def has_forbidden_script_file(desktop_path: Path) -> bool:
    allowed_names = {"eval.py", "license.py"}
    forbidden_suffixes = {
        ".bat",
        ".cmd",
        ".ps1",
        ".vbs",
        ".js",
        ".pyw",
        ".jou",
        ".wbjn",
    }
    try:
        entries = desktop_path.iterdir()
    except Exception:
        return True

    for entry in entries:
        try:
            if not entry.is_file():
                continue
        except Exception:
            return True

        name = entry.name.lower()
        if name in allowed_names:
            continue
        if _is_known_generated_script(name):
            continue
        if any(name.endswith(ext) for ext in forbidden_suffixes):
            return True

    return False

def find_fluent_executable() -> str:
    explicit = Path(FLUENT_EXEC_FILE)
    if explicit.exists() and explicit.is_file():
        return str(explicit)

    cmd = which("fluent")
    if cmd:
        return cmd

    candidates = []
    for key, value in os.environ.items():
        if key.startswith("AWP_ROOT"):
            candidates.append(Path(value) / "fluent" / "ntbin" / "win64" / "fluent.exe")

    for pattern in [
        r"C:\Program Files\ANSYS Inc\ANSYS Student\v*\fluent\ntbin\win64\fluent.exe",
        r"C:\Program Files\ANSYS Inc\v*\fluent\ntbin\win64\fluent.exe",
    ]:
        for p in glob.glob(pattern):
            candidates.append(Path(p))

    for p in candidates:
        if p.exists() and p.is_file():
            return str(p)
    raise FileNotFoundError("Fluent executable not found in PATH or common install paths")


def extract_predictions(root: Path) -> dict:
    jou = """
/file/read-case-data couette.cas
/report/surface-integrals/area-weighted-avg top () wall-shear no
/exit yes
"""
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".jou", dir=root, delete=False) as fp:
        fp.write(jou)
        jou_path = Path(fp.name)

    try:
        fluent_exe = find_fluent_executable()
        proc = subprocess.run(
            [fluent_exe, "2ddp", "-g", "-i", jou_path.name],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if proc.returncode != 0:
            raise RuntimeError("fluent failed")
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        m = re.search(
            r"^\s*top\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*$",
            out,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if not m:
            raise RuntimeError("top wall-shear value not found")
        return {"top_wall_shear_pa": abs(float(m.group(1)))}
    finally:
        try:
            jou_path.unlink()
        except OSError:
            pass


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

_FLOAT_RE = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"


def _decode_file(path: Path) -> str:
    try:
        return path.read_bytes().decode("latin-1", errors="ignore")
    except Exception:
        return ""


def _extract_case_config_blob(case_file: Path) -> str:
    text = _decode_file(case_file)
    if not text:
        return ""
    m = re.search(r"\(case-config\s*\(\(.*?\)\)\)", text, flags=re.S)
    if not m:
        return ""
    return m.group(0)


def _case_config_has_true(blob: str, key: str) -> bool:
    if not blob:
        return False
    return f"({key} . #t)" in blob


def _case_config_has_false(blob: str, key: str) -> bool:
    if not blob:
        return False
    return f"({key} . #f)" in blob


def _extract_mesh_extents_2d(text: str):
    if not text:
        return None
    m = re.search(r"\(10\s+\(1\s+[0-9a-f]+\s+[0-9a-f]+\s+1\s+2\)\((.*?)\)\)", text, flags=re.S | re.I)
    if not m:
        return None
    nums = [float(x) for x in re.findall(_FLOAT_RE, m.group(1))]
    if len(nums) < 4 or len(nums) % 2:
        return None
    xs = nums[0::2]
    ys = nums[1::2]
    return min(xs), max(xs), min(ys), max(ys)


def _contains_all(text: str, tokens) -> bool:
    low = (text or "").lower()
    return all(t.lower() in low for t in tokens)


def _within(value: float, target: float, tol: float) -> bool:
    return abs(value - target) <= tol


def passes_process_checks(pred: dict, case_file: Path = None, data_file: Path = None, mesh_file: Path = None) -> bool:
    if case_file is not None:
        case_text = _decode_file(case_file)
        if not case_text:
            return False

        blob = _extract_case_config_blob(case_file)
        if not blob:
            return False

        if not _case_config_has_false(blob, "rp-unsteady?"):
            return False
        if not _case_config_has_false(blob, "rp-3d?"):
            return False
        if not _case_config_has_true(blob, "rp-visc?"):
            return False

        name = case_file.name.lower()
        case_low = case_text.lower()

        if name == "cavity.cas":
            if not _contains_all(case_low, ["(2 2)", "wall top", "wall bottom", "wall left", "wall right"]):
                return False
        elif name == "poiseuille_shear.cas":
            if not _contains_all(case_low, ["(2 2)", "velocity-inlet inlet", "pressure-outlet outlet", "wall top", "wall bottom"]):
                return False
        elif name == "poiseuille_2d.cas":
            if not _contains_all(case_low, ["(2 2)", "velocity-inlet inlet", "pressure-outlet outlet", "wall top", "wall bottom"]):
                return False
        elif name == "couette.cas":
            if not _contains_all(case_low, ["(2 2)", "wall top", "wall bottom"]):
                return False
            if not (
                _contains_all(case_low, ["symmetry left", "symmetry right"])
                or _contains_all(case_low, ["periodic left", "periodic right"])
            ):
                return False

        ext = _extract_mesh_extents_2d(case_text)
        if ext is not None:
            xmin, xmax, ymin, ymax = ext
            if name == "cavity.cas":
                if not (_within(xmin, 0.0, 5e-5) and _within(xmax, 1e-3, 5e-5) and _within(ymin, 0.0, 5e-5) and _within(ymax, 1e-3, 5e-5)):
                    return False
            elif name == "poiseuille_shear.cas":
                if not (_within(xmin, 0.0, 1e-3) and _within(xmax, 2e-1, 1e-3) and _within(ymin, 0.0, 1e-4) and _within(ymax, 2e-3, 1e-4)):
                    return False
            elif name == "poiseuille_2d.cas":
                if not (_within(xmin, 0.0, 2e-3) and _within(xmax, 1.0, 2e-3) and _within(ymin, 0.0, 1e-4) and _within(ymax, 2e-3, 1e-4)):
                    return False
            elif name == "couette.cas":
                if not (_within(xmin, 0.0, 1e-3) and _within(xmax, 1e-1, 1e-3) and _within(ymin, 0.0, 1e-4) and _within(ymax, 2e-3, 1e-4)):
                    return False

    if mesh_file is not None:
        mesh_text = _decode_file(mesh_file)
        if not mesh_text:
            return False
        mesh_low = mesh_text.lower()
        name = mesh_file.name.lower()

        if name == "pipe_laminar.msh":
            if not _contains_all(mesh_low, ["velocity-inlet inlet", "pressure-outlet outlet", "wall wall"]):
                return False
            if "(2 3)" in mesh_low:
                return False

            ext = _extract_mesh_extents_2d(mesh_text)
            if ext is None:
                return False
            xmin, xmax, ymin, ymax = ext
            if not (_within(xmin, 0.0, 2e-3) and _within(xmax, 1e-1, 2e-3) and _within(ymin, 0.0, 2e-4) and _within(ymax, 2e-3, 2e-4)):
                return False

    if "lid_speed_m_s" in pred:
        v = pred["lid_speed_m_s"]
        if not (0.01 <= v <= 0.5):
            return False
    if "wall_shear_pa" in pred:
        v = pred["wall_shear_pa"]
        if not (1e-4 <= v <= 50.0):
            return False
    if "centerline_velocity_m_s" in pred:
        v = pred["centerline_velocity_m_s"]
        if not (1e-4 <= v <= 5.0):
            return False
    if "top_wall_shear_pa" in pred:
        v = pred["top_wall_shear_pa"]
        if not (1e-4 <= v <= 100.0):
            return False

    return True


def evaluate() -> bool:
    _kill_ansys_related()
    _cleanup_known_generated_scripts(DESKTOP)

    if has_forbidden_script_file(DESKTOP):
        return False

    if any(not is_nonempty_file(p) for p in REQUIRED_FILES):
        return False
    try:
        pred = extract_predictions(DESKTOP)
    except Exception:
        return False
    return passes_process_checks(pred, case_file=CASE_FILE, data_file=DATA_FILE, mesh_file=None)

def main() -> None:
    print("True" if evaluate() else "False")


if __name__ == "__main__":
    main()
