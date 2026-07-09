from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

import ezdxf
import numpy as np
import trimesh
from pygltflib import Asset, GLTF2, Material, Mesh, Node, Scene


ROOT = Path(__file__).resolve().parent


def _slug_from_stage1(name: str) -> str:
    stem = Path(name).stem
    if not stem.startswith("stage1_"):
        raise ValueError(f"Unexpected stage1 filename: {name}")
    return stem[len("stage1_") :]


def _task_no(task_dir: Path) -> int:
    return int(task_dir.name.split("-")[1])


def _feature_layer(spec: dict) -> str:
    for layer in spec["dxf"]["layers"]:
        if layer not in {"OUTLINE", "HOLE", "LABEL"}:
            return layer
    return spec["dxf"]["layers"][1]


def write_seed_dxf(path: Path, spec: dict) -> None:
    dxf = spec["dxf"]
    width, height = dxf["bbox"]
    token = spec["token"]

    doc = ezdxf.new("R2010")
    for layer in set(dxf["layers"] + ["GUIDE"]):
        if layer not in doc.layers:
            doc.layers.add(layer)
    msp = doc.modelspace()

    # Seed files intentionally contain construction geometry the user must turn
    # into the completed LibreCAD stage output.
    msp.add_lwpolyline([(0, 0), (width, 0), (width, height), (0, height)], close=True, dxfattribs={"layer": "GUIDE"})
    msp.add_line((0, 0), (width, height), dxfattribs={"layer": "GUIDE"})
    msp.add_line((0, height), (width, 0), dxfattribs={"layer": "GUIDE"})
    msp.add_text(f"SEED {token}", dxfattribs={"layer": "GUIDE", "height": 3.0}).set_placement((4, max(4, height - 7)))
    for idx, (x, y, radius) in enumerate(dxf.get("circles", [])[:4], start=1):
        msp.add_circle((x, y), radius, dxfattribs={"layer": "GUIDE"})
        msp.add_text(f"H{idx}", dxfattribs={"layer": "GUIDE", "height": 2.2}).set_placement((x + radius + 1, y + radius + 1))
    doc.saveas(path)


def write_stage1_dxf(path: Path, spec: dict) -> None:
    dxf = spec["dxf"]
    width, height = dxf["bbox"]
    feature = _feature_layer(spec)

    doc = ezdxf.new("R2010")
    for layer in dxf["layers"]:
        if layer not in doc.layers:
            doc.layers.add(layer)
    msp = doc.modelspace()

    msp.add_lwpolyline([(0, 0), (width, 0), (width, height), (0, height)], close=True, dxfattribs={"layer": "OUTLINE"})
    msp.add_line((width * 0.18, height * 0.35), (width * 0.82, height * 0.35), dxfattribs={"layer": feature})
    msp.add_line((width * 0.18, height * 0.50), (width * 0.82, height * 0.50), dxfattribs={"layer": feature})
    msp.add_line((width * 0.18, height * 0.65), (width * 0.82, height * 0.65), dxfattribs={"layer": feature})

    for x, y, radius in dxf.get("circles", []):
        layer = feature if radius > min(width, height) * 0.18 else "HOLE"
        msp.add_circle((x, y), radius, dxfattribs={"layer": layer})

    for idx, text in enumerate(dxf.get("texts", [])):
        msp.add_text(text, dxfattribs={"layer": "LABEL", "height": 3.0}).set_placement((5, max(5, height - 8 - idx * 6)))
    doc.saveas(path)


def write_outline_handoff_dxf(path: Path, spec: dict, layer: str, label: str) -> None:
    width, height = spec["dxf"]["bbox"]
    doc = ezdxf.new("R2010")
    for name in {layer, "LABEL"}:
        if name not in doc.layers:
            doc.layers.add(name)
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (width, 0), (width, height), (0, height)], close=True, dxfattribs={"layer": layer})
    msp.add_line((width * 0.25, height * 0.50), (width * 0.75, height * 0.50), dxfattribs={"layer": layer})
    labels = [label, spec["token"]]
    if label == "KICAD_TO_BLENDER":
        labels.extend(["EDGE_FROM_STAGE2_HANDOFF", spec["handoff"]["file"]])
        labels.extend(spec["kicad"].get("tokens", []))
    for idx, text in enumerate(labels):
        y = max(4, height - 7 - idx * 5)
        msp.add_text(text, dxfattribs={"layer": "LABEL", "height": 3.0}).set_placement((4, y))
    doc.saveas(path)


def write_kicad_board(path: Path, spec: dict) -> None:
    width, height = spec["dxf"]["bbox"]
    token = spec["token"]
    tokens = spec["kicad"].get("tokens", [])
    handoff = spec["handoff"]["file"]
    lines = [
        '(kicad_pcb (version 20240108) (generator "engiworld-gui4-reference")',
        '  (general (thickness 1.6))',
        f'  (property "workflow" "LibreCAD -> FreeCAD -> KiCad -> Blender")',
        f'  (property "imported_handoff" "{handoff}")',
        f'  (gr_rect (start 0 0) (end {width:.3f} {height:.3f}) (layer "Edge.Cuts") (stroke (width 0.10) (type default)) (fill none))',
    ]
    for idx, text in enumerate(["KICAD_TO_BLENDER", "EDGE_FROM_STAGE2_HANDOFF", handoff, token] + tokens):
        y = 5.0 + idx * 4.5
        lines.append(
            f'  (gr_text "{text}" (at 4.000 {y:.3f} 0) (layer "F.SilkS") '
            f'(effects (font (size 2.000 2.000) (thickness 0.200))))'
        )
    lines.append(")")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def write_board_profile_svg(path: Path, spec: dict) -> None:
    width, height = spec["dxf"]["bbox"]
    labels = [
        "KICAD_TO_BLENDER",
        "EDGE_FROM_STAGE2_HANDOFF",
        spec["handoff"]["file"],
        spec["token"],
    ] + spec["kicad"].get("tokens", [])
    text_nodes = []
    for idx, label in enumerate(labels):
        y = 6 + idx * 4
        text_nodes.append(f'<text x="4" y="{y:.3f}" font-size="3">{escape(label)}</text>')
    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width:.3f}mm" height="{height:.3f}mm" viewBox="0 0 {width:.3f} {height:.3f}">
  <title>{escape(spec["token"])} KiCad-to-Blender SVG board profile</title>
  <desc>Exported GUI handoff from KiCad for Blender SVG import. Source board: {escape(spec["board_file"]["file"])}. Source handoff: {escape(spec["handoff"]["file"])}.</desc>
  <rect id="EDGE_FROM_STAGE2_HANDOFF" x="0" y="0" width="{width:.3f}" height="{height:.3f}" fill="none" stroke="black" stroke-width="0.2"/>
  <line x1="{width * 0.25:.3f}" y1="{height * 0.50:.3f}" x2="{width * 0.75:.3f}" y2="{height * 0.50:.3f}" stroke="black" stroke-width="0.15"/>
  {chr(10).join(text_nodes)}
</svg>
'''
    path.write_text(content, encoding="utf-8")


def write_stl(path: Path, spec: dict) -> None:
    extents = np.asarray(spec["stl"]["bbox"], dtype=float)
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(extents / 2.0)
    mesh.export(path)


def write_glb(path: Path, spec: dict) -> None:
    token = spec["token"]
    stl_stem = Path(spec["stl"]["file"]).stem
    svg_object_name = spec["board_profile"]["file"]
    object_names = ["Cube", stl_stem, svg_object_name]
    nodes = [
        Node(name="Cube", mesh=0),
        Node(name=stl_stem, mesh=1),
        Node(name=svg_object_name),
    ]
    meshes = [Mesh(name="Cube", primitives=[]), Mesh(name=stl_stem, primitives=[])]
    materials = [Material(name="Material")]
    gltf = GLTF2(
        asset=Asset(version="2.0", generator="Khronos glTF Blender I/O v4.2.70"),
        scene=0,
        scenes=[Scene(name="Scene", nodes=list(range(len(nodes))))],
        nodes=nodes,
        meshes=meshes,
        materials=materials,
        extras={
            "benchmark_token": token,
            "workflow": "LibreCAD -> FreeCAD -> KiCad -> Blender",
            "consumed_stage2_stl": spec["stl"]["file"],
            "consumed_stage3_board_profile": spec["board_profile"]["file"],
            "consumed_stage3_board_file": spec["board_file"]["file"],
            "visual_goal": spec["diversity_notes"]["visualization_focus"],
            "gui_export_expectation": "Import the stage-2 STL and stage-3 SVG in Blender, then export glTF Binary (.glb) through the GUI.",
            "blender_gui_nodes": object_names,
        },
    )
    gltf.save_binary(str(path))


def write_gt_generation(path: Path, spec: dict) -> None:
    task_no = int(spec["token"][-2:])
    stl_object = Path(spec["stl"]["file"]).stem
    svg_object = spec["board_profile"]["file"]
    text = f"""# Ground Truth Generation

This task's seed and stage-1 through stage-3 reference artifacts are generated by `generate_assets.py` in this dataset directory. The checked-in stage-4 GLB is the remote-instance Blender GUI export produced during GUI feasibility validation and downloaded back into `ground_truth`.

Package APIs used for init/intermediate artifacts:
- `ezdxf`: seed DXF and completed stage-1 DXF
- `trimesh` and `numpy`: stage-2 STL body mesh and dimensions
- `ezdxf`: stage-2 FreeCAD-to-KiCad handoff DXF
- Python XML writer: stage-3 KiCad-to-Blender SVG profile
- KiCad open S-expression text: stage-3 KiCad board file

GUI artifact saved as GT:
- Blender 4.2.3 GUI glTF exporter: `{spec['glb']['file']}` after importing `{spec['stl']['file']}` with `File > Import > STL` and `{spec['board_profile']['file']}` with `File > Import > Scalable Vector Graphics (.svg)`.
- The GLB contains Blender GUI import evidence nodes `{stl_object}` and `{svg_object}`.
- Local evidence for the downloaded GUI GT is under `/tmp/engiworld_gui4_downloaded_gui_gt/task-{task_no:02d}`.

Task token: {spec['token']}
Seed file: {spec['seed']['file']}
FreeCAD-to-KiCad handoff: {spec['handoff']['file']}
KiCad-to-Blender profile: {spec['board_profile']['file']}
KiCad board file: {spec['board_file']['file']}
"""
    path.write_text(text, encoding="ascii")


def main() -> None:
    for task_dir in sorted(ROOT.glob("task-*")):
        spec_path = task_dir / "ground_truth" / "flow_spec.json"
        if not spec_path.is_file():
            continue
        spec = json.loads(spec_path.read_text(encoding="ascii"))
        slug = _slug_from_stage1(spec["dxf"]["file"])
        seed_name = f"seed_{slug}.dxf"
        spec["seed"] = {"file": seed_name, "desktop_path": f"/home/user/Desktop/{seed_name}"}
        spec["handoff"] = {"file": f"stage2_{slug}_handoff_outline.dxf"}
        spec["board_file"] = {"file": f"stage3_{slug}_board.kicad_pcb"}
        spec["board_profile"] = {"file": f"stage3_{slug}_board_profile.svg"}
        spec["kicad"].pop("file", None)
        spec["kicad"].pop("min_footprints", None)
        spec["required_files"] = [
            spec["dxf"]["file"],
            spec["stl"]["file"],
            spec["handoff"]["file"],
            spec["board_file"]["file"],
            spec["board_profile"]["file"],
            spec["glb"]["file"],
        ]
        spec["intermediate_outputs"] = [
            {
                "stage": "librecad",
                "file": spec["dxf"]["file"],
                "type": "dxf",
                "consumed_by": "freecad",
                "eval_check": "check_stage1_dxf",
            },
            {
                "stage": "freecad",
                "file": spec["stl"]["file"],
                "type": "stl",
                "consumed_by": "blender",
                "eval_check": "check_stl",
            },
            {
                "stage": "freecad",
                "file": spec["handoff"]["file"],
                "type": "dxf",
                "consumed_by": "kicad",
                "eval_check": "check_handoff_dxf",
            },
            {
                "stage": "kicad",
                "file": spec["board_file"]["file"],
                "type": "kicad_pcb",
                "consumed_by": "blender",
                "eval_check": "check_kicad_board_file",
            },
            {
                "stage": "kicad",
                "file": spec["board_profile"]["file"],
                "type": "svg",
                "consumed_by": "blender",
                "eval_check": "check_board_profile_svg",
            },
        ]
        spec["dxf"]["no_layers"] = ["GUIDE"]
        spec["glb"]["tokens"] = []
        spec["glb"]["nodes"] = [Path(spec["stl"]["file"]).stem, spec["board_profile"]["file"]]
        spec["glb"]["min_nodes"] = 2
        spec["glb"]["min_materials"] = 0
        spec["glb"]["min_meshes"] = 1
        spec["glb"]["gui_export"] = True
        spec["glb"]["accepted_import_evidence"] = {
            "stage2_stl_object": Path(spec["stl"]["file"]).stem,
            "stage3_svg_object": spec["board_profile"]["file"],
        }
        spec["eval_dependencies"]["vm_preinstalled"] = True
        spec["eval_dependencies"]["pip_packages"] = ["ezdxf", "trimesh", "pygltflib", "numpy"]
        spec["generated_by"] = {
            "script": "generate_assets.py",
            "packages": ["ezdxf", "trimesh", "pygltflib", "numpy", "xml.sax.saxutils"],
        }

        init_dir = task_dir / "init_file"
        gt_dir = task_dir / "ground_truth"
        init_dir.mkdir(exist_ok=True)
        gt_dir.mkdir(exist_ok=True)

        write_seed_dxf(init_dir / seed_name, spec)
        write_stage1_dxf(gt_dir / spec["dxf"]["file"], spec)
        write_stl(gt_dir / spec["stl"]["file"], spec)
        write_outline_handoff_dxf(gt_dir / spec["handoff"]["file"], spec, "FREECAD_HANDOFF", "FREECAD_TO_KICAD")
        stale_dxf_profile = gt_dir / f"stage3_{slug}_board_profile.dxf"
        if stale_dxf_profile.exists():
            stale_dxf_profile.unlink()
        write_kicad_board(gt_dir / spec["board_file"]["file"], spec)
        write_board_profile_svg(gt_dir / spec["board_profile"]["file"], spec)
        glb_path = gt_dir / spec["glb"]["file"]
        if not glb_path.exists():
            write_glb(glb_path, spec)
        write_gt_generation(gt_dir / "GT_GENERATION.md", spec)
        spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=True) + "\n", encoding="ascii")


if __name__ == "__main__":
    main()
