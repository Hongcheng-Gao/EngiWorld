from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import tempfile
import textwrap
from pathlib import Path


TARGET = Path(os.environ.get("ENGIWORLD_EVAL_TARGET", "/home/user/Desktop"))
CSV_PATH = TARGET / "tool_library.csv"
STEP_PATH = TARGET / "multi_feature.step"
FCSTD_PATH = TARGET / "task-05.FCStd"
NC_PATH = TARGET / "task-05.nc"
NATIVE_MARKER = "TASK_C05_NATIVE="
EXPECTED_TOOLS = (
    (1, "end mill", 16.0, 7000.0, 500.0, 5),
    (2, "drill", 14.0, 7000.0, 500.0, 5),
    (3, "drill", 12.0, 7000.0, 500.0, 5),
)


def close(actual: float, expected: float, tolerance: float = 1e-6) -> bool:
    return math.isfinite(actual) and abs(actual - expected) <= tolerance


def load_tool_library(path: Path) -> bool:
    if not path.is_file() or not 40 <= path.stat().st_size <= 20_000:
        return False
    try:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != [
                "tool_number",
                "type",
                "diameter",
                "spindle",
                "feed",
                "operation_count",
            ]:
                return False
            rows = list(reader)
        parsed = []
        for row in rows:
            number = float(row["tool_number"])
            operation_count = float(row["operation_count"])
            if not close(number, round(number)) or not close(operation_count, round(operation_count)):
                return False
            parsed.append(
                (
                    int(round(number)),
                    row["type"].strip().lower(),
                    float(row["diameter"]),
                    float(row["spindle"]),
                    float(row["feed"]),
                    int(round(operation_count)),
                )
            )
    except (OSError, TypeError, ValueError, csv.Error):
        return False
    if len(parsed) != len(EXPECTED_TOOLS):
        return False
    for actual, expected in zip(parsed, EXPECTED_TOOLS):
        if actual[:2] != expected[:2] or actual[-1] != expected[-1]:
            return False
        if any(not close(float(a), float(e)) for a, e in zip(actual[2:5], expected[2:5])):
            return False
    return True


def native_check(fcstd_path: Path, step_path: Path, nc_path: Path) -> bool:
    for path, minimum, maximum in (
        (fcstd_path, 1_000, 20_000_000),
        (step_path, 1_000, 20_000_000),
        (nc_path, 1_000, 5_000_000),
    ):
        if not path.is_file() or not minimum <= path.stat().st_size <= maximum:
            return False

    checker = textwrap.dedent(
        r'''
        import json
        import math
        import re
        import FreeCAD as App
        import Part
        import Path.Post.Command as PathPostCommand
        from Path.Post.Processor import PostProcessor

        FILE = __FILE__
        STEP_FILE = __STEP_FILE__
        NC_FILE = __NC_FILE__
        MARKER = __MARKER__
        TOL = 1e-4
        WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:E[+-]?\d+)?)", re.I)
        HOLES = {
            (-42.0, 0.0): (2, 14.0),
            (42.0, 0.0): (2, 14.0),
            (0.0, -28.0): (3, 12.0),
            (0.0, 28.0): (3, 12.0),
        }
        EXPECTED_MODULES = [
            "Path.Op.MillFace",
            "Path.Op.PocketShape",
            "Path.Op.Drilling",
            "Path.Op.Drilling",
            "Path.Op.Profile",
        ]
        EXPECTED_CLASSES = ["ObjectFace", "ObjectPocket", "ObjectDrilling", "ObjectDrilling", "ObjectProfile"]
        result = {"ok": False}
        doc = None

        def near(value, expected, tolerance=TOL):
            return math.isfinite(float(value)) and abs(float(value) - expected) <= tolerance

        def bounds(shape):
            box = shape.BoundBox
            return [box.XMin, box.XMax, box.YMin, box.YMax, box.ZMin, box.ZMax]

        def cylinders(shape):
            found = []
            for face in shape.Faces:
                if isinstance(face.Surface, Part.Cylinder):
                    surface = face.Surface
                    box = face.BoundBox
                    found.append((
                        round(surface.Center.x, 4),
                        round(surface.Center.y, 4),
                        round(2.0 * surface.Radius, 4),
                        round(box.ZMin, 4),
                        round(box.ZMax, 4),
                    ))
            return sorted(found)

        def check_shape(shape, expected_box, expected_cylinders, expected_volume, label):
            if shape.isNull() or not shape.isValid() or len(shape.Solids) != 1:
                raise RuntimeError(label + " is not one valid solid")
            if any(not near(a, b, 1e-5) for a, b in zip(bounds(shape), expected_box)):
                raise RuntimeError(label + " bounds are wrong")
            if not near(shape.Volume, expected_volume, 1e-3):
                raise RuntimeError(label + " volume is wrong")
            if cylinders(shape) != sorted(expected_cylinders):
                raise RuntimeError(label + " cylindrical geometry is wrong")

        def shape_of_reference(base, subname):
            try:
                return base.Shape.getElement(str(subname))
            except Exception:
                return None

        def selected_points(operation):
            points = [(float(point.x), float(point.y)) for point in operation.Locations]
            disabled = set(str(value) for value in operation.Disabled)
            for base, subnames in operation.Base:
                for subname in subnames:
                    if "{}.{}".format(base.Name, subname) in disabled:
                        continue
                    point = operation.Proxy.holePosition(operation, base, subname)
                    if point is None:
                        raise RuntimeError("Drilling Base contains a non-hole feature")
                    points.append((float(point.x), float(point.y)))
            return points

        def sampled_segments(operation, target_z, z_tolerance=0.03):
            segments = []
            x = y = z = None
            for command in operation.Path.Commands:
                name = str(command.Name).upper()
                params = command.Parameters
                if name not in ("G0", "G00", "G1", "G01", "G2", "G02", "G3", "G03"):
                    continue
                nx = float(params.get("X", x)) if params.get("X", x) is not None else None
                ny = float(params.get("Y", y)) if params.get("Y", y) is not None else None
                nz = float(params.get("Z", z)) if params.get("Z", z) is not None else None
                cutting = name in ("G1", "G01", "G2", "G02", "G3", "G03")
                if cutting and None not in (x, y, z, nx, ny, nz) and near(z, target_z, z_tolerance) and near(nz, target_z, z_tolerance):
                    start = (float(x), float(y))
                    end = (float(nx), float(ny))
                    if name in ("G2", "G02", "G3", "G03") and "I" in params and "J" in params:
                        cx = float(x) + float(params["I"])
                        cy = float(y) + float(params["J"])
                        radius = math.hypot(float(x) - cx, float(y) - cy)
                        a0 = math.atan2(float(y) - cy, float(x) - cx)
                        a1 = math.atan2(float(ny) - cy, float(nx) - cx)
                        if name in ("G2", "G02"):
                            sweep = -((a0 - a1) % (2.0 * math.pi))
                        else:
                            sweep = (a1 - a0) % (2.0 * math.pi)
                        if near(sweep, 0.0, 1e-8) and math.hypot(end[0] - start[0], end[1] - start[1]) < TOL:
                            sweep = -2.0 * math.pi if name in ("G2", "G02") else 2.0 * math.pi
                        count = max(2, int(math.ceil(abs(sweep) * max(radius, 1.0) / 0.5)))
                        previous = start
                        for index in range(1, count + 1):
                            angle = a0 + sweep * index / count
                            point = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
                            segments.append((previous, point))
                            previous = point
                    elif math.hypot(end[0] - start[0], end[1] - start[1]) > TOL:
                        segments.append((start, end))
                x, y, z = nx, ny, nz
            return segments

        def point_segment_distance(point, segment):
            px, py = point
            (ax, ay), (bx, by) = segment
            dx, dy = bx - ax, by - ay
            length2 = dx * dx + dy * dy
            if length2 <= 1e-16:
                return math.hypot(px - ax, py - ay)
            t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
            return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

        def arc_points(start, end, name, params):
            if "I" not in params or "J" not in params:
                raise RuntimeError("arc lacks I/J center offsets")
            cx = start[0] + float(params["I"])
            cy = start[1] + float(params["J"])
            radius = math.hypot(start[0] - cx, start[1] - cy)
            if radius <= TOL:
                raise RuntimeError("arc radius is zero")
            if abs(math.hypot(end[0] - cx, end[1] - cy) - radius) > 0.02:
                raise RuntimeError("arc end radius differs from its start radius")
            a0 = math.atan2(start[1] - cy, start[0] - cx)
            a1 = math.atan2(end[1] - cy, end[0] - cx)
            if name in ("G2", "G02"):
                sweep = -((a0 - a1) % (2.0 * math.pi))
            else:
                sweep = (a1 - a0) % (2.0 * math.pi)
            if near(sweep, 0.0, 1e-8) and math.hypot(end[0] - start[0], end[1] - start[1]) < TOL:
                sweep = -2.0 * math.pi if name in ("G2", "G02") else 2.0 * math.pi
            count = max(2, int(math.ceil(abs(sweep) * radius / 0.5)))
            points = [
                (cx + radius * math.cos(a0 + sweep * index / count), cy + radius * math.sin(a0 + sweep * index / count))
                for index in range(count + 1)
            ]
            points[-1] = end
            return points

        def validate_area_motion(operation, kind):
            safe_z = float(operation.SafeHeight.Value)
            x = y = z = None
            allowed = {"G0", "G00", "G1", "G01", "G2", "G02", "G3", "G03"}
            for command in operation.Path.Commands:
                name = str(command.Name).upper()
                params = command.Parameters
                if name.startswith(("M", "T", "S")):
                    raise RuntimeError(kind + " operation contains a tool or spindle command")
                if name.startswith("G") and name not in allowed:
                    raise RuntimeError(kind + " contains an unexpected modal command")
                if name not in allowed:
                    continue
                nx = float(params.get("X", x)) if params.get("X", x) is not None else None
                ny = float(params.get("Y", y)) if params.get("Y", y) is not None else None
                nz = float(params.get("Z", z)) if params.get("Z", z) is not None else None
                has_xy = "X" in params or "Y" in params
                if name in ("G0", "G00") and has_xy:
                    if z is None or nz is None or float(z) < safe_z - TOL or float(nz) < safe_z - TOL:
                        raise RuntimeError(kind + " contains an unsafe low-Z XY rapid")
                if name in ("G0", "G00") and "Z" in params:
                    if nz is None or ((z is None or float(nz) < float(z) - TOL) and float(nz) < safe_z - TOL):
                        raise RuntimeError(kind + " contains an unsafe downward Z rapid")
                if name in ("G1", "G01", "G2", "G02", "G3", "G03"):
                    if None in (x, y, z, nx, ny, nz):
                        raise RuntimeError(kind + " cutting move has unknown coordinates")
                    lower_z = min(float(z), float(nz))
                    limit = {"Face": 0.0, "Pocket": -6.0, "Profile": -18.0}[kind]
                    if lower_z < limit - 0.02:
                        raise RuntimeError(kind + " cuts below its final depth")
                    start = (float(x), float(y))
                    end = (float(nx), float(ny))
                    points = arc_points(start, end, name, params) if name in ("G2", "G02", "G3", "G03") else [start, end]
                    if kind == "Pocket" and any(abs(px) > 17.08 or abs(py) > 7.08 for px, py in points):
                        raise RuntimeError("Pocket cutter gouges outside the R8 pocket")
                    if kind == "Profile" and any(rectangle_distance(px, py) < 7.92 for px, py in points):
                        raise RuntimeError("Profile cutter enters the finished part")
                x, y, z = nx, ny, nz

        def validate_drill_motion(operation):
            x = y = z = None
            retract_mode = None
            cycle_active = False
            allowed = {"G0", "G00", "G80", "G81", "G82", "G83", "G90", "G98", "G99"}
            for command in operation.Path.Commands:
                name = str(command.Name).upper()
                params = command.Parameters
                if name.startswith(("M", "T", "S")):
                    raise RuntimeError("Drilling operation contains a tool or spindle command")
                if name.startswith("G") and name not in allowed:
                    raise RuntimeError("Drilling contains an unexpected motion command")
                if name == "G98":
                    retract_mode = 98
                    continue
                if name == "G99":
                    retract_mode = 99
                    continue
                if name == "G80":
                    cycle_active = False
                    continue
                if name in ("G0", "G00"):
                    nx = float(params.get("X", x)) if params.get("X", x) is not None else None
                    ny = float(params.get("Y", y)) if params.get("Y", y) is not None else None
                    nz = float(params.get("Z", z)) if params.get("Z", z) is not None else None
                    has_xy = "X" in params or "Y" in params
                    if has_xy and (z is None or nz is None or float(z) <= 1.0 or float(nz) <= 1.0):
                        raise RuntimeError("Drilling contains an unsafe low-Z XY rapid")
                    if "Z" in params and (nz is None or ((z is None or float(nz) < float(z) - TOL) and float(nz) <= 1.0)):
                        raise RuntimeError("Drilling contains an unsafe downward Z rapid")
                    x, y, z = nx, ny, nz
                elif name in ("G81", "G82", "G83"):
                    if retract_mode not in (98, 99) or z is None:
                        raise RuntimeError("Drilling cycle lacks a safe retract mode")
                    nx = float(params.get("X", x)) if params.get("X", x) is not None else None
                    ny = float(params.get("Y", y)) if params.get("Y", y) is not None else None
                    if nx is None or ny is None or "R" not in params or "Z" not in params:
                        raise RuntimeError("Drilling cycle coordinates are incomplete")
                    return_z = float(z) if retract_mode == 98 else float(params["R"])
                    if return_z <= 1.0:
                        raise RuntimeError("Drilling returns below the stock top")
                    cycle_active = True
                    x, y, z = nx, ny, return_z
            if cycle_active:
                raise RuntimeError("Drilling leaves a canned cycle active")

        def distance_to_path(point, segments):
            if not segments:
                return float("inf")
            return min(point_segment_distance(point, segment) for segment in segments)

        def check_face_coverage(operation):
            segments = sampled_segments(operation, 0.0)
            if not segments:
                raise RuntimeError("Face path is empty or trivial")
            for ix in range(63):
                x = -62.0 + 2.0 * ix
                for iy in range(43):
                    y = -42.0 + 2.0 * iy
                    if distance_to_path((x, y), segments) > 8.08:
                        raise RuntimeError("Face path does not cover the complete stock top")

        def inside_rounded_pocket(x, y):
            ax, ay = abs(x), abs(y)
            if ax > 25.0 + TOL or ay > 15.0 + TOL:
                return False
            if ax <= 17.0 or ay <= 7.0:
                return True
            return (ax - 17.0) ** 2 + (ay - 7.0) ** 2 <= 64.0 + TOL

        def check_pocket_coverage(operation):
            segments = sampled_segments(operation, -6.0)
            if not segments:
                raise RuntimeError("Pocket path does not clear the final depth")
            for ix in range(101):
                x = -25.0 + 0.5 * ix
                for iy in range(61):
                    y = -15.0 + 0.5 * iy
                    if inside_rounded_pocket(x, y) and distance_to_path((x, y), segments) > 8.08:
                        raise RuntimeError("Pocket path leaves material at final depth")
            all_cutting = []
            for depth in (-3.0, -6.0):
                all_cutting.extend(sampled_segments(operation, depth))
            for segment in all_cutting:
                for x, y in segment:
                    if abs(x) > 17.08 or abs(y) > 7.08:
                        raise RuntimeError("Pocket cutter gouges outside the R8 pocket")

        def rectangle_distance(x, y):
            return math.hypot(max(abs(x) - 60.0, 0.0), max(abs(y) - 40.0, 0.0))

        def check_profile_coverage(operation):
            segments = sampled_segments(operation, -18.0)
            if len(segments) < 4:
                raise RuntimeError("Profile path is empty or not closed")
            for segment in segments:
                for x, y in segment:
                    if rectangle_distance(x, y) < 7.92:
                        raise RuntimeError("Profile cutter enters the finished part")
            boundary = []
            for index in range(121):
                x = -60.0 + index
                boundary.extend(((x, -40.0), (x, 40.0)))
            for index in range(81):
                y = -40.0 + index
                boundary.extend(((-60.0, y), (60.0, y)))
            closed_contour = None
            for start in range(len(segments)):
                for end in range(start + 3, len(segments)):
                    first = segments[start][0]
                    last = segments[end][1]
                    if math.hypot(first[0] - last[0], first[1] - last[1]) > 0.12:
                        continue
                    candidate = segments[start : end + 1]
                    if all(distance_to_path(point, candidate) <= 8.08 for point in boundary):
                        closed_contour = candidate
                        break
                if closed_contour is not None:
                    break
            if closed_contour is None:
                raise RuntimeError("Profile lacks a closed contour covering the complete outside boundary")

        def strip_comments(text):
            output = []
            paren_depth = 0
            semicolon_comment = False
            for char in text:
                if semicolon_comment:
                    if char == "\n":
                        semicolon_comment = False
                        output.append(char)
                elif paren_depth:
                    if char == "(":
                        paren_depth += 1
                    elif char == ")":
                        paren_depth -= 1
                    elif char == "\n":
                        output.append(char)
                elif char == "(":
                    paren_depth = 1
                elif char == ")":
                    raise RuntimeError("unmatched NC comment terminator")
                elif char == ";":
                    semicolon_comment = True
                else:
                    output.append(char)
            if paren_depth:
                raise RuntimeError("unterminated NC comment")
            return "".join(output)

        def canonical_nc(text):
            canonical = []
            blocks = [line.strip().upper() for line in strip_comments(text).splitlines() if line.strip()]
            wrappers = [index for index, block in enumerate(blocks) if block == "%"]
            if wrappers:
                if wrappers != [0, len(blocks) - 1]:
                    raise RuntimeError("percent wrappers are not a single outer pair")
                blocks = blocks[1:-1]
            for cleaned in blocks:
                if "%" in cleaned:
                    raise RuntimeError("percent wrapper is embedded in an NC block")
                words = []
                cursor = 0
                for match in WORD_RE.finditer(cleaned):
                    if cleaned[cursor:match.start()].strip():
                        raise RuntimeError("malformed NC block")
                    letter = match.group(1)
                    value = float(match.group(2))
                    if not math.isfinite(value):
                        raise RuntimeError("non-finite NC word")
                    if letter != "N":
                        if letter in ("G", "M", "T", "H"):
                            if not near(value, round(value), 1e-6):
                                raise RuntimeError("non-integral modal NC word")
                            value = int(round(value))
                            if letter == "M" and value == 30:
                                value = 2
                        else:
                            value = round(value, 3)
                            if value == -0.0:
                                value = 0.0
                        words.append((letter, value))
                    cursor = match.end()
                if cleaned[cursor:].strip() or not words:
                    raise RuntimeError("malformed or empty NC block")
                canonical.append(tuple(sorted(words)))
            return canonical

        try:
            version = App.Version()
            if tuple(version[:3]) != ("0", "21", "2") or "b9bfa5c5507506e4515816414cd27f4851d00489" not in version:
                raise RuntimeError("wrong FreeCAD build")
            doc = App.openDocument(FILE)
            if doc is None:
                raise RuntimeError("FCStd did not open")
            doc.recompute()
            jobs = [
                obj for obj in doc.Objects
                if type(getattr(obj, "Proxy", None)).__module__ == "Path.Main.Job"
                and type(getattr(obj, "Proxy", None)).__name__ == "ObjectJob"
            ]
            if len(jobs) != 1:
                raise RuntimeError("expected exactly one native Job")
            job = jobs[0]
            models = list(job.Model.Group)
            controllers = list(job.Tools.Group)
            operations = list(job.Operations.Group)
            if len(models) != 1 or len(controllers) != 3 or len(operations) != 5:
                raise RuntimeError("wrong Job group cardinality")
            if [type(op.Proxy).__module__ for op in operations] != EXPECTED_MODULES:
                raise RuntimeError("wrong native operation sequence")
            if [type(op.Proxy).__name__ for op in operations] != EXPECTED_CLASSES:
                raise RuntimeError("wrong native operation types")
            path_ops = [obj for obj in doc.Objects if type(getattr(obj, "Proxy", None)).__module__.startswith("Path.Op.")]
            if set(path_ops) != set(operations):
                raise RuntimeError("FCStd contains ungrouped or fake Path operations")
            if any(not bool(op.Active) for op in operations):
                raise RuntimeError("an operation is inactive")
            if str(job.PostProcessor).lower() != "linuxcnc" or list(job.Fixtures) != ["G54"]:
                raise RuntimeError("wrong postprocessor or fixture")
            if str(job.OrderOutputBy) != "Operation" or bool(job.SplitOutput):
                raise RuntimeError("wrong operation output ordering")
            if str(job.PostProcessorOutputFile) != "/home/user/Desktop/task-05.nc":
                raise RuntimeError("wrong NC output path")

            source_objects = list(job.Proxy.baseObjects(job))
            if len(source_objects) != 1:
                raise RuntimeError("Job must reference exactly one source model")
            pocket_area = 50.0 * 30.0 - 4.0 * 8.0 ** 2 + math.pi * 8.0 ** 2
            removed_holes = 2.0 * math.pi * 7.0 ** 2 * 18.0 + 2.0 * math.pi * 6.0 ** 2 * 18.0
            expected_volume = 120.0 * 80.0 * 18.0 - pocket_area * 6.0 - removed_holes
            source_cylinders = [
                (-42.0, 0.0, 14.0, 0.0, 18.0),
                (42.0, 0.0, 14.0, 0.0, 18.0),
                (0.0, -28.0, 12.0, 0.0, 18.0),
                (0.0, 28.0, 12.0, 0.0, 18.0),
            ] + [(x, y, 16.0, 12.0, 18.0) for x in (-17.0, 17.0) for y in (-7.0, 7.0)]
            model_cylinders = [
                (-42.0, 0.0, 14.0, -18.0, 0.0),
                (42.0, 0.0, 14.0, -18.0, 0.0),
                (0.0, -28.0, 12.0, -18.0, 0.0),
                (0.0, 28.0, 12.0, -18.0, 0.0),
            ] + [(x, y, 16.0, -6.0, 0.0) for x in (-17.0, 17.0) for y in (-7.0, 7.0)]
            actual_step = Part.read(STEP_FILE)
            check_shape(actual_step, [-60.0, 60.0, -40.0, 40.0, 0.0, 18.0], source_cylinders, expected_volume, "input STEP")
            check_shape(source_objects[0].Shape, [-60.0, 60.0, -40.0, 40.0, 0.0, 18.0], source_cylinders, expected_volume, "FCStd source")
            expected_shape = Part.makeBox(120.0, 80.0, 18.0, App.Vector(-60.0, -40.0, 0.0))
            expected_pocket = Part.makeBox(34.0, 30.0, 6.0, App.Vector(-17.0, -15.0, 12.0))
            expected_pocket = expected_pocket.fuse(Part.makeBox(50.0, 14.0, 6.0, App.Vector(-25.0, -7.0, 12.0)))
            for x in (-17.0, 17.0):
                for y in (-7.0, 7.0):
                    expected_pocket = expected_pocket.fuse(Part.makeCylinder(8.0, 6.0, App.Vector(x, y, 12.0)))
            expected_shape = expected_shape.cut(expected_pocket)
            for (x, y), (_tool, diameter) in HOLES.items():
                expected_shape = expected_shape.cut(Part.makeCylinder(diameter / 2.0, 20.0, App.Vector(x, y, -1.0)))
            expected_shape = expected_shape.removeSplitter()
            if not near(actual_step.common(expected_shape).Volume, expected_volume, 1e-3):
                raise RuntimeError("input STEP differs from the required finished geometry")
            if not near(actual_step.common(source_objects[0].Shape).Volume, expected_volume, 1e-3):
                raise RuntimeError("FCStd source differs from the submitted STEP")
            check_shape(models[0].Shape, [-60.0, 60.0, -40.0, 40.0, -18.0, 0.0], model_cylinders, expected_volume, "Job model")
            translated = actual_step.copy()
            translated.translate(App.Vector(0.0, 0.0, -18.0))
            if not near(translated.common(models[0].Shape).Volume, expected_volume, 1e-3):
                raise RuntimeError("Job model differs from the translated STEP")
            if not (near(models[0].Placement.Base.x, 0.0) and near(models[0].Placement.Base.y, 0.0) and near(models[0].Placement.Base.z, -18.0)):
                raise RuntimeError("G54 is not at the source top-face center")

            stock = job.Stock
            if stock.Shape.isNull() or not stock.Shape.isValid() or len(stock.Shape.Solids) != 1:
                raise RuntimeError("stock is invalid")
            if any(not near(a, b, 1e-5) for a, b in zip(bounds(stock.Shape), [-62.0, 62.0, -42.0, 42.0, -18.0, 1.0])):
                raise RuntimeError("stock bounds are wrong")
            if not near(stock.Shape.Volume, 124.0 * 84.0 * 19.0, 1e-3):
                raise RuntimeError("stock volume is wrong")
            expected_stock = Part.makeBox(124.0, 84.0, 19.0, App.Vector(-62.0, -42.0, -18.0))
            if not near(stock.Shape.common(expected_stock).Volume, expected_stock.Volume, 1e-3):
                raise RuntimeError("stock is not the required complete rectangular block")
            tool_map = {}
            expected_tools = {1: ("endmill", 16.0), 2: ("drill", 14.0), 3: ("drill", 12.0)}
            for controller in controllers:
                if type(getattr(controller, "Proxy", None)).__module__ != "Path.Tool.Controller" or type(controller.Proxy).__name__ != "ToolController":
                    raise RuntimeError("controller is not native")
                number = int(controller.ToolNumber)
                if number in tool_map or number not in expected_tools:
                    raise RuntimeError("invalid or duplicate tool number")
                tool = controller.Tool
                if type(getattr(tool, "Proxy", None)).__module__ != "Path.Tool.Bit" or type(tool.Proxy).__name__ != "ToolBit":
                    raise RuntimeError("controller does not reference a native ToolBit")
                shape_name, diameter = expected_tools[number]
                if str(tool.ShapeName).lower() != shape_name or not near(tool.Diameter.Value, diameter):
                    raise RuntimeError("tool type or diameter is wrong")
                if number in (2, 3) and not near(tool.TipAngle.Value, 118.0):
                    raise RuntimeError("drill tip angle is wrong")
                if not near(controller.SpindleSpeed, 7000.0) or str(controller.SpindleDir) != "Forward":
                    raise RuntimeError("spindle configuration is wrong")
                if not near(controller.HorizFeed.Value, 500.0 / 60.0) or not near(controller.VertFeed.Value, 500.0 / 60.0):
                    raise RuntimeError("feed does not match the CSV")
                controller_commands = [
                    command for command in controller.Path.Commands
                    if not str(command.Name).strip().startswith("(")
                ]
                if [str(command.Name).upper() for command in controller_commands] != ["M6", "M3"]:
                    raise RuntimeError("ToolController contains unexpected tool or spindle commands")
                change, spindle = controller_commands
                if set(change.Parameters) != {"T"} or not near(change.Parameters["T"], float(number)):
                    raise RuntimeError("ToolController changes to the wrong tool")
                if set(spindle.Parameters) != {"S"} or not near(spindle.Parameters["S"], 7000.0):
                    raise RuntimeError("ToolController spindle command is wrong")
                tool_map[number] = controller

            face, pocket, drill14, drill12, profile = operations
            expected_assignment = [1, 1, 2, 3, 1]
            if [int(op.ToolController.ToolNumber) for op in operations] != expected_assignment:
                raise RuntimeError("operation-to-tool mapping is wrong")
            for op in operations:
                if op.ToolController not in controllers or len(op.Path.Commands) < 8:
                    raise RuntimeError("operation uses an external tool or has no real path")
                if op.SafeHeight.Value <= 1.0 or op.ClearanceHeight.Value <= op.SafeHeight.Value:
                    raise RuntimeError("operation heights are unsafe")

            if not near(face.StartDepth.Value, 1.0) or not near(face.FinalDepth.Value, 0.0) or face.StepDown.Value <= 0.0:
                raise RuntimeError("Face depth contract is wrong")
            if any(base is not models[0] for base, _names in face.Base):
                raise RuntimeError("Face must reference the Job model")
            face_refs = [shape_of_reference(base, name) for base, names in face.Base for name in names]
            if len(face_refs) != 1 or face_refs[0] is None or not near(face_refs[0].BoundBox.ZMin, 0.0) or not near(face_refs[0].BoundBox.ZMax, 0.0):
                raise RuntimeError("Face does not reference the model top")
            check_face_coverage(face)
            validate_area_motion(face, "Face")

            if not near(pocket.StartDepth.Value, 0.0) or not near(pocket.FinalDepth.Value, -6.0) or pocket.StepDown.Value <= 0.0:
                raise RuntimeError("Pocket depth contract is wrong")
            if any(base is not models[0] for base, _names in pocket.Base):
                raise RuntimeError("Pocket must reference the Job model")
            pocket_refs = [shape_of_reference(base, name) for base, names in pocket.Base for name in names]
            if len(pocket_refs) != 1 or pocket_refs[0] is None:
                raise RuntimeError("Pocket must reference one bottom face")
            pbox = pocket_refs[0].BoundBox
            if not (near(pbox.ZMin, -6.0) and near(pbox.ZMax, -6.0) and near(pbox.XLength, 50.0) and near(pbox.YLength, 30.0)):
                raise RuntimeError("Pocket bottom face is wrong")
            check_pocket_coverage(pocket)
            validate_area_motion(pocket, "Pocket")

            assignments = []
            for operation, expected_tool in ((drill14, 2), (drill12, 3)):
                if not near(operation.StartDepth.Value, 0.0) or not near(operation.FinalDepth.Value, -19.0):
                    raise RuntimeError("Drilling nominal depth is wrong")
                if str(operation.ExtraOffset) != "Drill Tip" or str(operation.RetractMode) not in ("G98", "G99"):
                    raise RuntimeError("Drilling tip or retract mode is wrong")
                if operation.RetractHeight.Value <= 1.0:
                    raise RuntimeError("Drilling retract height is unsafe")
                points = selected_points(operation)
                expected_points = sorted(point for point, contract in HOLES.items() if contract[0] == expected_tool)
                if sorted((round(x, 4), round(y, 4)) for x, y in points) != expected_points:
                    raise RuntimeError("Drilling hole assignment is wrong")
                diameter = HOLES[expected_points[0]][1]
                tip_length = (diameter / 2.0) / math.tan(math.radians(118.0 / 2.0))
                expected_cycle_z = -19.0 - tip_length
                cycles = []
                names = [str(command.Name).upper() for command in operation.Path.Commands]
                if not any(name in ("G98", "G99") for name in names) or "G80" not in names:
                    raise RuntimeError("Drilling path lacks retract mode or cycle cancel")
                for command in operation.Path.Commands:
                    if str(command.Name).upper() not in ("G81", "G82", "G83"):
                        continue
                    params = command.Parameters
                    if not all(name in params for name in ("X", "Y", "Z", "R", "F")):
                        raise RuntimeError("Drilling cycle is incomplete")
                    if not near(params["Z"], expected_cycle_z, 0.01) or float(params["R"]) <= 1.0 or not near(params["F"], 500.0 / 60.0):
                        raise RuntimeError("Drilling cycle depth, retract, or feed is wrong")
                    cycles.append((round(float(params["X"]), 4), round(float(params["Y"]), 4)))
                if sorted(cycles) != expected_points:
                    raise RuntimeError("native path does not drill each hole exactly once")
                validate_drill_motion(operation)
                assignments.extend((x, y, expected_tool) for x, y in cycles)
            if sorted(assignments) != sorted((x, y, contract[0]) for (x, y), contract in HOLES.items()):
                raise RuntimeError("drilling operations do not cover all holes exactly once")

            if not near(profile.StartDepth.Value, 0.0) or not near(profile.FinalDepth.Value, -18.0) or profile.StepDown.Value <= 0.0:
                raise RuntimeError("Profile depth contract is wrong")
            if str(profile.Side) != "Outside" or not bool(profile.UseComp) or bool(profile.processHoles):
                raise RuntimeError("Profile is not an outside-only compensated contour")
            check_profile_coverage(profile)
            validate_area_motion(profile, "Profile")

            post_groups = PathPostCommand.buildPostList(job)
            if len(post_groups) != 1 or not post_groups[0][1]:
                raise RuntimeError("unable to rebuild the Job post list")
            regenerated = PostProcessor.load("linuxcnc").export(post_groups[0][1], "-", "--no-show-editor")
            with open(NC_FILE, "r", encoding="utf-8", errors="strict") as stream:
                submitted = stream.read()
            expected_nc = canonical_nc(regenerated)
            submitted_nc = canonical_nc(submitted)
            if not expected_nc or submitted_nc != expected_nc:
                raise RuntimeError("submitted NC does not match this FCStd Job")
            result = {"ok": True, "operations": 5, "nc_blocks": len(expected_nc), "assignments": len(assignments)}
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
        finally:
            if doc is not None:
                try:
                    App.closeDocument(doc.Name)
                except Exception:
                    pass
        print(MARKER + json.dumps(result, sort_keys=True))
        '''
    )
    checker = checker.replace("__FILE__", repr(str(fcstd_path)))
    checker = checker.replace("__STEP_FILE__", repr(str(step_path)))
    checker = checker.replace("__NC_FILE__", repr(str(nc_path)))
    checker = checker.replace("__MARKER__", repr(NATIVE_MARKER))
    try:
        with tempfile.TemporaryDirectory(prefix="task_c05_eval_") as temp_dir:
            script = Path(temp_dir) / "check_native.py"
            script.write_text(checker, encoding="utf-8")
            completed = subprocess.run(
                ["/usr/bin/freecadcmd", str(script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=240,
                check=False,
            )
    except (OSError, subprocess.SubprocessError):
        return False
    if completed.returncode != 0:
        return False
    reports = [line[len(NATIVE_MARKER) :] for line in completed.stdout.splitlines() if line.startswith(NATIVE_MARKER)]
    if len(reports) != 1:
        return False
    try:
        report = json.loads(reports[0])
    except (TypeError, json.JSONDecodeError):
        return False
    return isinstance(report, dict) and report.get("ok") is True


def main() -> bool:
    return load_tool_library(CSV_PATH) and native_check(FCSTD_PATH, STEP_PATH, NC_PATH)


if __name__ == "__main__":
    try:
        ok = main()
    except Exception:
        ok = False
    print(True if ok else False)
