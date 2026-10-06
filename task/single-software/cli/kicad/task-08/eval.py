from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")
KICAD_CLI = Path("/usr/bin/kicad-cli")
OUTPUT_NAMES = (
    "board.kicad_pro",
    "design.kicad_sch",
    "design.kicad_pcb",
    "project.kicad_sym",
)
REQUIRED_REFERENCES = {"R1", "C1", "D1", "Q1", "U1"}
REQUIRED_LAYERS = {"F.Cu", "B.Cu", "F.SilkS", "B.SilkS", "Edge.Cuts"}
EXPECTED_COMPONENTS = {
    "R1": ("Device:R", "10k", {"1", "2"}),
    "C1": ("Device:C", "100nF", {"1", "2"}),
    "D1": ("Device:LED", "LED", {"1", "2"}),
    "Q1": ("Transistor_BJT:Q_NPN_BCE", "BC547", {"1", "2", "3"}),
    "U1": ("Regulator_Linear:LM7805_TO220", "LM7805", {"1", "2", "3"}),
}
EXPECTED_NET_NODES = {
    "+5V": {("U1", "3")},
    "GND": {("C1", "2"), ("Q1", "3"), ("R1", "2"), ("U1", "2")},
    "SIG_A": {("D1", "2"), ("Q1", "1")},
    "SIG_B": {("D1", "1"), ("Q1", "2")},
    "VCC": {("C1", "1"), ("R1", "1"), ("U1", "1")},
}
EXPECTED_FOOTPRINTS = {
    "R1": {
        "library": "Resistors_SMD:R_0603",
        "at": (20.0, 20.0),
        "pads": {
            "1": ("smd", "rect", (-0.8, 0.0), (0.9, 1.2), None, {"F.Cu", "F.Mask", "F.Paste"}),
            "2": ("smd", "rect", (0.8, 0.0), (0.9, 1.2), None, {"F.Cu", "F.Mask", "F.Paste"}),
        },
    },
    "C1": {
        "library": "Capacitors_SMD:C_0402",
        "at": (30.0, 20.0),
        "pads": {
            "1": ("smd", "rect", (-0.5, 0.0), (0.6, 0.7), None, {"F.Cu", "F.Mask", "F.Paste"}),
            "2": ("smd", "rect", (0.5, 0.0), (0.6, 0.7), None, {"F.Cu", "F.Mask", "F.Paste"}),
        },
    },
    "D1": {
        "library": "LEDs:LED_0603",
        "at": (40.0, 20.0),
        "pads": {
            "1": ("smd", "rect", (-0.8, 0.0), (0.9, 1.2), None, {"F.Cu", "F.Mask", "F.Paste"}),
            "2": ("smd", "rect", (0.8, 0.0), (0.9, 1.2), None, {"F.Cu", "F.Mask", "F.Paste"}),
        },
    },
    "Q1": {
        "library": "TO_SOT_Packages_THT:TO-92_Inline",
        "at": (50.0, 20.0),
        "pads": {
            "1": ("thru_hole", "circle", (-1.27, 0.0), (1.6, 1.6), (0.8,), {"*.Cu", "*.Mask"}),
            "2": ("thru_hole", "circle", (0.0, 0.0), (1.6, 1.6), (0.8,), {"*.Cu", "*.Mask"}),
            "3": ("thru_hole", "circle", (1.27, 0.0), (1.6, 1.6), (0.8,), {"*.Cu", "*.Mask"}),
        },
    },
    "U1": {
        "library": "TO_SOT_Packages_THT:TO-220_Vertical",
        "at": (60.0, 20.0),
        "pads": {
            "1": ("thru_hole", "rect", (-2.54, 0.0), (2.4, 2.4), (1.3,), {"*.Cu", "*.Mask"}),
            "2": ("thru_hole", "oval", (0.0, 0.0), (2.4, 2.4), (1.3,), {"*.Cu", "*.Mask"}),
            "3": ("thru_hole", "circle", (2.54, 0.0), (2.4, 2.4), (1.3,), {"*.Cu", "*.Mask"}),
        },
    },
}
EXPECTED_LIBRARY_SYMBOLS = {
    "R": (
        "R",
        "R",
        "R",
        {"1": ("passive", {"", "~"}), "2": ("passive", {"", "~"})},
    ),
    "C": (
        "C",
        "C",
        "C",
        {"1": ("passive", {"", "~"}), "2": ("passive", {"", "~"})},
    ),
    "LED": (
        "LED",
        "D",
        "LED",
        {"1": ("passive", {"K"}), "2": ("passive", {"A"})},
    ),
    "Q_NPN_BCE": (
        "Q",
        "Q",
        "Q_NPN_BCE",
        {
            "1": ("input", {"B"}),
            "2": ("passive", {"C"}),
            "3": ("passive", {"E"}),
        },
    ),
    "BC547": (
        "Q",
        "Q",
        "BC547",
        {
            "1": ("input", {"B"}),
            "2": ("passive", {"C"}),
            "3": ("passive", {"E"}),
        },
    ),
    "LM7805_TO220": (
        "U",
        "U",
        "LM7805_TO220",
        {
            "1": ("input", {"VI"}),
            "2": ("power_in", {"GND"}),
            "3": ("output", {"VO"}),
        },
    ),
    "LM7805": (
        "U",
        "U",
        "LM7805",
        {
            "1": ("input", {"IN"}),
            "2": ("power_in", {"GND"}),
            "3": ("output", {"OUT"}),
        },
    ),
}
EXPECTED_TARGET_PINS = {
    "Device:R": {
        "1": ("passive", {"", "~"}),
        "2": ("passive", {"", "~"}),
    },
    "Device:C": {
        "1": ("passive", {"", "~"}),
        "2": ("passive", {"", "~"}),
    },
    "Device:LED": {
        "1": ("passive", {"K"}),
        "2": ("passive", {"A"}),
    },
    "Transistor_BJT:Q_NPN_BCE": {
        "1": ("input", {"B"}),
        "2": ("passive", {"C"}),
        "3": ("passive", {"E"}),
    },
    "Regulator_Linear:LM7805_TO220": {
        "1": ("power_in", {"VI"}),
        "2": ("power_in", {"GND"}),
        "3": ("power_out", {"VO"}),
    },
}
SYMBOL_GRAPHICS = {"arc", "bezier", "circle", "polyline", "rectangle", "text", "text_box"}
EXPECTED_VERSIONS = {
    "kicad_sch": "20260306",
    "kicad_pcb": "20260206",
    "kicad_symbol_lib": "20251024",
}


class SexpError(ValueError):
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
                raise SexpError("unexpected closing parenthesis")
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
                        raise SexpError("unterminated escape")
                    escaped = text[index]
                    value.append({"n": "\n", "r": "\r", "t": "\t"}.get(escaped, escaped))
                    index += 1
                    continue
                value.append(char)
                index += 1
            else:
                raise SexpError("unterminated string")
            append("".join(value))
            continue

        start = index
        while index < length and not text[index].isspace() and text[index] not in "();":
            index += 1
        if start == index:
            raise SexpError("invalid token")
        append(text[start:index])

    if stack:
        raise SexpError("unterminated list")
    if len(roots) != 1 or not isinstance(roots[0], list):
        raise SexpError("expected one root list")
    return roots[0]


def _head(node):
    return node[0] if isinstance(node, list) and node else None


def _direct(node, name: str):
    return [
        child
        for child in node[1:]
        if isinstance(child, list) and child and child[0] == name
    ]


def _single_value(node, name: str):
    matches = _direct(node, name)
    if len(matches) != 1 or len(matches[0]) < 2 or isinstance(matches[0][1], list):
        raise SexpError(f"expected one scalar {name}")
    return matches[0][1]


def _single_node(node, name: str):
    matches = _direct(node, name)
    if len(matches) != 1:
        raise SexpError(f"expected one {name} node")
    return matches[0]


def _float_values(node, name: str, count: int):
    match = _single_node(node, name)
    values = match[1 : count + 1]
    if len(values) != count or any(isinstance(value, list) for value in values):
        raise SexpError(f"invalid numeric {name}")
    try:
        return tuple(float(value) for value in values)
    except ValueError as exc:
        raise SexpError(f"invalid numeric {name}") from exc


def _close_tuple(observed, expected, tolerance=1e-6):
    return len(observed) == len(expected) and all(
        abs(left - right) <= tolerance for left, right in zip(observed, expected)
    )


def _property(node, name: str):
    matches = [
        child
        for child in _direct(node, "property")
        if len(child) >= 3 and child[1] == name and not isinstance(child[2], list)
    ]
    if len(matches) != 1:
        raise SexpError(f"expected one {name} property")
    return matches[0][2]


def _walk(node):
    if not isinstance(node, list):
        return
    yield node
    for child in node:
        if isinstance(child, list):
            yield from _walk(child)


def _read_sexp(path: Path):
    return _parse_sexp(path.read_text(encoding="utf-8"))


def _check_root(root, expected_head: str):
    if _head(root) != expected_head:
        raise SexpError(f"expected {expected_head} root")
    if _single_value(root, "version") != EXPECTED_VERSIONS[expected_head]:
        raise SexpError(f"wrong {expected_head} version")
    if _single_value(root, "generator_version") != "10.0":
        raise SexpError(f"wrong {expected_head} generator version")


def _load_target_ids(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["v5_lib_id", "v9_lib_id"]:
            raise ValueError("invalid lib_map.csv header")
        rows = list(reader)
    targets = {row["v9_lib_id"].strip() for row in rows}
    if len(rows) != 5 or len(targets) != 5 or "" in targets:
        raise ValueError("lib_map.csv must contain five unique mappings")
    return targets


def _check_project(path: Path):
    project = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(project, dict):
        raise ValueError("project root is not an object")
    meta = project.get("meta")
    if not isinstance(meta, dict):
        raise ValueError("missing project meta")
    if meta.get("filename") != "board.kicad_pro" or meta.get("version") != 3:
        raise ValueError("wrong KiCad project metadata")
    for key in ("net_settings", "schematic", "pcbnew"):
        if not isinstance(project.get(key), dict):
            raise ValueError(f"missing project object {key}")
    net_settings = project["net_settings"]
    if net_settings.get("meta") != {"version": 5}:
        raise ValueError("wrong net-settings metadata")
    classes = net_settings.get("classes")
    if not isinstance(classes, list) or not any(
        isinstance(item, dict) and item.get("name") == "Default" for item in classes
    ):
        raise ValueError("missing Default net class")
    if project["schematic"].get("meta") != {"version": 1}:
        raise ValueError("wrong schematic project metadata")
    if not isinstance(project["pcbnew"].get("last_paths"), dict):
        raise ValueError("missing PCB project paths")


def _check_schematic(path: Path, target_ids):
    root = _read_sexp(path)
    _check_root(root, "kicad_sch")
    if _single_value(root, "generator") != "eeschema":
        raise SexpError("wrong schematic generator")

    label_names = {
        label[1]
        for label in _direct(root, "label")
        if len(label) >= 2 and not isinstance(label[1], list)
    }
    if label_names != set(EXPECTED_NET_NODES):
        raise SexpError("schematic labels do not match the five source nets")

    embedded_section = _single_node(root, "lib_symbols")
    embedded = _direct(embedded_section, "symbol")
    embedded_by_id = {
        symbol[1]: symbol
        for symbol in embedded
        if len(symbol) >= 2 and not isinstance(symbol[1], list)
    }
    if set(embedded_by_id) != target_ids or len(embedded_by_id) != len(embedded):
        raise SexpError("embedded symbols do not match the migration targets")
    for lib_id, symbol in embedded_by_id.items():
        if not any(_head(node) in SYMBOL_GRAPHICS for node in _walk(symbol)):
            raise SexpError(f"embedded symbol has no graphics: {lib_id}")
        expected_pins = EXPECTED_TARGET_PINS[lib_id]
        pins = {}
        for pin in (node for node in _walk(symbol) if _head(node) == "pin"):
            number = _single_value(pin, "number")
            if number in pins:
                raise SexpError(f"duplicate embedded pin {lib_id}:{number}")
            pins[number] = (pin[1], _single_value(pin, "name"))
        if set(pins) != set(expected_pins):
            raise SexpError(f"wrong embedded pin numbering: {lib_id}")
        for number, (pin_type, pin_name) in pins.items():
            expected_type, allowed_names = expected_pins[number]
            if pin_type != expected_type or pin_name not in allowed_names:
                raise SexpError(f"wrong embedded pin semantics: {lib_id}:{number}")

    placed = _direct(root, "symbol")
    if len(placed) != len(EXPECTED_COMPONENTS):
        raise SexpError("migration must preserve exactly five placed symbols")
    observed = {}
    for symbol in placed:
        reference = _property(symbol, "Reference")
        lib_id = _single_value(symbol, "lib_id")
        value = _property(symbol, "Value")
        if lib_id not in target_ids:
            raise SexpError(f"unmapped placed symbol {lib_id}")
        if reference in observed:
            raise SexpError(f"duplicate placed reference {reference}")
        observed[reference] = (lib_id, value)
    expected = {
        reference: (lib_id, value)
        for reference, (lib_id, value, _) in EXPECTED_COMPONENTS.items()
    }
    if observed != expected:
        raise SexpError("placed reference, library id, or value was not preserved")


def _check_pcb(path: Path):
    root = _read_sexp(path)
    _check_root(root, "kicad_pcb")
    if _single_value(root, "generator") != "pcbnew":
        raise SexpError("wrong PCB generator")

    general = _single_node(root, "general")
    if _single_value(general, "thickness") != "1.6":
        raise SexpError("PCB thickness was not preserved")
    title_block = _single_node(root, "title_block")
    expected_title = {
        "title": "Legacy Power Board",
        "date": "2015-04-28",
        "rev": "A",
        "company": "ACME Corp",
    }
    for field, value in expected_title.items():
        if _single_value(title_block, field) != value:
            raise SexpError(f"PCB title-block field was not preserved: {field}")

    layers_nodes = _direct(root, "layers")
    if len(layers_nodes) != 1:
        raise SexpError("missing layers section")
    layer_names = {
        child[1]
        for child in layers_nodes[0][1:]
        if isinstance(child, list)
        and len(child) >= 2
        and not isinstance(child[1], list)
    }
    if not REQUIRED_LAYERS.issubset(layer_names):
        raise SexpError("missing canonical KiCad layers")

    footprints = _direct(root, "footprint")
    if len(footprints) != len(EXPECTED_COMPONENTS):
        raise SexpError("migration must preserve exactly five footprints")
    observed = {}
    for footprint in footprints:
        if len(footprint) < 2 or isinstance(footprint[1], list):
            raise SexpError("footprint lacks a library identifier")
        reference = _property(footprint, "Reference")
        value = _property(footprint, "Value")
        if len(_direct(footprint, "layer")) != 1 or not _direct(footprint, "pad"):
            raise SexpError("footprint lacks native layer or pad structure")
        if reference in observed:
            raise SexpError(f"duplicate footprint reference {reference}")
        if reference not in EXPECTED_FOOTPRINTS:
            raise SexpError(f"unexpected footprint reference {reference}")
        expected = EXPECTED_FOOTPRINTS[reference]
        if footprint[1] != expected["library"]:
            raise SexpError(f"footprint library ID was not preserved: {reference}")
        if not _close_tuple(_float_values(footprint, "at", 2), expected["at"]):
            raise SexpError(f"footprint position was not preserved: {reference}")
        expected_value = EXPECTED_COMPONENTS[reference][1]
        if value != expected_value:
            raise SexpError(f"footprint value was not preserved: {reference}")

        pads = {}
        for pad in _direct(footprint, "pad"):
            if len(pad) < 4 or any(isinstance(value, list) for value in pad[1:4]):
                raise SexpError(f"invalid pad structure: {reference}")
            number, pad_type, shape = pad[1:4]
            if number in pads:
                raise SexpError(f"duplicate pad number: {reference}.{number}")
            at = _float_values(pad, "at", 2)
            size = _float_values(pad, "size", 2)
            drill_nodes = _direct(pad, "drill")
            if len(drill_nodes) > 1:
                raise SexpError(f"duplicate drill node: {reference}.{number}")
            drill = None
            if drill_nodes:
                raw_drill = drill_nodes[0][1:]
                if not raw_drill or any(isinstance(item, list) for item in raw_drill):
                    raise SexpError(f"invalid drill: {reference}.{number}")
                if raw_drill[0] == "oval":
                    raw_drill = raw_drill[1:]
                try:
                    drill = tuple(float(item) for item in raw_drill)
                except ValueError as exc:
                    raise SexpError(f"invalid drill: {reference}.{number}") from exc
            layers = _single_node(pad, "layers")
            layer_set = {
                item for item in layers[1:] if not isinstance(item, list)
            }
            pads[number] = (pad_type, shape, at, size, drill, layer_set)

        if set(pads) != set(expected["pads"]):
            raise SexpError(f"pad numbering was not preserved: {reference}")
        for number, details in pads.items():
            expected_details = expected["pads"][number]
            if details[:2] != expected_details[:2]:
                raise SexpError(f"pad type or shape was not preserved: {reference}.{number}")
            if not _close_tuple(details[2], expected_details[2]):
                raise SexpError(f"pad position was not preserved: {reference}.{number}")
            if not _close_tuple(details[3], expected_details[3]):
                raise SexpError(f"pad size was not preserved: {reference}.{number}")
            if details[4] is None or expected_details[4] is None:
                if details[4] != expected_details[4]:
                    raise SexpError(f"pad drill was not preserved: {reference}.{number}")
            elif not _close_tuple(details[4], expected_details[4]):
                raise SexpError(f"pad drill was not preserved: {reference}.{number}")
            if details[5] != expected_details[5]:
                raise SexpError(f"pad layers were not preserved: {reference}.{number}")
        observed[reference] = True
    if set(observed) != set(EXPECTED_FOOTPRINTS):
        raise SexpError("PCB footprint set was not preserved")
    if _direct(root, "module"):
        raise SexpError("legacy module structure remains")


def _check_symbol_library(path: Path, target_ids):
    root = _read_sexp(path)
    _check_root(root, "kicad_symbol_lib")
    if _single_value(root, "generator") != "kicad_symbol_editor":
        raise SexpError("wrong symbol-library generator")
    symbols = _direct(root, "symbol")
    if len(symbols) != 5:
        raise SexpError("local library must contain exactly five top-level symbols")
    names = [
        symbol[1]
        for symbol in symbols
        if len(symbol) >= 2 and not isinstance(symbol[1], list)
    ]
    if len(names) != len(symbols) or len(set(names)) != len(names):
        raise SexpError("invalid or duplicate top-level symbol name")
    canonical_names = {
        EXPECTED_LIBRARY_SYMBOLS[name][0]
        for name in names
        if name in EXPECTED_LIBRARY_SYMBOLS
    }
    if canonical_names != {"R", "C", "LED", "Q", "U"}:
        raise SexpError("local library does not freeze the five source symbols")
    for symbol in symbols:
        name = symbol[1]
        _, expected_reference, expected_value, expected_pins = EXPECTED_LIBRARY_SYMBOLS[name]
        if (
            _property(symbol, "Reference") != expected_reference
            or _property(symbol, "Value") != expected_value
        ):
            raise SexpError(f"wrong properties in local symbol {name}")
        if not any(_head(node) in SYMBOL_GRAPHICS for node in _walk(symbol)):
            raise SexpError(f"local symbol has no graphics: {name}")
        pins = {}
        for pin in (node for node in _walk(symbol) if _head(node) == "pin"):
            if len(pin) < 2 or isinstance(pin[1], list):
                raise SexpError(f"invalid pin in local symbol {name}")
            number = _single_value(pin, "number")
            if number in pins:
                raise SexpError(f"duplicate pin {number} in local symbol {name}")
            pins[number] = (pin[1], _single_value(pin, "name"))
        if set(pins) != set(expected_pins):
            raise SexpError(f"wrong pin numbering in {name}")
        for number, (pin_type, pin_name) in pins.items():
            expected_type, allowed_names = expected_pins[number]
            if pin_type != expected_type or pin_name not in allowed_names:
                raise SexpError(f"wrong pin name or electrical type in {name}")


def _run_cli(args, timeout=30):
    completed = subprocess.run(
        [str(KICAD_CLI), *map(str, args)],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"kicad-cli failed: {detail}")
    return completed.stdout


def _check_exported_nets(netlist_path: Path):
    root = _read_sexp(netlist_path)
    if _head(root) != "export":
        raise SexpError("invalid exported netlist")
    sections = _direct(root, "nets")
    if len(sections) != 1:
        raise SexpError("missing exported nets section")

    named_nodes = {}
    for net in _direct(sections[0], "net"):
        name = _single_value(net, "name")
        canonical_name = name[1:] if name.startswith("/") else name
        if canonical_name in named_nodes:
            raise SexpError(f"duplicate exported net: {canonical_name}")
        nodes = set()
        for node in _direct(net, "node"):
            member = (_single_value(node, "ref"), _single_value(node, "pin"))
            if member in nodes:
                raise SexpError(f"duplicate node on exported net: {canonical_name}")
            nodes.add(member)
        named_nodes[canonical_name] = nodes
    if named_nodes != EXPECTED_NET_NODES:
        raise SexpError("exported electrical topology does not match the source")


def _check_with_kicad_cli(paths):
    if not KICAD_CLI.is_file():
        raise RuntimeError("kicad-cli is unavailable")
    if _run_cli(["version"]).strip() != "10.0.2":
        raise RuntimeError("wrong KiCad version")

    with tempfile.TemporaryDirectory(prefix="engiworld-kicad-task-08-") as temp:
        temp_dir = Path(temp)
        schematic = temp_dir / "design.kicad_sch"
        pcb = temp_dir / "design.kicad_pcb"
        symbols = temp_dir / "project.kicad_sym"
        netlist = temp_dir / "design.net"
        shutil.copy2(paths["design.kicad_sch"], schematic)
        shutil.copy2(paths["design.kicad_pcb"], pcb)
        shutil.copy2(paths["project.kicad_sym"], symbols)
        shutil.copy2(paths["board.kicad_pro"], temp_dir / "design.kicad_pro")

        _run_cli(["sch", "upgrade", "--force", schematic])
        _run_cli(["pcb", "upgrade", "--force", pcb])
        _run_cli(["sym", "upgrade", "--force", symbols])
        _run_cli(
            [
                "sch",
                "export",
                "netlist",
                "--format",
                "kicadsexpr",
                "--output",
                netlist,
                schematic,
            ]
        )
        _check_exported_nets(netlist)


def evaluate():
    paths = {name: DESKTOP / name for name in OUTPUT_NAMES}
    if any(not path.is_file() for path in paths.values()):
        return False
    for path in paths.values():
        if path.stat().st_size > 64 * 1024 * 1024:
            return False
        if b"EESchema" in path.read_bytes():
            return False

    target_ids = _load_target_ids(DESKTOP / "lib_map.csv")
    _check_project(paths["board.kicad_pro"])
    _check_schematic(paths["design.kicad_sch"], target_ids)
    _check_pcb(paths["design.kicad_pcb"])
    _check_symbol_library(paths["project.kicad_sym"], target_ids)
    _check_with_kicad_cli(paths)
    return True


def main():
    try:
        result = evaluate()
    except Exception as exc:
        if os.environ.get("ENGIWORLD_EVAL_DEBUG") == "1":
            print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        result = False
    print("True" if result else "False")


if __name__ == "__main__":
    main()
