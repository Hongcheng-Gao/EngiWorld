from pathlib import Path
from shutil import which
import subprocess
import tempfile
import os
import glob


DESKTOP = Path(r"C:\Users\Administrator\Desktop")
CASE_FILE = DESKTOP / "pipe_laminar.cas"
DATA_FILE = DESKTOP / "pipe_laminar.dat"
REQUIRED_FILES = [CASE_FILE, DATA_FILE]

GROUND_TRUTH = {
    "centerline_velocity_m_s": 0.2,
}

TOLERANCE = {
    "centerline_velocity_m_s": {"rel": 0.12, "abs": 0.03},
}


def is_nonempty_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def has_forbidden_py_file(root: Path) -> bool:
    try:
        entries = list(root.iterdir())
    except Exception:
        return True

    for path in entries:
        try:
            if not path.is_file():
                continue
        except Exception:
            return True

        name = path.name.lower()
        if name.endswith(".py") and name != "eval.py":
            return True

    return False


def find_fluent_executable() -> str:
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
/file/read-case-data pipe_laminar.cas
/surface/point-surface outlet-center (0.05 0 0)
/report/surface-integrals/velocity-magnitude outlet-center () no
/exit yes
"""
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".jou", dir=root, delete=False) as fp:
        fp.write(jou)
        jou_path = Path(fp.name)

    try:
        fluent_exe = find_fluent_executable()
        proc = subprocess.run(
            [fluent_exe, "3ddp", "-g", "-i", jou_path.name],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if proc.returncode != 0:
            raise RuntimeError("fluent failed")
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        vals = []
        for tok in out.replace(",", " ").split():
            try:
                vals.append(float(tok))
            except ValueError:
                pass
        candidates = [abs(v) for v in vals if 0.0 <= abs(v) <= 5.0]
        if not candidates:
            raise RuntimeError("no velocity candidate extracted")
        return {"centerline_velocity_m_s": candidates[-1]}
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
