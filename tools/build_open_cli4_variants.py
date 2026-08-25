#!/usr/bin/env python3
"""Build open-choice variants of the ten four-tool CLI benchmark tasks.

The generated tasks preserve the engineering target but remove every model-side
tool, stage, handoff, provenance, and execution-order requirement.  Evaluation
compares only the submitted neutral STEP geometry with the trusted reference.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import textwrap


ROOT = Path(__file__).resolve().parents[1]
SOURCE_GROUP = ROOT / "task/multi/cli-4-kicad-openscad-freecad-blender"
TARGET_GROUP = ROOT / "task/挑选的 10 个最难题目"
DESKTOP = "/home/user/Desktop"

TOOL_INTRO = (
    "Available command-line tools include KiCad (`/usr/bin/kicad-cli`), "
    "OpenSCAD (`/usr/bin/openscad`), FreeCAD "
    "(`/home/user/.local/bin/freecadcmd`), and Blender "
    "(`/snap/bin/blender`). This is an open-choice task: use any subset of "
    "the available tools, in any order, with any amount of iteration. No "
    "application, stage sequence, intermediate handoff, command history, "
    "software version record, or provenance log is required."
)

OUTPUT_CONTRACT = (
    "Save the completed final assembly into `/home/user/Desktop/result` as "
    "one non-empty STEP or STP file; the filename is unrestricted. The STEP "
    "assembly must contain the physical enclosure or carrier, lid where "
    "required, PCB, installed components, and task-specific physical features "
    "in their final coordinates. Additional files are allowed but are not "
    "required. The evaluator grades only the final submitted geometry against "
    "the design contract. It does not grade which tools were used, their order, "
    "intermediate filenames, logs, reports, renders, or software identity."
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def neutralize_requirement_strings(value):
    if isinstance(value, dict):
        return {key: neutralize_requirement_strings(item) for key, item in value.items()}
    if isinstance(value, list):
        return [neutralize_requirement_strings(item) for item in value]
    if not isinstance(value, str):
        return value
    text = value
    text = text.replace(
        " and must be shown by a matching visible Blender overlay",
        "",
    )
    text = text.replace(
        " and keep a matching independent overlay visible in Blender",
        "",
    )
    text = text.replace("inspection scene", "enclosure assembly")
    text = text.replace("final FreeCAD and Blender assembly", "final assembly")
    text = text.replace("FreeCAD and Blender assembly", "final assembly")
    text = text.replace("OpenSCAD STL", "final carrier geometry")
    text = text.replace("FreeCAD", "the final geometry")
    text = text.replace("Blender", "the final assembly")
    text = text.replace("OpenSCAD", "the selected modeling workflow")
    text = text.replace("handoff", "design")
    text = text.replace("Handoff", "Design")
    return text


def open_requirements(source: dict, open_id: str) -> dict:
    value = neutralize_requirement_strings(source)
    value.pop("handoff_rule", None)
    if "mass_report_relative_tolerance" in value:
        value["mass_relative_tolerance"] = value.pop("mass_report_relative_tolerance")
    if "rib_stage_contract" in value:
        value["rib_geometry_contract"] = value.pop("rib_stage_contract")
    antenna = value.get("antenna_keepout")
    if isinstance(antenna, dict):
        antenna.pop("visible_blender_overlay", None)
    value["task"] = open_id
    value["schema_version"] = max(int(value.get("schema_version", 1)), 3)
    value["workflow_policy"] = {
        "mode": "open_choice",
        "mandatory_software": [],
        "required_order": [],
        "required_intermediate_artifacts": [],
        "evaluation_basis": "final STEP geometry only",
    }
    return value


def open_instruction(original: str) -> str:
    title = original.split(".", 1)[0].strip() + "."
    title = title.replace(" handoff.", " design.").replace(" flow.", " design.")
    title = title.replace("inspection scene.", "enclosure assembly.")
    body_start = original.find("Use the PCB outline center")
    if body_start < 0:
        raise ValueError("cannot find geometry contract start")
    body = original[body_start:]
    artifact_marker = body.find("Produce every required artifact directly on the desktop:")
    if artifact_marker < 0:
        raise ValueError("cannot find legacy artifact contract")
    body = body[:artifact_marker].strip()

    # Remove review-tool requirements while retaining physical geometry checks.
    body = re.sub(r"\s*In Blender,[^.]*\.", "", body)
    body = re.sub(r"\s*Blender must contain[^.]*\.", "", body)
    body = re.sub(r"\s*The FreeCAD report must include[^.]*\.", "", body)
    body = body.replace("In FreeCAD, measure", "Measure")
    body = body.replace("FreeCAD must calculate", "The final geometry must allow the evaluator to calculate")
    body = body.replace("from the submitted geometry", "from the final submitted geometry")
    body = body.replace("from submitted geometry", "from final submitted geometry")
    body = body.replace("mechanical_requirements.json", "design_requirements.json")
    body = re.sub(r"[ \t]+\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    inputs = (
        "Start from the supplied `board_input.kicad_pcb`, "
        "`design_requirements.json`, and `connector_keepouts.csv`. These files "
        "define the authoritative PCB geometry, installed coordinates, package "
        "dimensions, materials, tolerances, keepouts, and access bounds. They "
        "constrain the final design but do not prescribe a software workflow."
    )
    return "\n\n".join((TOOL_INTRO, title, inputs, body, OUTPUT_CONTRACT))


EVAL_TEMPLATE = r'''from __future__ import annotations

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
'''


def build_task(number: int) -> None:
    task_name = f"task-{number:02d}"
    source_dir = SOURCE_GROUP / task_name
    target_dir = TARGET_GROUP / task_name
    source_task = read_json(source_dir / f"{task_name}.json")
    open_id = source_task["id"].replace("c-multi-", "c-open-")

    target_init = target_dir / "init_file"
    target_gt = target_dir / "ground_truth"
    target_init.mkdir(parents=True, exist_ok=True)
    target_gt.mkdir(parents=True, exist_ok=True)

    shutil.copy2(source_dir / "init_file/board_input.kicad_pcb", target_init / "board_input.kicad_pcb")
    shutil.copy2(source_dir / "init_file/connector_keepouts.csv", target_init / "connector_keepouts.csv")
    requirements = open_requirements(
        read_json(source_dir / "init_file/mechanical_requirements.json"),
        open_id,
    )
    write_json(target_init / "design_requirements.json", requirements)

    reference_source = source_dir / "ground_truth/03_freecad_assembly.step"
    shutil.copy2(reference_source, target_gt / "result.step")
    open_spec = {
        "schema_version": 1,
        "mode": "open_choice",
        "source_task": str(source_dir.relative_to(ROOT)),
        "reference_artifact": "result.step",
        "workflow_constraints": {
            "mandatory_software": [],
            "required_order": [],
            "required_intermediate_artifacts": [],
            "software_identity_checked": False,
            "provenance_checked": False,
        },
        "accepted_output": {
            "root": f"{DESKTOP}/result",
            "extensions": [".step", ".stp"],
            "filename_required": False,
        },
        "geometry_tolerance": {
            "bounds_mm": 0.2,
            "absolute_volume_mm3": 3.0,
            "relative_volume": 0.001,
            "absolute_symmetric_difference_mm3": 3.0,
            "relative_symmetric_difference": 0.001,
            "minimum_reference_coverage": 0.999,
            "minimum_solid_count": 3,
        },
    }
    write_json(target_gt / "open_choice_spec.json", open_spec)
    (target_dir / "eval.py").write_text(EVAL_TEMPLATE, encoding="utf-8")

    local_prefix = f"{task_name}/init_file"
    evaluator_files = [
        {"local_path": f"{task_name}/eval.py", "path": f"{DESKTOP}/eval.py"},
        {
            "local_path": f"{task_name}/ground_truth/result.step",
            "path": f"{DESKTOP}/_eval_reference_result.step",
        },
        {
            "local_path": f"{task_name}/ground_truth/open_choice_spec.json",
            "path": f"{DESKTOP}/_eval_open_choice_spec.json",
        },
    ]
    task = {
        "id": open_id,
        "snapshot": source_task["snapshot"],
        "instruction": open_instruction(source_task["instruction"]),
        "source": source_task["source"] + f"; generated open-choice variant from {source_dir.relative_to(ROOT)}",
        "config": [
            {
                "type": "upload_file",
                "parameters": {
                    "files": [
                        {
                            "local_path": f"{local_prefix}/board_input.kicad_pcb",
                            "path": f"{DESKTOP}/board_input.kicad_pcb",
                        },
                        {
                            "local_path": f"{local_prefix}/design_requirements.json",
                            "path": f"{DESKTOP}/design_requirements.json",
                        },
                        {
                            "local_path": f"{local_prefix}/connector_keepouts.csv",
                            "path": f"{DESKTOP}/connector_keepouts.csv",
                        },
                    ]
                },
            }
        ],
        "trajectory": source_task.get("trajectory", "trajectories/"),
        "related_apps": source_task["related_apps"],
        "artifact_paths": [f"{DESKTOP}/result"],
        "evaluator": {
            "postconfig": [{"type": "upload_file", "parameters": {"files": evaluator_files}}],
            "func": "exact_match",
            "result": {
                "type": "vm_command_line",
                "command": f"python3 {DESKTOP}/eval.py",
                "shell": "true",
            },
            "expected": {"type": "rule", "rules": {"expected": "True\n"}},
        },
        "proxy": source_task.get("proxy", False),
        "fixed_ip": source_task.get("fixed_ip", False),
        "possibility_of_env_change": source_task.get("possibility_of_env_change", "low"),
    }
    write_json(target_dir / f"{task_name}.json", task)


def main() -> None:
    TARGET_GROUP.mkdir(parents=True, exist_ok=True)
    for number in range(1, 11):
        build_task(number)
    validate_generated_tasks()
    print(f"generated 10 open-choice tasks in {TARGET_GROUP.relative_to(ROOT)}")


def validate_generated_tasks() -> None:
    forbidden_instruction_fragments = (
        "run the tools in this order",
        "run the cli handoff in this order",
        "files must follow this sequence",
        "must consume the kicad step",
        "must consume the freecad",
        "in that order",
        "do not skip",
        "do not reorder",
        "01_kicad_",
        "02_openscad_",
        "03_freecad_",
        "04_blender_",
    )
    forbidden_requirement_fragments = (
        '"handoff_rule"',
        '"rib_stage_contract"',
        '"visible_blender_overlay"',
        '"mass_report_relative_tolerance"',
        "previous stage",
        "must consume",
        "visible blender overlay",
        "overlay visible in blender",
    )
    expected_inputs = {
        f"{DESKTOP}/board_input.kicad_pcb",
        f"{DESKTOP}/design_requirements.json",
        f"{DESKTOP}/connector_keepouts.csv",
    }

    for number in range(1, 11):
        task_name = f"task-{number:02d}"
        task_dir = TARGET_GROUP / task_name
        task = read_json(task_dir / f"{task_name}.json")
        instruction = task["instruction"].lower()
        for fragment in forbidden_instruction_fragments:
            if fragment in instruction:
                raise AssertionError(f"{task_name}: legacy instruction fragment remains: {fragment}")

        assert task["id"].startswith("c-open-")
        assert task["artifact_paths"] == [f"{DESKTOP}/result"]
        uploaded_inputs = {
            item["path"]
            for action in task["config"]
            for item in action["parameters"]["files"]
        }
        assert uploaded_inputs == expected_inputs

        requirements = read_json(task_dir / "init_file/design_requirements.json")
        workflow = requirements["workflow_policy"]
        assert workflow["mode"] == "open_choice"
        assert workflow["mandatory_software"] == []
        assert workflow["required_order"] == []
        assert workflow["required_intermediate_artifacts"] == []
        serialized_requirements = json.dumps(requirements, ensure_ascii=False).lower()
        for fragment in forbidden_requirement_fragments:
            if fragment in serialized_requirements:
                raise AssertionError(f"{task_name}: legacy requirement fragment remains: {fragment}")

        spec = read_json(task_dir / "ground_truth/open_choice_spec.json")
        constraints = spec["workflow_constraints"]
        assert constraints["mandatory_software"] == []
        assert constraints["required_order"] == []
        assert constraints["required_intermediate_artifacts"] == []
        assert constraints["software_identity_checked"] is False
        assert constraints["provenance_checked"] is False

        source_step = SOURCE_GROUP / task_name / "ground_truth/03_freecad_assembly.step"
        generated_step = task_dir / "ground_truth/result.step"
        assert generated_step.read_bytes() == source_step.read_bytes()
        evaluator_source = (task_dir / "eval.py").read_text(encoding="utf-8")
        compile(evaluator_source, str(task_dir / "eval.py"), "exec")


if __name__ == "__main__":
    main()
