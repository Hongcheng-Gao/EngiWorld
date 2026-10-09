from __future__ import annotations

import math
import re
from collections import defaultdict
from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
STEP_NAME = "cli_040_ap242_quality_out.step"
REPORT_NAME = "cli_040_quality_report.txt"
TOL = 0.08

PART_BBOXES = [
    (-25.0, 25.0, -20.0, 20.0, 0.0, 20.0),
    (35.0, 75.0, -17.5, 17.5, 0.0, 18.0),
    (85.0, 115.0, -12.5, 12.5, 0.0, 16.0),
    (121.0, 149.0, -11.0, 11.0, 0.0, 14.0),
    (156.0, 180.0, -10.0, 10.0, 0.0, 12.0),
    (187.0, 207.0, -8.0, 8.0, 0.0, 10.0),
]
ASSEMBLY_BBOX = (-25.0, 207.0, -20.0, 20.0, 0.0, 20.0)

ENTITY_RE = re.compile(r"^\s*#(\d+)\s*=\s*(.+)\s*$", re.DOTALL)
REF_RE = re.compile(r"#(\d+)")
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"


def split_part21(text: str) -> list[str]:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    statements: list[str] = []
    current: list[str] = []
    quoted = False
    index = 0
    while index < len(text):
        char = text[index]
        current.append(char)
        if char == "'":
            if quoted and index + 1 < len(text) and text[index + 1] == "'":
                current.append(text[index + 1])
                index += 1
            else:
                quoted = not quoted
        elif char == ";" and not quoted:
            statement = "".join(current[:-1]).strip()
            if statement:
                statements.append(statement)
            current = []
        index += 1
    if quoted or "".join(current).strip():
        raise ValueError("unterminated STEP statement")
    return statements


def parse_part21(path: Path):
    if not path.is_file() or path.stat().st_size < 4096:
        raise ValueError("missing or implausibly small STEP file")
    text = path.read_text(encoding="utf-8", errors="strict")
    statements = split_part21(text)
    entities: dict[int, str] = {}
    header: list[str] = []
    for statement in statements:
        match = ENTITY_RE.match(statement)
        if match:
            entity_id = int(match.group(1))
            if entity_id in entities:
                raise ValueError("duplicate entity id")
            entities[entity_id] = match.group(2).strip()
        else:
            header.append(statement)
    if not entities:
        raise ValueError("STEP has no entities")
    return entities, header


def refs(body: str) -> list[int]:
    return [int(value) for value in REF_RE.findall(body)]


def has_type(body: str, entity_type: str) -> bool:
    return re.search(rf"(?<![A-Z0-9_]){re.escape(entity_type)}\s*\(", body.upper()) is not None


def check_schema(header: list[str]) -> bool:
    schemas = [item.upper() for item in header if item.upper().startswith("FILE_SCHEMA")]
    return (
        len(schemas) == 1
        and "AP242" in schemas[0]
        and "AUTOMOTIVE_DESIGN" not in schemas[0]
        and "CONFIG_CONTROL_DESIGN" not in schemas[0]
    )


def check_millimeter_contexts(entities: dict[int, str]) -> bool:
    contexts = {
        entity_id: body
        for entity_id, body in entities.items()
        if has_type(body, "GEOMETRIC_REPRESENTATION_CONTEXT")
        and has_type(body, "GLOBAL_UNIT_ASSIGNED_CONTEXT")
    }
    if not contexts:
        return False
    millimeter = re.compile(
        r"SI_UNIT\s*\(\s*\.MILLI\.\s*,\s*\.METRE\.\s*\)", re.IGNORECASE
    )
    for context in contexts.values():
        match = re.search(
            r"GLOBAL_UNIT_ASSIGNED_CONTEXT\s*\(\s*\(([^)]*)\)\s*\)",
            context,
            re.IGNORECASE,
        )
        if not match:
            return False
        unit_ids = [int(value) for value in REF_RE.findall(match.group(1))]
        length_units = [
            entities.get(unit_id, "")
            for unit_id in unit_ids
            if has_type(entities.get(unit_id, ""), "LENGTH_UNIT")
        ]
        if len(length_units) != 1 or not millimeter.search(length_units[0]):
            return False
    used_contexts = set()
    for body in entities.values():
        if has_type(body, "SHAPE_REPRESENTATION"):
            linked = refs(body)
            if not linked:
                return False
            used_contexts.add(linked[-1])
    return bool(used_contexts) and used_contexts <= set(contexts)


def check_references(entities: dict[int, str]) -> bool:
    defined = set(entities)
    return all(set(refs(body)) <= defined for body in entities.values())


def load_solids(path: Path):
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 6 or any(not solid.isValid() for solid in solids):
        raise ValueError("expected six valid solids")
    return solids


def bbox_tuple(solid):
    box = solid.BoundingBox()
    return (box.xmin, box.xmax, box.ymin, box.ymax, box.zmin, box.zmax)


def close_tuple(actual, expected, tolerance=TOL) -> bool:
    return len(actual) == len(expected) and all(
        abs(float(a) - float(e)) <= tolerance for a, e in zip(actual, expected)
    )


def check_geometry(solids) -> bool:
    unmatched = list(solids)
    for expected in PART_BBOXES:
        match = next(
            (solid for solid in unmatched if close_tuple(bbox_tuple(solid), expected)),
            None,
        )
        if match is None:
            return False
        dx = expected[1] - expected[0]
        dy = expected[3] - expected[2]
        dz = expected[5] - expected[4]
        if abs(float(match.Volume()) - dx * dy * dz) > 1.0:
            return False
        if len(match.Faces()) != 6:
            return False
        unmatched.remove(match)
    return not unmatched


def shape_product_map(entities: dict[int, str], solid_ids: set[int]) -> dict[int, int]:
    advanced_to_solids: dict[int, set[int]] = {}
    for entity_id, body in entities.items():
        if has_type(body, "ADVANCED_BREP_SHAPE_REPRESENTATION"):
            linked = set(refs(body)) & solid_ids
            if linked:
                advanced_to_solids[entity_id] = linked

    shape_to_solids: dict[int, set[int]] = defaultdict(set)
    for body in entities.values():
        if not has_type(body, "SHAPE_REPRESENTATION_RELATIONSHIP"):
            continue
        linked = refs(body)
        advanced = [value for value in linked if value in advanced_to_solids]
        shapes = [
            value
            for value in linked
            if value in entities
            and has_type(entities[value], "SHAPE_REPRESENTATION")
            and not has_type(entities[value], "SHAPE_REPRESENTATION_RELATIONSHIP")
            and value not in advanced_to_solids
        ]
        for advanced_id in advanced:
            for shape_id in shapes:
                shape_to_solids[shape_id].update(advanced_to_solids[advanced_id])

    pds_to_product: dict[int, int] = {}
    for entity_id, body in entities.items():
        if has_type(body, "PRODUCT_DEFINITION_SHAPE"):
            linked = refs(body)
            product_defs = [
                value
                for value in linked
                if value in entities and has_type(entities[value], "PRODUCT_DEFINITION")
            ]
            if len(product_defs) == 1:
                pds_to_product[entity_id] = product_defs[0]

    result: dict[int, int] = {}
    for body in entities.values():
        if not has_type(body, "SHAPE_DEFINITION_REPRESENTATION"):
            continue
        linked = refs(body)
        pds = [value for value in linked if value in pds_to_product]
        shapes = [value for value in linked if value in shape_to_solids]
        if len(pds) != 1 or len(shapes) != 1:
            continue
        product_def = pds_to_product[pds[0]]
        for solid_id in shape_to_solids[shapes[0]]:
            if solid_id in result and result[solid_id] != product_def:
                raise ValueError("solid mapped to multiple product definitions")
            result[solid_id] = product_def
    return result


def check_assembly(entities: dict[int, str], solid_ids: set[int]) -> bool:
    if len(solid_ids) != 6:
        return False
    solid_products = shape_product_map(entities, solid_ids)
    if set(solid_products) != solid_ids or len(set(solid_products.values())) != 6:
        return False

    edges: set[tuple[int, int]] = set()
    for body in entities.values():
        if has_type(body, "NEXT_ASSEMBLY_USAGE_OCCURRENCE"):
            linked = refs(body)
            if len(linked) >= 2:
                edges.add((linked[-2], linked[-1]))
    part_products = set(solid_products.values())
    children = {child for _, child in edges}
    if not part_products <= children:
        return False
    if any(parent in part_products for parent, _ in edges):
        return False

    parents = {parent for parent, _ in edges}
    roots = parents - children
    adjacency: dict[int, set[int]] = defaultdict(set)
    for parent, child in edges:
        adjacency[parent].add(child)

    def reachable(root: int) -> set[int]:
        seen: set[int] = set()
        stack = [root]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(adjacency.get(current, ()))
        return seen

    return any(part_products <= reachable(root) for root in roots)


def color_entities(entities: dict[int, str]) -> dict[int, tuple[float, float, float]]:
    pattern = re.compile(
        rf"COLOUR_RGB\s*\(\s*'(?:''|[^'])*'\s*,\s*({NUMBER})\s*,\s*({NUMBER})\s*,\s*({NUMBER})\s*\)",
        re.IGNORECASE,
    )
    result = {}
    for entity_id, body in entities.items():
        match = pattern.search(body)
        if match:
            color = tuple(float(match.group(index)) for index in range(1, 4))
            if not all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in color):
                raise ValueError("invalid RGB value")
            result[entity_id] = color
    return result


def descendants(start: int, entities: dict[int, str]) -> set[int]:
    seen: set[int] = set()
    stack = [start]
    while stack:
        current = stack.pop()
        if current in seen or current not in entities:
            continue
        seen.add(current)
        stack.extend(refs(entities[current]))
    return seen


def check_colors(entities: dict[int, str], solid_ids: set[int]) -> bool:
    colors = color_entities(entities)
    if len(colors) < 6:
        return False

    style_pattern = re.compile(
        r"(?:CONTEXT_DEPENDENT_OVER_RIDING_)?STYLED_ITEM\s*\(\s*'(?:''|[^'])*'\s*,\s*\(([^)]*)\)\s*,\s*#(\d+)",
        re.IGNORECASE,
    )
    target_colors: dict[int, set[tuple[float, float, float]]] = defaultdict(set)
    for body in entities.values():
        match = style_pattern.search(body)
        if not match:
            continue
        style_ids = [int(value) for value in REF_RE.findall(match.group(1))]
        target = int(match.group(2))
        for style_id in style_ids:
            for linked in descendants(style_id, entities):
                if linked in colors:
                    target_colors[target].add(tuple(round(value, 5) for value in colors[linked]))

    signatures: list[frozenset[tuple[float, float, float]]] = []
    for solid_id in solid_ids:
        geometry = descendants(solid_id, entities)
        associated: set[tuple[float, float, float]] = set()
        for target, linked_colors in target_colors.items():
            if target in geometry:
                associated.update(linked_colors)
        if not associated:
            return False
        signatures.append(frozenset(associated))
    return len(set(signatures)) == 6 and len(set().union(*signatures)) >= 6


def parse_bbox_lines(text: str, label: str) -> list[tuple[float, ...]]:
    pattern = re.compile(
        rf"(?im)^\s*{label}\s*[:=]\s*((?:{NUMBER})(?:\s*[,\s]\s*(?:{NUMBER})){{5}})\s*$"
    )
    rows = []
    for match in pattern.finditer(text):
        values = tuple(float(value) for value in re.findall(NUMBER, match.group(1)))
        if len(values) == 6 and all(math.isfinite(value) for value in values):
            rows.append(values)
    return rows


def check_report(path: Path, solids) -> bool:
    if not path.is_file() or not 0 < path.stat().st_size <= 100_000:
        return False
    text = path.read_text(encoding="utf-8", errors="strict")
    if not re.search(r"(?im)^\s*(?:solid|part)[ _-]?count\s*[:=]\s*6\s*$", text):
        return False
    if not re.search(r"(?im)^\s*units?\s*[:=]\s*(?:millimet(?:er|re)s?|mm)\s*$", text):
        return False
    if not re.search(r"(?im)^\s*(?:step[ _-]?)?schema\s*[:=]\s*AP242\s*$", text):
        return False

    reported = parse_bbox_lines(text, r"part[_ -]?\d+(?:[_ -]?bbox)")
    actual = [bbox_tuple(solid) for solid in solids]
    if len(reported) != 6:
        return False
    unmatched = list(actual)
    for row in reported:
        match = next((box for box in unmatched if close_tuple(row, box, 0.1)), None)
        if match is None:
            return False
        unmatched.remove(match)
    if unmatched:
        return False
    assembly = parse_bbox_lines(text, r"assembly[_ -]?bbox")
    return len(assembly) == 1 and close_tuple(assembly[0], ASSEMBLY_BBOX, 0.1)


def evaluate() -> bool:
    step_path = OUTPUT_ROOT / STEP_NAME
    report_path = OUTPUT_ROOT / REPORT_NAME
    entities, header = parse_part21(step_path)
    if (
        not check_schema(header)
        or not check_references(entities)
        or not check_millimeter_contexts(entities)
    ):
        return False
    solid_ids = {
        entity_id
        for entity_id, body in entities.items()
        if has_type(body, "MANIFOLD_SOLID_BREP")
    }
    if not check_assembly(entities, solid_ids) or not check_colors(entities, solid_ids):
        return False
    solids = load_solids(step_path)
    return check_geometry(solids) and check_report(report_path, solids)


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
