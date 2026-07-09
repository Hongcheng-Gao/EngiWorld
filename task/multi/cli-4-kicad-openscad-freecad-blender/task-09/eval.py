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
      118,
      92,
      1.6
    ],
    "components": [
      {
        "height_mm": 2.0,
        "keepout_radius_mm": 8.0,
        "kind": "THERMAL_SENSOR",
        "ref": "U1",
        "x_mm": 0,
        "y_mm": 18
      },
      {
        "height_mm": 1.0,
        "keepout_radius_mm": 18.0,
        "kind": "HEATER_ZONE",
        "ref": "H1",
        "x_mm": -24,
        "y_mm": -12
      },
      {
        "height_mm": 1.0,
        "keepout_radius_mm": 18.0,
        "kind": "HEATER_ZONE",
        "ref": "H2",
        "x_mm": 24,
        "y_mm": -12
      },
      {
        "height_mm": 4.6,
        "keepout_radius_mm": 10.0,
        "kind": "USB_C",
        "ref": "J1",
        "x_mm": -56,
        "y_mm": 0
      },
      {
        "height_mm": 4.0,
        "keepout_radius_mm": 8.0,
        "kind": "SYNC",
        "ref": "J2",
        "x_mm": 56,
        "y_mm": 0
      }
    ],
    "corrected_board": "01_kicad_board.kicad_pcb",
    "critical_requirement": "The heater zones must be exposed in the Blender material review while the USB and sync connectors get separate side apertures.",
    "input_board": "board_input.kicad_pcb",
    "max_component_height_mm": 18.0,
    "mechanical_map": "01_kicad_mechanical_map.csv",
    "mounting_holes": [
      {
        "diameter_mm": 3.0,
        "ref": "MH1",
        "x_mm": -50,
        "y_mm": -38
      },
      {
        "diameter_mm": 3.0,
        "ref": "MH2",
        "x_mm": 50,
        "y_mm": -38
      },
      {
        "diameter_mm": 3.0,
        "ref": "MH3",
        "x_mm": -50,
        "y_mm": 38
      },
      {
        "diameter_mm": 3.0,
        "ref": "MH4",
        "x_mm": 50,
        "y_mm": 38
      }
    ],
    "software_stage": "KiCad",
    "task": "task-09"
  },
  "02_openscad_parameters.json": {
    "board_bbox_mm": [
      118,
      92,
      1.6
    ],
    "critical_requirement": "The heater zones must be exposed in the Blender material review while the USB and sync connectors get separate side apertures.",
    "enclosure_bbox_mm": [
      131.0,
      105.0,
      25.1
    ],
    "input_mechanical_map": "01_kicad_mechanical_map.csv",
    "lid_clearance_mm": 3.0,
    "mesh": "02_openscad_enclosure.stl",
    "software_stage": "OpenSCAD",
    "source": "02_openscad_enclosure.scad",
    "standoff_count": 4,
    "task": "task-09",
    "wall_mm": 2.5,
    "window_count": 2
  },
  "03_freecad_clearance_report.json": {
    "assembly_step": "03_freecad_assembly.step",
    "board_bbox_mm": [
      118,
      92,
      1.6
    ],
    "decision": "pass",
    "enclosure_bbox_mm": [
      131.0,
      105.0,
      25.1
    ],
    "estimated_shell_mass_g": 121.424,
    "inputs": [
      "01_kicad_board.kicad_pcb",
      "02_openscad_enclosure.stl",
      "02_openscad_parameters.json"
    ],
    "interference_volume_mm3": 0.0,
    "keepout_count": 5,
    "minimum_side_clearance_mm": 4.0,
    "minimum_top_clearance_mm": 3.0,
    "software_stage": "FreeCAD",
    "task": "task-09"
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
      "03_freecad_assembly.step",
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
    "task": "task-09",
    "visible_keepouts": [
      "H1",
      "H2",
      "J1",
      "J2"
    ]
  },
  "final_release_package.json": {
    "critical_requirement": "The heater zones must be exposed in the Blender material review while the USB and sync connectors get separate side apertures.",
    "domain": "calibration target electronics mount",
    "key_metrics": {
      "board_bbox_mm": [
        118,
        92,
        1.6
      ],
      "enclosure_bbox_mm": [
        131.0,
        105.0,
        25.1
      ],
      "estimated_shell_mass_g": 121.424,
      "side_clearance_mm": 4.0,
      "top_clearance_mm": 3.0
    },
    "release_decision": "pass",
    "required_artifacts": [
      "01_kicad_board.kicad_pcb",
      "01_kicad_export.json",
      "01_kicad_mechanical_map.csv",
      "02_openscad_enclosure.scad",
      "02_openscad_enclosure.stl",
      "02_openscad_parameters.json",
      "03_freecad_assembly.step",
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
        "03_freecad_clearance_report.json"
      ],
      "KiCad": [
        "01_kicad_board.kicad_pcb",
        "01_kicad_export.json",
        "01_kicad_mechanical_map.csv"
      ],
      "OpenSCAD": [
        "02_openscad_enclosure.scad",
        "02_openscad_enclosure.stl",
        "02_openscad_parameters.json"
      ]
    },
    "task": "task-09",
    "title": "Thermal camera calibration target PCB mount"
  },
  "toolchain_invocation_log.json": {
    "commands": [
      {
        "command": "kicad-cli pcb export step board_input.kicad_pcb --output board.step && python3 kicad_extract_mechanical_map.py",
        "inputs": [
          "board_input.kicad_pcb",
          "mechanical_requirements.json",
          "connector_keepouts.csv"
        ],
        "outputs": [
          "01_kicad_board.kicad_pcb",
          "01_kicad_export.json",
          "01_kicad_mechanical_map.csv"
        ],
        "software": "KiCad"
      },
      {
        "command": "openscad -o 02_openscad_enclosure.stl 02_openscad_enclosure.scad",
        "inputs": [
          "01_kicad_mechanical_map.csv",
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
          "03_freecad_clearance_report.json"
        ],
        "software": "FreeCAD"
      },
      {
        "command": "blender --background --python blender_release_review.py",
        "inputs": [
          "03_freecad_assembly.step",
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
    "task": "task-09"
  }
}""")
EXPECTED_TEXT_SHA256 = json.loads(r"""{
  "01_kicad_board.kicad_pcb": "94c522ef3d53c1af1f09d12fe68e4a6f6e10dfb258913168c9d25adab4baf4b1",
  "01_kicad_mechanical_map.csv": "ca885f900dedac0b4fd44f2dc700bc29e923a23a5f3ee50dfb4134e5ab6f7ba4",
  "02_openscad_enclosure.scad": "55c9c69946c92f4123bf59911367670e0a906bf4fd56657ccc3978d619e93b13",
  "02_openscad_enclosure.stl": "f714b2799a31e9f97bba870b9ec49b0e734a49f74aa385488087cca9842a966a",
  "03_freecad_assembly.step": "0c739a0688215635dbf4a6bd70ee5c3c41a7f1100fae8e2881a9fd458c6b037b",
  "04_blender_review.mtl": "992c2628c54b4f619ad489f0ca0a02c4a7b999c5b16869ce46e2cec69edf2ad2",
  "04_blender_review.obj": "39d819c65cb6b5efdd1d21ef8f5a90d2343cfd3d8af0d9c3207810e5b223a5fd"
}""")
REQUIRED_ARTIFACTS = [
  "01_kicad_board.kicad_pcb",
  "01_kicad_export.json",
  "01_kicad_mechanical_map.csv",
  "02_openscad_enclosure.scad",
  "02_openscad_enclosure.stl",
  "02_openscad_parameters.json",
  "03_freecad_assembly.step",
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
            if sha_text(path) != expected_sha:
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
