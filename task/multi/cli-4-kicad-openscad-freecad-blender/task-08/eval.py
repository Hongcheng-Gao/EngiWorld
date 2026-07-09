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
      176,
      38,
      1.6
    ],
    "components": [
      {
        "height_mm": 8.0,
        "keepout_radius_mm": 13.0,
        "kind": "BUSBAR_POS",
        "ref": "J1",
        "x_mm": -54,
        "y_mm": 0
      },
      {
        "height_mm": 8.0,
        "keepout_radius_mm": 13.0,
        "kind": "BUSBAR_NEG",
        "ref": "J2",
        "x_mm": 54,
        "y_mm": 0
      },
      {
        "height_mm": 3.6,
        "keepout_radius_mm": 12.0,
        "kind": "CURRENT_SENSOR",
        "ref": "U1",
        "x_mm": 0,
        "y_mm": 0
      },
      {
        "height_mm": 0.2,
        "keepout_radius_mm": 3.0,
        "kind": "HV_TEST",
        "ref": "TP1",
        "x_mm": -12,
        "y_mm": 14
      },
      {
        "height_mm": 0.2,
        "keepout_radius_mm": 3.0,
        "kind": "HV_TEST",
        "ref": "TP2",
        "x_mm": 12,
        "y_mm": 14
      }
    ],
    "corrected_board": "01_kicad_board.kicad_pcb",
    "critical_requirement": "The carrier must maintain separate positive and negative busbar windows and report creepage-side clearance in FreeCAD.",
    "input_board": "board_input.kicad_pcb",
    "max_component_height_mm": 13.0,
    "mechanical_map": "01_kicad_mechanical_map.csv",
    "mounting_holes": [
      {
        "diameter_mm": 3.5,
        "ref": "MH1",
        "x_mm": -78,
        "y_mm": -14
      },
      {
        "diameter_mm": 3.5,
        "ref": "MH2",
        "x_mm": 78,
        "y_mm": -14
      },
      {
        "diameter_mm": 3.5,
        "ref": "MH3",
        "x_mm": -78,
        "y_mm": 14
      },
      {
        "diameter_mm": 3.5,
        "ref": "MH4",
        "x_mm": 78,
        "y_mm": 14
      }
    ],
    "software_stage": "KiCad",
    "task": "task-08"
  },
  "02_openscad_parameters.json": {
    "board_bbox_mm": [
      176,
      38,
      1.6
    ],
    "critical_requirement": "The carrier must maintain separate positive and negative busbar windows and report creepage-side clearance in FreeCAD.",
    "enclosure_bbox_mm": [
      190.0,
      52.0,
      23.6
    ],
    "input_mechanical_map": "01_kicad_mechanical_map.csv",
    "lid_clearance_mm": 6.0,
    "mesh": "02_openscad_enclosure.stl",
    "software_stage": "OpenSCAD",
    "source": "02_openscad_enclosure.scad",
    "standoff_count": 4,
    "task": "task-08",
    "wall_mm": 3.0,
    "window_count": 2
  },
  "03_freecad_clearance_report.json": {
    "assembly_step": "03_freecad_assembly.step",
    "board_bbox_mm": [
      176,
      38,
      1.6
    ],
    "decision": "pass",
    "enclosure_bbox_mm": [
      190.0,
      52.0,
      23.6
    ],
    "estimated_shell_mass_g": 194.799,
    "inputs": [
      "01_kicad_board.kicad_pcb",
      "02_openscad_enclosure.stl",
      "02_openscad_parameters.json"
    ],
    "interference_volume_mm3": 0.0,
    "keepout_count": 5,
    "minimum_side_clearance_mm": 4.0,
    "minimum_top_clearance_mm": 6.0,
    "software_stage": "FreeCAD",
    "task": "task-08"
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
    "task": "task-08",
    "visible_keepouts": [
      "J1",
      "J2",
      "TP1",
      "TP2"
    ]
  },
  "final_release_package.json": {
    "critical_requirement": "The carrier must maintain separate positive and negative busbar windows and report creepage-side clearance in FreeCAD.",
    "domain": "busbar isolation carrier",
    "key_metrics": {
      "board_bbox_mm": [
        176,
        38,
        1.6
      ],
      "enclosure_bbox_mm": [
        190.0,
        52.0,
        23.6
      ],
      "estimated_shell_mass_g": 194.799,
      "side_clearance_mm": 4.0,
      "top_clearance_mm": 6.0
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
    "task": "task-08",
    "title": "High-current busbar insulator carrier"
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
    "task": "task-08"
  }
}""")
EXPECTED_TEXT_SHA256 = json.loads(r"""{
  "01_kicad_board.kicad_pcb": "378cc095f1b59782fc5766f1173f6f468b3316d1542b9c4fbc6ea6ff2565c5b2",
  "01_kicad_mechanical_map.csv": "52b34b4c3c107f57b831b6e36bf5c016d83de8570e52fab96ec37720e18e2903",
  "02_openscad_enclosure.scad": "ed082f60e65e9fce46a05addb313f10d0069798e028d3137eeb9eb3c75473a15",
  "02_openscad_enclosure.stl": "c8a38c7e0e304c2b395444d0532e5f1d3a9a761c8e1486fe3e743cadd5e810b4",
  "03_freecad_assembly.step": "7a3aa30569b08cdeac6ed4c22bfa32570748a9626eb7b1312e9f2754336b64c7",
  "04_blender_review.mtl": "80fb41264c68598ad85e782860fae8c5945de1cfc66e425181be5787742d567d",
  "04_blender_review.obj": "910953afe48e55c0f013327d9206a591fd0ed1e2be232ac8d7f4bf9e6ed59f71"
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
