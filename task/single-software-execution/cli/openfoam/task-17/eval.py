#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import math
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
    # Check the three actual defects, without requiring one exact English phrase.
    duplicate = any(token in low for token in ("duplicat", "coincident", "same coordinate", "identical to vertex"))
    orientation = any(token in low for token in ("inside-out", "right-handed", "right hand", "left-handed", "wrong-handed"))
    bad_index = "99" in low and any(token in low for token in ("range", "nonexistent", "non-existent", "does not exist", "invalid", "undefined"))
    corrected_corner = re.search(r"\(\s*0(?:\.0*)?\s+1(?:\.0*)?\s+0\.0*1\s*\)", low) is not None
    return "blockmesh" in low and duplicate and orientation and bad_index and corrected_corner


def final_field_is_structured(path: Path, class_name: str, list_type: str) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    text = read_text(path)
    if not re.search(r"\bformat\s+ascii\s*;", text) or not re.search(rf"\bclass\s+{re.escape(class_name)}\s*;", text):
        return False
    declaration = re.search(
        rf"internalField\s+nonuniform\s+List<{re.escape(list_type)}>\s+(\d+)\s*\(",
        text,
        flags=re.DOTALL,
    )
    if not declaration or int(declaration.group(1)) != 400:
        return False
    return re.search(r"(?i)(?:^|[^A-Za-z])(?:nan|inf)(?:[^A-Za-z]|$)", text) is None


def field_payload(path: Path) -> dict:
    """Parse ASCII field dictionaries without depending on whitespace or key order."""
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", read_text(path), flags=re.S)
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[{}();\[\]]|[^\s{}();\[\]]+', text)
    position = 0

    def dictionary(nested=False):
        nonlocal position
        result = {}
        while position < len(tokens):
            if tokens[position] == "}":
                if not nested:
                    raise ValueError("unexpected dictionary end")
                position += 1
                return result
            key = tokens[position].strip('"')
            position += 1
            if key in result or position >= len(tokens):
                raise ValueError("duplicate or unfinished field entry")
            if tokens[position] == "{":
                position += 1
                result[key] = dictionary(True)
                if position < len(tokens) and tokens[position] == ";":
                    position += 1
            else:
                values = []
                depth = 0
                while position < len(tokens):
                    token = tokens[position]
                    position += 1
                    if token == ";" and depth == 0:
                        break
                    if token in ("(", "["):
                        depth += 1
                    elif token in (")", "]"):
                        depth -= 1
                    if depth < 0 or token in ("{", "}"):
                        raise ValueError("invalid field syntax")
                    try:
                        value = float(token)
                    except ValueError:
                        value = token.strip('"')
                    else:
                        if not math.isfinite(value):
                            raise ValueError("nonfinite field value")
                    values.append(value)
                else:
                    raise ValueError("unterminated field entry")
                if depth:
                    raise ValueError("unbalanced field list")
                result[key] = values
        if nested:
            raise ValueError("unterminated dictionary")
        return result

    result = dictionary()
    header = result.pop("FoamFile", {})
    if header.get("format") != ["ascii"] or header.get("object") != [path.name]:
        raise ValueError("field header mismatch")
    expected = "volVectorField" if path.name == "U" else "volScalarField"
    if header.get("class") != [expected]:
        raise ValueError("field class mismatch")
    if not {"dimensions", "internalField", "boundaryField"}.issubset(result):
        raise ValueError("required field payload missing")
    return result


def equivalent_fields(left: Path, right: Path) -> bool:
    def equivalent(a, b):
        if isinstance(a, dict) and isinstance(b, dict):
            return a.keys() == b.keys() and all(equivalent(a[k], b[k]) for k in a)
        if isinstance(a, list) and isinstance(b, list):
            return len(a) == len(b) and all(equivalent(x, y) for x, y in zip(a, b))
        if isinstance(a, float) and isinstance(b, float):
            return math.isclose(a, b, rel_tol=5e-6, abs_tol=1e-9)
        return a == b
    try:
        return equivalent(field_payload(left), field_payload(right))
    except (ValueError, OSError):
        return False


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
        if not equivalent_fields(rerun_u, submitted_u):
            return False
        if not equivalent_fields(rerun_p, submitted_p):
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
