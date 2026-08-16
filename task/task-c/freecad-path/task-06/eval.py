from __future__ import annotations

import math
import os
import re
import shlex
import stat
import subprocess
import sys
from pathlib import Path


TARGET = Path("/home/user/Desktop")
FCSTD = TARGET / "task-06.FCStd"
NC = TARGET / "task-06.nc"
INPUT = TARGET / "job_input.step"
MARKER = "TASK_C06_FREECAD_EVAL="
MAX_FCSTD_SIZE = 50 * 1024 * 1024
MAX_NC_SIZE = 5 * 1024 * 1024


def regular_file(path: Path, maximum: int) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISREG(info.st_mode)
        and not path.is_symlink()
        and 0 < info.st_size <= maximum
    )


def outer_main() -> bool:
    if not regular_file(INPUT, MAX_FCSTD_SIZE):
        return False
    if not regular_file(FCSTD, MAX_FCSTD_SIZE) or not regular_file(NC, MAX_NC_SIZE):
        return False
    try:
        result = subprocess.run(
            ["/usr/bin/freecadcmd", str(Path(__file__).resolve())],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    marker_lines = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip().startswith(MARKER)
    ]
    return result.returncode == 0 and marker_lines == [MARKER + "True"]


try:
    import FreeCAD as App
    import Part
    import Path.Post.Command as PathPostCommand
    from Path.Post.Processor import PostProcessor
except ImportError:
    if __name__ == "__main__":
        try:
            print(True if outer_main() else False)
        except Exception:
            print(False)
    raise SystemExit(0)


def near(actual, expected, tolerance=1e-5):
    return abs(float(actual) - float(expected)) <= tolerance


def bbox_values(shape):
    box = shape.BoundBox
    return [box.XMin, box.XMax, box.YMin, box.YMax, box.ZMin, box.ZMax]


def bbox_dimensions(shape):
    box = shape.BoundBox
    return [box.XLength, box.YLength, box.ZLength]


def valid_source_shape(shape) -> bool:
    if shape.isNull() or not shape.isValid() or len(shape.Solids) != 1:
        return False
    if not near(shape.Volume, 172800.0, 1e-2):
        return False
    if sorted(round(value, 4) for value in bbox_dimensions(shape)) != [18.0, 80.0, 120.0]:
        return False
    if len(shape.Faces) != 6:
        return False
    return all(isinstance(face.Surface, Part.Plane) for face in shape.Faces)


def proxy_module(obj) -> str:
    return type(getattr(obj, "Proxy", None)).__module__


def unwrap_operation(operation):
    path_object = operation
    current = operation
    seen = set()
    while proxy_module(current).startswith("Path.Dressup"):
        if current.Name in seen:
            return None, None
        seen.add(current.Name)
        base = getattr(current, "Base", None)
        if isinstance(base, tuple):
            base = base[0]
        if base is None or not hasattr(base, "Proxy"):
            return None, None
        current = base
    return current, path_object


def quantity_mm_per_minute(value) -> float:
    try:
        return float(value.getValueAs("mm/min"))
    except Exception:
        return float(value.Value) * 60.0


def native_tool_kind(controller) -> str | None:
    if proxy_module(controller) != "Path.Tool.Controller":
        return None
    tool = getattr(controller, "Tool", None)
    if tool is None or proxy_module(tool) != "Path.Tool.Bit":
        return None
    shape_name = re.sub(
        r"[^a-z0-9]", "", str(getattr(tool, "ShapeName", "")).lower()
    )
    if shape_name in {"drill", "twistdrill"}:
        return "drill"
    if shape_name in {"endmill", "ballend", "bullnose"}:
        return "endmill"
    return None


def controller_ok(controller, number: int, expected_kind: str) -> bool:
    try:
        diameter = float(controller.Tool.Diameter.Value)
        spindle = float(controller.SpindleSpeed)
        hfeed = quantity_mm_per_minute(controller.HorizFeed)
        vfeed = quantity_mm_per_minute(controller.VertFeed)
    except Exception:
        return False
    if int(controller.ToolNumber) != number or native_tool_kind(controller) != expected_kind:
        return False
    if not math.isfinite(diameter) or diameter <= 0.0:
        return False
    return (
        near(spindle, 7000.0, 1e-3)
        and near(hfeed, 500.0, 1e-3)
        and near(vfeed, 500.0, 1e-3)
    )


def command_records(operation):
    x = y = z = None
    retract_mode = "G98"
    cycle_initial_z = None
    records = []
    for index, command in enumerate(operation.Path.Commands):
        name = str(command.Name).upper().replace("G00", "G0").replace("G01", "G1")
        params = {str(key).upper(): float(value) for key, value in command.Parameters.items()}
        if name in {"G98", "G99"}:
            retract_mode = name
        old_x, old_y, old_z = x, y, z
        x = params.get("X", x)
        y = params.get("Y", y)
        z = params.get("Z", z)
        records.append(
            {
                "index": index,
                "name": name,
                "params": params,
                "old": (old_x, old_y, old_z),
                "position": (x, y, z),
            }
        )
        if name in {"G81", "G82", "G83"}:
            if cycle_initial_z is None:
                cycle_initial_z = old_z
            retract = params.get("R", old_z)
            z = cycle_initial_z if retract_mode == "G98" else retract
        elif name == "G80":
            cycle_initial_z = None
    return records


def safe_rapids(records, model_top: float) -> bool:
    for record in records:
        if record["name"] not in {"G0", "G00"}:
            continue
        params = record["params"]
        if "X" not in params and "Y" not in params:
            continue
        old_z = record["old"][2]
        new_z = record["position"][2]
        if old_z is None or new_z is None:
            return False
        if min(old_z, new_z) <= model_top + 0.1:
            return False
    return True


def cutting_points(records, model_top: float):
    points = []
    for record in records:
        if record["name"] not in {"G1", "G01", "G2", "G02", "G3", "G03"}:
            continue
        x, y, z = record["position"]
        if x is not None and y is not None and z is not None and z < model_top - 0.01:
            points.append((float(x), float(y), float(z), record["index"]))
    return points


def non_collinear(points) -> bool:
    xy = []
    for x, y, _z, _index in points:
        candidate = (round(x, 5), round(y, 5))
        if candidate not in xy:
            xy.append(candidate)
    if len(xy) < 3:
        return False
    a = xy[0]
    for index in range(1, len(xy) - 1):
        b = xy[index]
        for c in xy[index + 1 :]:
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if abs(cross) > 1e-3:
                return True
    return False


def validate_pocket(operation, path_object, model_shape) -> bool:
    controller = getattr(operation, "ToolController", None)
    if controller is None or not controller_ok(controller, 1, "endmill"):
        return False
    bases = list(getattr(operation, "Base", []))
    if not bases:
        return False
    base_overlaps_model = False
    for base, subelements in bases:
        if not subelements or not hasattr(base, "Shape") or base.Shape.isNull():
            continue
        base_box = base.Shape.BoundBox
        model_box = model_shape.BoundBox
        if (
            base_box.XMax >= model_box.XMin
            and base_box.XMin <= model_box.XMax
            and base_box.YMax >= model_box.YMin
            and base_box.YMin <= model_box.YMax
            and base_box.ZMax >= model_box.ZMin - 0.1
            and base_box.ZMin <= model_box.ZMax + 0.1
        ):
            base_overlaps_model = True
    if not base_overlaps_model:
        return False
    records = command_records(path_object)
    box = model_shape.BoundBox
    if len(records) < 10 or not safe_rapids(records, box.ZMax):
        return False
    points = cutting_points(records, box.ZMax)
    if len(points) < 4 or not non_collinear(points):
        return False
    diameter = float(controller.Tool.Diameter.Value)
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    if max(xs) - min(xs) < max(0.1, 0.2 * diameter):
        return False
    if max(ys) - min(ys) < max(0.1, 0.2 * diameter):
        return False
    tolerance = max(0.1, diameter * 0.05)
    if any(
        x < box.XMin - tolerance
        or x > box.XMax + tolerance
        or y < box.YMin - tolerance
        or y > box.YMax + tolerance
        or z < box.ZMin - tolerance
        for x, y, z, _index in points
    ):
        return False
    return True


def validate_drilling(operation, path_object, model_shape) -> bool:
    controller = getattr(operation, "ToolController", None)
    if controller is None or not controller_ok(controller, 2, "drill"):
        return False
    records = command_records(path_object)
    box = model_shape.BoundBox
    if len(records) < 7 or not safe_rapids(records, box.ZMax):
        return False
    diameter = float(controller.Tool.Diameter.Value)
    cycles = [record for record in records if record["name"] in {"G81", "G82", "G83"}]
    if not cycles or not any(record["name"] == "G80" for record in records):
        return False
    locations = set()
    for cycle in cycles:
        x, y, z = cycle["position"]
        if x is None or y is None or z is None:
            return False
        if not (box.XMin + diameter / 2.0 <= x <= box.XMax - diameter / 2.0):
            return False
        if not (box.YMin + diameter / 2.0 <= y <= box.YMax - diameter / 2.0):
            return False
        if not (box.ZMin - 2.0 * diameter <= z < box.ZMax - 0.1):
            return False
        retract = cycle["params"].get("R")
        if retract is None or retract < box.ZMax + 0.1 or retract <= z:
            return False
        locations.add((round(x, 5), round(y, 5)))
    declared = {
        (round(float(location.x), 5), round(float(location.y), 5))
        for location in getattr(operation, "Locations", [])
    }
    return len(locations) >= 1 and locations.issubset(declared)


def closed_cutting_loops(points):
    levels = {}
    for x, y, z, index in points:
        levels.setdefault(round(z, 4), []).append((x, y, index))
    loops = []
    for level_points in levels.values():
        runs = []
        current = []
        for point in level_points:
            if current and point[2] != current[-1][2] + 1:
                runs.append(current)
                current = []
            current.append(point)
        if current:
            runs.append(current)
        for run in runs:
            if len(run) < 5:
                continue
            for left in range(len(run)):
                for right in range(left + 4, len(run)):
                    if math.hypot(
                        run[left][0] - run[right][0],
                        run[left][1] - run[right][1],
                    ) <= 0.05:
                        loops.append(run[left : right + 1])
    return loops


def validate_profile(operation, path_object, model_shape) -> bool:
    controller = getattr(operation, "ToolController", None)
    if controller is None or not controller_ok(controller, 3, "endmill"):
        return False
    if str(getattr(operation, "Side", "")).lower() != "outside":
        return False
    if hasattr(operation, "processPerimeter") and not bool(operation.processPerimeter):
        return False
    records = command_records(path_object)
    box = model_shape.BoundBox
    if len(records) < 10 or not safe_rapids(records, box.ZMax):
        return False
    points = cutting_points(records, box.ZMax)
    loops = closed_cutting_loops(points)
    if len(points) < 8 or not loops:
        return False
    diameter = float(controller.Tool.Diameter.Value)
    radius = diameter / 2.0
    tolerance = max(0.05, diameter * 0.01)
    enclosing_loops = []
    for loop in loops:
        xs = [point[0] for point in loop]
        ys = [point[1] for point in loop]
        if (
            min(xs) <= box.XMin - radius + tolerance
            and max(xs) >= box.XMax + radius - tolerance
            and min(ys) <= box.YMin - radius + tolerance
            and max(ys) >= box.YMax + radius - tolerance
        ):
            enclosing_loops.append(loop)
    if not enclosing_loops:
        return False
    allowed_through = max(2.0, 0.5 * diameter)
    if min(point[2] for point in points) < box.ZMin - allowed_through:
        return False
    return True


def strip_gcode_comments(text: str) -> str:
    result = []
    depth = 0
    index = 0
    while index < len(text):
        char = text[index]
        if depth:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char in "\r\n":
                result.append(char)
            index += 1
            continue
        if char == "(":
            depth = 1
            index += 1
            continue
        if char == ")":
            raise ValueError("unmatched closing G-code comment")
        if char == ";":
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue
        result.append(char)
        index += 1
    if depth:
        raise ValueError("unclosed G-code comment")
    return "".join(result)


WORD_RE = re.compile(r"^([A-Z])([+-]?(?:\d+(?:\.\d*)?|\.\d+))$")


def canonical_number(letter: str, value: str) -> str:
    number = float(value)
    if letter in {"G", "M", "T", "H", "N"} and near(number, round(number), 1e-9):
        return str(int(round(number)))
    number = round(number, 5)
    if abs(number) < 0.000005:
        number = 0.0
    return ("{:.5f}".format(number)).rstrip("0").rstrip(".")


def canonical_gcode(text: str):
    stripped = strip_gcode_comments(text)
    nonblank = [line.strip() for line in stripped.splitlines() if line.strip()]
    percent_indices = [index for index, line in enumerate(nonblank) if "%" in line]
    if any(nonblank[index] != "%" for index in percent_indices):
        raise ValueError("percent delimiter must be a standalone line")
    if percent_indices and percent_indices != [0, len(nonblank) - 1]:
        raise ValueError("percent delimiters must be paired around the program")
    lines = []
    for raw in stripped.upper().splitlines():
        raw = raw.strip()
        if not raw or raw == "%":
            continue
        tokens = []
        for token in raw.split():
            match = WORD_RE.match(token)
            if match:
                letter, value = match.groups()
                if letter == "N":
                    continue
                tokens.append(letter + canonical_number(letter, value))
            else:
                tokens.append(token)
        if tokens:
            lines.append(tuple(tokens))
    return lines


def nc_sanity(lines, require_tlo=False) -> bool:
    flat = [token for line in lines for token in line]
    if not lines or "G21" not in flat or "G90" not in flat:
        return False
    units = None
    distance = None
    for token in flat:
        if token in {"G20", "G21"}:
            units = token
        elif token in {"G90", "G91"}:
            distance = token
    if units != "G21" or distance != "G90":
        return False
    if not any(token in {"M2", "M30"} for token in lines[-1]):
        return False

    changes = []
    for index, line in enumerate(lines):
        if "M6" not in line:
            continue
        tools = [int(token[1:]) for token in line if re.fullmatch(r"T\d+", token)]
        if len(tools) != 1:
            return False
        changes.append((index, tools[0]))
    if any(tool not in {1, 2, 3} for _index, tool in changes):
        return False
    for required in (1, 2, 3):
        matches = [index for index, tool in changes if tool == required]
        if not matches:
            return False
        start = matches[0]
        later = [index for index, _tool in changes if index > start]
        end = min(later) if later else len(lines)
        section = [token for line in lines[start:end] for token in line]
        if require_tlo and "H{}".format(required) not in section:
            return False
        if "S7000" not in section or not any(token in {"M3", "M4"} for token in section):
            return False
        if "F500" not in section:
            return False
        if not any(token in {"G1", "G2", "G3", "G81", "G82", "G83"} for token in section):
            return False
    return True


def nc_safe_execution(lines, model_box, tool_diameters, require_tlo) -> bool:
    x = y = z = None
    absolute = True
    motion = None
    current_tool = None
    spindle_on = False
    spindle_speed = None
    feed = None
    feed_mode = "G94"
    spindle_mode = "G97"
    plane = "G17"
    tlo_enabled = False
    current_h = None
    retract_mode = "G98"
    cycle_initial_z = None
    for line in lines:
        if "G20" in line:
            return False
        if "G90" in line:
            absolute = True
        if "G91" in line:
            absolute = False
        if "G98" in line:
            retract_mode = "G98"
        if "G99" in line:
            retract_mode = "G99"
        for candidate in ("G17", "G18", "G19"):
            if candidate in line:
                plane = candidate
        for candidate in ("G93", "G94", "G95"):
            if candidate in line:
                feed_mode = candidate
        for candidate in ("G96", "G97"):
            if candidate in line:
                spindle_mode = candidate
        if "G49" in line:
            tlo_enabled = False
            current_h = None
        if "G43" in line:
            height_tokens = [int(token[1:]) for token in line if re.fullmatch(r"H\d+", token)]
            if len(height_tokens) != 1:
                return False
            tlo_enabled = True
            current_h = height_tokens[0]
        if "M5" in line:
            spindle_on = False
        if "M3" in line or "M4" in line:
            spindle_on = True
        tool_tokens = [int(token[1:]) for token in line if re.fullmatch(r"T\d+", token)]
        if "M6" in line:
            if len(tool_tokens) != 1 or tool_tokens[0] not in {1, 2, 3}:
                return False
            if spindle_on:
                return False
            current_tool = tool_tokens[0]
            spindle_on = False
            feed = None
            tlo_enabled = False
            current_h = None
        for token in line:
            if re.fullmatch(r"S[+-]?(?:\d+(?:\.\d*)?|\.\d+)", token):
                spindle_speed = float(token[1:])
            if re.fullmatch(r"F[+-]?(?:\d+(?:\.\d*)?|\.\d+)", token):
                feed = float(token[1:])

        line_motion = next(
            (
                token
                for token in line
                if token in {"G0", "G1", "G2", "G3", "G81", "G82", "G83"}
            ),
            None,
        )
        if line_motion is not None:
            motion = line_motion
        values = {}
        for token in line:
            if len(token) > 1 and token[0] in {"X", "Y", "Z", "R", "I", "J"}:
                try:
                    values[token[0]] = float(token[1:])
                except ValueError:
                    return False

        old_x, old_y, old_z = x, y, z

        def target(old, axis):
            if axis not in values:
                return old
            if absolute or old is None:
                return values[axis]
            return old + values[axis]

        new_x = target(x, "X")
        new_y = target(y, "Y")
        new_z = target(z, "Z")
        if motion == "G0" and ("X" in values or "Y" in values):
            if old_z is None or new_z is None or min(old_z, new_z) <= model_box.ZMax + 0.1:
                return False
        x, y, z = new_x, new_y, new_z

        cutting = motion in {"G1", "G2", "G3", "G81", "G82", "G83"} and any(
            axis in values for axis in {"X", "Y", "Z"}
        )
        if cutting:
            if (
                current_tool not in {1, 2, 3}
                or not spindle_on
                or spindle_speed is None
                or feed is None
                or not near(spindle_speed, 7000.0, 1e-3)
                or not near(feed, 500.0, 1e-3)
                or feed_mode != "G94"
                or spindle_mode != "G97"
                or (require_tlo and (not tlo_enabled or current_h != current_tool))
                or (not require_tlo and tlo_enabled)
            ):
                return False
            diameter = tool_diameters[current_tool]
            if current_tool == 1:
                xy_margin = 0.1 * diameter
                z_min = model_box.ZMin - 0.1
            elif current_tool == 2:
                xy_margin = -diameter / 2.0
                z_min = model_box.ZMin - 2.0 * diameter
            else:
                xy_margin = diameter
                z_min = model_box.ZMin - max(2.0, 0.5 * diameter)
            if x is not None and not model_box.XMin - xy_margin <= x <= model_box.XMax + xy_margin:
                return False
            if y is not None and not model_box.YMin - xy_margin <= y <= model_box.YMax + xy_margin:
                return False
            if z is not None and z < z_min:
                return False
            if motion in {"G2", "G3"}:
                if plane != "G17" or old_x is None or old_y is None or x is None or y is None:
                    return False
                if "I" not in values or "J" not in values:
                    return False
                center_x = old_x + values["I"]
                center_y = old_y + values["J"]
                start_radius = math.hypot(old_x - center_x, old_y - center_y)
                end_radius = math.hypot(x - center_x, y - center_y)
                if start_radius <= 1e-6 or abs(start_radius - end_radius) > max(0.05, 0.01 * start_radius):
                    return False
                if not (
                    model_box.XMin - xy_margin <= center_x - start_radius
                    and center_x + start_radius <= model_box.XMax + xy_margin
                    and model_box.YMin - xy_margin <= center_y - start_radius
                    and center_y + start_radius <= model_box.YMax + xy_margin
                ):
                    return False

        if motion in {"G81", "G82", "G83"} and any(
            token in line for token in {"G81", "G82", "G83"}
        ):
            if cycle_initial_z is None:
                cycle_initial_z = old_z
            retract = values.get("R", old_z)
            if retract is None or retract < model_box.ZMax + 0.1:
                return False
            z = cycle_initial_z if retract_mode == "G98" else retract
        if "G80" in line:
            cycle_initial_z = None
            motion = None
    return True


def validate_job(job, input_shape, submitted_lines) -> bool:
    models = list(getattr(getattr(job, "Model", None), "Group", []))
    model = next(
        (
            candidate
            for candidate in models
            if hasattr(candidate, "Shape") and valid_source_shape(candidate.Shape)
        ),
        None,
    )
    if model is None:
        return False
    model_shape = model.Shape
    if not near(model_shape.Volume, input_shape.Volume, 1e-2):
        return False
    try:
        source_objects = list(job.Proxy.baseObjects(job))
    except Exception:
        return False
    source_matches_input = False
    for source in source_objects:
        if not hasattr(source, "Shape") or source.Shape.isNull() or not source.Shape.isValid():
            continue
        try:
            missing_volume = input_shape.cut(source.Shape).Volume
            extra_volume = source.Shape.cut(input_shape).Volume
        except Exception:
            continue
        if missing_volume <= 1e-3 and extra_volume <= 1e-3:
            source_matches_input = True
            break
    if not source_matches_input:
        return False
    if sorted(round(value, 4) for value in bbox_dimensions(model_shape)) != sorted(
        round(value, 4) for value in bbox_dimensions(input_shape)
    ):
        return False
    stock = getattr(job, "Stock", None)
    if stock is None or not hasattr(stock, "Shape") or stock.Shape.isNull() or not stock.Shape.isValid():
        return False
    if len(stock.Shape.Solids) != 1:
        return False
    model_box = model_shape.BoundBox
    stock_box = stock.Shape.BoundBox
    if not (
        stock_box.XMin <= model_box.XMin + 1e-4
        and stock_box.XMax >= model_box.XMax - 1e-4
        and stock_box.YMin <= model_box.YMin + 1e-4
        and stock_box.YMax >= model_box.YMax - 1e-4
        and stock_box.ZMin <= model_box.ZMin + 1e-4
        and stock_box.ZMax >= model_box.ZMax - 1e-4
    ):
        return False
    if not math.isfinite(stock.Shape.Volume) or stock.Shape.Volume < model_shape.Volume - 1e-3:
        return False
    try:
        if model_shape.cut(stock.Shape).Volume > 1e-3:
            return False
    except Exception:
        return False

    operations = []
    for entry in list(getattr(getattr(job, "Operations", None), "Group", [])):
        operation, path_object = unwrap_operation(entry)
        if operation is None or not bool(getattr(entry, "Active", True)):
            continue
        states = {str(value).lower() for value in list(getattr(entry, "State", []))}
        states.update(str(value).lower() for value in list(getattr(operation, "State", [])))
        if states.intersection({"invalid", "error", "touched"}):
            return False
        operations.append((proxy_module(operation), operation, path_object))
    for module, operation, path_object in operations:
        if module in {"Path.Op.PocketShape", "Path.Op.Pocket", "Path.Op.Drilling", "Path.Op.Profile"}:
            continue
        records = command_records(path_object)
        controller = getattr(operation, "ToolController", None)
        try:
            number = int(controller.ToolNumber)
        except Exception:
            return False
        expected_kind = {1: "endmill", 2: "drill", 3: "endmill"}.get(number)
        if expected_kind is None or not controller_ok(controller, number, expected_kind):
            return False
        if not records or not safe_rapids(records, model_shape.BoundBox.ZMax):
            return False
        for record in records:
            if record["name"] not in {"G1", "G01", "G2", "G02", "G3", "G03", "G81", "G82", "G83"}:
                continue
            x, y, z = record["position"]
            if z is not None and z < stock.Shape.BoundBox.ZMin - 2.0:
                return False
            if x is not None and not stock.Shape.BoundBox.XMin - 2.0 <= x <= stock.Shape.BoundBox.XMax + 2.0:
                return False
            if y is not None and not stock.Shape.BoundBox.YMin - 2.0 <= y <= stock.Shape.BoundBox.YMax + 2.0:
                return False
    pocket_modules = {"Path.Op.PocketShape", "Path.Op.Pocket"}
    pockets = [(op, path) for module, op, path in operations if module in pocket_modules]
    drills = [(op, path) for module, op, path in operations if module == "Path.Op.Drilling"]
    profiles = [(op, path) for module, op, path in operations if module == "Path.Op.Profile"]
    if not pockets or not drills or not profiles:
        return False
    if not all(validate_pocket(op, path, model_shape) for op, path in pockets):
        return False
    if not all(validate_drilling(op, path, model_shape) for op, path in drills):
        return False
    if not all(validate_profile(op, path, model_shape) for op, path in profiles):
        return False
    tool_diameters = {}
    for controller in job.Tools.Group:
        number = int(controller.ToolNumber)
        if number in {1, 2, 3}:
            tool_diameters[number] = float(controller.Tool.Diameter.Value)
    if set(tool_diameters) != {1, 2, 3}:
        return False
    if str(getattr(job, "PostProcessor", "")).strip().lower() != "linuxcnc":
        return False
    arguments = str(getattr(job, "PostProcessorArgs", ""))
    if len(arguments) > 500 or any(char in arguments for char in "\x00\r\n"):
        return False
    try:
        argument_tokens = shlex.split(arguments)
    except ValueError:
        return False
    require_tlo = "--no-tlo" not in argument_tokens
    if not nc_safe_execution(
        submitted_lines, model_shape.BoundBox, tool_diameters, require_tlo
    ):
        return False
    groups = PathPostCommand.buildPostList(job)
    if len(groups) != 1 or not groups[0][1]:
        return False
    regenerated = PostProcessor.load("linuxcnc").export(
        groups[0][1], "-", (arguments + " --no-show-editor").strip()
    )
    regenerated_lines = canonical_gcode(regenerated)
    return (
        regenerated_lines == submitted_lines
        and nc_sanity(regenerated_lines, require_tlo=require_tlo)
        and nc_safe_execution(
            regenerated_lines, model_shape.BoundBox, tool_diameters, require_tlo
        )
    )


def inner_main() -> bool:
    if tuple(App.Version()[:3]) != ("0", "21", "2"):
        return False
    if not regular_file(INPUT, MAX_FCSTD_SIZE):
        return False
    if not regular_file(FCSTD, MAX_FCSTD_SIZE) or not regular_file(NC, MAX_NC_SIZE):
        return False
    input_shape = Part.read(str(INPUT))
    if not valid_source_shape(input_shape):
        return False
    try:
        submitted_text = NC.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError):
        return False
    submitted_lines = canonical_gcode(submitted_text)
    if not nc_sanity(submitted_lines):
        return False

    document = None
    try:
        document = App.openDocument(str(FCSTD))
        for obj in document.Objects:
            if proxy_module(obj).startswith("Path.Op.") or proxy_module(obj).startswith("Path.Dressup"):
                obj.touch()
        document.recompute()
        jobs = [
            obj
            for obj in document.Objects
            if proxy_module(obj) == "Path.Main.Job"
            and type(getattr(obj, "Proxy", None)).__name__ == "ObjectJob"
        ]
        if not jobs:
            return False
        return any(validate_job(job, input_shape, submitted_lines) for job in jobs)
    finally:
        if document is not None:
            App.closeDocument(document.Name)


if __name__ in {"__main__", Path(__file__).stem}:
    try:
        result = inner_main()
    except Exception:
        result = False
    print(MARKER + ("True" if result else "False"))
