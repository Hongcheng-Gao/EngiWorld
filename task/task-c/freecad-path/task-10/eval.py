from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import math
import os
import re
import resource
import shlex
import stat
import subprocess
import sys
import tempfile
import traceback
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from pathlib import PurePosixPath


DESKTOP = Path("/home/user/Desktop")
ROOT = Path(os.environ.get("ENGIWORLD_TASK10_STAGE", str(DESKTOP)))
PART_PATH = ROOT / "part.step"
FIXTURE_PATH = ROOT / "fixture.step"
FCSTD_PATH = ROOT / "task-10.FCStd"
NC_PATH = ROOT / "task-10.nc"
EXPECTED_PART_SHA256 = "57e6e748d29109dce6f137ebce5e6b291868c6e2091a1155b5999116c31cf060"
EXPECTED_FIXTURE_SHA256 = "98300ac3a6160094e2c008bdc4760487d3337877fe24dfb14560fcab83907122"
EXPECTED_FREECAD_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
FREECADCMD = Path("/usr/bin/freecadcmd")
BWRAP = Path("/usr/bin/bwrap")
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(rf"([A-Z])\s*({NUMBER})", re.IGNORECASE)

TOP_Z = 18.0
FLOOR_Z = 13.0
INTERMEDIATE_Z = 15.5
SAFE_Z = 26.0
CLEARANCE_Z = 27.0
TOOL_DIAMETER = 10.0
TOOL_RADIUS = TOOL_DIAMETER / 2.0
CUTTING_EDGE_HEIGHT = 20.0
FIXTURE_CLEARANCE = 3.0
CENTER_CLEARANCE = TOOL_RADIUS + FIXTURE_CLEARANCE
POCKET_BOUNDS = (-25.0, 25.0, -15.0, 15.0)

ALLOWED_OBJECT_TYPES = {
    "App::DocumentObjectGroup",
    "App::FeaturePython",
    "App::Line",
    "App::Origin",
    "App::Plane",
    "Part::Feature",
    "Part::FeaturePython",
    "PartDesign::Feature",
    "PartDesign::Body",
    "Path::FeaturePython",
    "Sketcher::SketchObject",
}
PROXY_STATES = {
    ("Path.Base.SetupSheet", "SetupSheet"): b"null",
    ("Path.Dressup.Boundary", "DressupPathBoundary"): b"null",
    ("Path.Main.Job", "ObjectJob"): b"null",
    ("Path.Main.Stock", "StockFromBase"): b"null",
    ("Path.Main.Stock", "StockCreateBox"): b"null",
    ("Path.Op.PocketShape", "ObjectPocket"): b"null",
    ("Path.Tool.Bit", "ToolBit"): b"null",
    ("Path.Tool.Controller", "ToolController"): b"{}",
    ("draftobjects.clone", "Clone"): b'"Clone"',
}
STOCK_PROXY_PAIRS = {
    ("Path.Main.Stock", "StockFromBase"),
    ("Path.Main.Stock", "StockCreateBox"),
}
ALLOWED_EXTENSIONS = {
    "App::GeoFeatureGroupExtension",
    "App::GroupExtension",
    "App::GroupExtensionPython",
    "App::OriginGroupExtension",
    "Part::AttachExtension",
    "Part::AttachExtensionPython",
}

G_MODAL_GROUPS = (
    frozenset({0, 1, 2, 3, 80}),
    frozenset({17}),
    frozenset({90}),
    frozenset({94}),
    frozenset({21}),
    frozenset({40}),
    frozenset({43, 49}),
    frozenset({54}),
)
M_MODAL_GROUPS = (
    frozenset({2, 30}),
    frozenset({3, 4, 5}),
    frozenset({6}),
    frozenset({7, 8, 9}),
)


def close(first, second, tolerance: float = 1e-5) -> bool:
    return abs(float(first) - float(second)) <= tolerance


def regular_file(path: Path, maximum_size: int) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return stat.S_ISREG(info.st_mode) and not path.is_symlink() and 0 < info.st_size <= maximum_size


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stage_file(source: Path, destination: Path, maximum_size: int) -> bool:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(source, flags)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= maximum_size:
                return False
            remaining = info.st_size
            chunks = []
            while remaining:
                chunk = os.read(descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    return False
                chunks.append(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                return False
        finally:
            os.close(descriptor)
        destination.write_bytes(b"".join(chunks))
        destination.chmod(0o444)
        return True
    except OSError:
        return False


def safe_fcstd_container(path: Path) -> bool:
    if not regular_file(path, 20 * 1024 * 1024) or not zipfile.is_zipfile(path):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if (
                not 1 <= len(entries) <= 120
                or len(names) != len(set(names))
                or names.count("Document.xml") != 1
                or sum(entry.file_size for entry in entries) > 50 * 1024 * 1024
            ):
                return False
            for entry in entries:
                member = PurePosixPath(entry.filename)
                mode = (entry.external_attr >> 16) & 0o170000
                ratio = entry.file_size / max(entry.compress_size, 1)
                if (
                    entry.is_dir()
                    or entry.flag_bits & 0x1
                    or entry.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                    or entry.file_size > 20 * 1024 * 1024
                    or ratio > 200
                    or entry.filename.startswith("/")
                    or "\\" in entry.filename
                    or ".." in member.parts
                    or mode == stat.S_IFLNK
                    or member.suffix.lower() in {".py", ".pyc", ".pyd", ".so", ".dll", ".exe", ".sh"}
                    or not (
                        entry.filename == "Document.xml"
                        or entry.filename == "GuiDocument.xml"
                        or entry.filename == "Locations"
                        or entry.filename == "thumbnails/Thumbnail.png"
                        or member.suffix.lower() in {".brp", ".nc"}
                    )
                ):
                    return False
            xml_data = archive.read("Document.xml")
            gui_xml_data = archive.read("GuiDocument.xml") if "GuiDocument.xml" in names else None
    except (OSError, KeyError, RuntimeError, zipfile.BadZipFile):
        return False
    xml_payloads = [xml_data] + ([gui_xml_data] if gui_xml_data is not None else [])
    if any(
        len(payload) > 5 * 1024 * 1024
        or b"<!DOCTYPE" in payload.replace(b"\x00", b"").upper()
        or b"<!ENTITY" in payload.replace(b"\x00", b"").upper()
        for payload in xml_payloads
    ):
        return False
    try:
        root = ET.fromstring(xml_data)
        if gui_xml_data is not None:
            ET.fromstring(gui_xml_data)
    except ET.ParseError:
        return False
    objects = root.find("Objects")
    object_data = root.find("ObjectData")
    if objects is None or object_data is None:
        return False
    declarations = objects.findall("Object")
    data_objects = object_data.findall("Object")
    declared_names = [obj.get("name", "") for obj in declarations]
    data_names = [obj.get("name", "") for obj in data_objects]
    if (
        not 1 <= len(declarations) <= 60
        or len(declared_names) != len(set(declared_names))
        or set(declared_names) != set(data_names)
        or any(obj.get("type") not in ALLOWED_OBJECT_TYPES for obj in declarations)
    ):
        return False
    if any(extension.get("type") not in ALLOWED_EXTENSIONS for extension in root.findall(".//Extension")):
        return False
    archive_names = set(names)
    for tag, suffix in (("Part", ".brp"), ("Path", ".nc")):
        for node in root.findall(f".//{tag}"):
            reference = node.get("file", "")
            member = PurePosixPath(reference)
            if (
                not reference
                or reference.startswith("/")
                or "\\" in reference
                or ".." in member.parts
                or len(member.parts) != 1
                or member.suffix.lower() != suffix
                or reference not in archive_names
            ):
                return False

    all_python_properties = root.findall('.//*[@type="App::PropertyPythonObject"]')
    audited_python_properties = []
    seen_pairs = []
    for obj in data_objects:
        python_properties = [
            prop
            for prop in obj.findall("./Properties/Property")
            if prop.get("type") == "App::PropertyPythonObject"
        ]
        audited_python_properties.extend(python_properties)
        for prop in python_properties:
            nodes = prop.findall("Python")
            if prop.get("name") != "Proxy" or len(nodes) != 1:
                return False
            node = nodes[0]
            if set(node.attrib) != {"value", "encoded", "module", "class"} or node.get("encoded") != "yes":
                return False
            pair = (node.get("module"), node.get("class"))
            if pair not in PROXY_STATES:
                return False
            try:
                decoded = base64.b64decode(node.get("value", ""), validate=True)
            except (ValueError, TypeError):
                return False
            if decoded != PROXY_STATES[pair]:
                return False
            seen_pairs.append(pair)
    required_pairs = set(PROXY_STATES) - STOCK_PROXY_PAIRS
    stock_pairs = [pair for pair in seen_pairs if pair in STOCK_PROXY_PAIRS]
    if (
        len(all_python_properties) != len(audited_python_properties)
        or {id(prop) for prop in all_python_properties} != {id(prop) for prop in audited_python_properties}
        or any(seen_pairs.count(pair) != 1 for pair in required_pairs)
        or len(stock_pairs) != 1
        or len(seen_pairs) != len(required_pairs) + 1
    ):
        return False

    allowed_file_values = {
        "",
        "/home/user/Desktop/task-10.nc",
        "/usr/lib/freecad/Mod/Path/Tools/Shape/endmill.fcstd",
    }
    for prop in root.findall('.//Property[@type="App::PropertyFile"]'):
        strings = prop.findall("String")
        if len(strings) != 1 or strings[0].get("value", "") not in allowed_file_values:
            return False
    return True


def proxy_module(obj) -> str:
    proxy = getattr(obj, "Proxy", None)
    return getattr(proxy.__class__, "__module__", "") if proxy is not None else ""


def object_state_clean(obj) -> bool:
    try:
        states = {str(value) for value in obj.State}
    except Exception:
        return False
    return not states.intersection({"Touched", "Invalid", "Error"})


def shapes_equal(first, second, tolerance: float = 1e-5) -> bool:
    try:
        return (
            first.isValid()
            and second.isValid()
            and first.cut(second).Volume <= tolerance
            and second.cut(first).Volume <= tolerance
        )
    except Exception:
        return False


def expected_part(Part, App):
    return Part.makeBox(120.0, 80.0, TOP_Z, App.Vector(-60.0, -40.0, 0.0))


def expected_fixture(Part, App):
    return Part.makeCompound(
        [
            Part.makeBox(15.0, 20.0, 4.0, App.Vector(-45.0, -10.0, TOP_Z)),
            Part.makeBox(15.0, 20.0, 4.0, App.Vector(30.0, -10.0, TOP_Z)),
        ]
    )


def expected_avoidance(Part, App):
    envelopes = []
    for solid in expected_fixture(Part, App).Solids:
        box = solid.BoundBox
        radius = CENTER_CLEARANCE
        pieces = [
            Part.makeBox(box.XLength + 2.0 * radius, box.YLength, box.ZLength,
                         App.Vector(box.XMin - radius, box.YMin, box.ZMin)),
            Part.makeBox(box.XLength, box.YLength + 2.0 * radius, box.ZLength,
                         App.Vector(box.XMin, box.YMin - radius, box.ZMin)),
            Part.makeBox(box.XLength, box.YLength, box.ZLength + 2.0 * radius,
                         App.Vector(box.XMin, box.YMin, box.ZMin - radius)),
        ]
        for y in (box.YMin, box.YMax):
            for z in (box.ZMin, box.ZMax):
                pieces.append(Part.makeCylinder(radius, box.XLength, App.Vector(box.XMin, y, z), App.Vector(1, 0, 0)))
        for x in (box.XMin, box.XMax):
            for z in (box.ZMin, box.ZMax):
                pieces.append(Part.makeCylinder(radius, box.YLength, App.Vector(x, box.YMin, z), App.Vector(0, 1, 0)))
        for x in (box.XMin, box.XMax):
            for y in (box.YMin, box.YMax):
                pieces.append(Part.makeCylinder(radius, box.ZLength, App.Vector(x, y, box.ZMin), App.Vector(0, 0, 1)))
        for x in (box.XMin, box.XMax):
            for y in (box.YMin, box.YMax):
                for z in (box.ZMin, box.ZMax):
                    pieces.append(Part.makeSphere(radius, App.Vector(x, y, z)))
        envelope = pieces[0]
        for piece in pieces[1:]:
            envelope = envelope.fuse(piece)
        envelopes.append(envelope)
    return Part.makeCompound(envelopes)


def distance_to_segment(px: float, py: float, start, end) -> float:
    ax, ay = start
    bx, by = end
    dx = bx - ax
    dy = by - ay
    denominator = dx * dx + dy * dy
    if denominator <= 1e-16:
        return math.hypot(px - ax, py - ay)
    scale = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denominator))
    return math.hypot(px - (ax + scale * dx), py - (ay + scale * dy))


def rounded_rectangle_contains(x: float, y: float, bounds, radius: float) -> bool:
    xmin, xmax, ymin, ymax = bounds
    center_x = min(max(x, xmin + radius), xmax - radius)
    center_y = min(max(y, ymin + radius), ymax - radius)
    return math.hypot(x - center_x, y - center_y) <= radius + 1e-8


def disk_face(Part, App, x: float, y: float, z: float, radius: float):
    edge = Part.makeCircle(radius, App.Vector(x, y, z))
    return Part.Face(Part.Wire([edge]))


def capsule_face(Part, App, start, end, z: float, radius: float):
    start_disk = disk_face(Part, App, start[0], start[1], z, radius)
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    if length <= 1e-10:
        return start_disk
    nx = -(end[1] - start[1]) * radius / length
    ny = (end[0] - start[0]) * radius / length
    corners = [
        App.Vector(start[0] + nx, start[1] + ny, z),
        App.Vector(end[0] + nx, end[1] + ny, z),
        App.Vector(end[0] - nx, end[1] - ny, z),
        App.Vector(start[0] - nx, start[1] - ny, z),
    ]
    strip = Part.Face(Part.makePolygon(corners + [corners[0]]))
    end_disk = disk_face(Part, App, end[0], end[1], z, radius)
    return start_disk.fuse(strip).fuse(end_disk).removeSplitter()


def cutter_at_point(Part, App, point):
    return Part.makeCylinder(
        TOOL_RADIUS,
        CUTTING_EDGE_HEIGHT,
        point,
        App.Vector(0.0, 0.0, 1.0),
    )


def edge_point_at_length(edge, distance: float):
    length = float(edge.Length)
    if distance <= 0.0:
        return edge.valueAt(edge.FirstParameter)
    if distance >= length:
        return edge.valueAt(edge.LastParameter)
    parameter = edge.getParameterByLength(distance)
    return edge.valueAt(parameter)


def certified_edge_clearance(edge, fixture_shape, Part, App):
    length = float(edge.Length)
    if not math.isfinite(length) or length <= 1e-10:
        return None
    cache = {}

    def sample(distance: float):
        key = round(distance, 12)
        if key in cache:
            return cache[key]
        point = edge_point_at_length(edge, distance)
        if not all(math.isfinite(value) for value in (point.x, point.y, point.z)):
            raise ValueError("non-finite edge point")
        cutter = cutter_at_point(Part, App, point)
        clearance = float(cutter.distToShape(fixture_shape)[0])
        if not math.isfinite(clearance):
            raise ValueError("non-finite fixture clearance")
        cache[key] = (point, clearance)
        return cache[key]

    try:
        start_point, start_clearance = sample(0.0)
        end_point, end_clearance = sample(length)
    except Exception:
        return None
    stack = [(0.0, length, start_clearance, end_clearance, 0)]
    certified_minimum = float("inf")
    while stack:
        start_length, end_length, first_clearance, second_clearance, depth = stack.pop()
        interval = end_length - start_length
        lower_bound = min(first_clearance, second_clearance) - interval / 2.0
        if lower_bound >= FIXTURE_CLEARANCE - 0.02:
            certified_minimum = min(certified_minimum, lower_bound)
            continue
        if min(first_clearance, second_clearance) < FIXTURE_CLEARANCE - 0.02 or depth >= 30:
            return None
        middle_length = (start_length + end_length) / 2.0
        try:
            _, middle_clearance = sample(middle_length)
        except Exception:
            return None
        if middle_clearance < FIXTURE_CLEARANCE - 0.02:
            return None
        stack.append((middle_length, end_length, middle_clearance, second_clearance, depth + 1))
        stack.append((start_length, middle_length, first_clearance, middle_clearance, depth + 1))
    if certified_minimum == float("inf"):
        return None
    return certified_minimum


def edge_chords(edge):
    if edge is None:
        return []
    try:
        points = list(edge.discretize(Deflection=0.02))
    except Exception:
        points = [edge.valueAt(edge.FirstParameter), edge.valueAt(edge.LastParameter)]
    if len(points) < 2:
        return []
    return list(zip(points, points[1:]))


def contact_chord(start, end):
    if min(start.z, end.z) >= TOP_Z - 1e-5:
        return None
    first = start
    second = end
    dz = end.z - start.z
    if abs(dz) > 1e-12:
        fraction = (TOP_Z - start.z) / dz
        if 0.0 < fraction < 1.0:
            crossing = start + (end - start) * fraction
            if start.z > TOP_Z:
                first = crossing
            elif end.z > TOP_Z:
                second = crossing
    return first, second


def property_semantics(obj, name: str) -> str:
    details = [name]
    for method_name in ("getGroupOfProperty", "getDocumentationOfProperty"):
        try:
            details.append(str(getattr(obj, method_name)(name)))
        except Exception:
            pass
    return " ".join(details).lower().replace("_", " ")


def property_meaning(obj, name: str) -> str:
    details = [name]
    try:
        details.append(str(obj.getDocumentationOfProperty(name)))
    except Exception:
        pass
    return " ".join(details).lower().replace("_", " ")


def fixture_semantics(obj, name: str) -> bool:
    text = property_semantics(obj, name)
    return any(token in text for token in ("fixture", "check geometry", "checkgeometry", "clamp"))


def linked_to(obj, target) -> bool:
    link_types = {
        "App::PropertyLink",
        "App::PropertyLinkChild",
        "App::PropertyLinkGlobal",
        "App::PropertyLinkHidden",
        "App::PropertyLinkList",
        "App::PropertyLinkListChild",
        "App::PropertyLinkListGlobal",
        "App::PropertyLinkListHidden",
        "App::PropertyLinkSub",
        "App::PropertyLinkSubChild",
        "App::PropertyLinkSubGlobal",
        "App::PropertyLinkSubHidden",
        "App::PropertyLinkSubList",
        "App::PropertyLinkSubListChild",
        "App::PropertyLinkSubListGlobal",
        "App::PropertyLinkSubListHidden",
        "App::PropertyXLink",
        "App::PropertyXLinkContainer",
        "App::PropertyXLinkList",
        "App::PropertyXLinkSub",
        "App::PropertyXLinkSubList",
    }

    def targets(value):
        if value is None:
            return []
        if hasattr(value, "Name") and hasattr(value, "Document"):
            return [value]
        if isinstance(value, tuple) and value and hasattr(value[0], "Name"):
            return [value[0]]
        if isinstance(value, (list, tuple)):
            result = []
            for item in value:
                result.extend(targets(item))
            return result
        return []

    try:
        links = [
            (name, targets(getattr(obj, name)))
            for name in obj.PropertiesList
            if obj.getTypeIdOfProperty(name) in link_types
            and fixture_semantics(obj, name)
        ]
        return bool(links) and all(
            values and all(value == target for value in values) and not obj.getEditorMode(name)
            for name, values in links
        )
    except Exception:
        return False


def semantic_scalar_values(obj, predicate):
    scalar_types = {
        "App::PropertyDistance",
        "App::PropertyFloat",
        "App::PropertyFloatConstraint",
        "App::PropertyInteger",
        "App::PropertyIntegerConstraint",
        "App::PropertyLength",
        "App::PropertyPercent",
        "App::PropertyQuantity",
    }
    try:
        values = []
        for name in obj.PropertiesList:
            if obj.getTypeIdOfProperty(name) not in scalar_types:
                continue
            semantics = property_semantics(obj, name)
            meaning = property_meaning(obj, name)
            normalized_name = name.lower().replace("_", "").replace(" ", "")
            if not predicate(normalized_name, semantics, meaning):
                continue
            if obj.getEditorMode(name):
                return []
            value = getattr(obj, name)
            number = value.Value if hasattr(value, "Value") else value
            values.append(float(number))
        return values
    except Exception:
        return []


def has_scalar_value(obj, expected: float) -> bool:
    values = semantic_scalar_values(
        obj,
        lambda name, semantics, meaning: (
            name not in {"clearanceheight", "safeheight"}
            and any(token in semantics for token in ("fixture", "check geometry", "checkgeometry", "clamp"))
            and any(token in meaning for token in ("clear", "offset", "distance", "gap", "safety"))
            and not ("tool" in meaning and "radius" in meaning)
        ),
    )
    return bool(values) and all(close(value, expected) for value in values)


def avoidance_has_editable_offset(avoidance) -> bool:
    total_markers = ("center", "envelope", "total", "combined")
    total_values = semantic_scalar_values(
        avoidance,
        lambda name, semantics, meaning: (
            any(marker in meaning for marker in total_markers)
            and any(token in meaning for token in ("clear", "offset", "distance", "gap", "safety"))
            and any(token in semantics for token in ("fixture", "check geometry", "checkgeometry", "clamp"))
            and not ("tool" in meaning and "radius" in meaning)
        ),
    )
    fixture_values = semantic_scalar_values(
        avoidance,
        lambda name, semantics, meaning: (
            any(token in meaning for token in ("clear", "offset", "distance", "gap", "safety"))
            and any(token in semantics for token in ("fixture", "check geometry", "checkgeometry", "clamp"))
            and any(token in meaning for token in ("fixture", "clamp"))
            and not any(marker in meaning for marker in total_markers)
            and not ("tool" in meaning and "radius" in meaning)
        ),
    )
    radius_values = semantic_scalar_values(
        avoidance,
        lambda name, semantics, meaning: (
            "tool" in meaning
            and "radius" in meaning
            and any(token in semantics for token in ("fixture", "check geometry", "checkgeometry", "clamp"))
        ),
    )
    if total_values and not all(close(value, CENTER_CLEARANCE) for value in total_values):
        return False
    if fixture_values and not all(close(value, FIXTURE_CLEARANCE) for value in fixture_values):
        return False
    if radius_values and not all(close(value, TOOL_RADIUS) for value in radius_values):
        return False
    return bool(total_values) or (bool(fixture_values) and bool(radius_values))


def avoidance_is_linked_offset(avoidance, fixture_object, fixture_shape, Part, App) -> bool:
    try:
        shape = avoidance.Shape
        if (
            not linked_to(avoidance, fixture_object)
            or not avoidance_has_editable_offset(avoidance)
            or shape.isNull()
            or not shape.isValid()
        ):
            return False
        if fixture_shape.cut(shape).Volume > 1e-4:
            return False
        expected_shape = expected_avoidance(Part, App)
        if expected_shape.cut(shape).Volume > 1e-3:
            return False
        expected_bounds = expected_shape.BoundBox
        actual_bounds = shape.BoundBox
        if any(
            not close(actual, expected, 1e-4)
            for actual, expected in (
                (actual_bounds.XMin, expected_bounds.XMin),
                (actual_bounds.XMax, expected_bounds.XMax),
                (actual_bounds.YMin, expected_bounds.YMin),
                (actual_bounds.YMax, expected_bounds.YMax),
                (actual_bounds.ZMin, expected_bounds.ZMin),
                (actual_bounds.ZMax, expected_bounds.ZMax),
            )
        ):
            return False
        return True
    except Exception:
        return False


def validate_operation_path(operation, fixture_shape, Part, App, PathGeom):
    commands = list(operation.Path.Commands)
    current = {axis: None for axis in ("X", "Y", "Z")}
    first_motion = True
    floor_segments = []
    level_segments = {INTERMEDIATE_Z: [], FLOOR_Z: []}
    minimum_clearance = float("inf")
    for command in commands:
        name = str(command.Name).upper().replace(" ", "")
        if name not in {"G0", "G00", "G1", "G01", "G2", "G02", "G3", "G03"}:
            continue
        parameters = command.Parameters
        before = dict(current)
        for axis in current:
            if axis in parameters:
                current[axis] = float(parameters[axis])
        if first_motion:
            first_motion = False
            if name not in {"G0", "G00"} or "Z" not in parameters or float(parameters["Z"]) < CLEARANCE_Z - 1e-4:
                return None
        if not all(value is not None for value in current.values()):
            continue
        if not all(value is not None for value in before.values()):
            if current["Z"] < CLEARANCE_Z - 1e-4:
                return None
            continue
        start = App.Vector(before["X"], before["Y"], before["Z"])
        try:
            edge = PathGeom.edgeForCmd(command, start)
        except Exception:
            return None
        chords = edge_chords(edge)
        if not chords:
            continue
        rapid = name in {"G0", "G00"}
        for first, second in chords:
            if min(first.z, second.z) < FLOOR_Z - 1e-4:
                return None
            horizontal = math.hypot(second.x - first.x, second.y - first.y) > 1e-6
            if rapid and min(first.z, second.z) < SAFE_Z - 1e-4:
                vertical_retract = not horizontal and second.z >= first.z - 1e-6
                if not vertical_retract:
                    return None
            if rapid:
                continue
            contact = contact_chord(first, second)
            if contact is None:
                continue
            low_first, low_second = contact
            if any(
                point.x < POCKET_BOUNDS[0] + TOOL_RADIUS - 0.02
                or point.x > POCKET_BOUNDS[1] - TOOL_RADIUS + 0.02
                or point.y < POCKET_BOUNDS[2] + TOOL_RADIUS - 0.02
                or point.y > POCKET_BOUNDS[3] - TOOL_RADIUS + 0.02
                for point in (low_first, low_second)
            ):
                return None
            if horizontal and close(first.z, second.z, 1e-4):
                for level in level_segments:
                    if close(first.z, level, 1e-4):
                        segment = ((first.x, first.y), (second.x, second.y))
                        level_segments[level].append(segment)
                        if level == FLOOR_Z:
                            floor_segments.append(segment)
        clearance = certified_edge_clearance(edge, fixture_shape, Part, App)
        if clearance is None:
            return None
        minimum_clearance = min(minimum_clearance, clearance)
    if not floor_segments or minimum_clearance == float("inf"):
        return None
    for level, segments in level_segments.items():
        if not segments:
            return None
        samples = 0
        x = POCKET_BOUNDS[0]
        while x <= POCKET_BOUNDS[1] + 1e-8:
            y = POCKET_BOUNDS[2]
            while y <= POCKET_BOUNDS[3] + 1e-8:
                if rounded_rectangle_contains(x, y, POCKET_BOUNDS, TOOL_RADIUS):
                    if min(distance_to_segment(x, y, start, end) for start, end in segments) > TOOL_RADIUS + 0.12:
                        return None
                    samples += 1
                y += 0.5
            x += 0.5
        if samples < 4000:
            return None
    return minimum_clearance


ACTIVE_COMMENT = re.compile(
    r"^(?:ABORT|DEBUG|LOG|LOGAPPEND|LOGCLOSE|LOGOPEN|MSG|PRINT|PROBECLOSE|PROBEOPEN)(?:\s|,|$)"
)


def reject_active_comment(content: str) -> None:
    if ACTIVE_COMMENT.match(content.strip().upper()):
        raise ValueError("active LinuxCNC comment")


def strip_comments(text: str):
    output = []
    for raw_line in text.splitlines(keepends=True):
        if raw_line.endswith("\r\n"):
            line, ending = raw_line[:-2], "\r\n"
        elif raw_line.endswith(("\r", "\n")):
            line, ending = raw_line[:-1], raw_line[-1]
        else:
            line, ending = raw_line, ""
        cleaned = list(line)
        parenthesis_comments = []
        semicolon_comment = None
        index = 0
        while index < len(line):
            char = line[index]
            if char == "(":
                end = line.find(")", index + 1)
                if end < 0 or "(" in line[index + 1 : end]:
                    raise ValueError("malformed parenthesis comment")
                parenthesis_comments.append(line[index + 1 : end])
                cleaned[index : end + 1] = " " * (end + 1 - index)
                index = end + 1
            elif char == ")":
                raise ValueError("unmatched parenthesis")
            elif char == ";":
                semicolon_comment = line[index + 1 :]
                cleaned[index:] = " " * (len(line) - index)
                break
            else:
                index += 1
        if semicolon_comment is not None:
            reject_active_comment(semicolon_comment)
        elif parenthesis_comments:
            reject_active_comment(parenthesis_comments[-1])
        output.append("".join(cleaned) + ending)
    return "".join(output)


def parse_nc(text: str):
    executable = strip_comments(text)
    raw_lines = executable.splitlines()
    nonempty = [index for index, line in enumerate(raw_lines) if line.strip()]
    percent_lines = [index for index, line in enumerate(raw_lines) if line.strip() == "%"]
    if percent_lines and (len(percent_lines) != 2 or percent_lines != [nonempty[0], nonempty[-1]]):
        raise ValueError("illegal percent wrapper")
    blocks = []
    for raw_line in raw_lines:
        line = raw_line.strip().upper()
        if not line or line == "%":
            continue
        tokens = []
        cursor = 0
        for match in WORD_RE.finditer(line):
            if line[cursor : match.start()].strip():
                raise ValueError("unparsed NC text")
            letter = match.group(1).upper()
            number_text = match.group(2)
            number = float(number_text)
            if not math.isfinite(number):
                raise ValueError("non-finite NC word")
            if letter == "N" and (tokens or not re.fullmatch(r"\d+(?:\.\d+)?", number_text)):
                raise ValueError("invalid line number")
            tokens.append((letter, number))
            cursor = match.end()
        if line[cursor:].strip() or not tokens:
            raise ValueError("unparsed NC line")
        blocks.append(tokens)
    if not blocks:
        raise ValueError("empty NC")
    return blocks


def block_codes(block):
    codes = {"G": [], "M": []}
    for letter, number in block:
        if letter not in codes:
            continue
        if not close(number, round(number), 1e-9):
            raise ValueError("fractional G/M code")
        codes[letter].append(int(round(number)))
    for letter, groups in (("G", G_MODAL_GROUPS), ("M", M_MODAL_GROUPS)):
        values = codes[letter]
        if len(values) != len(set(values)):
            raise ValueError("duplicate G/M code")
        if any(sum(code in group for code in values) > 1 for group in groups):
            raise ValueError("conflicting modal codes")
    return codes["G"], codes["M"]


def canonical_blocks(text: str):
    result = []
    position = {axis: None for axis in ("X", "Y", "Z")}
    modal_motion = None
    modal_feed = None
    for block in parse_nc(text):
        g_codes, _ = block_codes(block)
        words = {}
        codes = []
        for letter, number in block:
            if letter == "N":
                continue
            if letter in {"G", "M"}:
                codes.append((letter, number))
            else:
                if letter in words:
                    raise ValueError("duplicate NC word")
                words[letter] = number
        for code in g_codes:
            if code in {0, 1, 2, 3}:
                modal_motion = code
        if "F" in words:
            modal_feed = words["F"]
        moved = any(axis in words for axis in position)
        for axis in position:
            if axis in words:
                position[axis] = words[axis]
        if moved and modal_motion in {0, 1, 2, 3} and all(value is not None for value in position.values()):
            for axis, value in position.items():
                words.setdefault(axis, value)
            codes = [(letter, number) for letter, number in codes if letter != "G" or int(round(number)) not in {0, 1, 2, 3}]
            codes.append(("G", float(modal_motion)))
            if modal_motion in {1, 2, 3} and modal_feed is not None:
                words.setdefault("F", modal_feed)
        normalized = []
        for letter, number in codes + list(words.items()):
            if letter == "M" and close(number, 30.0, 1e-9):
                number = 2.0
            if letter in {"G", "M", "T", "H", "O"} and close(number, round(number), 1e-9):
                value = str(int(round(number)))
            else:
                value = f"{number:.9f}".rstrip("0").rstrip(".")
                if value in {"-0", "+0"}:
                    value = "0"
            normalized.append(letter + value)
        result.append(tuple(sorted(normalized)))
    return result


def validate_nc_safety(text: str) -> bool:
    try:
        blocks = parse_nc(text)
    except Exception:
        return False
    state = {
        "units": False,
        "absolute": False,
        "wcs": False,
        "motion": None,
        "feed": None,
        "speed": None,
        "tool": None,
        "spindle": False,
        "changed": False,
        "X": None,
        "Y": None,
        "Z": None,
    }
    tool_changes = []
    levels = set()
    terminators = 0
    for block_index, block in enumerate(blocks):
        words = {}
        try:
            g_codes, m_codes = block_codes(block)
        except ValueError:
            return False
        for letter, number in block:
            if letter not in {"F", "G", "H", "I", "J", "K", "M", "N", "S", "T", "X", "Y", "Z"}:
                return False
            if letter not in {"G", "M"}:
                if letter in words:
                    return False
                words[letter] = number
        if any(code not in {0, 1, 2, 3, 17, 21, 40, 43, 49, 54, 80, 90, 94} for code in g_codes):
            return False
        if any(code not in {2, 3, 4, 5, 6, 7, 8, 9, 30} for code in m_codes):
            return False
        if 21 in g_codes:
            state["units"] = True
        if 90 in g_codes:
            state["absolute"] = True
        if 54 in g_codes:
            state["wcs"] = True
        for code in g_codes:
            if code in {0, 1, 2, 3}:
                state["motion"] = code
        if "T" in words:
            if not close(words["T"], 1.0, 1e-9):
                return False
            state["tool"] = 1
        if "H" in words and not close(words["H"], 1.0, 1e-9):
            return False
        if "S" in words:
            if not close(words["S"], 7000.0, 1e-6):
                return False
            state["speed"] = words["S"]
        if "F" in words:
            if not close(words["F"], 500.0, 1e-4):
                return False
            state["feed"] = words["F"]
        if 5 in m_codes:
            state["spindle"] = False
        if 6 in m_codes:
            if state["spindle"] or state["tool"] != 1:
                return False
            state["changed"] = True
            tool_changes.append(1)
        if 3 in m_codes or 4 in m_codes:
            if state["speed"] is None or not close(state["speed"], 7000.0):
                return False
            state["spindle"] = True
        before = {axis: state[axis] for axis in ("X", "Y", "Z")}
        moved = False
        for axis in before:
            if axis in words:
                state[axis] = words[axis]
                moved = True
        if moved and state["motion"] in {0, 1, 2, 3}:
            if not state["units"] or not state["absolute"] or not state["wcs"]:
                return False
            if state["motion"] == 0:
                if state["Z"] is None:
                    return False
                if before["Z"] is None and state["Z"] < CLEARANCE_Z - 1e-4:
                    return False
                horizontal = (
                    before["X"] is not None
                    and before["Y"] is not None
                    and state["X"] is not None
                    and state["Y"] is not None
                    and (not close(before["X"], state["X"]) or not close(before["Y"], state["Y"]))
                )
                if before["Z"] is not None and min(before["Z"], state["Z"]) < SAFE_Z - 1e-4:
                    vertical_retract = not horizontal and state["Z"] >= before["Z"] - 1e-6
                    if not vertical_retract:
                        return False
            else:
                if not state["changed"] or not state["spindle"] or state["feed"] is None or state["Z"] is None:
                    return False
                if state["Z"] < FLOOR_Z - 1e-4:
                    return False
                horizontal = (
                    before["X"] is not None
                    and before["Y"] is not None
                    and (not close(before["X"], state["X"]) or not close(before["Y"], state["Y"]))
                )
                if horizontal and before["Z"] is not None and close(before["Z"], state["Z"], 1e-4):
                    if close(state["Z"], INTERMEDIATE_Z, 1e-4):
                        levels.add(INTERMEDIATE_Z)
                    if close(state["Z"], FLOOR_Z, 1e-4):
                        levels.add(FLOOR_Z)
        if 2 in m_codes or 30 in m_codes:
            terminators += 1
            if block_index != len(blocks) - 1 or state["spindle"]:
                return False
    return (
        state["units"]
        and state["absolute"]
        and state["wcs"]
        and tool_changes == [1]
        and levels == {INTERMEDIATE_Z, FLOOR_Z}
        and terminators == 1
    )


def valid_postprocessor_args(value: str) -> bool:
    try:
        arguments = shlex.split(value)
    except ValueError:
        return False
    flags = {
        "--no-header",
        "--no-comments",
        "--line-numbers",
        "--no-show-editor",
        "--modal",
        "--axis-modal",
        "--no-tlo",
    }
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in flags:
            index += 1
            continue
        if argument == "--precision":
            index += 1
            if index >= len(arguments) or not re.fullmatch(r"(?:\d|1\d|20)", arguments[index]):
                return False
            index += 1
            continue
        if re.fullmatch(r"--precision=(?:\d|1\d|20)", argument):
            index += 1
            continue
        return False
    return True


def evaluate_in_freecad() -> bool:
    import builtins

    builtins.pythonopen = open
    import FreeCAD as App
    import Part
    import Path.Geom as PathGeom
    import Path.Post.Command as PathPostCommand
    from Path.Post.Processor import PostProcessor

    if App.Version()[:4] != ["0", "21", "2", "33771 (Git)"] or App.Version()[-1] != EXPECTED_FREECAD_COMMIT:
        return False
    if not all(
        regular_file(path, maximum)
        for path, maximum in (
            (PART_PATH, 5 * 1024 * 1024),
            (FIXTURE_PATH, 5 * 1024 * 1024),
            (FCSTD_PATH, 20 * 1024 * 1024),
            (NC_PATH, 5 * 1024 * 1024),
        )
    ):
        return False
    if not safe_fcstd_container(FCSTD_PATH):
        return False
    if sha256(PART_PATH) != EXPECTED_PART_SHA256 or sha256(FIXTURE_PATH) != EXPECTED_FIXTURE_SHA256:
        return False

    part_shape = Part.read(str(PART_PATH))
    fixture_shape = Part.read(str(FIXTURE_PATH))
    expected_part_shape = expected_part(Part, App)
    expected_fixture_shape = expected_fixture(Part, App)
    if (
        len(part_shape.Solids) != 1
        or len(fixture_shape.Solids) != 2
        or not shapes_equal(part_shape, expected_part_shape, 1e-3)
        or not shapes_equal(fixture_shape, expected_fixture_shape, 1e-3)
        or part_shape.common(fixture_shape).Volume > 1e-5
    ):
        return False

    document = App.openDocument(str(FCSTD_PATH))
    if document is None or "prototype" in str(document.Label).lower():
        return False
    jobs = [obj for obj in document.Objects if proxy_module(obj) == "Path.Main.Job"]
    pockets = [obj for obj in document.Objects if proxy_module(obj) == "Path.Op.PocketShape"]
    dressups = [obj for obj in document.Objects if proxy_module(obj) == "Path.Dressup.Boundary"]
    stocks = [obj for obj in document.Objects if proxy_module(obj) == "Path.Main.Stock"]
    controllers = [obj for obj in document.Objects if proxy_module(obj) == "Path.Tool.Controller"]
    tools = [obj for obj in document.Objects if proxy_module(obj) == "Path.Tool.Bit"]
    if not all(len(items) == 1 for items in (jobs, pockets, dressups, stocks, controllers, tools)):
        return False
    job, pocket, dressup, controller, tool = jobs[0], pockets[0], dressups[0], controllers[0], tools[0]

    tracked = list(document.Objects)
    for obj in tracked:
        obj.touch()
    document.recompute()
    if not all(object_state_clean(obj) for obj in tracked):
        return False

    if (
        list(job.Operations.Group) != [dressup]
        or dressup.Base != pocket
        or bool(dressup.Inside)
        or str(job.PostProcessor).strip().lower() != "linuxcnc"
        or bool(job.SplitOutput)
        or os.path.normpath(str(job.PostProcessorOutputFile)) != "/home/user/Desktop/task-10.nc"
        or not valid_postprocessor_args(str(job.PostProcessorArgs))
        or [str(value).strip().upper() for value in job.Fixtures] != ["G54"]
    ):
        return False
    if len(job.Model.Group) != 1 or not shapes_equal(job.Model.Group[0].Shape, part_shape, 1e-3):
        return False
    if not shapes_equal(job.Stock.Shape, part_shape, 1e-3):
        return False

    fixture_objects = [
        obj
        for obj in document.Objects
        if hasattr(obj, "Shape")
        and not obj.Shape.isNull()
        and shapes_equal(obj.Shape, fixture_shape, 1e-3)
    ]
    if (
        len(fixture_objects) != 1
        or job.Model.Group[0] in fixture_objects
    ):
        return False
    source_model = job.Model.Group[0]
    fixture_object = fixture_objects[0]

    if (
        controller.Tool != tool
        or int(controller.ToolNumber) != 1
        or not close(controller.SpindleSpeed, 7000.0)
        or str(controller.SpindleDir) != "Forward"
        or not close(controller.HorizFeed.getValueAs("mm/min").Value, 500.0)
        or not close(controller.VertFeed.getValueAs("mm/min").Value, 500.0)
        or pocket.ToolController != controller
        or not close(tool.Diameter.Value, TOOL_DIAMETER)
        or not close(tool.ShankDiameter.Value, TOOL_DIAMETER)
        or str(tool.ShapeName).lower() != "endmill"
    ):
        return False

    for obj in (pocket, dressup):
        if not linked_to(obj, fixture_object) or not has_scalar_value(obj, FIXTURE_CLEARANCE):
            return False
    if (
        not close(pocket.StartDepth.Value, TOP_Z)
        or not close(pocket.FinalDepth.Value, FLOOR_Z)
        or not close(pocket.StepDown.Value, 2.5)
        or not close(pocket.SafeHeight.Value, SAFE_Z)
        or not close(pocket.ClearanceHeight.Value, CLEARANCE_Z)
    ):
        return False

    try:
        bases = list(pocket.Base)
    except Exception:
        return False
    if len(bases) != 1 or len(bases[0][1]) != 1 or not str(bases[0][1][0]).startswith("Face"):
        return False
    boundary = bases[0][0]
    try:
        selected = boundary.Shape.getElement(str(bases[0][1][0]))
    except Exception:
        return False
    expected_boundary = Part.makePlane(50.0, 30.0, App.Vector(-25.0, -15.0, TOP_Z))
    if (
        selected.BoundBox.ZLength > 1e-5
        or selected.cut(expected_boundary).Area > 1e-4
        or expected_boundary.cut(selected).Area > 1e-4
    ):
        return False

    avoidance = dressup.Stock
    if (
        avoidance is None
        or not avoidance_is_linked_offset(avoidance, fixture_object, fixture_shape, Part, App)
    ):
        return False

    minimum_clearance = validate_operation_path(dressup, fixture_shape, Part, App, PathGeom)
    if minimum_clearance is None or minimum_clearance < FIXTURE_CLEARANCE - 0.02:
        return False

    try:
        submitted_text = NC_PATH.read_text(encoding="utf-8")
    except Exception:
        return False
    if not validate_nc_safety(submitted_text):
        return False
    sections = PathPostCommand.buildPostList(job)
    if len(sections) != 1 or dressup not in sections[0][1] or pocket in sections[0][1]:
        return False
    with tempfile.TemporaryDirectory(prefix="engiworld-task10-repost-") as temporary:
        repost_path = Path(temporary) / "task-10.nc"
        try:
            PostProcessor.load("linuxcnc").export(
                sections[0][1],
                str(repost_path),
                str(job.PostProcessorArgs),
            )
            repost_text = repost_path.read_text(encoding="utf-8")
        except BaseException:
            return False
        if canonical_blocks(submitted_text) != canonical_blocks(repost_text):
            return False
    return True


def run_outer() -> bool:
    trusted_source = globals().get("TRUSTED_EVALUATOR_SOURCE")
    if os.geteuid() != 0 or not isinstance(trusted_source, bytes):
        return False
    try:
        if ctypes.CDLL(None).prctl(4, 0, 0, 0, 0) != 0:
            return False
    except Exception:
        return False
    try:
        executable = FREECADCMD.resolve(strict=True)
        info = executable.stat()
        bwrap = BWRAP.resolve(strict=True)
        bwrap_info = bwrap.stat()
    except OSError:
        return False
    if any(
        not stat.S_ISREG(item.st_mode) or item.st_uid != 0 or item.st_mode & 0o022
        for item in (info, bwrap_info)
    ):
        return False
    try:
        with tempfile.TemporaryDirectory(prefix="engiworld-task10-stage-") as stage_text:
            stage = Path(stage_text)
            pairs = (
                (DESKTOP / "part.step", stage / "part.step", 5 * 1024 * 1024),
                (DESKTOP / "fixture.step", stage / "fixture.step", 5 * 1024 * 1024),
                (DESKTOP / "task-10.FCStd", stage / "task-10.FCStd", 20 * 1024 * 1024),
                (DESKTOP / "task-10.nc", stage / "task-10.nc", 5 * 1024 * 1024),
            )
            if not all(stage_file(source, destination, maximum) for source, destination, maximum in pairs):
                return False
            evaluator_path = stage / "eval.py"
            descriptor = os.open(evaluator_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
            try:
                view = memoryview(trusted_source)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        return False
                    view = view[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            stage.chmod(0o755)
            evaluator = "/work/eval.py"
            command = (
                "import builtins,os; builtins.pythonopen=open; "
                "exec(\"try:\\n"
                f" ns={{'__name__':'task10_inner','__file__':{evaluator!r}}}\\n"
                f" exec(compile(open({evaluator!r}, encoding='utf-8').read(), {evaluator!r}, 'exec'), ns)\\n"
                " ok=ns['evaluate_in_freecad']()\\n"
                "except BaseException:\\n os._exit(125)\\n"
                "os._exit(0 if ok is True else 1)\")"
            )
            environment = {
                "HOME": "/tmp",
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "LOGNAME": "user",
                "PATH": "/usr/bin:/bin",
                "PYTHONNOUSERSITE": "1",
                "TMPDIR": "/tmp",
                "USER": "user",
                "XDG_CACHE_HOME": "/tmp/.cache",
                "XDG_CONFIG_HOME": "/tmp/.config",
                "ENGIWORLD_TASK10_STAGE": "/work",
            }
            sandbox = [
                str(bwrap),
                "--unshare-all",
                "--unshare-user",
                "--die-with-parent",
                "--new-session",
                "--cap-drop", "ALL",
                "--disable-userns",
                "--ro-bind", "/usr", "/usr",
                "--symlink", "usr/bin", "/bin",
                "--symlink", "usr/lib", "/lib",
                "--symlink", "usr/lib64", "/lib64",
                "--dir", "/etc",
                "--ro-bind", "/etc/fonts", "/etc/fonts",
                "--ro-bind", "/etc/group", "/etc/group",
                "--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache",
                "--ro-bind", "/etc/localtime", "/etc/localtime",
                "--ro-bind", "/etc/nsswitch.conf", "/etc/nsswitch.conf",
                "--ro-bind", "/etc/passwd", "/etc/passwd",
                "--proc", "/proc",
                "--dev", "/dev",
                "--size", str(256 * 1024 * 1024),
                "--tmpfs", "/tmp",
                "--ro-bind", str(stage), "/work",
                "--uid", "1000",
                "--gid", "1000",
                "--clearenv",
            ]
            for name, value in environment.items():
                sandbox.extend(("--setenv", name, value))
            sandbox.extend(("--chdir", "/tmp", "--", str(executable), "-c", command))

            def apply_limits():
                resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                resource.setrlimit(resource.RLIMIT_CPU, (230, 230))
                resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
                resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
                resource.setrlimit(resource.RLIMIT_NPROC, (128, 128))

            completed = subprocess.run(
                sandbox,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=240,
                env={"PATH": "/usr/bin:/bin"},
                cwd="/",
                preexec_fn=apply_limits,
                check=False,
            )
    except Exception:
        return False
    return completed.returncode == 0


if __name__ == "__main__":
    print(True if run_outer() else False)
