from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")
KICAD_CLI = Path(os.environ.get("KICAD_CLI", "/usr/bin/kicad-cli"))
EXPECTED_SCHEMATIC_VERSION = "20260306"
EXPECTED_KICAD_VERSION = "10.0.2-10.0.2~ubuntu24.04.1"
EXPECTED_SOURCE_SEMANTIC_SHA256 = "faf6fb84a45fc52b2d5aa22a4dfac0260f841f319aede360cc8f1da384eec986"
EXPECTED_SECTION_COUNTS = {"buck": 24, "ldo": 15, "load": 56}
EXPECTED_NET_SIZES = {
    "GND": 71,
    "VBUCK": 24,
    "VLDO": 17,
    "VIN": 6,
    "SW": 3,
    "COMP": 3,
    "BOOT": 2,
    "FB": 2,
    "LED_A": 2,
    "EN": 1,
    "LDO_EN": 1,
    "LOAD_1_OUT": 3,
    "LOAD_2_OUT": 3,
    "LOAD_3_OUT": 3,
    "LOAD_4_OUT": 3,
    "3V3_LOAD_1_OUT": 3,
    "3V3_LOAD_2_OUT": 3,
    "3V3_LOAD_3_OUT": 3,
    "3V3_LOAD_4_OUT": 3,
}
CHILD_CONTRACTS = {
    "buck.kicad_sch": {"VBUCK": "output", "GND": "bidirectional"},
    "ldo.kicad_sch": {"VBUCK": "input", "VLDO": "output", "GND": "bidirectional"},
    "load.kicad_sch": {"VBUCK": "input", "VLDO": "input", "GND": "bidirectional"},
}
KNOWN_LIBRARY_IDS = {"Device:R", "Device:C", "Device:L", "Device:D", "Device:LED"}
UNKNOWN_LIBRARY_IDS = {
    "Benchmark:MOSFET_GSD_Abstract",
    "Benchmark:Connector_02_Abstract",
    "Benchmark:IC_06_Abstract",
    "Benchmark:IC_04_Abstract",
}
FORBIDDEN_DESKTOP_SCRIPT_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".vbs", ".js", ".mjs", ".ts", ".rb", ".lua", ".tcl",
}


class ValidationError(ValueError):
    pass


def _parse_sexp(text: str):
    roots = []
    stack = []
    index = 0
    length = len(text)

    def append(value):
        if stack:
            stack[-1].append(value)
        else:
            roots.append(value)

    while index < length:
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if char == ";":
            newline = text.find("\n", index)
            index = length if newline < 0 else newline + 1
            continue
        if char == "(":
            node = []
            append(node)
            stack.append(node)
            index += 1
            continue
        if char == ")":
            if not stack:
                raise ValidationError("unexpected closing parenthesis")
            stack.pop()
            index += 1
            continue
        if char == '"':
            index += 1
            value = []
            while index < length:
                char = text[index]
                if char == '"':
                    index += 1
                    break
                if char == "\\":
                    index += 1
                    if index >= length:
                        raise ValidationError("unterminated escape")
                    escaped = text[index]
                    value.append({"n": "\n", "r": "\r", "t": "\t"}.get(escaped, escaped))
                    index += 1
                    continue
                value.append(char)
                index += 1
            else:
                raise ValidationError("unterminated string")
            append("".join(value))
            continue

        start = index
        while index < length and not text[index].isspace() and text[index] not in "();":
            index += 1
        if start == index:
            raise ValidationError("invalid token")
        append(text[start:index])

    if stack:
        raise ValidationError("unterminated list")
    if len(roots) != 1 or not isinstance(roots[0], list):
        raise ValidationError("expected exactly one root expression")
    return roots[0]


def _head(node):
    return node[0] if isinstance(node, list) and node else None


def _direct(node, name: str):
    return [child for child in node[1:] if isinstance(child, list) and child and child[0] == name]


def _single_node(node, name: str):
    matches = _direct(node, name)
    if len(matches) != 1:
        raise ValidationError(f"expected one {name} node")
    return matches[0]


def _single_value(node, name: str):
    match = _single_node(node, name)
    if len(match) < 2 or isinstance(match[1], list):
        raise ValidationError(f"invalid {name} value")
    return str(match[1])


def _optional_value(node, name: str, default: str = ""):
    matches = _direct(node, name)
    if not matches:
        return default
    if len(matches) != 1 or len(matches[0]) < 2 or isinstance(matches[0][1], list):
        raise ValidationError(f"invalid {name} value")
    return str(matches[0][1])


def _numbers(node, name: str, minimum: int = 2):
    match = _single_node(node, name)
    raw = []
    for item in match[1:]:
        if isinstance(item, list):
            break
        raw.append(item)
    if len(raw) < minimum:
        raise ValidationError(f"invalid {name} coordinates")
    try:
        return tuple(float(item) for item in raw)
    except ValueError as exc:
        raise ValidationError(f"non-numeric {name}") from exc


def _properties(node):
    result = {}
    for prop in _direct(node, "property"):
        if len(prop) < 3 or isinstance(prop[1], list) or isinstance(prop[2], list):
            raise ValidationError("invalid property")
        name, value = str(prop[1]), str(prop[2])
        if name in result:
            raise ValidationError(f"duplicate property {name}")
        result[name] = value
    return result


def _read_schematic(path: Path):
    if not path.is_file() or path.stat().st_size < 500:
        raise ValidationError(f"missing or empty {path.name}")
    root = _parse_sexp(path.read_text(encoding="utf-8"))
    if _head(root) != "kicad_sch":
        raise ValidationError(f"{path.name} is not a KiCad schematic")
    if _single_value(root, "version") != EXPECTED_SCHEMATIC_VERSION:
        raise ValidationError(f"{path.name} is not in the KiCad 10.0.2 format")
    if _single_value(root, "generator") != "eeschema":
        raise ValidationError(f"{path.name} has the wrong generator")
    if _single_value(root, "generator_version") != "10.0":
        raise ValidationError(f"{path.name} has the wrong generator version")
    instances = _single_node(root, "sheet_instances")
    if not _direct(instances, "path"):
        raise ValidationError(f"{path.name} has no sheet instance path")
    return root


def _placed_symbols(root):
    result = {}
    for node in _direct(root, "symbol"):
        props = _properties(node)
        reference = props.get("Reference")
        if not reference:
            raise ValidationError("placed symbol without Reference")
        if reference in result:
            raise ValidationError(f"duplicate reference {reference}")
        if len(_direct(node, "instances")) != 1:
            raise ValidationError(f"{reference} has no native instance metadata")
        pin_numbers = []
        for pin in _direct(node, "pin"):
            if len(pin) < 2 or isinstance(pin[1], list):
                raise ValidationError(f"invalid pin instance on {reference}")
            pin_numbers.append(str(pin[1]))
        if len(pin_numbers) != len(set(pin_numbers)) or not pin_numbers:
            raise ValidationError(f"invalid pin set on {reference}")
        result[reference] = {
            "node": node,
            "lib_id": _single_value(node, "lib_id"),
            "unit": _single_value(node, "unit"),
            "body_style": _single_value(node, "body_style"),
            "exclude_from_sim": _single_value(node, "exclude_from_sim"),
            "in_bom": _single_value(node, "in_bom"),
            "on_board": _single_value(node, "on_board"),
            "in_pos_files": _single_value(node, "in_pos_files"),
            "dnp": _single_value(node, "dnp"),
            "pins": tuple(sorted(pin_numbers)),
            "properties": props,
        }
    return result


def _symbol_semantic(symbol):
    return {
        key: value
        for key, value in symbol.items()
        if key != "node"
    }


def _library_definitions(root):
    library = _single_node(root, "lib_symbols")
    result = {}
    for node in _direct(library, "symbol"):
        if len(node) < 2 or isinstance(node[1], list):
            raise ValidationError("invalid embedded library symbol")
        lib_id = str(node[1])
        if lib_id in result:
            raise ValidationError(f"duplicate embedded library symbol {lib_id}")
        result[lib_id] = node
    return result


def _walk(node):
    if not isinstance(node, list):
        return
    yield node
    for child in node[1:]:
        if isinstance(child, list):
            yield from _walk(child)


def _library_semantic(node):
    pins = []
    graphics = Counter()
    graphic_heads = {"arc", "bezier", "circle", "polyline", "rectangle", "text", "text_box"}
    for descendant in _walk(node):
        kind = _head(descendant)
        if kind in graphic_heads:
            graphics[kind] += 1
        if kind != "pin":
            continue
        if len(descendant) < 3 or isinstance(descendant[1], list):
            raise ValidationError("invalid library pin")
        at = _numbers(descendant, "at")
        name_node = _single_node(descendant, "name")
        number_node = _single_node(descendant, "number")
        if len(name_node) < 2 or len(number_node) < 2:
            raise ValidationError("library pin lacks name or number")
        pins.append(
            (
                str(number_node[1]), str(name_node[1]), str(descendant[1]),
                tuple(round(value, 6) for value in at[:3]),
            )
        )
    if not pins or not graphics:
        raise ValidationError("embedded symbol lacks real pins or graphics")
    return {"pins": sorted(pins), "graphics": dict(sorted(graphics.items()))}


def _validate_embedded_libraries(root, symbols, source_semantics=None):
    definitions = _library_definitions(root)
    used_ids = {symbol["lib_id"] for symbol in symbols.values()}
    observed = {}
    for lib_id in used_ids:
        if lib_id not in definitions:
            raise ValidationError(f"missing embedded definition {lib_id}")
        observed[lib_id] = _library_semantic(definitions[lib_id])
    if source_semantics is not None:
        for lib_id, semantic in observed.items():
            if source_semantics.get(lib_id) != semantic:
                raise ValidationError(f"changed embedded symbol definition {lib_id}")
    return observed


def _source_payload(symbols, libraries, no_connect_count):
    data = {
        "symbols": {reference: _symbol_semantic(symbols[reference]) for reference in sorted(symbols)},
        "libraries": {lib_id: libraries[lib_id] for lib_id in sorted(libraries)},
        "no_connect_count": no_connect_count,
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _validate_source(root):
    if _direct(root, "sheet"):
        raise ValidationError("flat source contains child sheets")
    symbols = _placed_symbols(root)
    if len(symbols) != 95:
        raise ValidationError("flat source must contain exactly 95 symbols")
    sections = Counter(symbol["properties"].get("Section") for symbol in symbols.values())
    if dict(sections) != EXPECTED_SECTION_COUNTS:
        raise ValidationError("wrong flat source Section counts")

    scopes = Counter(symbol["properties"].get("ConnectivityScope") for symbol in symbols.values())
    if scopes != Counter({"specified_by_source": 78, "unspecified_by_source": 17}):
        raise ValidationError("wrong connectivity-scope counts")
    unknown_pin_count = 0
    for reference, symbol in symbols.items():
        scope = symbol["properties"].get("ConnectivityScope")
        lib_id = symbol["lib_id"]
        if scope == "specified_by_source":
            if lib_id not in KNOWN_LIBRARY_IDS or symbol["pins"] != ("1", "2"):
                raise ValidationError(f"invalid source-defined symbol {reference}")
        else:
            if lib_id not in UNKNOWN_LIBRARY_IDS:
                raise ValidationError(f"unknown device {reference} is not explicitly abstract")
            unknown_pin_count += len(symbol["pins"])
    if unknown_pin_count != 58 or len(_direct(root, "no_connect")) != 58:
        raise ValidationError("unknown devices must have exactly 58 no-connect pins")

    libraries = _validate_embedded_libraries(root, symbols)
    payload_hash = hashlib.sha256(_source_payload(symbols, libraries, 58)).hexdigest()
    if payload_hash != EXPECTED_SOURCE_SEMANTIC_SHA256:
        raise ValidationError("flat source semantic manifest changed")
    return symbols, libraries


def _hierarchical_labels(root):
    result = {}
    for label in _direct(root, "hierarchical_label"):
        if len(label) < 2 or isinstance(label[1], list):
            raise ValidationError("invalid hierarchical label")
        name = str(label[1])
        if name in result:
            raise ValidationError(f"duplicate hierarchical label {name}")
        result[name] = _single_value(label, "shape")
    return result


def _validate_children(roots, source_symbols, source_libraries):
    all_references = []
    for filename, contract in CHILD_CONTRACTS.items():
        root = roots[filename]
        if _direct(root, "sheet"):
            raise ValidationError(f"{filename} contains nested sheets")
        symbols = _placed_symbols(root)
        section = filename.split(".", 1)[0]
        expected_refs = {
            reference
            for reference, source in source_symbols.items()
            if source["properties"]["Section"] == section
        }
        if set(symbols) != expected_refs:
            raise ValidationError(f"wrong reference partition in {filename}")
        for reference, symbol in symbols.items():
            if _symbol_semantic(symbol) != _symbol_semantic(source_symbols[reference]):
                raise ValidationError(f"changed symbol {reference} in {filename}")
        _validate_embedded_libraries(root, symbols, source_libraries)
        if _hierarchical_labels(root) != contract:
            raise ValidationError(f"wrong hierarchical ports in {filename}")
        expected_no_connects = sum(
            len(symbol["pins"])
            for symbol in symbols.values()
            if symbol["properties"]["ConnectivityScope"] == "unspecified_by_source"
        )
        if len(_direct(root, "no_connect")) != expected_no_connects:
            raise ValidationError(f"wrong no-connect count in {filename}")
        all_references.extend(symbols)
    if Counter(all_references) != Counter(source_symbols.keys()):
        raise ValidationError("child symbol union does not equal the flat source")


def _sheet_data(root):
    result = {}
    for sheet in _direct(root, "sheet"):
        properties = _properties(sheet)
        filename = properties.get("Sheetfile")
        if not filename or filename in result:
            raise ValidationError("invalid or duplicate Sheetfile")
        pins = {}
        for pin in _direct(sheet, "pin"):
            if len(pin) < 3 or isinstance(pin[1], list) or isinstance(pin[2], list):
                raise ValidationError("invalid sheet pin")
            name = str(pin[1])
            if name in pins:
                raise ValidationError(f"duplicate sheet pin {name}")
            pins[name] = {"type": str(pin[2]), "point": _numbers(pin, "at")[:2]}
        result[filename] = {"pins": pins, "sheet": sheet}
    return result


def _point_on_segment(point, segment, tolerance=1e-6):
    (px, py), ((ax, ay), (bx, by)) = point, segment
    cross = (px - ax) * (by - ay) - (py - ay) * (bx - ax)
    if abs(cross) > tolerance:
        return False
    return (
        min(ax, bx) - tolerance <= px <= max(ax, bx) + tolerance
        and min(ay, by) - tolerance <= py <= max(ay, by) + tolerance
    )


class _UnionFind:
    def __init__(self, size):
        self.parent = list(range(size))

    def find(self, item):
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left, right):
        left, right = self.find(left), self.find(right)
        if left != right:
            self.parent[right] = left


def _wire_segments(root):
    result = []
    for wire in _direct(root, "wire"):
        pts = _single_node(wire, "pts")
        points = []
        for child in pts[1:]:
            if isinstance(child, list) and _head(child) == "xy":
                if len(child) != 3:
                    raise ValidationError("invalid wire point")
                points.append((float(child[1]), float(child[2])))
        if len(points) != 2 or points[0] == points[1]:
            raise ValidationError("each wire must have exactly two distinct endpoints")
        result.append((points[0], points[1]))
    if not result:
        raise ValidationError("top schematic contains no wires")
    return result


def _validate_top_wire_graph(root, sheets):
    segments = _wire_segments(root)
    union = _UnionFind(len(segments))
    junctions = [_numbers(node, "at")[:2] for node in _direct(root, "junction")]
    for left in range(len(segments)):
        for right in range(left + 1, len(segments)):
            endpoints_connect = any(
                _point_on_segment(point, segments[right])
                for point in segments[left]
            ) or any(
                _point_on_segment(point, segments[left])
                for point in segments[right]
            )
            junction_connects = any(
                _point_on_segment(point, segments[left]) and _point_on_segment(point, segments[right])
                for point in junctions
            )
            if endpoints_connect or junction_connects:
                union.union(left, right)

    expected_groups = [
        frozenset({("buck.kicad_sch", "VBUCK"), ("ldo.kicad_sch", "VBUCK"), ("load.kicad_sch", "VBUCK")}),
        frozenset({("ldo.kicad_sch", "VLDO"), ("load.kicad_sch", "VLDO")}),
        frozenset({("buck.kicad_sch", "GND"), ("ldo.kicad_sch", "GND"), ("load.kicad_sch", "GND")}),
    ]
    component_pins = defaultdict(set)
    for filename, sheet in sheets.items():
        for name, pin in sheet["pins"].items():
            touching = [index for index, segment in enumerate(segments) if _point_on_segment(pin["point"], segment)]
            if not touching:
                raise ValidationError(f"unconnected top sheet pin {filename}:{name}")
            base = touching[0]
            for other in touching[1:]:
                union.union(base, other)
            component_pins[union.find(base)].add((filename, name))

    normalized = defaultdict(set)
    for component, pins in component_pins.items():
        normalized[union.find(component)].update(pins)
    actual_groups = {frozenset(pins) for pins in normalized.values()}
    if actual_groups != set(expected_groups):
        raise ValidationError("VBUCK, VLDO, and GND top-level connectivity is wrong")
    wire_components = {union.find(index) for index in range(len(segments))}
    if wire_components != set(normalized):
        raise ValidationError("top contains dangling wire components")


def _validate_top(root):
    if _direct(root, "symbol"):
        raise ValidationError("top contains ordinary components")
    if _direct(root, "hierarchical_label"):
        raise ValidationError("top contains child-style hierarchical labels")
    sheets = _sheet_data(root)
    if set(sheets) != set(CHILD_CONTRACTS):
        raise ValidationError("top must reference exactly the three required child files")
    for filename, contract in CHILD_CONTRACTS.items():
        observed = {name: data["type"] for name, data in sheets[filename]["pins"].items()}
        if observed != contract:
            raise ValidationError(f"wrong sheet pin contract for {filename}")
    _validate_top_wire_graph(root, sheets)


def _declared_endpoint_nets(source_symbols):
    result = {}
    for reference, symbol in source_symbols.items():
        props = symbol["properties"]
        if props["ConnectivityScope"] != "specified_by_source":
            continue
        if symbol["lib_id"] in {"Device:D", "Device:LED"}:
            mapping = {"1": props.get("NetK"), "2": props.get("NetA")}
        else:
            mapping = {"1": props.get("Net1"), "2": props.get("Net2")}
        if not all(mapping.values()):
            raise ValidationError(f"missing source net metadata on {reference}")
        for pin, net in mapping.items():
            result[(reference, pin)] = net
    if len(result) != 156 or Counter(result.values()) != Counter(EXPECTED_NET_SIZES):
        raise ValidationError("wrong declared source endpoint network sizes")
    return result


def _read_netlist(path: Path):
    root = _parse_sexp(path.read_text(encoding="utf-8"))
    if _head(root) != "export":
        raise ValidationError("not a KiCad s-expression netlist")
    components_node = _single_node(root, "components")
    references = []
    for component in _direct(components_node, "comp"):
        references.append(_single_value(component, "ref"))
    if len(references) != len(set(references)):
        raise ValidationError("duplicate component in native netlist")
    pin_map = {}
    for net in _direct(_single_node(root, "nets"), "net"):
        name = _single_value(net, "name")
        for node in _direct(net, "node"):
            endpoint = (_single_value(node, "ref"), _single_value(node, "pin"))
            if endpoint in pin_map:
                raise ValidationError("endpoint appears in multiple native nets")
            pin_map[endpoint] = name
    return set(references), pin_map


def _partition(pin_map, endpoints):
    groups = defaultdict(set)
    for endpoint in endpoints:
        if endpoint not in pin_map:
            raise ValidationError(f"native netlist is missing endpoint {endpoint}")
        groups[pin_map[endpoint]].add(endpoint)
    return {endpoint: frozenset(groups[pin_map[endpoint]]) for endpoint in endpoints}


def _run_command(command, environment):
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=60,
        env=environment,
    )
    if completed.returncode != 0:
        raise ValidationError(f"native command failed: {' '.join(map(str, command))}")
    return completed


def _validate_native(source_symbols):
    version = subprocess.run(
        [str(KICAD_CLI), "version", "--format", "about"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if version.returncode != 0 or EXPECTED_KICAD_VERSION not in (version.stdout + version.stderr):
        raise ValidationError("wrong native KiCad CLI version")

    filenames = ["power.kicad_sch", "buck.kicad_sch", "ldo.kicad_sch", "load.kicad_sch", "top.kicad_sch"]
    with tempfile.TemporaryDirectory(prefix="engiworld-kicad-v02-") as temporary:
        root = Path(temporary)
        for filename in filenames:
            shutil.copy2(DESKTOP / filename, root / filename)
        environment = os.environ.copy()
        environment["XDG_CONFIG_HOME"] = str(root / "xdg-config")
        environment["XDG_CACHE_HOME"] = str(root / "xdg-cache")
        for filename in filenames:
            _run_command([str(KICAD_CLI), "sch", "upgrade", "--force", str(root / filename)], environment)
        for stem in ("power", "top"):
            _run_command(
                [
                    str(KICAD_CLI), "sch", "export", "netlist", "--format", "kicadsexpr",
                    "-o", str(root / f"{stem}.net"), str(root / f"{stem}.kicad_sch"),
                ],
                environment,
            )

        flat_refs, flat_pins = _read_netlist(root / "power.net")
        top_refs, top_pins = _read_netlist(root / "top.net")
        expected_refs = set(source_symbols)
        if flat_refs != expected_refs or top_refs != expected_refs:
            raise ValidationError("native netlist component set is wrong")

        declared = _declared_endpoint_nets(source_symbols)
        known_endpoints = set(declared)
        declared_partition = {
            endpoint: frozenset(other for other, net in declared.items() if net == declared[endpoint])
            for endpoint in known_endpoints
        }
        if _partition(flat_pins, known_endpoints) != declared_partition:
            raise ValidationError("flat native connectivity contradicts source metadata")
        if _partition(top_pins, known_endpoints) != declared_partition:
            raise ValidationError("hierarchical native connectivity differs from the flat source")

        unknown_endpoints = {
            (reference, pin)
            for reference, symbol in source_symbols.items()
            if symbol["properties"]["ConnectivityScope"] == "unspecified_by_source"
            for pin in symbol["pins"]
        }
        if len(unknown_endpoints) != 58:
            raise ValidationError("wrong unknown endpoint count")
        if set(flat_pins) - known_endpoints != unknown_endpoints:
            raise ValidationError("flat no-connect endpoints are not explicit")
        for endpoint in unknown_endpoints:
            if "unconnected" not in flat_pins[endpoint].lower():
                raise ValidationError(f"unknown endpoint {endpoint} is electrically connected")
        if set(top_pins) - known_endpoints != unknown_endpoints:
            raise ValidationError("hierarchical no-connect endpoints are not explicit")
        for endpoint in unknown_endpoints:
            if "unconnected" not in top_pins[endpoint].lower():
                raise ValidationError(f"unknown endpoint {endpoint} was connected in the hierarchy")


def _check_no_desktop_scripts():
    if not DESKTOP.is_dir():
        return False
    for path in DESKTOP.iterdir():
        if path.is_file() and path.name != "eval.py" and path.suffix.lower() in FORBIDDEN_DESKTOP_SCRIPT_EXTENSIONS:
            return False
    return True


def evaluate():
    if not _check_no_desktop_scripts():
        return False
    roots = {
        filename: _read_schematic(DESKTOP / filename)
        for filename in ("power.kicad_sch", "buck.kicad_sch", "ldo.kicad_sch", "load.kicad_sch", "top.kicad_sch")
    }
    source_symbols, source_libraries = _validate_source(roots["power.kicad_sch"])
    _validate_children(roots, source_symbols, source_libraries)
    _validate_top(roots["top.kicad_sch"])
    _validate_native(source_symbols)
    return True


if __name__ == "__main__":
    try:
        passed = evaluate()
    except Exception:
        passed = False
    print("True" if passed else "False")
