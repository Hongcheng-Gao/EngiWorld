from pathlib import Path
from shutil import which
import subprocess
import tempfile
import traceback
import os
import glob


DESKTOP = Path(r"C:\Users\Administrator\Desktop")
CASE_FILE = DESKTOP / "cavity.cas"
DATA_FILE = DESKTOP / "cavity.dat"
REQUIRED_FILES = [CASE_FILE, DATA_FILE]

GROUND_TRUTH = {
    "lid_speed_m_s": 0.1,
}

TOLERANCE = {
    "lid_speed_m_s": {"rel": 0.20, "abs": 0.02},
}


def debug(msg: str) -> None:
    print(f"[DEBUG] {msg}")


def is_nonempty_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def find_fluent_executable() -> str:
    cmd = which("fluent")
    if cmd:
        debug(f"Found fluent from PATH: {cmd}")
        return cmd

    candidates = []

    for key, value in os.environ.items():
        if key.startswith("AWP_ROOT"):
            candidates.append(
                Path(value) / "fluent" / "ntbin" / "win64" / "fluent.exe"
            )

    for pattern in [
        r"C:\Program Files\ANSYS Inc\ANSYS Student\v*\fluent\ntbin\win64\fluent.exe",
        r"C:\Program Files\ANSYS Inc\v*\fluent\ntbin\win64\fluent.exe",
    ]:
        for p in glob.glob(pattern):
            candidates.append(Path(p))

    for p in candidates:
        debug(f"Probe fluent path: {p}")
        if p.exists() and p.is_file():
            debug(f"Found fluent from install path: {p}")
            return str(p)

    raise FileNotFoundError("Fluent executable not found in PATH or common install paths")


def check_required_files() -> bool:
    debug(f"Expect desktop path: {DESKTOP}")
    all_ok = True
    for file_path in REQUIRED_FILES:
        exists = file_path.exists()
        is_file = file_path.is_file() if exists else False
        size = file_path.stat().st_size if exists and is_file else 0
        debug(
            f"Check file: {file_path} | exists={exists} | is_file={is_file} | size={size}"
        )
        if not (exists and is_file and size > 0):
            all_ok = False

    if not all_ok:
        debug("Required files missing or empty. Eval returns false.")
        return False

    return True


def run_fluent_extract(root: Path) -> float:
    jou = """
/file/read-case-data cavity.cas
/surface/point-surface top_lid_midpoint (0.0005 0.001 0)
/report/surface-integrals/x-velocity top_lid_midpoint () no
/report/surface-integrals/velocity-magnitude top_lid_midpoint () no
/exit yes
"""
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".jou", dir=root, delete=False
    ) as fp:
        fp.write(jou)
        jou_path = Path(fp.name)

    debug(f"Journal path: {jou_path}")
    fluent_exe = find_fluent_executable()
    debug(f"Launching: {fluent_exe} 2ddp -g -i <journal>")
    try:
        proc = subprocess.run(
            [fluent_exe, "2ddp", "-g", "-i", jou_path.name],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=300,
        )
        debug(f"Fluent return code: {proc.returncode}")
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        debug(f"Fluent stdout length: {len(stdout)}")
        debug(f"Fluent stderr length: {len(stderr)}")

        if proc.returncode != 0:
            debug("Fluent process failed. stdout/stderr tail:")
            print(stdout[-2000:])
            print(stderr[-2000:])
            raise RuntimeError("fluent failed")

        out = stdout + "\n" + stderr
        vals = []
        for tok in out.replace(",", " ").split():
            try:
                vals.append(float(tok))
            except ValueError:
                pass

        debug(f"Numeric token count: {len(vals)}")
        if not vals:
            raise RuntimeError("no numeric value extracted")

        candidates = [v for v in vals if 0.0 <= v <= 2.0]
        debug(f"Velocity candidates in [0,2]: {len(candidates)}")
        if candidates:
            preview = candidates[:10]
            debug(f"Candidate preview: {preview}")
        if not candidates:
            raise RuntimeError("no velocity candidate extracted")

        target = GROUND_TRUTH["lid_speed_m_s"]
        pred = min(candidates, key=lambda v: abs(v - target))
        debug(f"Selected prediction: {pred}")
        return pred
    finally:
        try:
            jou_path.unlink()
            debug(f"Deleted journal: {jou_path}")
        except OSError:
            debug(f"Failed to delete journal: {jou_path}")


def within_tolerance(truth: float, pred: float) -> bool:
    tol = TOLERANCE["lid_speed_m_s"]
    rel_allow = abs(truth) * tol["rel"]
    abs_allow = tol["abs"]
    allow = max(rel_allow, abs_allow)
    err = abs(pred - truth)
    debug(
        f"Compare: truth={truth}, pred={pred}, abs_err={err}, "
        f"allow=max({rel_allow}, {abs_allow})={allow}"
    )
    return err <= allow


def evaluate() -> bool:
    debug("=== task-09 evaldebug start ===")
    if not check_required_files():
        return False

    try:
        pred = run_fluent_extract(DESKTOP)
    except Exception as exc:
        debug(f"Extraction exception: {exc}")
        debug(traceback.format_exc())
        return False

    truth = GROUND_TRUTH["lid_speed_m_s"]
    ok = within_tolerance(truth, pred)
    debug(f"Final compare result: {ok}")
    return ok


def main() -> None:
    ok = evaluate()
    print("True" if ok else "False")


if __name__ == "__main__":
    main()
