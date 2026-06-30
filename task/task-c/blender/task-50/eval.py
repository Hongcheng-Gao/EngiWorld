from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path


ROI_X0, ROI_Y0 = 32, 32
ROI_X1, ROI_Y1 = 96, 96
REF_MEAN_R = 0.942661
REF_MEAN_G = 0.812086
REF_MEAN_B = 0.805858
ROI_TOL = 0.05
BLEND_PATH = "/home/user/Desktop/answer.blend"
BLENDER_PATH = os.environ.get("BLENDER_PATH", "blender")


def _apply_eval_render_settings(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = False
    scene.cycles.seed = 0
    scene.render.resolution_x = 128
    scene.render.resolution_y = 128
    scene.render.resolution_percentage = 100
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 1
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"


def _roi_mean_from_png(png_path):
    import bpy
    img = bpy.data.images.load(png_path)
    try:
        w, h = img.size[0], img.size[1]
        px = list(img.pixels)
    finally:
        bpy.data.images.remove(img)
    if (w, h) != (128, 128):
        raise RuntimeError(f"unexpected render size {w}x{h}")
    rs = gs = bs = 0.0
    n = 0
    for y in range(ROI_Y0, ROI_Y1):
        for x in range(ROI_X0, ROI_X1):
            i = (y * w + x) * 4
            rs += px[i + 0]
            gs += px[i + 1]
            bs += px[i + 2]
            n += 1
    return (rs / n, gs / n, bs / n)


def _find_image_node_by_image(nt, image_name):
    for n in nt.nodes:
        if n.type == "TEX_IMAGE" and n.image is not None and n.image.name == image_name:
            return n
    return None


def _run_eval(blend_path):
    import bpy

    if not os.path.isfile(blend_path):
        return False
    try:
        bpy.ops.wm.open_mainfile(filepath=blend_path)
    except Exception:
        return False

    plate = bpy.data.objects.get("Plate")
    if plate is None or plate.type != "MESH":
        return False
    if sum(1 for o in bpy.data.objects if o.type == "MESH") != 1:
        return False
    if not plate.data.materials or plate.data.materials[0] is None or plate.data.materials[0].name != "PlateMat":
        return False
    mat = plate.data.materials[0]
    if not (mat.use_nodes and mat.node_tree is not None):
        return False
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    bc_node = _find_image_node_by_image(nt, "basecolor.png")
    nm_node = _find_image_node_by_image(nt, "normalmap.png")
    mask_node = _find_image_node_by_image(nt, "mask.png")
    nmap_node = next((n for n in nt.nodes if n.type == "NORMAL_MAP"), None)
    if any(n is None for n in (bsdf, bc_node, nm_node, mask_node, nmap_node)):
        return False
    if bc_node.outputs["Color"].is_linked is False or nm_node.outputs["Color"].is_linked is False:
        return False
    if bc_node.image.colorspace_settings.name != "sRGB":
        return False
    if nm_node.image.colorspace_settings.name != "Non-Color":
        return False
    if mask_node.image.colorspace_settings.name != "Non-Color":
        return False

    scene = bpy.context.scene
    _apply_eval_render_settings(scene)
    tmp_dir = tempfile.mkdtemp(prefix="lh06_eval_")
    out_png = os.path.join(tmp_dir, "render.png")
    scene.render.filepath = out_png
    try:
        bpy.ops.render.render(write_still=True)
        mean_r, mean_g, mean_b = _roi_mean_from_png(out_png)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return (
        abs(mean_r - REF_MEAN_R) <= ROI_TOL
        and abs(mean_g - REF_MEAN_G) <= ROI_TOL
        and abs(mean_b - REF_MEAN_B) <= ROI_TOL
    )


def eval_outputs(blend_path, expected=None, postconfig=None):
    return _run_eval(blend_path)


def _have_bpy() -> bool:
    try:
        import bpy  # noqa: F401
        return True
    except Exception:
        return False


def _run_via_blender(blend_path: str) -> bool:
    proc = subprocess.run(
        [BLENDER_PATH, "--background", "--factory-startup", "--python", __file__],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    return proc.returncode == 0


def main():
    passed = _run_eval(BLEND_PATH) if _have_bpy() else _run_via_blender(BLEND_PATH)
    print("True" if passed else "False")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
