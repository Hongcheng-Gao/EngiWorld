from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
OUTPUT_NAME = "task-15.nc"

NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(rf"([A-Z])\s*({NUMBER})", re.IGNORECASE)
PAREN_COMMENT_RE = re.compile(r"\(([^()]*)\)")

ALLOWED_G_CODES = {
    0, 1, 2, 3, 4, 10, 17, 18, 19, 20, 21, 28, 29, 30, 31, 40, 41, 42,
    43, 44, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 61, 64, 68, 69, 73,
    80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 98, 99,
    187,
}
ALLOWED_M_CODES = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 19, 30, 48, 49, 88, 89}
ALLOWED_WORDS = set("NOGMXYZABCUVWIJKRFSTHDLPQ")
ROTARY_AXES = {"A", "B", "C", "U", "V", "W"}

BALL_HINT = re.compile(
    r"(?:\bBALL(?:\s*[- ]?\s*(?:NOSE|END|MILL))?\b|\bSPHERICAL\b|\bBM\b)",
    re.IGNORECASE,
)
NON_BALL_HINT = re.compile(
    r"(?:\bFLAT\s*[- ]?\s*END\b|\bSQUARE\s*[- ]?\s*END\b|\bFACE\s+MILL\b|"
    r"\bDRILL\b|\bTAPER(?:ED)?\b|\bBULL\s*[- ]?\s*NOSE\b)",
    re.IGNORECASE,
)


@dataclass
class Record:
    line: int
    section: int
    motion: int
    start: dict[str, float | None]
    end: dict[str, float | None]
    explicit: dict[str, float]
    tool: int
    wcs: str | None
    spindle_on: bool
    spindle_speed: float | None
    feed: float | None
    length_comp: bool
    length_offset: int | None


@dataclass
class Section:
    tool: int
    start_line: int
    records: list[Record] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    has_m3: bool = False
    has_g43: bool = False
    has_positive_feed: bool = False
    has_positive_speed: bool = False
    end_line: int | None = None


@dataclass
class Program:
    sections: list[Section] = field(default_factory=list)
    comments: list[tuple[int, str]] = field(default_factory=list)
    axes_seen: set[str] = field(default_factory=set)
    units_seen: set[int] = field(default_factory=set)
    m30_line: int | None = None
    executable_after_m30: bool = False


@dataclass
class Geometry:
    section: int
    points: list[tuple[float, float, float]]
    lengths: list[float]
    center: tuple[float, float]
    spans: tuple[float, float]
    z_range: tuple[float, float]
    z_levels: int
    occupied_cells: int
    angular_bins: int
    radial_z_corr: float
    sphere_residual: float
    min_radius: float
    polar_points: int
    polar_min_z: float | None

    @property
    def count(self) -> int:
        return len(self.points)

    @property
    def path_length(self) -> float:
        return sum(self.lengths)


def split_line(raw: str) -> tuple[str, list[str]]:
    upper = raw.upper()
    if upper.count("(") != upper.count(")"):
        raise ValueError("unbalanced comment")
    comments = [value.strip() for value in PAREN_COMMENT_RE.findall(upper) if value.strip()]
    code = PAREN_COMMENT_RE.sub(" ", upper)
    if "(" in code or ")" in code:
        raise ValueError("nested comment")
    if ";" in code:
        code, semicolon = code.split(";", 1)
        if semicolon.strip():
            comments.append(semicolon.strip())
    return code, comments


def integer_controls(words: list[tuple[str, float]], letter: str) -> list[int]:
    result: list[int] = []
    for word_letter, value in words:
        if word_letter != letter:
            continue
        rounded = int(round(value))
        if abs(value - rounded) > 1.0e-9:
            raise ValueError(f"fractional {letter} word")
        result.append(rounded)
    return result


def validate_lexemes(code: str, words: list[tuple[str, float]]) -> None:
    if re.search(r"[A-Z]\s*[+-]?(?:NAN|INF(?:INITY)?)\b", code, re.IGNORECASE):
        raise ValueError("non-finite numeric word")
    residue = WORD_RE.sub(" ", code)
    residue = residue.replace("%", " ").replace("/", " ")
    if residue.strip():
        raise ValueError("unparsed executable text")
    if any(letter not in ALLOWED_WORDS for letter, _ in words):
        raise ValueError("unsupported address word")
    counts: dict[str, int] = {}
    for letter, _ in words:
        counts[letter] = counts.get(letter, 0) + 1
    if any(counts.get(axis, 0) > 1 for axis in "XYZABCUVWIJKRFSTH"):
        raise ValueError("duplicate word")


def parse_program(source: str) -> Program:
    program = Program()
    position: dict[str, float | None] = {"x": None, "y": None, "z": None}
    unit_scale: float | None = None
    units_locked = False
    absolute = True
    wcs: str | None = None
    pending_tool: int | None = None
    current_tool: int | None = None
    section_index: int | None = None
    modal_motion: int | None = None
    spindle_on = False
    spindle_speed: float | None = None
    feed: float | None = None
    length_comp = False
    length_offset: int | None = None

    for line_number, raw in enumerate(source.splitlines()):
        code, comments = split_line(raw)
        program.comments.extend((line_number, comment) for comment in comments)
        words = [(letter.upper(), float(value)) for letter, value in WORD_RE.findall(code)]
        validate_lexemes(code, words)
        if not words:
            continue

        if program.m30_line is not None:
            program.executable_after_m30 = True
            continue

        g_codes = integer_controls(words, "G")
        m_codes = integer_controls(words, "M")
        if any(value not in ALLOWED_G_CODES for value in g_codes):
            raise ValueError("unsupported G code")
        if any(value not in ALLOWED_M_CODES for value in m_codes):
            raise ValueError("unsupported M code")
        if 20 in g_codes and 21 in g_codes:
            raise ValueError("conflicting units")

        if 20 in g_codes or 21 in g_codes:
            selected = 20 if 20 in g_codes else 21
            scale = 25.4 if selected == 20 else 1.0
            if units_locked and unit_scale != scale:
                raise ValueError("unit switch after motion")
            unit_scale = scale
            program.units_seen.add(selected)
        if 90 in g_codes and 91 in g_codes:
            raise ValueError("conflicting distance modes")
        if 90 in g_codes:
            absolute = True
        if 91 in g_codes:
            absolute = False
        for value in g_codes:
            if 54 <= value <= 59:
                wcs = f"G{value}"

        for letter, value in words:
            if letter == "T":
                rounded = int(round(value))
                if abs(value - rounded) > 1.0e-9 or rounded <= 0:
                    raise ValueError("invalid tool")
                pending_tool = rounded
            if letter in "XYZ" or letter in ROTARY_AXES:
                program.axes_seen.add(letter)

        if 6 in m_codes:
            if pending_tool is None:
                raise ValueError("M6 without tool")
            if section_index is not None:
                program.sections[section_index].end_line = line_number - 1
            current_tool = pending_tool
            program.sections.append(Section(current_tool, line_number))
            section_index = len(program.sections) - 1
            spindle_on = False
            spindle_speed = None
            feed = None
            length_comp = False
            length_offset = None
            modal_motion = None

        if 3 in m_codes:
            spindle_on = True
            if section_index is not None:
                program.sections[section_index].has_m3 = True
        if 4 in m_codes:
            spindle_on = True
        if 5 in m_codes:
            spindle_on = False
        speeds = [value for letter, value in words if letter == "S"]
        if speeds:
            spindle_speed = speeds[-1]
            if not math.isfinite(spindle_speed) or spindle_speed <= 0:
                raise ValueError("invalid spindle speed")
            if section_index is not None:
                program.sections[section_index].has_positive_speed = True
        feeds = [value for letter, value in words if letter == "F"]
        if feeds:
            if unit_scale is None:
                raise ValueError("feed before units")
            feed = feeds[-1] * unit_scale
            if not math.isfinite(feed) or feed <= 0:
                raise ValueError("invalid feed")
            if section_index is not None:
                program.sections[section_index].has_positive_feed = True

        if 43 in g_codes:
            offsets = [value for letter, value in words if letter == "H"]
            if not offsets:
                raise ValueError("G43 without H")
            rounded = int(round(offsets[-1]))
            if abs(offsets[-1] - rounded) > 1.0e-9 or rounded <= 0:
                raise ValueError("invalid H offset")
            length_comp = True
            length_offset = rounded
            if section_index is not None:
                program.sections[section_index].has_g43 = True
        if 49 in g_codes:
            length_comp = False
            length_offset = None

        explicit_motion = next((value for value in g_codes if value in {0, 1, 2, 3}), None)
        if explicit_motion is not None:
            modal_motion = explicit_motion
        is_machine_return = 28 in g_codes or 53 in g_codes
        raw_axes = {
            letter.lower(): value
            for letter, value in words
            if letter in {"X", "Y", "Z"}
        }
        if raw_axes and unit_scale is None:
            raise ValueError("coordinate before units")
        if raw_axes and not is_machine_return:
            units_locked = True
            start = dict(position)
            explicit: dict[str, float] = {}
            for axis, value in raw_axes.items():
                scaled = value * float(unit_scale)
                if absolute or position[axis] is None:
                    target = scaled
                else:
                    target = float(position[axis]) + scaled
                if not math.isfinite(target):
                    raise ValueError("non-finite coordinate")
                position[axis] = target
                explicit[axis] = target
            if modal_motion is not None and current_tool is not None and section_index is not None:
                record = Record(
                    line=line_number,
                    section=section_index,
                    motion=modal_motion,
                    start=start,
                    end=dict(position),
                    explicit=explicit,
                    tool=current_tool,
                    wcs=wcs,
                    spindle_on=spindle_on,
                    spindle_speed=spindle_speed,
                    feed=feed,
                    length_comp=length_comp,
                    length_offset=length_offset,
                )
                program.sections[section_index].records.append(record)

        if 30 in m_codes:
            if program.m30_line is not None:
                raise ValueError("multiple M30")
            program.m30_line = line_number
            if section_index is not None:
                program.sections[section_index].end_line = line_number

    if section_index is not None and program.sections[section_index].end_line is None:
        program.sections[section_index].end_line = len(source.splitlines()) - 1
    for line_number, comment in program.comments:
        for section in program.sections:
            end = section.end_line if section.end_line is not None else line_number
            if section.start_line - 3 <= line_number <= end:
                section.comments.append(comment)
    return program


def xy_distance(record: Record) -> float:
    values = (record.start["x"], record.start["y"], record.end["x"], record.end["y"])
    if any(value is None for value in values):
        return 0.0
    return math.hypot(
        float(record.end["x"]) - float(record.start["x"]),
        float(record.end["y"]) - float(record.start["y"]),
    )


def cut_records(section: Section) -> list[Record]:
    return [
        record
        for record in section.records
        if record.motion in {1, 2, 3}
        and xy_distance(record) >= 0.01
        and record.end["z"] is not None
    ]


def correlation(left: list[float], right: list[float]) -> float:
    if len(left) < 3 or len(right) != len(left):
        return 0.0
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_energy = sum((x - left_mean) ** 2 for x in left)
    right_energy = sum((y - right_mean) ** 2 for y in right)
    if left_energy <= 1.0e-12 or right_energy <= 1.0e-12:
        return 0.0
    return numerator / math.sqrt(left_energy * right_energy)


def sphere_fit_residual(radii: list[float], zs: list[float]) -> float:
    # For a spherical offset surface, r^2 + (z-zc)^2 is constant.
    values = [radius * radius + z * z for radius, z in zip(radii, zs)]
    z_mean = sum(zs) / len(zs)
    value_mean = sum(values) / len(values)
    variance = sum((z - z_mean) ** 2 for z in zs)
    if variance <= 1.0e-9:
        return math.inf
    slope = sum((z - z_mean) * (value - value_mean) for z, value in zip(zs, values)) / variance
    center_z = slope / 2.0
    radius_squared = value_mean - slope * z_mean + center_z * center_z
    if radius_squared <= 1.0e-9:
        return math.inf
    residuals = [
        radius * radius + (z - center_z) ** 2 - radius_squared
        for radius, z in zip(radii, zs)
    ]
    rms = math.sqrt(sum(value * value for value in residuals) / len(residuals))
    return rms / radius_squared


def geometry(section_index: int, section: Section) -> Geometry | None:
    cuts = cut_records(section)
    if not cuts:
        return None
    points = [
        (float(record.end["x"]), float(record.end["y"]), float(record.end["z"]))
        for record in cuts
    ]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    zs = [point[2] for point in points]
    center = ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)
    spans = tuple(sorted((max(xs) - min(xs), max(ys) - min(ys)), reverse=True))
    radii = [math.hypot(x - center[0], y - center[1]) for x, y, _ in points]
    polar_zs = [z for radius, z in zip(radii, zs) if radius <= 1.0]

    cells: set[tuple[int, int]] = set()
    x_span = max(xs) - min(xs)
    y_span = max(ys) - min(ys)
    if x_span > 1.0e-9 and y_span > 1.0e-9:
        for x, y, _ in points:
            ix = min(3, int(4.0 * (x - min(xs)) / x_span))
            iy = min(3, int(4.0 * (y - min(ys)) / y_span))
            cells.add((ix, iy))
    max_radius = max(radii) if radii else 0.0
    angles = {
        int((math.atan2(y - center[1], x - center[0]) % (2.0 * math.pi)) / (2.0 * math.pi) * 12)
        for (x, y, _), radius in zip(points, radii)
        if radius >= max_radius * 0.65
    }
    levels = {round(z, 2) for z in zs}
    return Geometry(
        section=section_index,
        points=points,
        lengths=[xy_distance(record) for record in cuts],
        center=center,
        spans=(float(spans[0]), float(spans[1])),
        z_range=(min(zs), max(zs)),
        z_levels=len(levels),
        occupied_cells=len(cells),
        angular_bins=len(angles),
        radial_z_corr=correlation(zs, radii),
        sphere_residual=sphere_fit_residual(radii, zs),
        min_radius=min(radii),
        polar_points=len(polar_zs),
        polar_min_z=min(polar_zs) if polar_zs else None,
    )


def section_controls_valid(section: Section, cuts: list[Record]) -> bool:
    if not cuts:
        return False
    if not (section.has_m3 and section.has_g43 and section.has_positive_speed and section.has_positive_feed):
        return False
    if any(
        not record.spindle_on
        or record.spindle_speed is None
        or record.spindle_speed <= 0
        or record.feed is None
        or record.feed <= 0
        or not record.length_comp
        or record.length_offset is None
        or record.wcs is None
        for record in cuts
    ):
        return False
    return True


def section_safety_valid(section: Section, cuts: list[Record]) -> bool:
    if not cuts:
        return False
    max_cut_z = max(float(record.end["z"]) for record in cuts if record.end["z"] is not None)
    last_cut_line = max(record.line for record in cuts)

    for record in section.records:
        if record.motion != 0 or xy_distance(record) < 0.05:
            continue
        known_z = [value for value in (record.start["z"], record.end["z"]) if value is not None]
        if known_z and min(float(value) for value in known_z) < max_cut_z + 1.0:
            return False

    retracts = [
        record
        for record in section.records
        if record.line > last_cut_line
        and record.end["z"] is not None
        and record.start["z"] is not None
        and float(record.end["z"]) >= max_cut_z + 2.0
        and float(record.end["z"]) > float(record.start["z"]) + 1.0
    ]
    return bool(retracts)


def rough_candidate(value: Geometry) -> bool:
    long_span, short_span = value.spans
    z_span = value.z_range[1] - value.z_range[0]
    return (
        value.count >= 180
        and value.path_length >= 900.0
        and 48.0 <= long_span <= 85.0
        and 27.0 <= short_span <= 60.0
        and z_span >= 9.0
        and value.z_levels >= 5
        and value.occupied_cells >= 8
    )


def finish_candidate(value: Geometry, section: Section) -> bool:
    long_span, short_span = value.spans
    z_span = value.z_range[1] - value.z_range[0]
    comment_text = " ".join(section.comments)
    has_ball_hint = BALL_HINT.search(comment_text) is not None
    has_non_ball_hint = NON_BALL_HINT.search(comment_text) is not None
    return (
        has_ball_hint
        and not has_non_ball_hint
        and value.count >= 120
        and value.path_length >= 180.0
        and 12.0 <= short_span <= 30.0
        and 12.0 <= long_span <= 32.0
        and long_span / max(short_span, 1.0e-9) <= 1.3
        and z_span >= 3.8
        and value.z_levels >= 5
        and value.angular_bins >= 10
        and value.radial_z_corr >= 0.65
        and value.sphere_residual <= 0.14
        and value.min_radius <= 1.0
        and value.polar_points >= 3
        and value.polar_min_z is not None
        and value.polar_min_z <= value.z_range[0] + 0.35
    )


def program_valid(program: Program) -> bool:
    if program.m30_line is None or program.executable_after_m30:
        return False
    if len(program.units_seen) != 1:
        return False
    if program.axes_seen & ROTARY_AXES:
        return False
    if len(program.sections) < 2:
        return False

    geometries: dict[int, Geometry] = {}
    for index, section in enumerate(program.sections):
        value = geometry(index, section)
        if value is not None:
            geometries[index] = value

    roughs = [index for index, value in geometries.items() if rough_candidate(value)]
    finishes = [
        index
        for index, value in geometries.items()
        if finish_candidate(value, program.sections[index])
    ]
    if not roughs or not finishes:
        return False
    if min(finishes) < min(roughs):
        return False

    for rough_index in roughs:
        for finish_index in finishes:
            if finish_index <= rough_index:
                continue
            rough = geometries[rough_index]
            finish = geometries[finish_index]
            center_distance = math.hypot(
                rough.center[0] - finish.center[0],
                rough.center[1] - finish.center[1],
            )
            if center_distance > 4.0:
                continue
            rough_cuts = cut_records(program.sections[rough_index])
            finish_cuts = cut_records(program.sections[finish_index])
            if not section_controls_valid(program.sections[rough_index], rough_cuts):
                continue
            if not section_controls_valid(program.sections[finish_index], finish_cuts):
                continue
            if not section_safety_valid(program.sections[rough_index], rough_cuts):
                continue
            if not section_safety_valid(program.sections[finish_index], finish_cuts):
                continue
            rough_wcs = {record.wcs for record in rough_cuts}
            finish_wcs = {record.wcs for record in finish_cuts}
            if len(rough_wcs) != 1 or rough_wcs != finish_wcs:
                continue
            return True
    return False


def validate_nc(path: Path) -> bool:
    try:
        if not path.is_file() or path.stat().st_size < 1000:
            return False
        source = path.read_text(encoding="latin-1")
        return program_valid(parse_program(source))
    except (OSError, UnicodeError, ValueError, OverflowError):
        return False


def evaluate() -> bool:
    return validate_nc(TARGET / OUTPUT_NAME)


if __name__ == "__main__":
    print("True" if evaluate() else "False")
