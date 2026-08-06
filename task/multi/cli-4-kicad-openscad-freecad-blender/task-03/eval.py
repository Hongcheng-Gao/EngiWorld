from __future__ import annotations

import csv
import json
import os
import re
import sys
from pathlib import Path


DESKTOP = Path(os.environ.get("ENGIWORLD_DESKTOP", Path.home() / "Desktop"))
EXPECTED_JSON = json.loads(r"""{
  "01_kicad_export.json": {
    "board_bbox_mm": [
      72,
      48,
      1.2
    ],
    "components": [
      {
        "height_mm": 0.9,
        "keepout_radius_mm": 8.0,
        "kind": "RFIC",
        "ref": "U1",
        "x_mm": 0,
        "y_mm": 0
      },
      {
        "height_mm": 2.0,
        "keepout_radius_mm": 5.0,
        "kind": "TCXO",
        "ref": "Y1",
        "x_mm": -18,
        "y_mm": 12
      },
      {
        "height_mm": 2.4,
        "keepout_radius_mm": 7.0,
        "kind": "UFL_ANT",
        "ref": "J1",
        "x_mm": 32,
        "y_mm": 0
      },
      {
        "height_mm": 3.8,
        "keepout_radius_mm": 9.0,
        "kind": "MEZZ_CONN",
        "ref": "J2",
        "x_mm": -32,
        "y_mm": -12
      },
      {
        "height_mm": 0.2,
        "keepout_radius_mm": 3.0,
        "kind": "TEST_PAD",
        "ref": "TP1",
        "x_mm": 12,
        "y_mm": -18
      }
    ],
    "corrected_board": "01_kicad_board.kicad_pcb",
    "critical_requirement": "The shield window must exclude J1 while keeping the RFIC inside the protected volume.",
    "input_board": "board_input.kicad_pcb",
    "max_component_height_mm": 9.0,
    "mechanical_map": "01_kicad_mechanical_map.csv",
    "mounting_holes": [
      {
        "diameter_mm": 2.6,
        "ref": "MH1",
        "x_mm": -30,
        "y_mm": -18
      },
      {
        "diameter_mm": 2.6,
        "ref": "MH2",
        "x_mm": 30,
        "y_mm": -18
      },
      {
        "diameter_mm": 2.6,
        "ref": "MH3",
        "x_mm": -30,
        "y_mm": 18
      },
      {
        "diameter_mm": 2.6,
        "ref": "MH4",
        "x_mm": 30,
        "y_mm": 18
      }
    ],
    "software_stage": "KiCad",
    "task": "task-03",
    "openscad_parameter_handoff": "01_kicad_parameters.scad"
  },
  "02_openscad_parameters.json": {
    "board_bbox_mm": [
      72,
      48,
      1.2
    ],
    "critical_requirement": "The shield window must exclude J1 while keeping the RFIC inside the protected volume.",
    "enclosure_bbox_mm": [
      84.4,
      60.4,
      14.2
    ],
    "lid_clearance_mm": 1.8,
    "mesh": "02_openscad_enclosure.stl",
    "software_stage": "OpenSCAD",
    "source": "02_openscad_enclosure.scad",
    "standoff_count": 4,
    "task": "task-03",
    "wall_mm": 2.2,
    "window_count": 2,
    "input_parameter_handoff": "01_kicad_parameters.scad",
    "source_mechanical_map": "01_kicad_mechanical_map.csv"
  },
  "03_freecad_clearance_report.json": {
    "assembly_step": "03_freecad_assembly.step",
    "board_bbox_mm": [
      72,
      48,
      1.2
    ],
    "decision": "pass",
    "enclosure_bbox_mm": [
      84.4,
      60.4,
      14.2
    ],
    "estimated_shell_mass_g": 38.635,
    "inputs": [
      "01_kicad_board.kicad_pcb",
      "02_openscad_enclosure.stl",
      "02_openscad_parameters.json"
    ],
    "interference_volume_mm3": 0.0,
    "keepout_count": 5,
    "minimum_side_clearance_mm": 4.0,
    "minimum_top_clearance_mm": 1.8,
    "software_stage": "FreeCAD",
    "task": "task-03",
    "assembly_mesh": "03_freecad_assembly.obj"
  },
  "04_blender_scene_report.json": {
    "camera": {
      "name": "release_review_camera",
      "projection": "orthographic",
      "view": "top_oblique"
    },
    "collections": [
      "KiCad_board",
      "OpenSCAD_enclosure",
      "FreeCAD_clearance_overlays",
      "critical_keepouts"
    ],
    "decision": "pass",
    "inputs": [
      "03_freecad_assembly.obj",
      "03_freecad_clearance_report.json"
    ],
    "materials": [
      "enclosure_translucent",
      "pcb_green",
      "keepout_warning"
    ],
    "mesh_qc": {
      "missing_material_slots": 0,
      "nonmanifold_edges": 0,
      "unlabeled_keepouts": 0
    },
    "review_mtl": "04_blender_review.mtl",
    "review_obj": "04_blender_review.obj",
    "software_stage": "Blender",
    "task": "task-03",
    "visible_keepouts": [
      "J1",
      "J2",
      "TP1"
    ]
  },
  "final_release_package.json": {
    "critical_requirement": "The shield window must exclude J1 while keeping the RFIC inside the protected volume.",
    "domain": "RF shielded daughtercard",
    "key_metrics": {
      "board_bbox_mm": [
        72,
        48,
        1.2
      ],
      "enclosure_bbox_mm": [
        84.4,
        60.4,
        14.2
      ],
      "estimated_shell_mass_g": 38.635,
      "side_clearance_mm": 4.0,
      "top_clearance_mm": 1.8
    },
    "release_decision": "pass",
    "required_artifacts": [
      "01_kicad_board.kicad_pcb",
      "01_kicad_export.json",
      "01_kicad_mechanical_map.csv",
      "01_kicad_parameters.scad",
      "02_openscad_enclosure.scad",
      "02_openscad_enclosure.stl",
      "02_openscad_parameters.json",
      "03_freecad_assembly.step",
      "03_freecad_assembly.obj",
      "03_freecad_clearance_report.json",
      "04_blender_review.obj",
      "04_blender_review.mtl",
      "04_blender_scene_report.json",
      "toolchain_invocation_log.json",
      "final_release_package.json"
    ],
    "software_sequence": [
      "KiCad",
      "OpenSCAD",
      "FreeCAD",
      "Blender"
    ],
    "stage_outputs": {
      "Blender": [
        "04_blender_review.obj",
        "04_blender_review.mtl",
        "04_blender_scene_report.json"
      ],
      "FreeCAD": [
        "03_freecad_assembly.step",
        "03_freecad_assembly.obj",
        "03_freecad_clearance_report.json"
      ],
      "KiCad": [
        "01_kicad_board.kicad_pcb",
        "01_kicad_export.json",
        "01_kicad_mechanical_map.csv",
        "01_kicad_parameters.scad"
      ],
      "OpenSCAD": [
        "02_openscad_enclosure.scad",
        "02_openscad_enclosure.stl",
        "02_openscad_parameters.json"
      ]
    },
    "task": "task-03",
    "title": "RF daughtercard shield-can and inspection scene"
  },
  "toolchain_invocation_log.json": {
    "commands": [
      {
        "command": "kicad-cli pcb export step board_input.kicad_pcb --output board.step && python3 kicad_extract_mechanical_map.py --emit-scad 01_kicad_parameters.scad",
        "inputs": [
          "board_input.kicad_pcb",
          "mechanical_requirements.json",
          "connector_keepouts.csv"
        ],
        "outputs": [
          "01_kicad_board.kicad_pcb",
          "01_kicad_export.json",
          "01_kicad_mechanical_map.csv",
          "01_kicad_parameters.scad"
        ],
        "software": "KiCad"
      },
      {
        "command": "openscad -o 02_openscad_enclosure.stl 02_openscad_enclosure.scad",
        "inputs": [
          "01_kicad_parameters.scad",
          "enclosure_seed.scad"
        ],
        "outputs": [
          "02_openscad_enclosure.scad",
          "02_openscad_enclosure.stl",
          "02_openscad_parameters.json"
        ],
        "software": "OpenSCAD"
      },
      {
        "command": "FreeCADCmd freecad_assembly_check.py",
        "inputs": [
          "01_kicad_board.kicad_pcb",
          "02_openscad_enclosure.stl",
          "02_openscad_parameters.json"
        ],
        "outputs": [
          "03_freecad_assembly.step",
          "03_freecad_assembly.obj",
          "03_freecad_clearance_report.json"
        ],
        "software": "FreeCAD"
      },
      {
        "command": "blender --background --python blender_release_review.py",
        "inputs": [
          "03_freecad_assembly.obj",
          "03_freecad_clearance_report.json"
        ],
        "outputs": [
          "04_blender_review.obj",
          "04_blender_review.mtl",
          "04_blender_scene_report.json"
        ],
        "software": "Blender"
      }
    ],
    "required_software_sequence": [
      "KiCad",
      "OpenSCAD",
      "FreeCAD",
      "Blender"
    ],
    "task": "task-03"
  }
}""")
TEXT_ARTIFACTS = [
  "01_kicad_board.kicad_pcb",
  "01_kicad_mechanical_map.csv",
  "01_kicad_parameters.scad",
  "02_openscad_enclosure.scad",
  "02_openscad_enclosure.stl",
  "03_freecad_assembly.step",
  "03_freecad_assembly.obj",
  "04_blender_review.mtl",
  "04_blender_review.obj"
]
REQUIRED_ARTIFACTS = [
  "01_kicad_board.kicad_pcb",
  "01_kicad_export.json",
  "01_kicad_mechanical_map.csv",
  "01_kicad_parameters.scad",
  "02_openscad_enclosure.scad",
  "02_openscad_enclosure.stl",
  "02_openscad_parameters.json",
  "03_freecad_assembly.step",
  "03_freecad_assembly.obj",
  "03_freecad_clearance_report.json",
  "04_blender_review.obj",
  "04_blender_review.mtl",
  "04_blender_scene_report.json",
  "toolchain_invocation_log.json",
  "final_release_package.json"
]
SOFTWARE_SEQUENCE = ["KiCad", "OpenSCAD", "FreeCAD", "Blender"]


TOL = 0.05


def norm_text(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).rstrip() + "\n"


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def close(actual, expected, tol: float = TOL) -> bool:
    return is_number(actual) and abs(float(actual) - float(expected)) <= tol


def add(errors, message: str) -> None:
    errors.append(message)


def compare_numeric(label: str, actual, expected, errors, tol: float = TOL) -> None:
    if not close(actual, expected, max(tol, abs(float(expected)) * 0.02)):
        add(errors, f"{label} expected {expected}, got {actual}")


def compare_numeric_list(label: str, actual, expected, errors, tol: float = TOL) -> None:
    if not isinstance(actual, list) or len(actual) != len(expected):
        add(errors, f"{label} list length mismatch")
        return
    for idx, expected_value in enumerate(expected):
        compare_numeric(f"{label}[{idx}]", actual[idx], expected_value, errors, tol)


def require_string_list(label: str, actual, expected, errors, exact_set: bool = False) -> None:
    if not isinstance(actual, list):
        add(errors, f"{label} is not a list")
        return
    actual_set = {str(item) for item in actual}
    expected_set = {str(item) for item in expected}
    if exact_set:
        if actual_set != expected_set:
            add(errors, f"{label} set mismatch")
    elif not expected_set.issubset(actual_set):
        add(errors, f"{label} missing {sorted(expected_set - actual_set)}")


def compare_value(label: str, actual, expected, errors) -> None:
    if is_number(expected):
        if "minimum_" in label and float(expected) > 0:
            if not is_number(actual) or float(actual) < float(expected) - TOL:
                add(errors, f"{label} below expected minimum {expected}")
        elif "interference_volume" in label:
            if not is_number(actual) or float(actual) > max(float(expected), 0.0) + TOL:
                add(errors, f"{label} above allowed interference {expected}")
        elif "estimated_shell_mass_g" in label:
            compare_numeric(label, actual, expected, errors, tol=max(0.25, abs(float(expected)) * 0.05))
        else:
            compare_numeric(label, actual, expected, errors)
        return
    if isinstance(expected, list):
        if all(is_number(item) for item in expected):
            compare_numeric_list(label, actual, expected, errors)
        elif all(isinstance(item, str) for item in expected):
            exact = label.endswith("required_artifacts") or label.endswith("software_sequence")
            require_string_list(label, actual, expected, errors, exact_set=exact)
        elif all(isinstance(item, dict) and "ref" in item for item in expected):
            compare_ref_records(label, actual, expected, errors)
        else:
            if actual != expected:
                add(errors, f"{label} list mismatch")
        return
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            add(errors, f"{label} is not an object")
            return
        for key, expected_value in expected.items():
            if key not in actual:
                add(errors, f"{label}.{key} missing")
            else:
                compare_value(f"{label}.{key}", actual[key], expected_value, errors)
        return
    if actual != expected:
        add(errors, f"{label} expected {expected!r}, got {actual!r}")


def compare_ref_records(label: str, actual, expected, errors) -> None:
    if not isinstance(actual, list):
        add(errors, f"{label} is not a list")
        return
    actual_by_ref = {str(item.get("ref")): item for item in actual if isinstance(item, dict)}
    for expected_item in expected:
        ref = str(expected_item.get("ref"))
        actual_item = actual_by_ref.get(ref)
        if actual_item is None:
            add(errors, f"{label} missing ref {ref}")
            continue
        for key, expected_value in expected_item.items():
            if key not in actual_item:
                add(errors, f"{label}.{ref}.{key} missing")
            else:
                compare_value(f"{label}.{ref}.{key}", actual_item[key], expected_value, errors)


def validate_toolchain_log(actual, expected, errors) -> None:
    commands = actual.get("commands") if isinstance(actual, dict) else None
    expected_commands = expected.get("commands", [])
    if not isinstance(commands, list):
        add(errors, "toolchain log commands is not a list")
        return
    actual_sequence = [entry.get("software") for entry in commands if isinstance(entry, dict)]
    if actual_sequence != SOFTWARE_SEQUENCE:
        add(errors, "toolchain log does not use KiCad -> OpenSCAD -> FreeCAD -> Blender")
    by_software = {entry.get("software"): entry for entry in commands if isinstance(entry, dict)}
    for expected_entry in expected_commands:
        software = expected_entry.get("software")
        actual_entry = by_software.get(software)
        if actual_entry is None:
            add(errors, f"toolchain log missing {software}")
            continue
        if not str(actual_entry.get("command", "")).strip():
            add(errors, f"toolchain log {software} command is empty")
        require_string_list(f"toolchain log {software} inputs", actual_entry.get("inputs", []), expected_entry.get("inputs", []), errors)
        require_string_list(f"toolchain log {software} outputs", actual_entry.get("outputs", []), expected_entry.get("outputs", []), errors)


def validate_json_artifact(name: str, actual, expected, errors) -> None:
    if not isinstance(actual, dict):
        add(errors, f"{name} is not a JSON object")
        return
    if name == "toolchain_invocation_log.json":
        validate_toolchain_log(actual, expected, errors)
        return

    for key, expected_value in expected.items():
        if key not in actual:
            add(errors, f"{name}.{key} missing")
            continue
        if key == "commands":
            continue
        compare_value(f"{name}.{key}", actual[key], expected_value, errors)


def all_expected_refs():
    export = EXPECTED_JSON["01_kicad_export.json"]
    refs = [item["ref"] for item in export.get("components", [])]
    refs += [item["ref"] for item in export.get("mounting_holes", [])]
    return refs


def parse_csv_rows(path: Path):
    return list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))


def compare_csv_number(label: str, row, key: str, expected, errors) -> None:
    try:
        actual = float(row.get(key, "nan"))
    except ValueError:
        add(errors, f"{label}.{key} is not numeric")
        return
    compare_numeric(f"{label}.{key}", actual, expected, errors)


def validate_mechanical_map(path: Path, errors) -> None:
    rows = parse_csv_rows(path)
    by_ref = {row.get("ref"): row for row in rows}
    export = EXPECTED_JSON["01_kicad_export.json"]
    for component in export.get("components", []):
        ref = component["ref"]
        row = by_ref.get(ref)
        if row is None:
            add(errors, f"mechanical map missing {ref}")
            continue
        if row.get("kind") != component.get("kind"):
            add(errors, f"mechanical map {ref} kind mismatch")
        for key in ("x_mm", "y_mm", "height_mm", "keepout_radius_mm"):
            compare_csv_number(f"mechanical map {ref}", row, key, component[key], errors)
        if not row.get("role"):
            add(errors, f"mechanical map {ref} role missing")
    for hole in export.get("mounting_holes", []):
        ref = hole["ref"]
        row = by_ref.get(ref)
        if row is None:
            add(errors, f"mechanical map missing {ref}")
            continue
        if row.get("role") != "standoff_axis":
            add(errors, f"mechanical map {ref} must be a standoff_axis")
        compare_csv_number(f"mechanical map {ref}", row, "x_mm", hole["x_mm"], errors)
        compare_csv_number(f"mechanical map {ref}", row, "y_mm", hole["y_mm"], errors)
    roles = {row.get("role") for row in rows}
    if "standoff_axis" not in roles:
        add(errors, "mechanical map lacks standoff axes")
    if not ({"connector_window", "access_bore", "antenna_keepout", "component_keepout"} & roles):
        add(errors, "mechanical map lacks component-derived roles")


def parse_vertices(path: Path):
    vertices = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        fields = line.split()
        if len(fields) == 4 and fields[0] == "vertex":
            vertices.append(tuple(float(value) for value in fields[1:]))
        elif len(fields) >= 4 and fields[0] == "v":
            vertices.append(tuple(float(value) for value in fields[1:4]))
    return vertices


def bbox_from_vertices(vertices):
    mins = [min(vertex[idx] for vertex in vertices) for idx in range(3)]
    maxs = [max(vertex[idx] for vertex in vertices) for idx in range(3)]
    return [maxs[idx] - mins[idx] for idx in range(3)]


def validate_bbox_file(name: str, path: Path, expected_bbox, errors) -> None:
    vertices = parse_vertices(path)
    if len(vertices) < 8:
        add(errors, f"{name} does not contain enough mesh vertices")
        return
    bbox = bbox_from_vertices(vertices)
    compare_numeric_list(f"{name} bbox", bbox, expected_bbox, errors, tol=0.25)


def validate_step(path: Path, errors) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "ISO-10303-21" not in text or "END-ISO-10303-21" not in text:
        add(errors, "STEP file is missing ISO-10303-21 wrapper")
    if "FreeCAD" not in text and "freecad" not in text.lower():
        add(errors, "STEP file does not record FreeCAD assembly handoff")
    mins = re.search(r"ENCLOSURE_MIN[^\n]*\(([-0-9., ]+)\)", text)
    maxs = re.search(r"ENCLOSURE_MAX[^\n]*\(([-0-9., ]+)\)", text)
    if mins and maxs:
        min_values = [float(value) for value in mins.group(1).split(",")]
        max_values = [float(value) for value in maxs.group(1).split(",")]
        bbox = [max_values[idx] - min_values[idx] for idx in range(3)]
        expected_bbox = EXPECTED_JSON["02_openscad_parameters.json"]["enclosure_bbox_mm"]
        compare_numeric_list("STEP enclosure bbox", bbox, expected_bbox, errors, tol=0.25)


def require_text_contains(name: str, text: str, needles, errors) -> None:
    for needle in needles:
        if str(needle) not in text:
            add(errors, f"{name} missing {needle}")


def validate_text_artifact(name: str, path: Path, errors) -> None:
    export = EXPECTED_JSON["01_kicad_export.json"]
    openscad = EXPECTED_JSON["02_openscad_parameters.json"]
    blender = EXPECTED_JSON["04_blender_scene_report.json"]
    lower_suffix = path.suffix.lower()

    if name == "01_kicad_mechanical_map.csv":
        validate_mechanical_map(path, errors)
        return
    if lower_suffix == ".stl":
        validate_bbox_file(name, path, openscad["enclosure_bbox_mm"], errors)
        return
    if lower_suffix == ".step":
        validate_step(path, errors)
        return
    if lower_suffix == ".obj":
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "04_blender_review" in name:
            require_text_contains(name, text, ["mtllib 04_blender_review.mtl", "usemtl enclosure_translucent", "usemtl pcb_green"], errors)
        else:
            require_text_contains(name, text, ["enclosure", "pcb"], errors)
        validate_bbox_file(name, path, openscad["enclosure_bbox_mm"], errors)
        return
    text = path.read_text(encoding="utf-8", errors="ignore")
    if name == "01_kicad_board.kicad_pcb":
        require_text_contains(name, text, ["(kicad_pcb", "Edge.Cuts"], errors)
        require_text_contains(name, text, all_expected_refs(), errors)
        return
    if name == "01_kicad_parameters.scad":
        require_text_contains(name, text, ["01_kicad_mechanical_map.csv", "mechanical_features", "standoff_axes", "interface_features"], errors)
        require_text_contains(name, text, all_expected_refs(), errors)
        require_text_contains(name, text, [f"{value:.3f}" for value in export["board_bbox_mm"][:2]], errors)
        return
    if name == "02_openscad_enclosure.scad":
        require_text_contains(name, text, ["01_kicad_parameters.scad", "module", "enclosure"], errors)
        interface_refs = []
        for component in export.get("components", []):
            if component.get("kind") in {"USB_C", "POWER_IN", "POWER_OUT", "SENSOR_FFC", "ETHERNET", "SYNC"} or component["ref"].startswith("J"):
                interface_refs.append(component["ref"])
        require_text_contains(name, text, interface_refs, errors)
        return
    if name == "04_blender_review.mtl":
        require_text_contains(name, text, [f"newmtl {material}" for material in blender.get("materials", [])], errors)
        return


def main() -> bool:
    errors = []
    for name in REQUIRED_ARTIFACTS:
        if not (DESKTOP / name).exists():
            errors.append(f"missing {name}")

    for name, expected in EXPECTED_JSON.items():
        path = DESKTOP / name
        if not path.exists():
            continue
        try:
            actual = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid json {name}: {exc}")
            continue
        validate_json_artifact(name, actual, expected, errors)

    for name in TEXT_ARTIFACTS:
        path = DESKTOP / name
        if not path.exists():
            continue
        try:
            validate_text_artifact(name, path, errors)
        except Exception as exc:
            errors.append(f"artifact validation failure {name}: {exc}")

    final_path = DESKTOP / "final_release_package.json"
    log_path = DESKTOP / "toolchain_invocation_log.json"
    if final_path.exists():
        try:
            final = json.loads(final_path.read_text(encoding="utf-8"))
            if final.get("software_sequence") != SOFTWARE_SEQUENCE:
                errors.append("final package software sequence mismatch")
            require_string_list("final package required_artifacts", final.get("required_artifacts", []), REQUIRED_ARTIFACTS, errors, exact_set=True)
        except Exception as exc:
            errors.append(f"final package read failure: {exc}")
    if log_path.exists():
        try:
            log = json.loads(log_path.read_text(encoding="utf-8"))
            logged = [entry.get("software") for entry in log.get("commands", [])]
            if logged != SOFTWARE_SEQUENCE:
                errors.append("toolchain log does not use KiCad -> OpenSCAD -> FreeCAD -> Blender")
        except Exception as exc:
            errors.append(f"toolchain log read failure: {exc}")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return False
    return True



if __name__ == "__main__":
    print("True" if main() else "False")
