from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path


DESKTOP = Path(os.environ.get("ENGIWORLD_DESKTOP", Path.home() / "Desktop"))
EXPECTED_JSON = json.loads(r"""{
  "01_kicad_export.json": {
    "board_bbox_mm": [
      154,
      58,
      1.6
    ],
    "components": [
      {
        "height_mm": 1.1,
        "keepout_radius_mm": 6.0,
        "kind": "AFE",
        "ref": "U1",
        "x_mm": -38,
        "y_mm": 0
      },
      {
        "height_mm": 7.8,
        "keepout_radius_mm": 12.5,
        "kind": "CELL_STACK",
        "ref": "J1",
        "x_mm": -74,
        "y_mm": 0
      },
      {
        "height_mm": 5.4,
        "keepout_radius_mm": 10.0,
        "kind": "SERVICE",
        "ref": "J2",
        "x_mm": 74,
        "y_mm": 0
      },
      {
        "height_mm": 4.2,
        "keepout_radius_mm": 9.0,
        "kind": "FUSE",
        "ref": "F1",
        "x_mm": 20,
        "y_mm": 16
      },
      {
        "height_mm": 2.6,
        "keepout_radius_mm": 5.0,
        "kind": "THERMISTOR",
        "ref": "NTC1",
        "x_mm": 0,
        "y_mm": -20
      }
    ],
    "corrected_board": "01_kicad_board.kicad_pcb",
    "critical_requirement": "Cell-stack and service connectors require opposite-side windows and the fuse keepout must remain uncovered.",
    "input_board": "board_input.kicad_pcb",
    "max_component_height_mm": 12.5,
    "mechanical_map": "01_kicad_mechanical_map.csv",
    "mounting_holes": [
      {
        "diameter_mm": 3.2,
        "ref": "MH1",
        "x_mm": -68,
        "y_mm": -22
      },
      {
        "diameter_mm": 3.2,
        "ref": "MH2",
        "x_mm": 68,
        "y_mm": -22
      },
      {
        "diameter_mm": 3.2,
        "ref": "MH3",
        "x_mm": -68,
        "y_mm": 22
      },
      {
        "diameter_mm": 3.2,
        "ref": "MH4",
        "x_mm": 68,
        "y_mm": 22
      }
    ],
    "software_stage": "KiCad",
    "task": "task-06",
    "openscad_parameter_handoff": "01_kicad_parameters.scad"
  },
  "02_openscad_parameters.json": {
    "board_bbox_mm": [
      154,
      58,
      1.6
    ],
    "critical_requirement": "Cell-stack and service connectors require opposite-side windows and the fuse keepout must remain uncovered.",
    "enclosure_bbox_mm": [
      168.8,
      72.8,
      22.0
    ],
    "lid_clearance_mm": 4.5,
    "mesh": "02_openscad_enclosure.stl",
    "software_stage": "OpenSCAD",
    "source": "02_openscad_enclosure.scad",
    "standoff_count": 4,
    "task": "task-06",
    "wall_mm": 3.4,
    "window_count": 2,
    "input_parameter_handoff": "01_kicad_parameters.scad",
    "source_mechanical_map": "01_kicad_mechanical_map.csv"
  },
  "03_freecad_clearance_report.json": {
    "assembly_step": "03_freecad_assembly.step",
    "board_bbox_mm": [
      154,
      58,
      1.6
    ],
    "decision": "pass",
    "enclosure_bbox_mm": [
      168.8,
      72.8,
      22.0
    ],
    "estimated_shell_mass_g": 159.938,
    "inputs": [
      "01_kicad_board.kicad_pcb",
      "02_openscad_enclosure.stl",
      "02_openscad_parameters.json"
    ],
    "interference_volume_mm3": 0.0,
    "keepout_count": 5,
    "minimum_side_clearance_mm": 4.0,
    "minimum_top_clearance_mm": 4.5,
    "software_stage": "FreeCAD",
    "task": "task-06",
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
    "task": "task-06",
    "visible_keepouts": [
      "J1",
      "J2"
    ]
  },
  "final_release_package.json": {
    "critical_requirement": "Cell-stack and service connectors require opposite-side windows and the fuse keepout must remain uncovered.",
    "domain": "battery management service cover",
    "key_metrics": {
      "board_bbox_mm": [
        154,
        58,
        1.6
      ],
      "enclosure_bbox_mm": [
        168.8,
        72.8,
        22.0
      ],
      "estimated_shell_mass_g": 159.938,
      "side_clearance_mm": 4.0,
      "top_clearance_mm": 4.5
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
    "task": "task-06",
    "title": "Battery BMS service-cover enclosure"
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
    "task": "task-06"
  }
}""")
EXPECTED_TEXT_SHA256 = json.loads(r"""{
  "01_kicad_board.kicad_pcb": "a2e8b8d326bcb30e1f3a95b0823b9a6a78d61cf4a8b3eddf97491461b00d7660",
  "01_kicad_mechanical_map.csv": "76e08371ef7dfa97eaa73a95c2a7d18f8b4dc723363269a4ad3ea2887b729304",
  "01_kicad_parameters.scad": "61eaca9da7d3dea00af1f3ec324b740a8875ebae0603f0534da409847067d959",
  "02_openscad_enclosure.scad": "ed441734f78b05b1f97a745c23f332a2890d37d75832d4b04d8e76c06b3f2020",
  "02_openscad_enclosure.stl": "b0c2aaf1820b9c8ef1843fd7ef2efe01c53c1deb190b94903d81c1f006150e3f",
  "03_freecad_assembly.step": "40ba3344617e1c557ab5e0bf34f7f5bcd7a92d1958cbfd281980c65b3664fb17",
  "03_freecad_assembly.obj": "bc1624e7663e9e541c0626483929f44fcc367ac95e2f032567b6b45e9daa4b20",
  "04_blender_review.mtl": "ed9ce71fc440e0ca91b8ef6f7843137eccad1d535efa8ee20e84a6d09368d1ad",
  "04_blender_review.obj": "2ab721ef42a8de50f7c6743c5588415b41ac96f31f37499d837c64e5322a02bf"
}""")
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


def norm_text(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).rstrip() + "\n"


def sha_text(path: Path) -> str:
    return hashlib.sha256(norm_text(path.read_text(encoding="utf-8")).encode("utf-8")).hexdigest()


def sha_stl_geometry(path: Path) -> str:
    facets = []
    triangle = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) != 4 or fields[0] != "vertex":
            continue
        vertex = tuple(0.0 if abs(float(value)) < 1e-12 else round(float(value), 9) for value in fields[1:])
        triangle.append(vertex)
        if len(triangle) == 3:
            facets.append(tuple(sorted(triangle)))
            triangle = []
    if triangle or not facets:
        raise ValueError("invalid or empty ASCII STL")
    canonical = json.dumps(sorted(facets), separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sha_artifact(path: Path) -> str:
    if path.suffix.lower() == ".stl":
        return sha_stl_geometry(path)
    return sha_text(path)


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
        if actual != expected:
            errors.append(f"json mismatch {name}")

    for name, expected_sha in EXPECTED_TEXT_SHA256.items():
        path = DESKTOP / name
        if not path.exists():
            continue
        try:
            if sha_artifact(path) != expected_sha:
                errors.append(f"text mismatch {name}")
        except Exception as exc:
            errors.append(f"text read failure {name}: {exc}")

    map_path = DESKTOP / "01_kicad_mechanical_map.csv"
    if map_path.exists():
        try:
            rows = list(csv.DictReader(map_path.read_text(encoding="utf-8").splitlines()))
            roles = {row.get("role") for row in rows}
            if "standoff_axis" not in roles:
                errors.append("mechanical map lacks standoff axes")
            if not ({"connector_window", "access_bore", "antenna_keepout", "component_keepout"} & roles):
                errors.append("mechanical map lacks component-derived roles")
        except Exception as exc:
            errors.append(f"mechanical map parse failure: {exc}")

    final_path = DESKTOP / "final_release_package.json"
    log_path = DESKTOP / "toolchain_invocation_log.json"
    if final_path.exists():
        final = json.loads(final_path.read_text(encoding="utf-8"))
        if final.get("software_sequence") != SOFTWARE_SEQUENCE:
            errors.append("final package software sequence mismatch")
        if final.get("required_artifacts") != REQUIRED_ARTIFACTS:
            errors.append("final package artifact list mismatch")
    if log_path.exists():
        log = json.loads(log_path.read_text(encoding="utf-8"))
        logged = [entry.get("software") for entry in log.get("commands", [])]
        if logged != SOFTWARE_SEQUENCE:
            errors.append("toolchain log does not use KiCad -> OpenSCAD -> FreeCAD -> Blender")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return False
    return True


if __name__ == "__main__":
    print("True" if main() else "False")
