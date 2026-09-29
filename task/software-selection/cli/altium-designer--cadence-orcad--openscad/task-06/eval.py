from __future__ import annotations

import csv
import json
import math
import os
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


DESKTOP = Path(os.environ.get("ENGIWORLD_DESKTOP", Path(__file__).resolve().parent))
RESULT_DIR = DESKTOP / "result"


def _xml_rows(root: ET.Element, path: str, key: str) -> dict[str, dict[str, str]]:
    rows = {}
    for element in root.findall(path):
        name = element.get(key)
        if not name or name in rows:
            raise ValueError(f"invalid or duplicate {key}")
        rows[name] = dict(element.attrib)
    return rows


def _nets(root: ET.Element) -> dict[str, tuple[dict[str, str], tuple[str, ...]]]:
    result = {}
    for net in root.findall("./Nets/Net"):
        name = net.get("name")
        if not name or name in result:
            raise ValueError("invalid or duplicate net")
        pins = tuple(sorted(pin.get("name", "") for pin in net.findall("./PinRef")))
        result[name] = (dict(net.attrib), pins)
    return result


def _components(root: ET.Element) -> dict[str, dict[str, str]]:
    return _xml_rows(root, "./Components/Component", "ref")


def _read_placement(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = ["Reference", "X_mm", "Y_mm", "Side", "Rotation"]
        if reader.fieldnames != required:
            raise ValueError("placement.csv header mismatch")
        rows = {}
        for row in reader:
            ref = row["Reference"].strip()
            if not ref or ref in rows:
                raise ValueError("invalid or duplicate placement row")
            rows[ref] = row
        return rows


def _same_static_board(source: ET.Element, placed: ET.Element) -> bool:
    if source.tag != placed.tag:
        return False
    if source.get("name") != placed.get("name") or source.get("version") != placed.get("version"):
        return False
    if [dict(x.attrib) for x in source.findall("./Stackup/Layer")] != [
        dict(x.attrib) for x in placed.findall("./Stackup/Layer")
    ]:
        return False
    if _nets(source) != _nets(placed):
        return False
    for path, key in (
        ("./Vias/Via", "id"),
        ("./Padstacks/Padstack", "name"),
        ("./DifferentialPairs/DifferentialPair", "name"),
        ("./Violations/Violation", "id"),
    ):
        if _xml_rows(source, path, key) != _xml_rows(placed, path, key):
            return False
    return True


def evaluate() -> bool:
    source_path = DESKTOP / "fulladd.ipc2581"
    output_path = DESKTOP / "result" / "fulladd_placed.ipc2581"
    csv_path = DESKTOP / "result" / "placement.csv"
    rules_path = DESKTOP / "placement_rules.json"
    if not all(path.is_file() for path in (source_path, output_path, csv_path, rules_path)):
        return False

    try:
        source = ET.parse(source_path).getroot()
        placed = ET.parse(output_path).getroot()
        rules = json.loads(rules_path.read_text(encoding="utf-8"))
        csv_rows = _read_placement(csv_path)
        source_components = _components(source)
        placed_components = _components(placed)
        if not _same_static_board(source, placed):
            return False
    except (OSError, ValueError, ET.ParseError, json.JSONDecodeError):
        return False

    if set(source_components) != set(placed_components) or set(csv_rows) != set(placed_components):
        return False

    try:
        grid = float(rules["grid_mm"])
        keepout = float(rules["keepout_mm"])
        strategy = str(rules["strategy"])
    except (KeyError, TypeError, ValueError):
        return False
    if not math.isfinite(grid) or grid <= 0 or not math.isfinite(keepout) or keepout < 0:
        return False
    if strategy != "compact_top_side":
        return False

    positions = {}
    original_positions = {}
    moved = False
    for ref, component in placed_components.items():
        original = source_components[ref]
        if component.get("footprint") != original.get("footprint"):
            return False
        if component.get("side") != "TOP":
            return False
        try:
            x = float(component["x"])
            y = float(component["y"])
            rotation = float(component["rotation"])
            csv_x = float(csv_rows[ref]["X_mm"])
            csv_y = float(csv_rows[ref]["Y_mm"])
            csv_rotation = float(csv_rows[ref]["Rotation"])
            original_x = float(original["x"])
            original_y = float(original["y"])
        except (KeyError, TypeError, ValueError):
            return False
        if not all(
            math.isfinite(value)
            for value in (x, y, rotation, csv_x, csv_y, csv_rotation, original_x, original_y)
        ):
            return False
        if abs(x / grid - round(x / grid)) > 1e-6 or abs(y / grid - round(y / grid)) > 1e-6:
            return False
        if csv_rows[ref]["Side"].strip() != component["side"]:
            return False
        if max(abs(csv_x - x), abs(csv_y - y), abs(csv_rotation - rotation)) > 1e-6:
            return False
        if abs(x - original_x) > 1e-6 or abs(y - original_y) > 1e-6:
            moved = True
        positions[ref] = (x, y)
        original_positions[ref] = (original_x, original_y)

    if not moved:
        return False
    refs = sorted(positions)
    for index, first in enumerate(refs):
        for second in refs[index + 1 :]:
            if math.dist(positions[first], positions[second]) + 1e-9 < keepout:
                return False

    def bounding_box_area(points: dict[str, tuple[float, float]]) -> float:
        xs = [point[0] for point in points.values()]
        ys = [point[1] for point in points.values()]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))

    source_area = bounding_box_area(original_positions)
    placed_area = bounding_box_area(positions)
    return source_area > 0 and placed_area + 1e-9 < source_area


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
