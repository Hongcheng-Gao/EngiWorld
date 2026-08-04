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
      128,
      86,
      1.6
    ],
    "components": [
      {
        "height_mm": 5.5,
        "keepout_radius_mm": 18.0,
        "kind": "MOSFET_BANK",
        "ref": "Q1",
        "x_mm": -28,
        "y_mm": 10
      },
      {
        "height_mm": 5.5,
        "keepout_radius_mm": 18.0,
        "kind": "MOSFET_BANK",
        "ref": "Q2",
        "x_mm": 0,
        "y_mm": 10
      },
      {
        "height_mm": 5.5,
        "keepout_radius_mm": 18.0,
        "kind": "MOSFET_BANK",
        "ref": "Q3",
        "x_mm": 28,
        "y_mm": 10
      },
      {
        "height_mm": 9.0,
        "keepout_radius_mm": 14.0,
        "kind": "PHASE_TERMINAL",
        "ref": "J1",
        "x_mm": 58,
        "y_mm": 0
      },
      {
        "height_mm": 4.0,
        "keepout_radius_mm": 8.0,
        "kind": "HALL_SENSOR",
        "ref": "J2",
        "x_mm": -58,
        "y_mm": -18
      }
    ],
    "corrected_board": "01_kicad_board.kicad_pcb",
    "critical_requirement": "The tray ribs must not enter the MOSFET bank keepouts and the phase terminal window must be on the X+ side.",
    "input_board": "board_input.kicad_pcb",
    "max_component_height_mm": 18.0,
    "mechanical_map": "01_kicad_mechanical_map.csv",
    "mounting_holes": [
      {
        "diameter_mm": 3.5,
        "ref": "MH1",
        "x_mm": -54,
        "y_mm": -36
      },
      {
        "diameter_mm": 3.5,
        "ref": "MH2",
        "x_mm": 54,
        "y_mm": -36
      },
      {
        "diameter_mm": 3.5,
        "ref": "MH3",
        "x_mm": -54,
        "y_mm": 36
      },
      {
        "diameter_mm": 3.5,
        "ref": "MH4",
        "x_mm": 54,
        "y_mm": 36
      }
    ],
    "software_stage": "KiCad",
    "task": "task-04",
    "openscad_parameter_handoff": "01_kicad_parameters.scad"
  },
  "02_openscad_parameters.json": {
    "board_bbox_mm": [
      128,
      86,
      1.6
    ],
    "critical_requirement": "The tray ribs must not enter the MOSFET bank keepouts and the phase terminal window must be on the X+ side.",
    "enclosure_bbox_mm": [
      142.4,
      100.4,
      26.4
    ],
    "lid_clearance_mm": 3.6,
    "mesh": "02_openscad_enclosure.stl",
    "software_stage": "OpenSCAD",
    "source": "02_openscad_enclosure.scad",
    "standoff_count": 4,
    "task": "task-04",
    "wall_mm": 3.2,
    "window_count": 2,
    "input_parameter_handoff": "01_kicad_parameters.scad",
    "source_mechanical_map": "01_kicad_mechanical_map.csv"
  },
  "03_freecad_clearance_report.json": {
    "assembly_step": "03_freecad_assembly.step",
    "board_bbox_mm": [
      128,
      86,
      1.6
    ],
    "decision": "pass",
    "enclosure_bbox_mm": [
      142.4,
      100.4,
      26.4
    ],
    "estimated_shell_mass_g": 150.489,
    "inputs": [
      "01_kicad_board.kicad_pcb",
      "02_openscad_enclosure.stl",
      "02_openscad_parameters.json"
    ],
    "interference_volume_mm3": 0.0,
    "keepout_count": 5,
    "minimum_side_clearance_mm": 4.0,
    "minimum_top_clearance_mm": 3.6,
    "software_stage": "FreeCAD",
    "task": "task-04",
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
    "task": "task-04",
    "visible_keepouts": [
      "J1",
      "J2"
    ]
  },
  "final_release_package.json": {
    "critical_requirement": "The tray ribs must not enter the MOSFET bank keepouts and the phase terminal window must be on the X+ side.",
    "domain": "rugged motor controller tray",
    "key_metrics": {
      "board_bbox_mm": [
        128,
        86,
        1.6
      ],
      "enclosure_bbox_mm": [
        142.4,
        100.4,
        26.4
      ],
      "estimated_shell_mass_g": 150.489,
      "side_clearance_mm": 4.0,
      "top_clearance_mm": 3.6
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
    "task": "task-04",
    "title": "Motor-controller vibration tray handoff"
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
    "task": "task-04"
  }
}""")
EXPECTED_TEXT_SHA256 = json.loads(r"""{
  "01_kicad_board.kicad_pcb": "8f8ddcaae122f8a52bfe6706468faccb033c916667a29c92a02c3026c9c2d2c3",
  "01_kicad_mechanical_map.csv": "9873ba740fdee39c282f389eda250f2515299b53026fddfeff034da63b18e5fb",
  "01_kicad_parameters.scad": "55a7260b24fc8667c1781ce920e91012573dd3517fd37cb6ba810664fb9f6eaf",
  "02_openscad_enclosure.scad": "b018657d6d2ba952a088f7d971b7244b8c3fddcb3fccc7e56238b4e523847f21",
  "02_openscad_enclosure.stl": "ec50a6c97b27ca41c5835a022be48c097a14bb3fdac7664a83fbaf03de96a5f7",
  "03_freecad_assembly.step": "e3e27df7a1bbbf13daf33551f3bda148e53a227d05e6760bd12ab339f4c0733a",
  "03_freecad_assembly.obj": "614cc06f0c26346d601e23ec0545c048a790e5bb547214d42939680d8ed5d6ac",
  "04_blender_review.mtl": "e6b927b2133889b80a70689c148c80b736948d25ced107c5e0f635692802d9d2",
  "04_blender_review.obj": "08e89ad9e59232b08d97e072c6ca1a0e0c4043d3d9085a70dc97a8d0b9980656"
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
