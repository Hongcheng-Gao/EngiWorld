from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


DESKTOP = Path(os.environ.get("ENGIWORLD_DESKTOP", "/home/user/Desktop"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", str(DESKTOP / "result")))
REFERENCE_STEP = Path(os.environ.get("ENGIWORLD_OPEN_REFERENCE_STEP", str(DESKTOP / "_eval_reference_result.step")))
SPEC_PATH = Path(os.environ.get("ENGIWORLD_OPEN_SPEC", str(DESKTOP / "_eval_open_choice_spec.json")))


def fail(message: str) -> None:
    raise RuntimeError(message)


def load_spec() -> dict:
    try:
        value = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"cannot read trusted open-choice spec: {exc}")
    if not isinstance(value, dict):
        fail("trusted open-choice spec must be an object")
    return value


def find_submission() -> Path:
    if not OUTPUT_ROOT.is_dir():
        fail("result directory is missing")
    candidates = sorted(
        (
            path for path in OUTPUT_ROOT.rglob("*")
            if path.is_file() and path.suffix.lower() in {".step", ".stp"} and path.stat().st_size > 1000
        ),
        key=lambda path: (
            path.name.lower() not in {"result.step", "result.stp", "final.step", "final.stp", "assembly.step", "assembly.stp"},
            -path.stat().st_size,
            str(path),
        ),
    )
    if not candidates:
        fail("result directory contains no non-empty STEP/STP assembly")
    return candidates[0]


FREECAD_CHECKER = r"""
import json
import os
import traceback

import Part


candidate_path = os.environ["ENGIWORLD_OPEN_CANDIDATE"]
reference_path = os.environ["ENGIWORLD_OPEN_REFERENCE"]
result_path = os.environ["ENGIWORLD_OPEN_RESULT"]


def metrics(shape):
    box = shape.BoundBox
    return {
        "bounds_mm": [box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax],
        "bbox_mm": [box.XLength, box.YLength, box.ZLength],
        "volume_mm3": float(shape.Volume),
        "solid_count": len([solid for solid in shape.Solids if float(solid.Volume) > 0.01]),
    }


def evaluate():
    candidate = Part.read(candidate_path)
    reference = Part.read(reference_path)
    if candidate.isNull() or reference.isNull():
        raise RuntimeError("candidate or reference STEP is empty")
    if not candidate.isValid():
        raise RuntimeError("candidate STEP contains invalid geometry")
    common = float(candidate.common(reference).Volume)
    candidate_only = float(candidate.cut(reference).Volume)
    reference_only = float(reference.cut(candidate).Volume)
    return {
        "candidate": metrics(candidate),
        "reference": metrics(reference),
        "common_volume_mm3": common,
        "candidate_only_volume_mm3": candidate_only,
        "reference_only_volume_mm3": reference_only,
        "symmetric_difference_volume_mm3": candidate_only + reference_only,
    }


try:
    payload = {"ok": True, "result": evaluate()}
except Exception as exc:
    payload = {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}
with open(result_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
"""


def resolve_freecad() -> str:
    candidates = (
        "/home/user/.local/bin/freecadcmd",
        "/usr/bin/freecadcmd",
        "/usr/bin/FreeCADCmd",
    )
    for candidate in candidates:
        if Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    fail("FreeCADCmd is unavailable to the evaluator")


def close_vector(actual, expected, tolerance: float, label: str) -> None:
    if not isinstance(actual, list) or len(actual) != len(expected):
        fail(f"{label} has the wrong shape")
    if any(abs(float(a) - float(b)) > tolerance for a, b in zip(actual, expected)):
        fail(f"{label} differs: {actual} vs {expected}")


def evaluate() -> bool:
    spec = load_spec()
    candidate = find_submission()
    if not REFERENCE_STEP.is_file() or REFERENCE_STEP.stat().st_size <= 1000:
        fail("trusted reference STEP is missing")

    with tempfile.TemporaryDirectory(prefix="engiworld_open_eval_") as temp_dir:
        runtime = Path(temp_dir)
        checker = runtime / "geometry_checker.py"
        result_path = runtime / "geometry_result.json"
        checker.write_text(FREECAD_CHECKER, encoding="utf-8")
        env = {
            **os.environ,
            "PYTHONPATH": "",
            "ENGIWORLD_OPEN_CANDIDATE": str(candidate),
            "ENGIWORLD_OPEN_REFERENCE": str(REFERENCE_STEP),
            "ENGIWORLD_OPEN_RESULT": str(result_path),
        }
        completed = subprocess.run(
            [resolve_freecad(), str(checker)],
            cwd=str(runtime),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
            env=env,
        )
        output = completed.stdout + completed.stderr
        shutdown_crash = (
            completed.returncode == 1
            and result_path.is_file()
            and "Program received signal SIGSEGV" in output
            and "closeAllDocuments" in output
        )
        if completed.returncode != 0 and not shutdown_crash:
            fail(f"geometry evaluator failed: {(completed.stdout + completed.stderr)[-3000:]}")
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"geometry evaluator returned no readable result: {exc}")
        if not payload.get("ok"):
            fail(f"geometry evaluator rejected the final STEP: {payload.get('error')}")
        result = payload["result"]

    tolerance = spec["geometry_tolerance"]
    candidate_metrics = result["candidate"]
    reference_metrics = result["reference"]
    close_vector(
        candidate_metrics["bounds_mm"],
        reference_metrics["bounds_mm"],
        float(tolerance["bounds_mm"]),
        "final assembly bounds",
    )
    reference_volume = float(reference_metrics["volume_mm3"])
    if reference_volume <= 0 or float(candidate_metrics["volume_mm3"]) <= 0:
        fail("final assembly has non-positive volume")
    volume_delta = abs(float(candidate_metrics["volume_mm3"]) - reference_volume)
    if volume_delta > max(float(tolerance["absolute_volume_mm3"]), reference_volume * float(tolerance["relative_volume"])):
        fail(f"final assembly volume differs by {volume_delta} mm3")
    symmetric = float(result["symmetric_difference_volume_mm3"])
    symmetric_limit = max(
        float(tolerance["absolute_symmetric_difference_mm3"]),
        reference_volume * float(tolerance["relative_symmetric_difference"]),
    )
    if symmetric > symmetric_limit:
        fail(f"final geometry symmetric difference {symmetric} exceeds {symmetric_limit} mm3")
    coverage = float(result["common_volume_mm3"]) / reference_volume
    if coverage < float(tolerance["minimum_reference_coverage"]):
        fail(f"final geometry covers only {coverage:.6f} of the reference")
    if int(candidate_metrics["solid_count"]) < int(tolerance["minimum_solid_count"]):
        fail("final STEP does not retain enough distinct physical solids")
    return True


if __name__ == "__main__":
    try:
        passed = evaluate()
        detail = "PASS: final STEP geometry satisfies the open-choice contract."
    except Exception as exc:
        passed = False
        detail = f"FAIL: {type(exc).__name__}: {exc}"
    if not passed:
        print(detail, file=sys.stderr)
    print("True" if passed else "False")
