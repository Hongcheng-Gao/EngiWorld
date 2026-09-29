from __future__ import annotations

import csv
import json
import math
import os
import re
import subprocess
import tempfile
import textwrap
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


TARGET = Path(os.environ.get("ENGIWORLD_EVAL_TARGET", "/home/user/Desktop"))
CSV_PATH = TARGET / "hole_table.csv"
STEP_PATH = TARGET / "hole_table_plate.step"
NC_PATH = TARGET / "task-04.nc"
FCSTD_PATH = TARGET / "task-04.FCStd"
TOL = 1e-3
WORD_RE = re.compile(
    r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:E[+-]?\d+)?)",
    re.IGNORECASE,
)
NATIVE_MARKER = "TASK_C04_NATIVE="
EXPECTED_ROWS = (
    (-45.0, -10.0, 5.0, 13.0, "through"),
    (-35.0, 10.0, 6.0, 13.0, "through"),
    (-25.0, -10.0, 7.0, 13.0, "through"),
    (-15.0, 10.0, 5.0, 13.0, "through"),
    (-5.0, -10.0, 6.0, 13.0, "through"),
    (5.0, 10.0, 7.0, 13.0, "through"),
    (15.0, -10.0, 5.0, 5.0, "blind"),
    (25.0, 10.0, 6.0, 5.0, "blind"),
    (35.0, -10.0, 7.0, 5.0, "blind"),
    (45.0, 10.0, 5.0, 5.0, "blind"),
)


@dataclass(frozen=True)
class Hole:
    x: float
    y: float
    diameter: float
    depth: float
    hole_type: str

    @property
    def tool(self) -> int:
        return {5.0: 1, 6.0: 2, 7.0: 3}[self.diameter]

    @property
    def final_z(self) -> float:
        return -self.depth


@dataclass(frozen=True)
class Cycle:
    block: int
    code: int
    tool: int
    x: float
    y: float
    z: float
    retract: float
    feed: float


def close(actual: float | None, expected: float, tolerance: float = TOL) -> bool:
    return actual is not None and math.isfinite(actual) and abs(actual - expected) <= tolerance


def load_holes(path: Path) -> list[Hole] | None:
    if not path.is_file() or not 20 <= path.stat().st_size <= 20_000:
        return None
    try:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ["x", "y", "d", "depth", "type"]:
                return None
            raw_rows = list(reader)
        holes = [
            Hole(
                float(row["x"]),
                float(row["y"]),
                float(row["d"]),
                float(row["depth"]),
                row["type"].strip().lower(),
            )
            for row in raw_rows
        ]
    except (OSError, TypeError, ValueError, csv.Error):
        return None
    if len(holes) != 10:
        return None
    if any(not all(math.isfinite(value) for value in (hole.x, hole.y, hole.diameter, hole.depth)) for hole in holes):
        return None
    if len({(hole.x, hole.y) for hole in holes}) != len(holes):
        return None
    actual_rows = Counter(
        (hole.x, hole.y, hole.diameter, hole.depth, hole.hole_type)
        for hole in holes
    )
    if actual_rows != Counter(EXPECTED_ROWS):
        return None
    if Counter(hole.diameter for hole in holes) != Counter({5.0: 4, 6.0: 3, 7.0: 3}):
        return None
    if Counter(hole.hole_type for hole in holes) != Counter({"through": 6, "blind": 4}):
        return None
    for hole in holes:
        if hole.hole_type == "through" and not close(hole.depth, 13.0):
            return None
        if hole.hole_type == "blind" and not close(hole.depth, 5.0):
            return None
    return holes


def strip_comments(text: str) -> str:
    output: list[str] = []
    depth = 0
    for char in text:
        if char == "\n":
            depth = 0
            output.append(char)
        elif depth:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
        elif char == "(":
            depth = 1
        elif char == ";":
            depth = 1
        else:
            output.append(char)
    return "".join(output)


def parse_words(line: str) -> list[tuple[str, float]] | None:
    cleaned = line.strip().upper().replace("%", "")
    if not cleaned:
        return []
    words: list[tuple[str, float]] = []
    cursor = 0
    for match in WORD_RE.finditer(cleaned):
        if cleaned[cursor : match.start()].strip():
            return None
        try:
            value = float(match.group(2))
        except ValueError:
            return None
        if not math.isfinite(value):
            return None
        words.append((match.group(1), value))
        cursor = match.end()
    if cleaned[cursor:].strip() or not words:
        return None
    return words


def parse_nc(path: Path, holes: list[Hole]) -> list[Cycle] | None:
    if not path.is_file() or not 300 <= path.stat().st_size <= 2_000_000:
        return None
    try:
        raw = path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError):
        return None
    if "\x00" in raw:
        return None

    metric = False
    absolute = False
    fixture: int | None = None
    selected_tool: int | None = None
    active_tool: int | None = None
    changed_tools: set[int] = set()
    compensated_tools: set[int] = set()
    spindle_on = False
    spindle_stop_armed = False
    spindle_speed: float | None = None
    feed: float | None = None
    x = y = z = None
    motion: int | None = None
    cycle_code: int | None = None
    cycle_z = cycle_r = cycle_feed = cycle_q = None
    retract_mode: int | None = None
    cycles: list[Cycle] = []
    cycle_groups: list[tuple[int, float]] = []
    open_cycle_group: tuple[int, float] | None = None
    last_cycle_block = -1
    last_cancel_block = -1
    last_group: tuple[int, float] | None = None
    stopped_after_last_cycle = False
    program_ended = False
    safe_after_last_cycle = False

    for block, line in enumerate(strip_comments(raw).splitlines()):
        words = parse_words(line)
        if words is None:
            return None
        if not words:
            continue
        values: dict[str, list[float]] = {}
        for letter, value in words:
            values.setdefault(letter, []).append(value)
        if set(values) - set("NGXYZRQPFSTHML"):
            return None
        if any(len(values.get(letter, [])) > 1 for letter in "NXYZRQPFSTHL"):
            return None
        if "L" in values or program_ended:
            return None

        g_codes = values.get("G", [])
        explicit_motion: int | None = None
        explicit_cycle: int | None = None
        cancel_cycle = False
        for code_value in g_codes:
            if abs(code_value - round(code_value)) > TOL:
                return None
            code = int(round(code_value))
            if code == 20:
                metric = False
            elif code == 21:
                metric = True
            elif code == 90:
                absolute = True
            elif code == 91:
                absolute = False
            elif 54 <= code <= 59:
                fixture = code
            elif code == 0:
                explicit_motion = code
                cycle_code = None
            elif code in (1, 2, 3):
                return None
            elif code in (81, 82, 83):
                explicit_cycle = code
            elif code == 80:
                cancel_cycle = True
            elif code in (98, 99):
                retract_mode = code
            elif code in (10, 28, 30, 50, 51, 52, 53, 68, 69, 92):
                return None
            elif code not in (4, 17, 40, 43, 49, 61, 64, 94):
                return None

        if cancel_cycle:
            cycle_code = None
            last_cancel_block = block
            if open_cycle_group is not None:
                cycle_groups.append(open_cycle_group)
                open_cycle_group = None
        if values.get("T"):
            tool_value = values["T"][-1]
            if abs(tool_value - round(tool_value)) > TOL:
                return None
            selected_tool = int(round(tool_value))
            if selected_tool not in (1, 2, 3):
                return None
        if values.get("S"):
            spindle_speed = values["S"][-1]
        if values.get("F"):
            feed = values["F"][-1]

        m_codes = values.get("M", [])
        if any(abs(code - round(code)) > TOL for code in m_codes):
            return None
        m_ints = [int(round(code)) for code in m_codes]
        if any(code not in (0, 1, 2, 3, 5, 6, 7, 8, 9, 30) for code in m_ints):
            return None
        if 5 in m_ints and 6 in m_ints:
            return None
        if 5 in m_ints:
            spindle_on = False
            spindle_stop_armed = True
            if cycles:
                stopped_after_last_cycle = True
        if 6 in m_ints:
            if spindle_on or not spindle_stop_armed or selected_tool not in (1, 2, 3) or (
                last_cycle_block >= 0 and last_cancel_block <= last_cycle_block
            ):
                return None
            active_tool = selected_tool
            changed_tools.add(active_tool)
            spindle_stop_armed = False
        has_g43 = any(close(code, 43.0) for code in g_codes)
        if has_g43:
            if active_tool not in (1, 2, 3) or len(values.get("H", [])) != 1:
                return None
            if not close(values["H"][0], float(active_tool)):
                return None
            compensated_tools.add(active_tool)
        elif "H" in values:
            return None
        if 3 in m_ints:
            if active_tool not in (1, 2, 3) or not close(spindle_speed, 7000.0):
                return None
            spindle_on = True
        if any(code in m_ints for code in (2, 30)):
            if not cycles or any(letter in values for letter in "XYZRQ"):
                return None
            program_ended = True

        next_x = values.get("X", [x])[-1]
        next_y = values.get("Y", [y])[-1]
        next_z = values.get("Z", [z])[-1]

        if any(letter in values for letter in "XYZ") and not (metric and absolute and fixture == 54):
            return None
        if explicit_motion == 0 and "Z" in values and (next_z is None or next_z <= TOL):
            return None

        if explicit_cycle is not None:
            cycle_code = explicit_cycle
        if cycle_code is not None:
            if "Z" in values:
                cycle_z = values["Z"][-1]
            if "R" in values:
                cycle_r = values["R"][-1]
            if "F" in values:
                cycle_feed = values["F"][-1]
            if "Q" in values:
                cycle_q = values["Q"][-1]
            executes_cycle = explicit_cycle is not None or (
                explicit_motion is None and ("X" in values or "Y" in values)
            )
            if executes_cycle:
                if not (metric and absolute and fixture == 54):
                    return None
                if not (
                    active_tool in (1, 2, 3)
                    and active_tool in compensated_tools
                    and spindle_on
                    and close(spindle_speed, 7000.0)
                ):
                    return None
                if retract_mode not in (98, 99):
                    return None
                if None in (next_x, next_y, cycle_z, cycle_r, cycle_feed):
                    return None
                if not close(cycle_feed, 500.0) or float(cycle_r) <= TOL:
                    return None
                if cycle_code == 83 and (cycle_q is None or cycle_q <= TOL):
                    return None
                group = (int(active_tool), round(float(cycle_z), 4))
                if last_group is not None and group != last_group and last_cancel_block <= last_cycle_block:
                    return None
                cycles.append(
                    Cycle(
                        block,
                        cycle_code,
                        int(active_tool),
                        float(next_x),
                        float(next_y),
                        float(cycle_z),
                        float(cycle_r),
                        float(cycle_feed),
                    )
                )
                last_cycle_block = block
                last_group = group
                if open_cycle_group is None:
                    open_cycle_group = group
                elif open_cycle_group != group:
                    return None
                return_z = z if retract_mode == 98 else cycle_r
                if return_z is None or return_z <= TOL:
                    return None
                z = float(return_z)
                stopped_after_last_cycle = False
                safe_after_last_cycle = True
        if explicit_motion is not None:
            motion = explicit_motion
        executes_noncycle_xy = (
            ("X" in values or "Y" in values)
            and not (cycle_code is not None and explicit_motion is None)
            and explicit_cycle is None
        )
        if executes_noncycle_xy and motion in (0, 1, 2, 3):
            if z is None or z <= TOL or next_z is None or next_z <= TOL:
                return None
        if explicit_motion is not None:
            x, y, z = next_x, next_y, next_z
        elif cycle_code is None:
            x, y, z = next_x, next_y, next_z
        else:
            x, y = next_x, next_y

    if changed_tools != {1, 2, 3}:
        return None
    if not (
        metric
        and absolute
        and fixture == 54
        and compensated_tools == {1, 2, 3}
        and last_cancel_block > last_cycle_block >= 0
    ):
        return None
    if open_cycle_group is not None:
        return None
    expected_groups = {(hole.tool, round(hole.final_z, 4)) for hole in holes}
    if not 6 <= len(cycle_groups) <= 10 or set(cycle_groups) != expected_groups:
        return None
    if not (cycles and safe_after_last_cycle and stopped_after_last_cycle and program_ended):
        return None

    expected = Counter(
        (round(hole.x, 4), round(hole.y, 4), hole.tool, round(hole.final_z, 4))
        for hole in holes
    )
    actual = Counter(
        (round(cycle.x, 4), round(cycle.y, 4), cycle.tool, round(cycle.z, 4))
        for cycle in cycles
    )
    if actual != expected:
        return None
    return cycles


def native_check(path: Path, step_path: Path, holes: list[Hole]) -> bool:
    if not path.is_file() or not 1_000 <= path.stat().st_size <= 20_000_000:
        return False
    if not step_path.is_file() or not 1_000 <= step_path.stat().st_size <= 20_000_000:
        return False
    expected_rows = [
        {
            "x": hole.x,
            "y": hole.y,
            "diameter": hole.diameter,
            "depth": hole.depth,
            "type": hole.hole_type,
            "tool": hole.tool,
        }
        for hole in holes
    ]
    checker = textwrap.dedent(
        """
        import json
        import math
        import FreeCAD as App
        import Part

        FILE = __FILE__
        STEP_FILE = __STEP_FILE__
        EXPECTED = __EXPECTED__
        MARKER = __MARKER__
        result = {"ok": False}
        doc = None

        def near(value, expected, tolerance=1e-5):
            return abs(float(value) - expected) <= tolerance

        def bounds(shape):
            box = shape.BoundBox
            return [box.XMin, box.XMax, box.YMin, box.YMax, box.ZMin, box.ZMax]

        def check_shape(shape, expected_box, expected_cylinders, expected_volume, label):
            if shape.isNull() or not shape.isValid() or len(shape.Solids) != 1:
                raise RuntimeError(label + " is not one valid solid")
            if any(not near(a, b) for a, b in zip(bounds(shape), expected_box)):
                raise RuntimeError(label + " bounds are wrong")
            if not near(shape.Volume, expected_volume, 1e-3):
                raise RuntimeError(label + " volume is wrong")
            cylinders = []
            for face in shape.Faces:
                if isinstance(face.Surface, Part.Cylinder):
                    surface = face.Surface
                    box = face.BoundBox
                    cylinders.append((
                        round(surface.Center.x, 5),
                        round(surface.Center.y, 5),
                        round(2.0 * surface.Radius, 5),
                        round(box.ZMin, 5),
                        round(box.ZMax, 5),
                    ))
            if sorted(cylinders) != sorted(expected_cylinders):
                raise RuntimeError(label + " cylindrical-hole geometry is wrong")

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

        try:
            version = App.Version()
            if tuple(version[:3]) != ("0", "21", "2") or "b9bfa5c5507506e4515816414cd27f4851d00489" not in version:
                raise RuntimeError("wrong FreeCAD 0.21.2 build")
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
                raise RuntimeError("expected one native Job")
            job = jobs[0]
            models = list(job.Model.Group)
            controllers = list(job.Tools.Group)
            operations = list(job.Operations.Group)
            if len(models) != 1 or len(controllers) != 3 or len(operations) != 6:
                raise RuntimeError("wrong Job group cardinality")
            if str(job.PostProcessor).lower() != "linuxcnc" or list(job.Fixtures) != ["G54"]:
                raise RuntimeError("wrong postprocessor or fixture")
            if str(job.PostProcessorOutputFile) != "/home/user/Desktop/task-04.nc":
                raise RuntimeError("wrong postprocessor output path")

            source = list(job.Proxy.baseObjects(job))
            if len(source) != 1:
                raise RuntimeError("Job does not reference one source model")
            source_cylinders = [
                (row["x"], row["y"], row["diameter"], 0.0 if row["type"] == "through" else 12.0 - row["depth"], 12.0)
                for row in EXPECTED
            ]
            model_cylinders = [
                (row["x"], row["y"], row["diameter"], -12.0 if row["type"] == "through" else -row["depth"], 0.0)
                for row in EXPECTED
            ]
            removed_volume = sum(math.pi * (row["diameter"] / 2.0) ** 2 * (12.0 if row["type"] == "through" else row["depth"]) for row in EXPECTED)
            finished_volume = 120.0 * 80.0 * 12.0 - removed_volume
            actual_step = Part.read(STEP_FILE)
            check_shape(actual_step, [-60.0, 60.0, -40.0, 40.0, 0.0, 12.0], source_cylinders, finished_volume, "input STEP")
            check_shape(source[0].Shape, [-60.0, 60.0, -40.0, 40.0, 0.0, 12.0], source_cylinders, finished_volume, "source")
            if not near(actual_step.common(source[0].Shape).Volume, finished_volume, 1e-3):
                raise RuntimeError("FCStd source differs from the uploaded STEP")
            check_shape(models[0].Shape, [-60.0, 60.0, -40.0, 40.0, -12.0, 0.0], model_cylinders, finished_volume, "Job model")
            if not (
                near(models[0].Placement.Base.x, 0.0)
                and near(models[0].Placement.Base.y, 0.0)
                and near(models[0].Placement.Base.z, -12.0)
            ):
                raise RuntimeError("Job origin is not the source top-face center")

            stock = job.Stock
            if stock.Shape.isNull() or not stock.Shape.isValid() or len(stock.Shape.Solids) != 1:
                raise RuntimeError("stock is invalid")
            if any(not near(a, b) for a, b in zip(bounds(stock.Shape), [-60.0, 60.0, -40.0, 40.0, -12.0, 0.0])):
                raise RuntimeError("stock bounds are wrong")
            if not near(stock.Shape.Volume, 120.0 * 80.0 * 12.0, 1e-3):
                raise RuntimeError("stock is not the complete starting block")
            for prop in ("ExtXneg", "ExtXpos", "ExtYneg", "ExtYpos", "ExtZneg", "ExtZpos"):
                if not near(getattr(stock, prop).Value, 0.0):
                    raise RuntimeError("stock extension is nonzero")

            tool_map = {}
            for controller in controllers:
                if type(getattr(controller, "Proxy", None)).__module__ != "Path.Tool.Controller" or type(controller.Proxy).__name__ != "ToolController":
                    raise RuntimeError("controller is not a native ToolController")
                number = int(controller.ToolNumber)
                if number in tool_map or number not in (1, 2, 3):
                    raise RuntimeError("invalid or duplicate tool number")
                tool = controller.Tool
                if type(getattr(tool, "Proxy", None)).__module__ != "Path.Tool.Bit" or type(tool.Proxy).__name__ != "ToolBit":
                    raise RuntimeError("controller does not reference a native ToolBit")
                expected_diameter = {1: 5.0, 2: 6.0, 3: 7.0}[number]
                if (
                    str(getattr(tool, "ShapeName", "")).lower() != "drill"
                    or not near(tool.Diameter.Value, expected_diameter)
                    or not 60.0 <= float(tool.TipAngle.Value) <= 150.0
                    or float(tool.Length.Value) < 13.0
                ):
                    raise RuntimeError("tool type or diameter is wrong")
                if not near(controller.SpindleSpeed, 7000.0) or str(controller.SpindleDir) != "Forward":
                    raise RuntimeError("spindle configuration is wrong")
                if not near(controller.VertFeed.Value, 500.0 / 60.0) or not near(controller.HorizFeed.Value, 500.0 / 60.0):
                    raise RuntimeError("tool feed is not 500 mm/min")
                tool_map[number] = controller
            if set(tool_map) != {1, 2, 3}:
                raise RuntimeError("tool mapping is incomplete")

            expected_by_xy = {(round(row["x"], 5), round(row["y"], 5)): row for row in EXPECTED}
            assignments = []
            operation_groups = []
            for operation in operations:
                proxy = getattr(operation, "Proxy", None)
                if type(proxy).__module__ != "Path.Op.Drilling" or type(proxy).__name__ != "ObjectDrilling" or not bool(operation.Active):
                    raise RuntimeError("operation is not active native Drilling")
                controller = operation.ToolController
                if controller not in controllers:
                    raise RuntimeError("operation uses an external controller")
                tool_number = int(controller.ToolNumber)
                final_z = float(operation.FinalDepth.Value)
                if not near(operation.StartDepth.Value, 0.0):
                    raise RuntimeError("Drilling start depth is not the top face")
                if operation.RetractHeight.Value <= 0.0 or operation.SafeHeight.Value <= 0.0 or operation.ClearanceHeight.Value <= 0.0:
                    raise RuntimeError("Drilling heights are unsafe")
                if bool(operation.KeepToolDown) or str(operation.RetractMode) not in ("G98", "G99"):
                    raise RuntimeError("Drilling retract configuration is unsafe")
                if str(operation.ExtraOffset) != "None":
                    raise RuntimeError("Drilling drill-tip depth offset is wrong")
                operation_groups.append((tool_number, round(final_z, 5)))

                points = selected_points(operation)
                if not points:
                    raise RuntimeError("Drilling operation has no selected holes")
                operation_keys = []
                for x, y in points:
                    key = (round(x, 5), round(y, 5))
                    row = expected_by_xy.get(key)
                    if row is None:
                        raise RuntimeError("Drilling operation contains an unlisted hole")
                    if tool_number != row["tool"] or not near(final_z, -row["depth"]):
                        raise RuntimeError("hole uses the wrong tool or depth")
                    assignments.append((key[0], key[1], tool_number, round(final_z, 5)))
                    operation_keys.append(key)

                names = [str(command.Name).upper() for command in operation.Path.Commands]
                if not any(name in ("G98", "G99") for name in names) or "G80" not in names:
                    raise RuntimeError("native Drilling path lacks retract or cycle cancel")
                cycles = []
                for command in operation.Path.Commands:
                    if str(command.Name).upper() not in ("G81", "G82", "G83"):
                        continue
                    params = command.Parameters
                    if not all(key in params for key in ("X", "Y", "Z", "R", "F")):
                        raise RuntimeError("native drilling cycle is incomplete")
                    if float(params["R"]) <= 0.0 or not near(params["F"], 500.0 / 60.0):
                        raise RuntimeError("native drilling cycle retract or feed is wrong")
                    if not near(params["Z"], final_z):
                        raise RuntimeError("native drilling cycle depth differs from operation")
                    cycles.append((round(float(params["X"]), 5), round(float(params["Y"]), 5)))
                if sorted(cycles) != sorted(operation_keys):
                    raise RuntimeError("native path does not drill each selected hole exactly once")

            expected_assignments = sorted(
                (round(row["x"], 5), round(row["y"], 5), row["tool"], round(-row["depth"], 5))
                for row in EXPECTED
            )
            if sorted(assignments) != expected_assignments:
                raise RuntimeError("native operations do not cover the CSV exactly once")
            expected_groups = sorted(set((row["tool"], round(-row["depth"], 5)) for row in EXPECTED))
            if sorted(operation_groups) != expected_groups:
                raise RuntimeError("native operations are not six distinct tool/depth groups")
            result = {"ok": True, "operations": len(operations), "assignments": len(assignments)}
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
        finally:
            if doc is not None:
                try:
                    App.closeDocument(doc.Name)
                except Exception:
                    pass
        print(MARKER + json.dumps(result, sort_keys=True))
        """
    )
    checker = checker.replace("__FILE__", repr(str(path)))
    checker = checker.replace("__STEP_FILE__", repr(str(step_path)))
    checker = checker.replace("__EXPECTED__", repr(expected_rows))
    checker = checker.replace("__MARKER__", repr(NATIVE_MARKER))
    try:
        with tempfile.TemporaryDirectory(prefix="task_c04_eval_") as temp_dir:
            script = Path(temp_dir) / "check_native.py"
            script.write_text(checker, encoding="utf-8")
            completed = subprocess.run(
                ["/usr/bin/freecadcmd", str(script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=180,
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
    holes = load_holes(CSV_PATH)
    if holes is None:
        return False
    return parse_nc(NC_PATH, holes) is not None and native_check(FCSTD_PATH, STEP_PATH, holes)


if __name__ == "__main__":
    try:
        ok = main()
    except Exception:
        ok = False
    print(True if ok else False)
