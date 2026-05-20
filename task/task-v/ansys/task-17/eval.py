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

GROUND_TRUTH = {
    "top_wall_shear_pa": 3.2029001,
}

TOLERANCE = {
    "top_wall_shear_pa": {"rel": 0.12, "abs": 0.08},
}


def is_nonempty_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def has_forbidden_py_file(desktop_path: Path) -> bool:
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
        if name.endswith(".py") and name != "eval.py":
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


def within_tolerance(name: str, truth: float, pred: float) -> bool:
    tol = TOLERANCE[name]
    return abs(pred - truth) <= max(abs(truth) * tol["rel"], tol["abs"])


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
    _kill_ansys_related()

    if has_forbidden_py_file(DESKTOP):
        return False

    if any(not is_nonempty_file(p) for p in REQUIRED_FILES):
        return False
    try:
        pred = extract_predictions(DESKTOP)
    except Exception:
        return False
    for name, truth in GROUND_TRUTH.items():
        if name not in pred or not within_tolerance(name, truth, pred[name]):
            return False
    return True


def main() -> None:
    print("True" if evaluate() else "False")


if __name__ == "__main__":
    main()
