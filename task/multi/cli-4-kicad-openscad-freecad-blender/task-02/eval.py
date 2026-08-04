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
      104,
      62,
      1.6
    ],
    "components": [
      {
        "height_mm": 1.0,
        "keepout_radius_mm": 5.0,
        "kind": "REGULATOR_QFN",
        "ref": "U1",
        "x_mm": -8,
        "y_mm": 0
      },
      {
        "height_mm": 6.4,
        "keepout_radius_mm": 12.0,
        "kind": "INDUCTOR",
        "ref": "L1",
        "x_mm": 18,
        "y_mm": 4
      },
      {
        "height_mm": 8.2,
        "keepout_radius_mm": 8.0,
        "kind": "BULK_CAP",
        "ref": "C1",
        "x_mm": 34,
        "y_mm": -18
      },
      {
        "height_mm": 5.0,
        "keepout_radius_mm": 10.5,
        "kind": "POWER_IN",
        "ref": "J1",
        "x_mm": -48,
        "y_mm": 12
      },
      {
        "height_mm": 5.0,
        "keepout_radius_mm": 10.5,
        "kind": "POWER_OUT",
        "ref": "J2",
        "x_mm": 48,
        "y_mm": -12
      }
    ],
    "corrected_board": "01_kicad_board.kicad_pcb",
    "critical_requirement": "The OpenSCAD clamp must leave a keepout over L1 and the FreeCAD assembly must report positive clearance over the bulk capacitor.",
    "input_board": "board_input.kicad_pcb",
    "max_component_height_mm": 12.0,
    "mechanical_map": "01_kicad_mechanical_map.csv",
    "mounting_holes": [
      {
        "diameter_mm": 3.0,
        "ref": "MH1",
        "x_mm": -44,
        "y_mm": -24
      },
      {
        "diameter_mm": 3.0,
        "ref": "MH2",
        "x_mm": 44,
        "y_mm": -24
      },
      {
        "diameter_mm": 3.0,
        "ref": "MH3",
        "x_mm": -44,
        "y_mm": 24
      },
      {
        "diameter_mm": 3.0,
        "ref": "MH4",
        "x_mm": 44,
        "y_mm": 24
      }
    ],
    "software_stage": "KiCad",
    "task": "task-02",
    "openscad_parameter_handoff": "01_kicad_parameters.scad"
  },
  "02_openscad_parameters.json": {
    "board_bbox_mm": [
      104,
      62,
      1.6
    ],
    "critical_requirement": "The OpenSCAD clamp must leave a keepout over L1 and the FreeCAD assembly must report positive clearance over the bulk capacitor.",
    "enclosure_bbox_mm": [
      117.2,
      75.2,
      18.6
    ],
    "lid_clearance_mm": 2.4,
    "mesh": "02_openscad_enclosure.stl",
    "software_stage": "OpenSCAD",
    "source": "02_openscad_enclosure.scad",
    "standoff_count": 4,
    "task": "task-02",
    "wall_mm": 2.6,
    "window_count": 2,
    "input_parameter_handoff": "01_kicad_parameters.scad",
    "source_mechanical_map": "01_kicad_mechanical_map.csv"
  },
  "03_freecad_clearance_report.json": {
    "assembly_step": "03_freecad_assembly.step",
    "board_bbox_mm": [
      104,
      62,
      1.6
    ],
    "decision": "pass",
    "enclosure_bbox_mm": [
      117.2,
      75.2,
      18.6
    ],
    "estimated_shell_mass_g": 72.424,
    "inputs": [
      "01_kicad_board.kicad_pcb",
      "02_openscad_enclosure.stl",
      "02_openscad_parameters.json"
    ],
    "interference_volume_mm3": 0.0,
    "keepout_count": 5,
    "minimum_side_clearance_mm": 4.0,
    "minimum_top_clearance_mm": 2.4,
    "software_stage": "FreeCAD",
    "task": "task-02",
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
    "task": "task-02",
    "visible_keepouts": [
      "J1",
      "J2"
    ]
  },
  "final_release_package.json": {
    "critical_requirement": "The OpenSCAD clamp must leave a keepout over L1 and the FreeCAD assembly must report positive clearance over the bulk capacitor.",
    "domain": "power converter thermal clamp",
    "key_metrics": {
      "board_bbox_mm": [
        104,
        62,
        1.6
      ],
      "enclosure_bbox_mm": [
        117.2,
        75.2,
        18.6
      ],
      "estimated_shell_mass_g": 72.424,
      "side_clearance_mm": 4.0,
      "top_clearance_mm": 2.4
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
    "task": "task-02",
    "title": "Buck regulator heat-spreader clamp package"
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
    "task": "task-02"
  }
}""")
EXPECTED_TEXT_SHA256 = json.loads(r"""{
  "01_kicad_board.kicad_pcb": "9bfa4406136b7bda749cd1356c23ae02f9c04cc8925cd94141ba1e3931c8cb5b",
  "01_kicad_mechanical_map.csv": "b61b93228b58c5f384ca1f8e47e9c3a6ab17ab9c453ac0fd92f231aa79390dae",
  "01_kicad_parameters.scad": "abf1eb417b78e93481ce2e3e88c8d271455561f6a1f4b18dca13e784994c6ba8",
  "02_openscad_enclosure.scad": "b360a3efbe4a5066bfd36afd61233038714bcc689f18900143a898d3d210dc08",
  "02_openscad_enclosure.stl": "8e256cd48f1081e3ce6755d4a8b2610baf30c0041e8f04d6ddfb5c267b353451",
  "03_freecad_assembly.step": "bd3890e6c48130c3ca9ad1e8802d738af88c19fc9eafde9333519e2695c36e12",
  "03_freecad_assembly.obj": "dc94191490234042621c39073d558c5bdf920dc83c957e8b6e77cb27197d6786",
  "04_blender_review.mtl": "ee4648978d3f3bda55beea6323c99ac95149778ea43dbe051ded6c7b06f524f4",
  "04_blender_review.obj": "00bb84c33f3c92ef715361e7de85c9e50a39d5d42316b85b06967fd4b5a9fb40"
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
