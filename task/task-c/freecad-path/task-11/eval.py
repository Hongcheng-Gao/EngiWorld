from __future__ import annotations

import csv
import re
from pathlib import Path


TARGET = Path("/home/user/Desktop")
FONT_FILE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
TOOL_LABEL = "ToolController_T1_VBit_A60_D10_TD1_CEH1_SD5_L20"

TEXT_SPEC = {
    "plate_A.nc": {
        "plate": "plate_A",
        "text": "A100",
        "height": 8.0,
        "cx": 0.0,
        "cy": 0.0,
        "contours": 7,
    },
    "plate_B.nc": {
        "plate": "plate_B",
        "text": "B200",
        "height": 8.0,
        "cx": 0.0,
        "cy": 0.0,
        "contours": 8,
    },
    "plate_C.nc": {
        "plate": "plate_C",
        "text": "C300",
        "height": 8.0,
        "cx": 0.0,
        "cy": 0.0,
        "contours": 6,
    },
}

TOOL_SPEC = {
    "tool_number": 1.0,
    "cutting_edge_angle_deg": 60.0,
    "diameter_mm": 10.0,
    "tip_diameter_mm": 1.0,
    "cutting_edge_height_mm": 1.0,
    "shank_diameter_mm": 5.0,
    "length_mm": 20.0,
    "spindle_rpm": 7000.0,
    "feed_mm_min": 500.0,
}

AXIS_RE = re.compile(
    r"\b([XYZ])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))",
    re.IGNORECASE,
)
MOTION_RE = re.compile(r"\bG0*([0123])\b", re.IGNORECASE)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def close_enough(actual: str, expected: float, tol: float = 1e-6) -> bool:
    try:
        return abs(float(actual) - expected) <= tol
    except (TypeError, ValueError):
        return False


def check_input_tables() -> bool:
    text_table = TARGET / "text_table.csv"
    tool_table = TARGET / "tool_table.csv"
    if not text_table.is_file() or not tool_table.is_file():
        return False

    with text_table.open(newline="", encoding="utf-8-sig") as handle:
        text_rows = list(csv.DictReader(handle))
    if len(text_rows) != len(TEXT_SPEC):
        return False
    rows_by_plate = {row.get("plate", ""): row for row in text_rows}
    if len(rows_by_plate) != len(text_rows):
        return False

    for expected in TEXT_SPEC.values():
        row = rows_by_plate.get(expected["plate"])
        if row is None or row.get("text") != expected["text"]:
            return False
        if row.get("font_file") != FONT_FILE:
            return False
        for key in ("height", "cx", "cy"):
            if not close_enough(row.get(key, ""), float(expected[key])):
                return False

    with tool_table.open(newline="", encoding="utf-8-sig") as handle:
        tool_rows = list(csv.DictReader(handle))
    if len(tool_rows) != 1 or tool_rows[0].get("tool_type", "").strip().lower() != "v-bit":
        return False
    tool_row = tool_rows[0]
    return all(close_enough(tool_row.get(key, ""), value) for key, value in TOOL_SPEC.items())


def code_only(line: str) -> str:
    line = re.sub(r"\([^)]*\)", " ", line)
    return line.split(";", 1)[0].upper()


def motion_summary(text: str) -> tuple[list[tuple[float, float, float]], list[float], int]:
    state: dict[str, float | None] = {"X": None, "Y": None, "Z": None}
    motion: int | None = None
    cutting_points: list[tuple[float, float, float]] = []
    z_values: list[float] = []
    plunges = 0

    for raw_line in text.splitlines():
        line = code_only(raw_line)
        motion_match = MOTION_RE.search(line)
        if motion_match:
            motion = int(motion_match.group(1))
        values = {axis.upper(): float(value) for axis, value in AXIS_RE.findall(line)}
        if not values:
            continue

        previous_z = state["Z"]
        state.update(values)
        current_z = state["Z"]
        if "Z" in values and current_z is not None:
            z_values.append(current_z)
            if (
                motion in {1, 2, 3}
                and previous_z is not None
                and previous_z > -0.27
                and abs(current_z + 0.3) <= 0.03
            ):
                plunges += 1

        if (
            motion in {1, 2, 3}
            and ("X" in values or "Y" in values)
            and state["X"] is not None
            and state["Y"] is not None
            and current_z is not None
            and abs(current_z + 0.3) <= 0.03
        ):
            cutting_points.append(
                (float(state["X"]), float(state["Y"]), float(current_z))
            )

    return cutting_points, z_values, plunges


def check_nc(path: Path, spec: dict[str, object]) -> frozenset[tuple[float, float]] | None:
    raw = read_text(path)
    text = raw.upper()
    for token in ("G21", "G90", "G54", "M30", "JOB"):
        if token not in text:
            return None
    if re.search(r"\bT\s*1\b[^\n]*\bM0?6\b", text) is None:
        return None
    if re.search(r"\bS\s*7000\b", text) is None:
        return None
    if re.search(r"\bF\s*500(?:\.0*)?\b", text) is None:
        return None

    operation_label = (
        f"Engrave_{spec['text']}_DejaVuSans_{float(spec['height']):g}mm"
    )
    if operation_label.upper() not in text or TOOL_LABEL.upper() not in text:
        return None
    required_metadata = (
        f"FONT FILE {FONT_FILE}",
        f"TEXT {spec['text']}",
        f"SHAPESTRING SIZE {float(spec['height']):.3f} MM",
        f"TEXT CENTER X{float(spec['cx']):.3f} Y{float(spec['cy']):.3f}",
        "WORK ZERO TOP FACE CENTER",
        "ENGRAVE DEPTH 0.300 MM",
        "TOOL T1 60 DEG V-BIT",
        "TOOL CUTTING EDGE ANGLE 60.000 DEG",
        "TOOL DIAMETER 10.000 MM",
        "TOOL TIP DIAMETER 1.000 MM",
        "TOOL CUTTING EDGE HEIGHT 1.000 MM",
        "TOOL SHANK DIAMETER 5.000 MM",
        "TOOL LENGTH 20.000 MM",
    )
    if any(item.upper() not in text for item in required_metadata):
        return None

    points, z_values, plunges = motion_summary(raw)
    if not z_values or not any(abs(z + 0.3) <= 0.02 for z in z_values):
        return None
    if any(z < -0.32 for z in z_values):
        return None
    if any(z < -0.02 and abs(z + 0.3) > 0.03 for z in z_values):
        return None
    if plunges != int(spec["contours"]) or len(points) < 40:
        return None

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    width, height = xmax - xmin, ymax - ymin
    if not 17.0 <= width <= 23.0 or not 5.2 <= height <= 7.2:
        return None
    if abs((xmin + xmax) / 2.0 - float(spec["cx"])) > 0.4:
        return None
    if abs((ymin + ymax) / 2.0 - float(spec["cy"])) > 0.4:
        return None
    if any(abs(x) > 55.0 or abs(y) > 35.0 for x, y, _ in points):
        return None

    signature = frozenset((round(x, 2), round(y, 2)) for x, y, _ in points)
    return signature if len(signature) >= 20 else None


def main() -> bool:
    if not check_input_tables():
        return False

    signatures: list[frozenset[tuple[float, float]]] = []
    for filename, spec in TEXT_SPEC.items():
        path = TARGET / filename
        if not path.is_file() or path.stat().st_size == 0:
            return False
        signature = check_nc(path, spec)
        if signature is None:
            return False
        signatures.append(signature)

    return len(set(signatures)) == len(signatures)


if __name__ == "__main__":
    try:
        ok = main()
    except Exception:
        ok = False
    print("True" if ok else "False")
