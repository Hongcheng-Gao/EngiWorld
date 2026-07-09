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
      86,
      54,
      1.6
    ],
    "components": [
      {
        "height_mm": 2.1,
        "keepout_radius_mm": 7.0,
        "kind": "MCU",
        "ref": "U1",
        "x_mm": -18,
        "y_mm": 4
      },
      {
        "height_mm": 1.4,
        "keepout_radius_mm": 6.0,
        "kind": "BARO",
        "ref": "U2",
        "x_mm": 16,
        "y_mm": 8
      },
      {
        "height_mm": 4.6,
        "keepout_radius_mm": 10.0,
        "kind": "USB_C",
        "ref": "J1",
        "x_mm": -39,
        "y_mm": 0
      },
      {
        "height_mm": 3.0,
        "keepout_radius_mm": 8.5,
        "kind": "SENSOR_FFC",
        "ref": "J2",
        "x_mm": 33,
        "y_mm": -16
      },
      {
        "height_mm": 1.2,
        "keepout_radius_mm": 4.0,
        "kind": "STATUS_LED",
        "ref": "D1",
        "x_mm": 4,
        "y_mm": 22
      }
    ],
    "corrected_board": "01_kicad_board.kicad_pcb",
    "critical_requirement": "USB-C and sensor FFC side windows must align to their KiCad footprint centers while preserving the lid clearance above U1.",
    "input_board": "board_input.kicad_pcb",
    "max_component_height_mm": 10.0,
    "mechanical_map": "01_kicad_mechanical_map.csv",
    "mounting_holes": [
      {
        "diameter_mm": 3.2,
        "ref": "MH1",
        "x_mm": -36,
        "y_mm": -22
      },
      {
        "diameter_mm": 3.2,
        "ref": "MH2",
        "x_mm": 36,
        "y_mm": -22
      },
      {
        "diameter_mm": 3.2,
        "ref": "MH3",
        "x_mm": -36,
        "y_mm": 22
      },
      {
        "diameter_mm": 3.2,
        "ref": "MH4",
        "x_mm": 36,
        "y_mm": 22
      }
    ],
    "software_stage": "KiCad",
    "task": "task-01"
  },
  "02_openscad_parameters.json": {
    "board_bbox_mm": [
      86,
      54,
      1.6
    ],
    "critical_requirement": "USB-C and sensor FFC side windows must align to their KiCad footprint centers while preserving the lid clearance above U1.",
    "enclosure_bbox_mm": [
      100.0,
      68.0,
      18.8
    ],
    "input_mechanical_map": "01_kicad_mechanical_map.csv",
    "lid_clearance_mm": 4.2,
    "mesh": "02_openscad_enclosure.stl",
    "software_stage": "OpenSCAD",
    "source": "02_openscad_enclosure.scad",
    "standoff_count": 4,
    "task": "task-01",
    "wall_mm": 3.0,
    "window_count": 2
  },
  "03_freecad_clearance_report.json": {
    "assembly_step": "03_freecad_assembly.step",
    "board_bbox_mm": [
      86,
      54,
      1.6
    ],
    "decision": "pass",
    "enclosure_bbox_mm": [
      100.0,
      68.0,
      18.8
    ],
    "estimated_shell_mass_g": 82.735,
    "inputs": [
      "01_kicad_board.kicad_pcb",
      "02_openscad_enclosure.stl",
      "02_openscad_parameters.json"
    ],
    "interference_volume_mm3": 0.0,
    "keepout_count": 5,
    "minimum_side_clearance_mm": 4.0,
    "minimum_top_clearance_mm": 4.2,
    "software_stage": "FreeCAD",
    "task": "task-01"
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
    "task": "task-01",
    "visible_keepouts": [
      "J1",
      "J2"
    ]
  },
  "final_release_package.json": {
    "critical_requirement": "USB-C and sensor FFC side windows must align to their KiCad footprint centers while preserving the lid clearance above U1.",
    "domain": "sealed sensor electronics pod",
    "key_metrics": {
      "board_bbox_mm": [
        86,
        54,
        1.6
      ],
      "enclosure_bbox_mm": [
        100.0,
        68.0,
        18.8
      ],
      "estimated_shell_mass_g": 82.735,
      "side_clearance_mm": 4.0,
      "top_clearance_mm": 4.2
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
    "task": "task-01",
    "title": "Environmental sensor pod board-to-enclosure release"
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
    "task": "task-01"
  }
}""")
EXPECTED_TEXT_SHA256 = json.loads(r"""{
  "01_kicad_board.kicad_pcb": "7399b13417dd16d431d2eb3110c7f7b2aec94ec8eb710a4ec3f960d3b89eba75",
  "01_kicad_mechanical_map.csv": "97a63a78d6d54b975c7a5340cc0a95e6e1a68b851866d5d448393a59041d0c64",
  "02_openscad_enclosure.scad": "39de8fcfbd04f3246f9912a264ed3ee437e7249ff2bf61666c8cd30f88baa17e",
  "02_openscad_enclosure.stl": "ee4fcf1f2c5b961013c0be3d36daa3506acc03ec759bade98e918f1e0ce22a62",
  "03_freecad_assembly.step": "bd1c1699dc1ad53496b9b37efee50e8cef5a8a2543e4d078b8141f37f084dffb",
  "04_blender_review.mtl": "a08991c672ab25d0f8d50f45fdfab34c7410b5de3b805eb7e6d70a2ecd93f4f1",
  "04_blender_review.obj": "2be6c0f75a3f3af9c353b318f0031ae5f6df3d3005ae532258f5406904caf2ff"
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
