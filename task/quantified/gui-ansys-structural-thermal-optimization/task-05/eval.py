#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import math
import os
import re
import shutil
import tempfile
from pathlib import Path

ROOT = Path(os.environ.get("EVAL_ROOT", str(Path(os.environ.get("USERPROFILE", r"C:\Users\user")) / "Desktop")))
TASK = {'id': 'opt-ansys-gui-05', 'title': 'ANSYS GUI cantilever stiffness per mass optimization', 'kind': 'cantilever', 'objective_direction': 'maximize', 'metric_name': 'stiffness_per_mass', 'metric_units': 'N_per_mm_per_mass_unit', 'baseline_files': ['baseline_apdl_solid_beam.db', 'baseline_apdl_solid_beam.rst'], 'submission_files': ['submission.db', 'submission.rst'], 'result_suffixes': ['.rst'], 'constraints': {'force_magnitude': 500.0, 'allowable_mises': 160.0, 'fixed_support': 'one end face', 'loaded_region': 'opposite end face'}}
ANSYS_EXEC = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(lo, min(hi, value))


def required_paths(root: Path, names: list[str]) -> list[Path]:
    paths = [root / name for name in names]
    for path in paths:
        if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
            raise FileNotFoundError(path.name)
    return paths


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def native_artifacts_identical(baseline_paths: list[Path], submission_paths: list[Path]) -> bool:
    baseline = {path.suffix.lower(): path for path in baseline_paths if path.suffix.lower() in {".db", ".rst", ".rth"}}
    submission = {path.suffix.lower(): path for path in submission_paths if path.suffix.lower() in {".db", ".rst", ".rth"}}
    if not submission or any(suffix not in baseline for suffix in submission):
        return False
    return all(
        baseline[suffix].stat().st_size == path.stat().st_size and digest(baseline[suffix]) == digest(path)
        for suffix, path in submission.items()
    )


def _try_get(mapdl, *args) -> float | None:
    try:
        value = float(mapdl.get_value(*args))
        if math.isfinite(value):
            return value
    except Exception:
        return None
    return None


def _safe_run(mapdl, command: str) -> str:
    try:
        out = mapdl.run(command)
        return "" if out is None else str(out)
    except Exception:
        return ""


def prepare_case(case_name: str, source_paths: list[Path]) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory(prefix=f"ansys_{case_name}_")
    tmp_root = Path(tmp.name)
    for source in source_paths:
        suffix = source.suffix.lower()
        if suffix in {".db", ".rst", ".rth"}:
            target = tmp_root / f"case{suffix}"
        else:
            target = tmp_root / source.name
        shutil.copy2(source, target)
    return tmp


def launch_case(case_root: Path):
    from ansys.mapdl.core import launch_mapdl

    mapdl = launch_mapdl(exec_file=ANSYS_EXEC, run_location=str(case_root), nproc=1, override=True, cleanup_on_exit=False)
    _safe_run(mapdl, "/FILNAME,case")
    db = case_root / "case.db"
    if not db.exists():
        raise FileNotFoundError("case.db")
    try:
        mapdl.resume(str(db.with_suffix("")), "db")
    except Exception:
        _safe_run(mapdl, f"RESUME,{db.with_suffix('').as_posix()},db")
    _safe_run(mapdl, "/FILNAME,case")
    return mapdl


def get_bounds(mapdl) -> dict[str, float]:
    _safe_run(mapdl, "/PREP7")
    _safe_run(mapdl, "ALLSEL,ALL")
    out: dict[str, float] = {}
    for axis in ("X", "Y", "Z"):
        mn = _try_get(mapdl, "NODE", 0, "MNLOC", axis)
        mx = _try_get(mapdl, "NODE", 0, "MXLOC", axis)
        if mn is not None and mx is not None:
            out[f"min_{axis.lower()}"] = mn
            out[f"max_{axis.lower()}"] = mx
            out[f"span_{axis.lower()}"] = abs(mx - mn)
    return out


def get_model_counts(mapdl) -> dict[str, float]:
    _safe_run(mapdl, "/PREP7")
    _safe_run(mapdl, "ALLSEL,ALL")
    out: dict[str, float] = {}
    for entity, key in (("NODE", "node_count"), ("ELEM", "element_count"), ("MAT", "material_count"), ("TYPE", "element_type_count")):
        value = _try_get(mapdl, entity, 0, "COUNT")
        if value is not None:
            out[key] = value
    return out


def extract_mass_and_volume(mapdl) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for processor in ("/PREP7", "/POST1"):
        _safe_run(mapdl, processor)
        if processor == "/POST1":
            _safe_run(mapdl, "SET,LAST")
        _safe_run(mapdl, "ALLSEL,ALL")
        if "mass" not in metrics:
            for args in (("ELEM", 0, "MTOT", "X"), ("ELEM", 0, "MASS", "X")):
                val = _try_get(mapdl, *args)
                if val is not None and abs(val) > 0:
                    metrics["mass"] = abs(val)
                    break
        if "volume" not in metrics:
            for label, item in (("EVOL", "VOLU"), ("EAREA", "AREA")):
                _safe_run(mapdl, f"ETABLE,{label},{item}")
                _safe_run(mapdl, "SSUM")
                val = _try_get(mapdl, "SSUM", 0, "ITEM", label)
                if val is not None and abs(val) > 0:
                    metrics["volume"] = abs(val)
                    break
    if "volume" not in metrics:
        spans = []
        for axis in ("X", "Y", "Z"):
            mn = _try_get(mapdl, "NODE", 0, "MNLOC", axis)
            mx = _try_get(mapdl, "NODE", 0, "MXLOC", axis)
            if mn is not None and mx is not None:
                spans.append(abs(mx - mn))
        section_area = None
        for args in (("SECP", 1, "PROP", "AREA"), ("SECN", 1, "PROP", "AREA")):
            section_area = _try_get(mapdl, *args)
            if section_area is not None and section_area > 0:
                break
        if section_area is None or section_area <= 0:
            slist = _safe_run(mapdl, "SLIST,ALL")
            match = re.search(r"\bAREA\b\s*[:=]?\s*([-+0-9.Ee]+)", slist)
            if match:
                try:
                    section_area = float(match.group(1))
                except ValueError:
                    section_area = None
        if spans and max(spans) > 0:
            metrics["volume"] = max(spans) * (section_area if section_area and section_area > 0 else 1.0)
    return metrics


def extract_result_metrics(mapdl) -> dict[str, float]:
    metrics: dict[str, float] = {}
    metrics.update(get_bounds(mapdl))
    metrics.update(get_model_counts(mapdl))
    metrics.update(extract_mass_and_volume(mapdl))
    _safe_run(mapdl, "/POST1")
    _safe_run(mapdl, "SET,LAST")
    for sort_cmd, key in (
        ("NSORT,U,SUM,0,1,ALL", "max_disp"),
        ("NSORT,S,EQV,0,1,ALL", "max_mises"),
        ("NSORT,TEMP,,0,1,ALL", "max_temperature"),
    ):
        _safe_run(mapdl, sort_cmd)
        val = _try_get(mapdl, "SORT", 0, "MAX")
        if val is not None:
            metrics[key] = abs(val)
    for args, key in (
        (("MODE", 1, "FREQ"), "first_frequency"),
        (("MODE", 1, "STAB"), "first_buckling_factor"),
        (("ACTIVE", 0, "SET", "FREQ"), "active_frequency"),
    ):
        val = _try_get(mapdl, *args)
        if val is not None and val > 0:
            metrics[key] = val
    if "first_buckling_factor" not in metrics and TASK["kind"] == "buckling" and "first_frequency" in metrics:
        metrics["first_buckling_factor"] = metrics["first_frequency"]
    return metrics


def metrics_for(paths: list[Path]) -> dict[str, float]:
    tmp = prepare_case("case", paths)
    mapdl = None
    try:
        mapdl = launch_case(Path(tmp.name))
        return extract_result_metrics(mapdl)
    finally:
        if mapdl is not None:
            try:
                mapdl.exit()
            except Exception:
                pass
        try:
            tmp.cleanup()
        except Exception:
            shutil.rmtree(tmp.name, ignore_errors=True)


def positive(metrics: dict[str, float], key: str) -> float | None:
    value = metrics.get(key)
    if value is None or value <= 0 or not math.isfinite(value):
        return None
    return float(value)


def similar_span(submitted: dict[str, float], baseline: dict[str, float], axis: str, rel_tol: float = 0.02) -> bool:
    skey = f"span_{axis}"
    s_val = submitted.get(skey)
    b_val = baseline.get(skey)
    if s_val is None or b_val is None or b_val <= 0:
        return True
    return abs(s_val - b_val) <= max(1.0e-6, rel_tol * b_val)


def hard_constraints_ok(metrics: dict[str, float], baseline_metrics: dict[str, float]) -> bool:
    kind = TASK["kind"]
    constraints = TASK.get("constraints", {})
    if kind in {"bracket", "cantilever"}:
        allowable = constraints.get("allowable_mises")
        if allowable is not None and metrics.get("max_mises", float("inf")) > float(allowable):
            return False
    if kind == "bracket":
        max_disp = constraints.get("max_displacement")
        if max_disp is not None and metrics.get("max_disp", float("inf")) > float(max_disp):
            return False
        return all(similar_span(metrics, baseline_metrics, axis) for axis in ("x", "y", "z"))
    if kind == "buckling":
        return similar_span(metrics, baseline_metrics, "x")
    if kind == "modal":
        return similar_span(metrics, baseline_metrics, "x")
    if kind == "thermal":
        if constraints.get("submitted_volume_must_not_exceed_baseline"):
            sub_volume = positive(metrics, "volume")
            base_volume = positive(baseline_metrics, "volume")
            if sub_volume is not None and base_volume is not None and sub_volume > base_volume * 1.0001:
                return False
        return all(similar_span(metrics, baseline_metrics, axis) for axis in ("x", "y", "z"))
    if kind == "cantilever":
        return all(similar_span(metrics, baseline_metrics, axis) for axis in ("x", "y", "z"))
    return False


def raw_metric(metrics: dict[str, float], baseline_metrics: dict[str, float]) -> float | None:
    if not hard_constraints_ok(metrics, baseline_metrics):
        return None
    kind = TASK["kind"]
    constraints = TASK.get("constraints", {})
    if kind == "bracket":
        return positive(metrics, "mass") or positive(metrics, "volume")
    if kind == "buckling":
        factor = positive(metrics, "first_buckling_factor")
        mass = positive(metrics, "mass") or positive(metrics, "volume")
        if factor is None or mass is None:
            return None
        return factor / mass
    if kind == "modal":
        freq = positive(metrics, "first_frequency") or positive(metrics, "active_frequency")
        mass = positive(metrics, "mass") or positive(metrics, "volume")
        if freq is None or mass is None:
            return None
        return freq / mass
    if kind == "thermal":
        tmax = positive(metrics, "max_temperature")
        heat_power = constraints.get("heat_power_w")
        ambient = constraints.get("ambient_temperature_c")
        if tmax is None or heat_power is None or ambient is None or heat_power <= 0 or tmax <= ambient:
            return None
        return (tmax - float(ambient)) / float(heat_power)
    if kind == "cantilever":
        disp = positive(metrics, "max_disp")
        mass = positive(metrics, "mass") or positive(metrics, "volume")
        force = constraints.get("force_magnitude")
        if disp is None or mass is None or force is None or force <= 0:
            return None
        return float(force) / (disp * mass)
    return None


def score_from_metrics(submitted: float | None, baseline: float | None) -> float:
    if submitted is None or baseline is None:
        return 0.0
    if submitted <= 0 or baseline <= 0 or not math.isfinite(submitted) or not math.isfinite(baseline):
        return 0.0
    if TASK["objective_direction"] == "minimize":
        return clamp(1.0 - submitted / baseline)
    if TASK["objective_direction"] == "maximize":
        return clamp(1.0 - baseline / submitted)
    return 0.0


def evaluate() -> float:
    baseline_paths = required_paths(ROOT, TASK["baseline_files"])
    submission_paths = required_paths(ROOT, TASK["submission_files"])
    if native_artifacts_identical(baseline_paths, submission_paths):
        return 0.0
    baseline_metrics = metrics_for(baseline_paths)
    submitted_metrics = metrics_for(submission_paths)
    baseline_metric = raw_metric(baseline_metrics, baseline_metrics)
    submitted_metric = raw_metric(submitted_metrics, baseline_metrics)
    return score_from_metrics(submitted_metric, baseline_metric)


def main() -> int:
    try:
        score = evaluate()
    except Exception as exc:
        print("debug: " + str(exc))
        score = 0.0
    score = clamp(float(score))
    print(f"{score:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
