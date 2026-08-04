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
      82,
      82,
      1.2
    ],
    "components": [
      {
        "height_mm": 5.2,
        "keepout_radius_mm": 24.0,
        "kind": "PATCH_ANTENNA",
        "ref": "A1",
        "x_mm": 0,
        "y_mm": 16
      },
      {
        "height_mm": 1.1,
        "keepout_radius_mm": 7.0,
        "kind": "GNSS_SOC",
        "ref": "U1",
        "x_mm": -14,
        "y_mm": -18
      },
      {
        "height_mm": 7.2,
        "keepout_radius_mm": 12.0,
        "kind": "SMA_EDGE",
        "ref": "J1",
        "x_mm": 40,
        "y_mm": -12
      },
      {
        "height_mm": 4.8,
        "keepout_radius_mm": 11.0,
        "kind": "BACKUP_CELL",
        "ref": "BT1",
        "x_mm": -30,
        "y_mm": 26
      },
      {
        "height_mm": 0.2,
        "keepout_radius_mm": 3.0,
        "kind": "RF_TEST",
        "ref": "TP1",
        "x_mm": 18,
        "y_mm": -30
      }
    ],
    "corrected_board": "01_kicad_board.kicad_pcb",
    "critical_requirement": "The antenna keepout volume must be reserved through OpenSCAD and remain highlighted in the Blender review scene.",
    "input_board": "board_input.kicad_pcb",
    "max_component_height_mm": 24.0,
    "mechanical_map": "01_kicad_mechanical_map.csv",
    "mounting_holes": [
      {
        "diameter_mm": 2.8,
        "ref": "MH1",
        "x_mm": -34,
        "y_mm": -34
      },
      {
        "diameter_mm": 2.8,
        "ref": "MH2",
        "x_mm": 34,
        "y_mm": -34
      },
      {
        "diameter_mm": 2.8,
        "ref": "MH3",
        "x_mm": -34,
        "y_mm": 34
      },
      {
        "diameter_mm": 2.8,
        "ref": "MH4",
        "x_mm": 34,
        "y_mm": 34
      }
    ],
    "software_stage": "KiCad",
    "task": "task-10",
    "openscad_parameter_handoff": "01_kicad_parameters.scad"
  },
  "02_openscad_parameters.json": {
    "board_bbox_mm": [
      82,
      82,
      1.2
    ],
    "critical_requirement": "The antenna keepout volume must be reserved through OpenSCAD and remain highlighted in the Blender review scene.",
    "enclosure_bbox_mm": [
      95.4,
      95.4,
      35.4
    ],
    "lid_clearance_mm": 7.5,
    "mesh": "02_openscad_enclosure.stl",
    "software_stage": "OpenSCAD",
    "source": "02_openscad_enclosure.scad",
    "standoff_count": 4,
    "task": "task-10",
    "wall_mm": 2.7,
    "window_count": 1,
    "input_parameter_handoff": "01_kicad_parameters.scad",
    "source_mechanical_map": "01_kicad_mechanical_map.csv"
  },
  "03_freecad_clearance_report.json": {
    "assembly_step": "03_freecad_assembly.step",
    "board_bbox_mm": [
      82,
      82,
      1.2
    ],
    "decision": "pass",
    "enclosure_bbox_mm": [
      95.4,
      95.4,
      35.4
    ],
    "estimated_shell_mass_g": 116.427,
    "inputs": [
      "01_kicad_board.kicad_pcb",
      "02_openscad_enclosure.stl",
      "02_openscad_parameters.json"
    ],
    "interference_volume_mm3": 0.0,
    "keepout_count": 5,
    "minimum_side_clearance_mm": 4.0,
    "minimum_top_clearance_mm": 7.5,
    "software_stage": "FreeCAD",
    "task": "task-10",
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
    "task": "task-10",
    "visible_keepouts": [
      "A1",
      "J1",
      "TP1"
    ]
  },
  "final_release_package.json": {
    "critical_requirement": "The antenna keepout volume must be reserved through OpenSCAD and remain highlighted in the Blender review scene.",
    "domain": "GNSS receiver enclosure",
    "key_metrics": {
      "board_bbox_mm": [
        82,
        82,
        1.2
      ],
      "enclosure_bbox_mm": [
        95.4,
        95.4,
        35.4
      ],
      "estimated_shell_mass_g": 116.427,
      "side_clearance_mm": 4.0,
      "top_clearance_mm": 7.5
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
    "task": "task-10",
    "title": "GNSS antenna keepout enclosure flow"
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
    "task": "task-10"
  }
}""")
EXPECTED_TEXT_SHA256 = json.loads(r"""{
  "01_kicad_board.kicad_pcb": "b9cf064f101d577f7c743745efa42f5c9d528776e61030582fbea8fbbf9a3047",
  "01_kicad_mechanical_map.csv": "ac8b1612a829b4167f14bfe11775e74e13b85b84898f9ed31a901d1eaa89231f",
  "01_kicad_parameters.scad": "04b150bdf34273bbab46d7d0d43ede00c4e4cdea640b83d01b7a285a548119fc",
  "02_openscad_enclosure.scad": "44b12c0bbf309cae615e8d7640834fa97c7f51b1c7b787fdad9b8dac8f9d7c6f",
  "02_openscad_enclosure.stl": "6a07b6702f959be553adb81d29a6f646da78071c52f13ecf660ed44584951797",
  "03_freecad_assembly.step": "a031bc890beb4f7939898e7caf548f496250276ce746bb1b242d1662eed36f2f",
  "03_freecad_assembly.obj": "6a71af4732c70ce7273d11e416c116950a1166a3e3824b48abed433660bf4183",
  "04_blender_review.mtl": "2243ab35f45d56e4aeca83e595fd5bbcfed387463a0e4903fe134158c1d4ce4c",
  "04_blender_review.obj": "16bfe193caffb4741fe16b89e98aa24cba771f0bf38e39725364c8c29e919a08"
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
