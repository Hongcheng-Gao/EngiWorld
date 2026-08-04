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
      66,
      42,
      1.0
    ],
    "components": [
      {
        "height_mm": 0.8,
        "keepout_radius_mm": 6.0,
        "kind": "OPTICAL_ASIC",
        "ref": "U1",
        "x_mm": 0,
        "y_mm": 0
      },
      {
        "height_mm": 1.5,
        "keepout_radius_mm": 4.0,
        "kind": "EMITTER",
        "ref": "LED1",
        "x_mm": -16,
        "y_mm": 0
      },
      {
        "height_mm": 1.2,
        "keepout_radius_mm": 4.0,
        "kind": "PHOTODIODE",
        "ref": "PD1",
        "x_mm": 16,
        "y_mm": 0
      },
      {
        "height_mm": 2.8,
        "keepout_radius_mm": 8.0,
        "kind": "FLEX",
        "ref": "J1",
        "x_mm": 0,
        "y_mm": -20
      },
      {
        "height_mm": 0.1,
        "keepout_radius_mm": 2.0,
        "kind": "FIDUCIAL",
        "ref": "FID1",
        "x_mm": -24,
        "y_mm": 14
      }
    ],
    "corrected_board": "01_kicad_board.kicad_pcb",
    "critical_requirement": "The Blender review scene must show the optical line between LED1 and PD1 unobstructed by the OpenSCAD carrier.",
    "input_board": "board_input.kicad_pcb",
    "max_component_height_mm": 8.0,
    "mechanical_map": "01_kicad_mechanical_map.csv",
    "mounting_holes": [
      {
        "diameter_mm": 2.4,
        "ref": "MH1",
        "x_mm": -26,
        "y_mm": -16
      },
      {
        "diameter_mm": 2.4,
        "ref": "MH2",
        "x_mm": 26,
        "y_mm": -16
      },
      {
        "diameter_mm": 2.4,
        "ref": "MH3",
        "x_mm": -26,
        "y_mm": 16
      },
      {
        "diameter_mm": 2.4,
        "ref": "MH4",
        "x_mm": 26,
        "y_mm": 16
      }
    ],
    "software_stage": "KiCad",
    "task": "task-07",
    "openscad_parameter_handoff": "01_kicad_parameters.scad"
  },
  "02_openscad_parameters.json": {
    "board_bbox_mm": [
      66,
      42,
      1.0
    ],
    "critical_requirement": "The Blender review scene must show the optical line between LED1 and PD1 unobstructed by the OpenSCAD carrier.",
    "enclosure_bbox_mm": [
      78.0,
      54.0,
      12.2
    ],
    "lid_clearance_mm": 1.2,
    "mesh": "02_openscad_enclosure.stl",
    "software_stage": "OpenSCAD",
    "source": "02_openscad_enclosure.scad",
    "standoff_count": 4,
    "task": "task-07",
    "wall_mm": 2.0,
    "window_count": 1,
    "input_parameter_handoff": "01_kicad_parameters.scad",
    "source_mechanical_map": "01_kicad_mechanical_map.csv"
  },
  "03_freecad_clearance_report.json": {
    "assembly_step": "03_freecad_assembly.step",
    "board_bbox_mm": [
      66,
      42,
      1.0
    ],
    "decision": "pass",
    "enclosure_bbox_mm": [
      78.0,
      54.0,
      12.2
    ],
    "estimated_shell_mass_g": 33.237,
    "inputs": [
      "01_kicad_board.kicad_pcb",
      "02_openscad_enclosure.stl",
      "02_openscad_parameters.json"
    ],
    "interference_volume_mm3": 0.0,
    "keepout_count": 5,
    "minimum_side_clearance_mm": 4.0,
    "minimum_top_clearance_mm": 1.2,
    "software_stage": "FreeCAD",
    "task": "task-07",
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
    "task": "task-07",
    "visible_keepouts": [
      "J1"
    ]
  },
  "final_release_package.json": {
    "critical_requirement": "The Blender review scene must show the optical line between LED1 and PD1 unobstructed by the OpenSCAD carrier.",
    "domain": "precision encoder readhead carrier",
    "key_metrics": {
      "board_bbox_mm": [
        66,
        42,
        1.0
      ],
      "enclosure_bbox_mm": [
        78.0,
        54.0,
        12.2
      ],
      "estimated_shell_mass_g": 33.237,
      "side_clearance_mm": 4.0,
      "top_clearance_mm": 1.2
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
    "task": "task-07",
    "title": "Optical encoder readhead alignment carrier"
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
    "task": "task-07"
  }
}""")
EXPECTED_TEXT_SHA256 = json.loads(r"""{
  "01_kicad_board.kicad_pcb": "508a5730343ce8a9f399abcffdb84289d7ce32cf4806e0904d999d02c4ec5a3c",
  "01_kicad_mechanical_map.csv": "adb0dacc70e5b4282988e747a42b27c80f73c6486f3827fa4706e3d927e7c4ec",
  "01_kicad_parameters.scad": "a5c48b91d87c9b0d9a316c79e33de1eece050757877b332ba8425ed9afcbbfd4",
  "02_openscad_enclosure.scad": "e7bf5eac1823145fbcd6d47ed023f18e741a0c7f7c8b3e84eab40468ac10e827",
  "02_openscad_enclosure.stl": "8eb402d27e1706f75e2de36fba0f8752b23cf5ba6806821cfafe12dfe3e66d83",
  "03_freecad_assembly.step": "636c1d89bfbf529fb07f0cabbcc1bbe953e9f4b23d3a3cc24cc5e1e28c12d0a2",
  "03_freecad_assembly.obj": "0e75eeb3554b4212d9ef4af8d6c7351ab096810ab0a93a7540ce9645088007ba",
  "04_blender_review.mtl": "03c01a2be19a88304e989a596c403fda6d7eaf37d4ab9bbe8b7387b93357b484",
  "04_blender_review.obj": "d4069f48e43b7d1dc6fc0e129de2c67a9d8066d1f428cf3ce047d6a5cbc326b0"
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
