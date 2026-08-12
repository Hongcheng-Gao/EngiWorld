#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path


FOAM_BASHRC = Path("/opt/openfoam11/etc/bashrc")
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_foam(case: Path, args: list[str], timeout: int = 60) -> tuple[int, str]:
    command = [args[0], "-case", str(case), *args[1:]]
    script = f". {shlex.quote(str(FOAM_BASHRC))} && {shlex.join(command)}"
    completed = subprocess.run(
        ["bash", "-lc", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )
    return completed.returncode, completed.stdout


def has_required_case_files(case: Path) -> bool:
    required = (
        "0/U",
        "0/p",
        "constant/physicalProperties",
        "system/blockMeshDict",
        "system/controlDict",
        "system/fvSchemes",
        "system/fvSolution",
    )
    return all((case / rel).is_file() and (case / rel).stat().st_size > 0 for rel in required)


def diagnosis_is_specific(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    text = read_text(path)
    low = text.lower()
    if len(WORD_RE.findall(text)) < 100:
        return False
    requirements = (
        "vertex 7",
        "vertex 6",
        "99",
        "blockmesh",
        "checkmesh",
        "icofoam",
        "0.5",
    )
    if not all(token in low for token in requirements):
        return False
    if not ("inside-out" in low or "right-handed" in low or "right hand" in low):
        return False
    if not ("out of range" in low or "nonexistent" in low or "does not exist" in low):
        return False
    return bool(re.search(r"\(\s*0\s+1\s+0(?:\.0*)?1\s*\)", low))


def final_field_is_structured(path: Path, class_name: str, list_type: str) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    text = read_text(path)
    if "format      ascii;" not in text or f"class       {class_name};" not in text:
        return False
    declaration = re.search(
        rf"internalField\s+nonuniform\s+List<{re.escape(list_type)}>\s+(\d+)\s*\(",
        text,
        flags=re.DOTALL,
    )
    if not declaration or int(declaration.group(1)) != 400:
        return False
    return re.search(r"(?i)(?:^|[^A-Za-z])(?:nan|inf)(?:[^A-Za-z]|$)", text) is None


def remove_generated_mesh_and_times(case: Path) -> None:
    poly_mesh = case / "constant" / "polyMesh"
    if poly_mesh.exists():
        shutil.rmtree(poly_mesh)
    for child in case.iterdir():
        if not child.is_dir():
            continue
        try:
            time_value = float(child.name)
        except ValueError:
            continue
        if time_value > 0:
            shutil.rmtree(child)


def check_task(root: Path) -> bool:
    diagnosis = root / "diagnosis.txt"
    broken = root / "broken_block"
    fixed = root / "fixed"
    if not FOAM_BASHRC.is_file():
        return False
    if not diagnosis_is_specific(diagnosis):
        return False
    if not has_required_case_files(broken) or not has_required_case_files(fixed):
        return False

    submitted_u = fixed / "0.5" / "U"
    submitted_p = fixed / "0.5" / "p"
    if not final_field_is_structured(submitted_u, "volVectorField", "vector"):
        return False
    if not final_field_is_structured(submitted_p, "volScalarField", "scalar"):
        return False
    submitted_hashes = {"U": file_hash(submitted_u), "p": file_hash(submitted_p)}

    with tempfile.TemporaryDirectory(prefix="engiworld-openfoam17-eval-") as tmp:
        tmp_root = Path(tmp)
        broken_copy = tmp_root / "broken_block"
        fixed_copy = tmp_root / "fixed"
        shutil.copytree(broken, broken_copy)
        shutil.copytree(fixed, fixed_copy)

        broken_poly_mesh = broken_copy / "constant" / "polyMesh"
        if broken_poly_mesh.exists():
            shutil.rmtree(broken_poly_mesh)
        broken_rc, broken_log = run_foam(broken_copy, ["blockMesh"])
        broken_low = broken_log.lower()
        if broken_rc == 0 or "version:  11" not in broken_low:
            return False
        if "inside-out" not in broken_low or "fatal io error" not in broken_low:
            return False

        remove_generated_mesh_and_times(fixed_copy)
        mesh_rc, mesh_log = run_foam(fixed_copy, ["blockMesh"])
        if mesh_rc != 0 or "Version:  11" not in mesh_log or not mesh_log.rstrip().endswith("End"):
            return False
        if "nCells: 400" not in mesh_log or "Number of undefined boundary faces : 0" not in mesh_log:
            return False

        check_rc, check_log = run_foam(
            fixed_copy,
            ["checkMesh", "-allTopology", "-allGeometry"],
        )
        if check_rc != 0 or "Mesh OK." not in check_log or "Failed " in check_log:
            return False
        if "hexahedra:     400" not in check_log or "wedges:        0" not in check_log:
            return False

        solver_rc, solver_log = run_foam(fixed_copy, ["icoFoam"], timeout=90)
        if solver_rc != 0 or "Version:  11" not in solver_log or not solver_log.rstrip().endswith("End"):
            return False
        if "Time = 0.5s" not in solver_log:
            return False

        rerun_u = fixed_copy / "0.5" / "U"
        rerun_p = fixed_copy / "0.5" / "p"
        if not final_field_is_structured(rerun_u, "volVectorField", "vector"):
            return False
        if not final_field_is_structured(rerun_p, "volScalarField", "scalar"):
            return False
        if file_hash(rerun_u) != submitted_hashes["U"]:
            return False
        if file_hash(rerun_p) != submitted_hashes["p"]:
            return False

    return True


def evaluate() -> int:
    root = Path(os.environ.get("ENGIWORLD_EVAL_ROOT", "/home/user/Desktop"))
    try:
        return 1 if check_task(root) else 0
    except Exception:
        return 0


def main() -> int:
    print("True" if evaluate() == 1 else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
