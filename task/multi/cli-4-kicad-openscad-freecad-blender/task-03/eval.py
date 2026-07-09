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
    "task": "task-03"
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
    "input_mechanical_map": "01_kicad_mechanical_map.csv",
    "lid_clearance_mm": 1.8,
    "mesh": "02_openscad_enclosure.stl",
    "software_stage": "OpenSCAD",
    "source": "02_openscad_enclosure.scad",
    "standoff_count": 4,
    "task": "task-03",
    "wall_mm": 2.2,
    "window_count": 2
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
    "task": "task-03"
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
    "task": "task-03",
    "title": "RF daughtercard shield-can and inspection scene"
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
    "task": "task-03"
  }
}""")
EXPECTED_TEXT_SHA256 = json.loads(r"""{
  "01_kicad_board.kicad_pcb": "dd6c0adaceec5c219ae112c4b185ca72f9e526251ba02ccd1c8a9d885fc9d584",
  "01_kicad_mechanical_map.csv": "7f1e01592df9d80f437c4d1aece1bbc06da1f255509b898b4a77aba49a11734f",
  "02_openscad_enclosure.scad": "0d2536bd0084a6a0d8b80f9c40787da5a305a6e4cbac6d34e2ed75716eb6a806",
  "02_openscad_enclosure.stl": "8c1f3f08ec97690a0e57b7b4c1bc090fe69c61cded163532a27cde7508d266b5",
  "03_freecad_assembly.step": "dc9f04e8c8bce392707f3ecf69d09b2b858c5903ad162fa8889d76e8cf9446a9",
  "04_blender_review.mtl": "735fc99c0f7a56724c1a2158035b893855f7c45f1bd89e3305ea35c04a86e166",
  "04_blender_review.obj": "df65c2b089cf69f767b321b38c8b37f6fe986d1e9b69f686140d7ba71914cb70"
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
