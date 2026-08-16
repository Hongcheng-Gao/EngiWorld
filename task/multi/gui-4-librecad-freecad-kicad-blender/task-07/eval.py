from __future__ import annotations

import json
import math
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SPEC = json.loads(r'''{
  "case_id":"multi-gui-4-librecad-freecad-kicad-blender-task-07-ubuntu",
  "token":"EW4G07",
  "required_files":["stage1_sbc_hat_mount_plate.dxf","stage2_sbc_hat_mount_plate.stl","stage2_sbc_hat_mount_plate_handoff_outline.dxf","stage3_sbc_hat_mount_plate_board.kicad_pcb","stage3_sbc_hat_mount_plate_board_profile.svg","stage4_sbc_hat_mount_plate.glb"],
  "dxf":{"file":"stage1_sbc_hat_mount_plate.dxf","bbox":[85,65],"circles":[[7,7,2.75],[78,7,2.75],[7,58,2.75],[78,58,2.75],[42.5,32.5,3]],"texts":["EW4G07","GPIO40","CAM","I2C"]},
  "stl":{"file":"stage2_sbc_hat_mount_plate.stl","bbox":[85,65,12]},
  "handoff":{"file":"stage2_sbc_hat_mount_plate_handoff_outline.dxf"},
  "board":{"file":"stage3_sbc_hat_mount_plate_board.kicad_pcb"},
  "svg":{"file":"stage3_sbc_hat_mount_plate_board_profile.svg"},
  "glb":{"file":"stage4_sbc_hat_mount_plate.glb"}
}''')
ROOT = Path(os.environ.get("OUTPUT_ROOT", "/home/user/Desktop"))
DETAILS = []

try:
    import ezdxf
    import numpy as np
    import trimesh
    from pygltflib import GLTF2
except Exception as exc:
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


def log(message): DETAILS.append(str(message))
def fail(message): log("[FAIL] " + str(message)); return False
def ok(message): log("[PASS] " + str(message)); return True
def close(a, b, tol=.2): return abs(float(a) - float(b)) <= tol
def norm(value): return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def finish(valid):
    valid = bool(valid)
    payload = {"case_id": SPEC["case_id"], "valid": valid,
               "score": 1.0 if valid else 0.0,
               "metric_name": "four_gui_transfer_completion",
               "output_field": "score", "details": DETAILS}
    try:
        (ROOT / "eval_detail.txt").write_text("\n".join(DETAILS) + "\n", encoding="utf-8")
        (ROOT / "eval_result.txt").write_text(str(valid) + "\n", encoding="utf-8")
        for name in ("score.json", "quant_metrics.json"):
            (ROOT / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception:
        pass
    print(valid)
    raise SystemExit(0)


def entity_text(entity):
    if entity.dxftype() == "TEXT": return str(entity.dxf.text)
    if entity.dxftype() == "MTEXT":
        try: return entity.plain_text()
        except Exception: return str(entity.text)
    return ""


def poly_points(entity):
    if entity.dxftype() == "LWPOLYLINE":
        return [(float(p[0]), float(p[1])) for p in entity.get_points("xy")]
    if entity.dxftype() == "POLYLINE":
        return [(float(v.dxf.location.x), float(v.dxf.location.y)) for v in entity.vertices]
    return []


def polygon_area(points):
    return abs(sum(points[i][0] * points[(i + 1) % len(points)][1] -
                   points[(i + 1) % len(points)][0] * points[i][1]
                   for i in range(len(points))) / 2) if len(points) >= 3 else 0


def polygon_dims(points):
    arr = np.asarray(points, float)
    return (arr.max(axis=0) - arr.min(axis=0)).tolist() if len(arr) else []


def point_in_polygon(point, points):
    x, y = point; inside = False
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        if ((y1 > y) != (y2 > y)) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def semantic_keepouts(entities):
    regions = []
    for entity in entities:
        if (str(entity.dxf.layer).upper() == "KEEP_OUT" and
                entity.dxftype() in {"LWPOLYLINE", "POLYLINE"} and bool(entity.is_closed)):
            points = poly_points(entity); area = polygon_area(points)
            if len(points) >= 3 and 20 <= area <= 1800:
                regions.append(points)
    labels = {}
    for entity in entities:
        if entity.dxftype() in {"TEXT", "MTEXT"} and str(entity.dxf.layer).upper() == "LABEL":
            value = norm(entity_text(entity))
            insert = entity.dxf.insert
            labels[value] = (float(insert.x), float(insert.y))
    result = {}
    for token in ("GPIO40", "CAM"):
        matches = [points for points in regions if token in labels and point_in_polygon(labels[token], points)]
        if len(matches) == 1:
            result[token] = matches[0]
    return regions, result


def closed_rect(entity, dims=(85, 65), tol=.2):
    points = poly_points(entity)
    if not points or not bool(entity.is_closed): return False
    got = polygon_dims(points)
    return all(close(a, b, tol) for a, b in zip(got, dims)) and close(polygon_area(points), dims[0] * dims[1], 2)


def required_files():
    for name in SPEC["required_files"]:
        path = ROOT / name
        if not path.is_file() or path.stat().st_size < 100:
            return fail("Missing or too-small deliverable: " + name)
    return ok("All six required deliverables exist")


def check_stage1():
    try:
        doc = ezdxf.readfile(str(ROOT / SPEC["dxf"]["file"])); entities = list(doc.modelspace())
    except Exception as exc: return fail("Cannot parse stage1 DXF: " + str(exc))
    from ezdxf import bbox as ezdxf_bbox
    extent = ezdxf_bbox.extents(entities, fast=False)
    if not extent.has_data: return fail("Stage1 has no bounded geometry")
    if np.max(np.abs([extent.extmin.x, extent.extmin.y])) > .05 or np.max(np.abs(np.asarray([extent.extmax.x, extent.extmax.y]) - [85, 65])) > .05:
        return fail("Stage1 complete geometry envelope is not exactly 85 x 65")
    if any(str(e.dxf.layer).upper() == "GUIDE" for e in entities): return fail("Stage1 retains GUIDE entities")
    outlines = [e for e in entities if str(e.dxf.layer).upper() == "OUTLINE" and e.dxftype() in {"LWPOLYLINE", "POLYLINE"} and closed_rect(e)]
    if len(outlines) != 1: return fail("Stage1 needs exactly one closed 85 x 65 OUTLINE")
    circles = [(str(e.dxf.layer).upper(), float(e.dxf.center.x), float(e.dxf.center.y), float(e.dxf.radius)) for e in entities if e.dxftype() == "CIRCLE"]
    if len(circles) != 5: return fail("Stage1 needs exactly five task circles")
    for x, y, r in SPEC["dxf"]["circles"]:
        hits = [c for c in circles if c[0] == "HOLE" and close(c[1], x, .05) and close(c[2], y, .05) and close(c[3], r, .03)]
        if len(hits) != 1: return fail("Missing or wrong-layer HOLE circle: " + str([x, y, r]))
    keepouts, semantic = semantic_keepouts(entities)
    if len(keepouts) != 2 or set(semantic) != {"GPIO40", "CAM"}:
        return fail("Stage1 needs separate positive-area GPIO40 and CAM KEEP_OUT regions containing their labels")
    if any(not all(0 <= value <= limit for point in points for value, limit in zip(point, (85, 65))) for points in keepouts):
        return fail("A KEEP_OUT region lies outside the mount outline")
    labels = [entity_text(e) for e in entities if e.dxftype() in {"TEXT", "MTEXT"} and str(e.dxf.layer).upper() == "LABEL"]
    if len(labels) != 4 or {norm(x) for x in labels} != {norm(x) for x in SPEC["dxf"]["texts"]}:
        return fail("Stage1 requires exactly the four task LABEL texts")
    return ok("LibreCAD DXF has exact outline, holes, clearances, labels, and no GUIDE")


def localized_mesh(mesh):
    bounds = np.asarray(mesh.bounds, float)
    return np.asarray(mesh.vertices, float) - bounds[0], bounds[1] - bounds[0]


def opening_evidence(mesh, x, y, radius):
    vertices, _ = localized_mesh(mesh)
    radial = np.hypot(vertices[:, 0] - x, vertices[:, 1] - y)
    ring = vertices[np.abs(radial - radius) < .55]
    core = vertices[radial < radius - .5]
    return len(ring) >= 16 and np.ptp(ring[:, 2]) >= 3 and len(core) == 0


def check_stl():
    try: mesh = trimesh.load_mesh(str(ROOT / SPEC["stl"]["file"]), file_type="stl", force="mesh", process=True)
    except Exception as exc: return fail("Cannot parse FreeCAD STL: " + str(exc))
    vertices, dims = localized_mesh(mesh)
    if len(mesh.faces) < 600 or len(mesh.vertices) < 250: return fail("STL lacks substantial manufactured geometry")
    if not mesh.is_watertight: return fail("STL must be watertight")
    if np.max(np.abs(dims - [85, 65, 12])) > .05: return fail("STL bbox is not 85 x 65 x 12: " + str(dims.tolist()))
    fill = abs(float(mesh.volume)) / float(np.prod(dims))
    if not .18 <= fill <= .48: return fail("STL is empty or box-like: fill %.4f" % fill)
    for x, y, r in SPEC["dxf"]["circles"]:
        if not opening_evidence(mesh, x, y, r): return fail("STL lacks a real through-opening at " + str([x, y, r]))
    stage1 = ezdxf.readfile(str(ROOT / SPEC["dxf"]["file"])); _, semantic = semantic_keepouts(list(stage1.modelspace()))
    if set(semantic) != {"GPIO40", "CAM"}: return fail("Cannot derive semantic clearances from stage1")
    # Both submitted polygonal clearance regions must become substantial
    # through-opening walls; do not assume the GT's rectangle dimensions.
    for name, points in semantic.items():
        polygon = np.asarray(points, float)
        if polygon_area(points) < 20: return fail("Stage1 %s clearance is too small" % name)
        supported = 0
        for index, start in enumerate(polygon):
            end = polygon[(index + 1) % len(polygon)]; edge = end - start; length2 = float(edge @ edge)
            if length2 < 1: continue
            relative = vertices[:, :2] - start
            along = np.clip((relative @ edge) / length2, 0, 1)
            distance = np.linalg.norm(relative - along[:, None] * edge, axis=1)
            near = vertices[distance < .35]
            near_along = along[distance < .35]
            supported += bool(len(near) >= 4 and np.ptp(near[:, 2]) >= 3 and
                              len(near_along) and near_along.min() <= .1 and near_along.max() >= .9)
        if supported < max(3, len(polygon) - 1):
            return fail("STL lacks walls following the submitted %s clearance boundary" % name)
    raised = 0
    for x, y, _ in SPEC["dxf"]["circles"][:4]:
        radial = np.hypot(vertices[:, 0] - x, vertices[:, 1] - y)
        ring = vertices[(radial >= 3.2) & (radial <= 5.2)]
        raised += bool(len(ring) >= 30 and ring[:, 2].max() > 11.5 and ring[:, 2].min() < 4.5)
    if raised != 4: return fail("STL lacks four raised corner standoff structures")
    return ok("FreeCAD STL is watertight, opened, non-box, and has four raised standoffs")


def insert_signature(doc, insert):
    points = []; segments = 0
    for item in insert.virtual_entities():
        if item.dxftype() == "LINE":
            points.extend([(float(item.dxf.start.x), float(item.dxf.start.y)), (float(item.dxf.end.x), float(item.dxf.end.y))]); segments += 1
        elif item.dxftype() in {"LWPOLYLINE", "POLYLINE"}:
            p = poly_points(item); points.extend(p); segments += max(len(p) - 1, 0)
    return segments, polygon_dims(points), np.asarray(points, float) if points else np.empty((0, 2))


def check_handoff():
    try: doc = ezdxf.readfile(str(ROOT / SPEC["handoff"]["file"])); entities = list(doc.modelspace())
    except Exception as exc: return fail("Cannot parse FreeCAD handoff: " + str(exc))
    outlines = [e for e in entities if e.dxftype() in {"LWPOLYLINE", "POLYLINE"} and closed_rect(e)]
    if len(outlines) != 1: return fail("Handoff needs exactly one closed 85 x 65 outline")
    inserts = [e for e in entities if e.dxftype() == "INSERT"]
    signatures = [insert_signature(doc, e) for e in inserts]
    if len(signatures) != 2 or min(s[0] for s in signatures) < 40: return fail("Handoff lacks two real outlined ShapeString labels")
    if not all(len(s[2]) and np.all(s[2].min(axis=0) >= 0) and s[2][:, 0].max() <= 85 and s[2][:, 1].max() <= 65 for s in signatures):
        return fail("Handoff label geometry is outside the board interface")
    widths = sorted(s[1][0] for s in signatures)
    if widths[0] < 20 or widths[1] / widths[0] < 1.6: return fail("Handoff labels do not represent EW4G07 and FREECAD_TO_KICAD")
    return ok("FreeCAD handoff has one closed interface and two real ShapeString labels")


def balanced_blocks(text, head):
    out = []
    for match in re.finditer(r"\(" + re.escape(head) + r"(?=\s|\")", text):
        depth = 0; quoted = False; escaped = False
        for i in range(match.start(), len(text)):
            ch = text[i]
            if quoted:
                if escaped: escaped = False
                elif ch == "\\": escaped = True
                elif ch == '"': quoted = False
            elif ch == '"': quoted = True
            elif ch == "(": depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0: out.append(text[match.start():i + 1]); break
    return out


def first_xy(block, head):
    match = re.search(r"\(" + re.escape(head) + r"\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)", block)
    return (float(match.group(1)), float(match.group(2))) if match else None


def check_board():
    try: text = (ROOT / SPEC["board"]["file"]).read_text(encoding="utf-8")
    except Exception as exc: return fail("Cannot read KiCad board: " + str(exc))
    if not text.lstrip().startswith("(kicad_pcb") or not re.search(r"\(generator\s+\"?pcbnew\"?\)", text, re.I): return fail("Board is not native pcbnew")
    shapes = balanced_blocks(text, "gr_line")
    edge_segments = []
    dwgs_count = 0
    for block in shapes:
        if '(layer "Edge.Cuts")' in block:
            a, b = first_xy(block, "start"), first_xy(block, "end")
            if a and b: edge_segments.append((a, b))
        if '(layer "Dwgs.User")' in block: dwgs_count += 1
    expected = {((0, 0), (85, 0)), ((85, 0), (85, 65)), ((85, 65), (0, 65)), ((0, 65), (0, 0))}
    canon = {(tuple(round(v, 2) for v in a), tuple(round(v, 2) for v in b)) for a, b in edge_segments}
    if len(edge_segments) != 4 or not all(edge in canon or (edge[1], edge[0]) in canon for edge in expected): return fail("Board lacks one exact closed 85 x 65 Edge.Cuts cycle")
    groups = balanced_blocks(text, "group")
    if len(groups) != 1 or len(re.findall(r'"[0-9a-f-]{36}"', groups[0], re.I)) < 200 or dwgs_count < 200:
        return fail("Board does not retain the complete imported FreeCAD handoff on Dwgs.User")
    footprints = balanced_blocks(text, "footprint")
    expected_pads = {"J1": 40, "J2": 4, "U1": 8, "J3": 2}
    got = {}
    for block in footprints:
        ref = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        if ref: got[ref.group(1)] = len(balanced_blocks(block, "pad"))
    if got != expected_pads: return fail("Native component/pad counts mismatch: " + str(got))
    stage1 = ezdxf.readfile(str(ROOT / SPEC["dxf"]["file"])); _, semantic = semantic_keepouts(list(stage1.modelspace()))
    camera_region = semantic.get("CAM", [])
    camera = []
    for zone in balanced_blocks(text, "zone"):
        if '(layer "F.Cu")' not in zone or "(keepout" not in zone or "copperpour not_allowed" not in zone:
            continue
        points = [(float(a), float(b)) for a, b in re.findall(r"\(xy\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)", zone)]
        if len(points) >= 3 and polygon_area(points) > 1:
            center = np.asarray(points, float).mean(axis=0)
            if camera_region and point_in_polygon(center, camera_region): camera.append(zone)
    if len(camera) != 1: return fail("Board needs one positive-area F.Cu camera keepout overlapping the submitted CAM region")
    silk = "\n".join(b for b in balanced_blocks(text, "gr_text") if '(layer "F.SilkS")' in b)
    for token in ("KICAD_TO_BLENDER", "EDGE_FROM_STAGE2_HANDOFF", SPEC["handoff"]["file"], "EW4G07", "GPIO40-J1", "CAM-KEEP", "I2C-J2", "EEPROM-U1", "PWR-J3"):
        if norm(token) not in norm(silk): return fail("Required token is not actual F.SilkS text: " + token)
    for block in footprints:
        at = first_xy(block, "at")
        if at and not (0 <= at[0] <= 85 and 0 <= at[1] <= 65): return fail("A component is outside the board")
    return ok("KiCad board has aligned handoff, native footprints/pads, keepout, outline, and silk")


def svg_paths(root):
    for element in root.iter():
        if element.tag.lower().endswith("path") and element.attrib.get("d"):
            yield element.attrib["d"]


def check_svg():
    try: root = ET.parse(ROOT / SPEC["svg"]["file"]).getroot(); raw = (ROOT / SPEC["svg"]["file"]).read_text(encoding="utf-8")
    except Exception as exc: return fail("Cannot parse KiCad SVG: " + str(exc))
    if "Image generated by PCBNEW" not in raw: return fail("SVG lacks PCBNEW provenance")
    segments = []
    for data in svg_paths(root):
        points = [(float(a), float(b)) for a, b in re.findall(r"[ML]\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)", data, re.I)]
        segments.extend(zip(points, points[1:]))
    canon = {(tuple(round(v, 2) for v in a), tuple(round(v, 2) for v in b)) for a, b in segments}
    expected = {((0, 0), (85, 0)), ((85, 0), (85, 65)), ((85, 65), (0, 65)), ((0, 65), (0, 0))}
    if len(segments) != 4 or not all(edge in canon or (edge[1], edge[0]) in canon for edge in expected):
        return fail("SVG painted geometry is not one closed 85 x 65 profile")
    painted = [e for e in root.iter() if e.tag.lower().endswith("g") and "stroke:" in e.attrib.get("style", "") and "stroke:none" not in e.attrib.get("style", "").replace(" ", "")]
    if not painted: return fail("SVG profile has no painted stroke geometry")
    return ok("KiCad SVG has PCBNEW provenance and painted closed 85 x 65 geometry")


def glb_json_and_bin(path):
    data = path.read_bytes()
    if data[:4] != b"glTF": raise ValueError("not binary glTF")
    json_len = struct.unpack_from("<I", data, 12)[0]
    doc = json.loads(data[20:20 + json_len].decode("utf-8").rstrip(" \x00"))
    off = 20 + json_len; bin_len = struct.unpack_from("<I", data, off)[0]
    return doc, data[off + 8:off + 8 + bin_len]


def accessor_array(doc, blob, index):
    acc = doc["accessors"][index]; view = doc["bufferViews"][acc["bufferView"]]
    component = {5120:("b",1),5121:("B",1),5122:("h",2),5123:("H",2),5125:("I",4),5126:("f",4)}[acc["componentType"]]
    width = {"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4}[acc["type"]]
    start = view.get("byteOffset", 0) + acc.get("byteOffset", 0); stride = view.get("byteStride", width * component[1])
    return np.asarray([struct.unpack_from("<" + component[0] * width, blob, start + i * stride) for i in range(acc["count"])])


def node_matrix(node):
    if "matrix" in node: return np.asarray(node["matrix"], float).reshape(4, 4).T
    matrix = np.eye(4); translation = np.asarray(node.get("translation", [0, 0, 0]), float)
    scale = np.asarray(node.get("scale", [1, 1, 1]), float); x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    rotation = np.asarray([[1-2*y*y-2*z*z, 2*x*y-2*z*w, 2*x*z+2*y*w],
                           [2*x*y+2*z*w, 1-2*x*x-2*z*z, 2*y*z-2*x*w],
                           [2*x*z-2*y*w, 2*y*z+2*x*w, 1-2*x*x-2*y*y]], float)
    matrix[:3, :3] = rotation @ np.diag(scale); matrix[:3, 3] = translation
    return matrix


def visible_material(doc, index):
    materials = doc.get("materials", [])
    if not isinstance(index, int) or not 0 <= index < len(materials): return None
    material = materials[index]; pbr = material.get("pbrMetallicRoughness", {})
    color = np.asarray((pbr.get("baseColorFactor") or [1, 1, 1, 1]), float)
    alpha = float(color[3] if len(color) > 3 else 1)
    mode = material.get("alphaMode", "OPAQUE")
    if mode == "MASK":
        visible = alpha >= float(material.get("alphaCutoff", .5))
    elif mode == "BLEND":
        visible = alpha >= .05
    else:
        visible = True
    return (color[:3], float(pbr.get("metallicFactor", 1)), visible)


def check_glb():
    path = ROOT / SPEC["glb"]["file"]
    try: gltf = GLTF2().load_binary(str(path)); doc, blob = glb_json_and_bin(path)
    except Exception as exc: return fail("Cannot parse Blender GLB: " + str(exc))
    if "Blender" not in str(doc.get("asset", {}).get("generator", "")): return fail("GLB lacks Blender exporter provenance")
    nodes = doc.get("nodes", []); meshes = doc.get("meshes", [])
    scene_index = doc.get("scene", 0); scenes = doc.get("scenes", [])
    if not isinstance(scene_index, int) or not 0 <= scene_index < len(scenes): return fail("GLB has no valid active scene")
    reachable = set(); world = {}
    def visit(index, parent):
        if not isinstance(index, int) or not 0 <= index < len(nodes): raise ValueError("invalid node index")
        if index in reachable: raise ValueError("node is reachable more than once")
        reachable.add(index); world[index] = parent @ node_matrix(nodes[index])
        for child in nodes[index].get("children", []): visit(child, world[index])
    try:
        for root in scenes[scene_index].get("nodes", []): visit(root, np.eye(4))
    except Exception as exc:
        return fail("Active scene graph is malformed: " + str(exc))
    named = {nodes[index].get("name", ""): nodes[index] for index in reachable}
    indices = {id(node): index for index, node in enumerate(nodes)}
    stl_nodes = [(name, n) for name, n in named.items() if name.startswith("stage2_sbc_hat_mount_plate") and isinstance(n.get("mesh"), int)]
    svg_nodes = [(name, n) for name, n in named.items() if "stage3_sbc_hat_mount_plate_board_profile.svg__EDGE_" in name and isinstance(n.get("mesh"), int)]
    if len(stl_nodes) != 1 or len(svg_nodes) != 4: return fail("GLB lacks reachable mesh-bound real STL or four SVG edges")
    def mesh_geometry(node):
        vertices = []; triangles = 0
        for primitive in meshes[node["mesh"]].get("primitives", []):
            pos = accessor_array(doc, blob, primitive["attributes"]["POSITION"])
            if len(pos): vertices.append(pos)
            indices = accessor_array(doc, blob, primitive["indices"]).reshape(-1) if "indices" in primitive else np.arange(len(pos))
            triangles += len(indices) // 3
        return np.vstack(vertices), triangles
    def world_vertices(node):
        vertices, triangles = mesh_geometry(node); matrix = world[indices[id(node)]]
        return (matrix @ np.c_[vertices, np.ones(len(vertices))].T).T[:, :3], triangles
    def world_origin(node): return world[indices[id(node)]][:3, 3]
    stl_vertices, stl_triangles = world_vertices(stl_nodes[0][1])
    if stl_triangles < 600 or np.max(np.abs((stl_vertices.max(axis=0) - stl_vertices.min(axis=0)) - [85, 12, 65])) > .15:
        return fail("GLB STL mesh does not preserve the real 85 x 65 x 12 imported body")
    if not all(mesh_geometry(n)[1] >= 8 for _, n in svg_nodes): return fail("A named SVG edge lacks indexed non-degenerate triangles")
    svg_world = []
    for _, node in svg_nodes:
        vertices, _ = world_vertices(node); svg_world.append(vertices)
    svg_world = np.vstack(svg_world); dims = svg_world.max(axis=0) - svg_world.min(axis=0)
    svg_height = float(svg_world[:, 1].mean())
    if np.max(np.abs(dims[[0, 2]] - [85, 65])) > .8 or not 15 <= svg_height <= 40:
        return fail("GLB SVG is not full-scale and aligned above the STL")
    standoffs = [(name, n) for name, n in named.items() if name.startswith("BRASS_STANDOFF_") and isinstance(n.get("mesh"), int)]
    if len(standoffs) != 4: return fail("GLB needs four real mesh-bound brass standoffs")
    expected = {(7, -7), (78, -7), (7, -58), (78, -58)}
    got = {(round(world_origin(n)[0]), round(world_origin(n)[2])) for _, n in standoffs}
    if got != expected or not all(mesh_geometry(n)[1] >= 32 and close(world_origin(n)[1], svg_height, .5) for _, n in standoffs):
        return fail("Standoffs are not real geometry aligned to the corner holes and SVG plane")
    for _, node in standoffs:
        values = [visible_material(doc, primitive.get("material")) for primitive in meshes[node["mesh"]].get("primitives", [])]
        brass = bool(values) and all(value is not None and value[2] and value[1] >= .6 and
                                     value[0][0] >= .45 and value[0][1] >= .22 and value[0][2] <= .3 and
                                     value[0][0] > value[0][1] > value[0][2]
                                     for value in values)
        if not brass: return fail("A standoff lacks a visible gold/brass-colored metallic material")
    header = [(name, n) for name, n in named.items() if name.startswith("GPIO40_HEADER_ALIGNMENT_BODY") and isinstance(n.get("mesh"), int)]
    pins = [(name, n) for name, n in named.items() if name.startswith("GPIO40_PIN_") and isinstance(n.get("mesh"), int)]
    if (len(header) != 1 or len(pins) != 40 or mesh_geometry(header[0][1])[1] < 12 or
            not close(world_origin(header[0][1])[1], svg_height + 4, .5)):
        return fail("GLB lacks real GPIO/header alignment geometry")
    return ok("Blender GLB has real STL/SVG meshes, full-scale profile, brass standoffs, and GPIO40 geometry")


def main():
    if IMPORT_ERROR is not None: finish(fail("Missing evaluator dependency: " + repr(IMPORT_ERROR)))
    for check in (required_files, check_stage1, check_stl, check_handoff, check_board, check_svg, check_glb):
        if not check(): finish(False)
    finish(True)


if __name__ == "__main__": main()
