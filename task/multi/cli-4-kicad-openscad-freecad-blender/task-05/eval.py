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
      94,
      70,
      1.6
    ],
    "components": [
      {
        "height_mm": 0.2,
        "keepout_radius_mm": 2.5,
        "kind": "POGO_TARGET",
        "ref": "TP1",
        "x_mm": -22,
        "y_mm": -12
      },
      {
        "height_mm": 0.2,
        "keepout_radius_mm": 2.5,
        "kind": "POGO_TARGET",
        "ref": "TP2",
        "x_mm": -6,
        "y_mm": -12
      },
      {
        "height_mm": 0.2,
        "keepout_radius_mm": 2.5,
        "kind": "POGO_TARGET",
        "ref": "TP3",
        "x_mm": 10,
        "y_mm": -12
      },
      {
        "height_mm": 0.2,
        "keepout_radius_mm": 2.5,
        "kind": "POGO_TARGET",
        "ref": "TP4",
        "x_mm": 26,
        "y_mm": -12
      },
      {
        "height_mm": 4.4,
        "keepout_radius_mm": 11.0,
        "kind": "EDGE_CONN",
        "ref": "J1",
        "x_mm": 0,
        "y_mm": 33
      }
    ],
    "corrected_board": "01_kicad_board.kicad_pcb",
    "critical_requirement": "Every pogo target in KiCad must become a matching access bore in the OpenSCAD adapter and remain visible in Blender.",
    "input_board": "board_input.kicad_pcb",
    "max_component_height_mm": 11.0,
    "mechanical_map": "01_kicad_mechanical_map.csv",
    "mounting_holes": [
      {
        "diameter_mm": 3.0,
        "ref": "MH1",
        "x_mm": -40,
        "y_mm": -28
      },
      {
        "diameter_mm": 3.0,
        "ref": "MH2",
        "x_mm": 40,
        "y_mm": -28
      },
      {
        "diameter_mm": 3.0,
        "ref": "MH3",
        "x_mm": -40,
        "y_mm": 28
      },
      {
        "diameter_mm": 3.0,
        "ref": "MH4",
        "x_mm": 40,
        "y_mm": 28
      }
    ],
    "software_stage": "KiCad",
    "task": "task-05"
  },
  "02_openscad_parameters.json": {
    "board_bbox_mm": [
      94,
      70,
      1.6
    ],
    "critical_requirement": "Every pogo target in KiCad must become a matching access bore in the OpenSCAD adapter and remain visible in Blender.",
    "enclosure_bbox_mm": [
      107.6,
      83.6,
      20.4
    ],
    "input_mechanical_map": "01_kicad_mechanical_map.csv",
    "lid_clearance_mm": 5.0,
    "mesh": "02_openscad_enclosure.stl",
    "software_stage": "OpenSCAD",
    "source": "02_openscad_enclosure.scad",
    "standoff_count": 4,
    "task": "task-05",
    "wall_mm": 2.8,
    "window_count": 1
  },
  "03_freecad_clearance_report.json": {
    "assembly_step": "03_freecad_assembly.step",
    "board_bbox_mm": [
      94,
      70,
      1.6
    ],
    "decision": "pass",
    "enclosure_bbox_mm": [
      107.6,
      83.6,
      20.4
    ],
    "estimated_shell_mass_g": 94.66,
    "inputs": [
      "01_kicad_board.kicad_pcb",
      "02_openscad_enclosure.stl",
      "02_openscad_parameters.json"
    ],
    "interference_volume_mm3": 0.0,
    "keepout_count": 5,
    "minimum_side_clearance_mm": 4.0,
    "minimum_top_clearance_mm": 5.0,
    "software_stage": "FreeCAD",
    "task": "task-05"
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
    "task": "task-05",
    "visible_keepouts": [
      "TP1",
      "TP2",
      "TP3",
      "TP4",
      "J1"
    ]
  },
  "final_release_package.json": {
    "critical_requirement": "Every pogo target in KiCad must become a matching access bore in the OpenSCAD adapter and remain visible in Blender.",
    "domain": "production test fixture adapter",
    "key_metrics": {
      "board_bbox_mm": [
        94,
        70,
        1.6
      ],
      "enclosure_bbox_mm": [
        107.6,
        83.6,
        20.4
      ],
      "estimated_shell_mass_g": 94.66,
      "side_clearance_mm": 4.0,
      "top_clearance_mm": 5.0
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
    "task": "task-05",
    "title": "Pogo-pin bed adapter with board-derived pin field"
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
    "task": "task-05"
  }
}""")
EXPECTED_TEXT_SHA256 = json.loads(r"""{
  "01_kicad_board.kicad_pcb": "9a15ce30a25a170b3d30e3ce7aadb4611e316959ebcd18c0efbfaadc1d4c5083",
  "01_kicad_mechanical_map.csv": "e5f95ab77ef93cf26d0aaa712c33c858c8268e5214ce06cddd46e9994a6682e8",
  "02_openscad_enclosure.scad": "5cb97ab708660fea33e665fe820c82fdc8162b1f51168deb76bbd71981328965",
  "02_openscad_enclosure.stl": "dbbde2ead6c82a0c81f9c7fef52984f7b5984f9d61824fa88ad34d2bd3003d4d",
  "03_freecad_assembly.step": "25b20bdb3814df60d7528f5d1cb0a161bea43539383c7ebce03e8a489e6166b7",
  "04_blender_review.mtl": "ee97cee43ee79bfdf9ca664355c73411740847b8fc94eea4e59889f447798502",
  "04_blender_review.obj": "c07cca655381f0a00faf47493f171c730c527d81349f1fef077808c16dbf2480"
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
