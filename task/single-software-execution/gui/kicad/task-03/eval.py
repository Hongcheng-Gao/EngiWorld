from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")
OUTPUT = "answer.kicad_sch"
ALLOWED_WARNING_TYPES = {"lib_symbol_issues", "lib_symbol_mismatch"}
SCRIPT_SUFFIXES = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".vbs", ".js", ".mjs", ".ts", ".rb", ".lua", ".tcl",
}

BASE_SYMBOLS = {
    "U1": ("MCU_ST_STM32F1:STM32F103C8Tx", "STM32F103C8T6", "Package_QFP:LQFP-48_7x7mm_P0.5mm"),
    "U2": ("EngiWorld:IS62WV51216BLL", "IS62WV51216BLL", "Package_SO:TSOP-II-44_10.16x18.41mm_P0.8mm"),
    "C1": ("Device:C", "100nF", "Capacitor_SMD:C_0402_1005Metric"),
    "C2": ("Device:C", "100nF", "Capacitor_SMD:C_0402_1005Metric"),
    "C3": ("Device:C", "100nF", "Capacitor_SMD:C_0402_1005Metric"),
    "C4": ("Device:C", "100nF", "Capacitor_SMD:C_0402_1005Metric"),
    "R1": ("Device:R", "10k", "Resistor_SMD:R_0402_1005Metric"),
    "R2": ("Device:R", "10k", "Resistor_SMD:R_0402_1005Metric"),
    "R3": ("Device:R", "10k", "Resistor_SMD:R_0402_1005Metric"),
    "#PWR01": ("power:+3V3", "+3V3", ""),
    "#PWR02": ("power:+3V3", "+3V3", ""),
    "#PWR03": ("power:GND", "GND", ""),
    "#PWR04": ("power:GND", "GND", ""),
}
FLAG_SYMBOLS = {
    "#FLG01": ("power:PWR_FLAG", "PWR_FLAG", ""),
    "#FLG02": ("power:PWR_FLAG", "PWR_FLAG", ""),
}
EXPECTED_SYMBOLS = BASE_SYMBOLS | FLAG_SYMBOLS


def no_gui_bypass(root: Path) -> bool:
    try:
        for path in root.iterdir():
            if path.is_file() and path.name != "eval.py" and path.suffix.lower() in SCRIPT_SUFFIXES:
                return False
            if path.is_dir() and path.name not in {"_runtime", "__pycache__"}:
                for child in path.iterdir():
                    if child.is_file() and child.suffix.lower() in SCRIPT_SUFFIXES:
                        return False
    except Exception:
        return False
    history_paths = [
        Path.home() / ".bash_history",
        Path.home() / ".zsh_history",
        Path.home() / ".python_history",
        Path.home() / ".local/share/fish/fish_history",
    ]
    command_tokens = ("python", "bash", "node", "kicad-cli", "eeschema")
    output_tokens = ("answer.kicad_sch", ".kicad_sch")
    for history in history_paths:
        if not history.is_file():
            continue
        try:
            lines = history.read_text(encoding="utf-8", errors="ignore").lower().splitlines()
        except Exception:
            return False
        for line in lines:
            if "eval.py" in line:
                continue
            if any(token in line for token in command_tokens) and any(token in line for token in output_tokens):
                return False
    return True


def parse_sexp(text: str):
    tokens = []
    index = 0
    while index < len(text):
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            break
        char = text[index]
        if char in "()":
            tokens.append(char)
            index += 1
            continue
        if char == '"':
            start = index
            index += 1
            escaped = False
            while index < len(text):
                current = text[index]
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    index += 1
                    break
                index += 1
            else:
                raise ValueError("unterminated string")
            tokens.append(json.loads(text[start:index]))
            continue
        start = index
        while index < len(text) and not text[index].isspace() and text[index] not in "()":
            index += 1
        tokens.append(text[start:index])

    def parse_at(position: int):
        if position >= len(tokens) or tokens[position] != "(":
            raise ValueError("expected opening parenthesis")
        result = []
        position += 1
        while position < len(tokens) and tokens[position] != ")":
            if tokens[position] == "(":
                child, position = parse_at(position)
                result.append(child)
            else:
                result.append(tokens[position])
                position += 1
        if position >= len(tokens):
            raise ValueError("unterminated expression")
        return result, position + 1

    root, final = parse_at(0)
    if final != len(tokens):
        raise ValueError("multiple root expressions")
    return root


def direct(node, head: str):
    return [child for child in node[1:] if isinstance(child, list) and child and child[0] == head]


def only(node, head: str):
    matches = direct(node, head)
    if len(matches) != 1:
        raise ValueError(f"expected one {head}, found {len(matches)}")
    return matches[0]


def walk(node):
    if not isinstance(node, list):
        return
    yield node
    for child in node:
        if isinstance(child, list):
            yield from walk(child)


def properties(symbol) -> dict[str, str]:
    result = {}
    for prop in direct(symbol, "property"):
        if len(prop) >= 3:
            result[str(prop[1])] = str(prop[2])
    return result


def coordinate(node) -> tuple[float, float]:
    at = only(node, "at")
    if len(at) < 3:
        raise ValueError("invalid coordinate")
    return round(float(at[1]), 6), round(float(at[2]), 6)


def connected_power_flags(root, symbols: dict[str, list]) -> bool:
    graph: dict[tuple[float, float], set[tuple[float, float]]] = {}
    segments = []

    def add_point(point: tuple[float, float]) -> None:
        graph.setdefault(point, set())

    for wire in direct(root, "wire"):
        points = []
        for xy in direct(only(wire, "pts"), "xy"):
            if len(xy) < 3:
                return False
            point = round(float(xy[1]), 6), round(float(xy[2]), 6)
            add_point(point)
            points.append(point)
        if len(points) < 2:
            return False
        for start, end in zip(points, points[1:]):
            segments.append((start, end))

    labels: dict[tuple[float, float], set[str]] = {}
    for head in ("label", "global_label", "hierarchical_label"):
        for item in direct(root, head):
            if len(item) < 2:
                return False
            point = coordinate(item)
            add_point(point)
            labels.setdefault(point, set()).add(str(item[1]).lstrip("/"))

    flag_points = []
    for symbol in symbols.values():
        lib_id = str(only(symbol, "lib_id")[1])
        point = coordinate(symbol)
        add_point(point)
        if lib_id == "power:PWR_FLAG":
            flag_points.append(point)
        elif lib_id in {"power:+3V3", "power:GND"}:
            labels.setdefault(point, set()).add(lib_id.split(":", 1)[1])

    no_connects = {coordinate(item) for item in direct(root, "no_connect")}
    if any(point in no_connects for point in flag_points):
        return False

    def on_segment(point, start, end) -> bool:
        cross = (point[0] - start[0]) * (end[1] - start[1]) - (point[1] - start[1]) * (end[0] - start[0])
        return (
            abs(cross) < 1e-6
            and min(start[0], end[0]) - 1e-6 <= point[0] <= max(start[0], end[0]) + 1e-6
            and min(start[1], end[1]) - 1e-6 <= point[1] <= max(start[1], end[1]) + 1e-6
        )

    all_points = list(graph)
    for start, end in segments:
        connected = [point for point in all_points if on_segment(point, start, end)]
        for left, right in zip(connected, connected[1:]):
            graph[left].add(right)
            graph[right].add(left)

    observed = []
    for flag in flag_points:
        stack = [flag]
        visited = set()
        names = set()
        while stack:
            point = stack.pop()
            if point in visited:
                continue
            visited.add(point)
            names.update(labels.get(point, set()))
            stack.extend(graph.get(point, set()) - visited)
        names &= {"+3V3", "GND"}
        if len(names) != 1:
            return False
        observed.append(next(iter(names)))
    return sorted(observed) == ["+3V3", "GND"]


def static_schematic_checks(root, raw_text: str) -> bool:
    if not root or root[0] != "kicad_sch":
        return False
    if only(root, "version")[1:] != ["20260306"]:
        return False
    if only(root, "generator")[1:] != ["eeschema"]:
        return False
    if only(root, "generator_version")[1:] != ["10.0"]:
        return False
    if re.search(r"DATA\s*\[", raw_text, flags=re.IGNORECASE) or "#BUS" in raw_text:
        return False

    symbols = {}
    for symbol in direct(root, "symbol"):
        props = properties(symbol)
        ref = props.get("Reference")
        if not ref or ref in symbols:
            return False
        symbols[ref] = symbol
    if set(symbols) != set(EXPECTED_SYMBOLS):
        return False
    for ref, expected in EXPECTED_SYMBOLS.items():
        symbol = symbols[ref]
        props = properties(symbol)
        actual = (only(symbol, "lib_id")[1], props.get("Value", ""), props.get("Footprint", ""))
        if actual != expected:
            return False
    if not connected_power_flags(root, symbols):
        return False

    labels = {str(item[1]).lstrip("/") for item in direct(root, "label") if len(item) >= 2}
    if not {f"DATA{index}" for index in range(8)}.issubset(labels):
        return False

    library_root = only(root, "lib_symbols")
    libraries = {str(item[1]): item for item in direct(library_root, "symbol") if len(item) >= 2}
    for required in {expected[0] for expected in EXPECTED_SYMBOLS.values()}:
        if required not in libraries:
            return False

    def pin_map(lib_id: str) -> dict[str, tuple[str, str]]:
        result = {}
        for item in walk(libraries[lib_id]):
            if not item or item[0] != "pin" or len(item) < 3:
                continue
            numbers = direct(item, "number")
            names = direct(item, "name")
            if len(numbers) != 1 or len(names) != 1:
                continue
            number = str(numbers[0][1])
            if number in result:
                return {}
            result[number] = (str(names[0][1]), str(item[1]))
        return result

    u1_pins = pin_map("MCU_ST_STM32F1:STM32F103C8Tx")
    u2_pins = pin_map("EngiWorld:IS62WV51216BLL")
    flag_pins = pin_map("power:PWR_FLAG")
    if len(u1_pins) != 48 or len(u2_pins) != 44:
        return False
    for index in range(8):
        if u1_pins.get(str(10 + index), (None,))[0] != f"PA{index}":
            return False
    for number, name in zip(("7", "8", "9", "10", "13", "14", "15", "16"), (f"IO{i}" for i in range(8))):
        if u2_pins.get(number, (None,))[0] != name:
            return False
    for number in ("1", "9", "24", "36", "48"):
        if u1_pins.get(number, (None, None))[1] != "power_in":
            return False
    for number in ("11", "12", "33", "34"):
        if u2_pins.get(number, (None, None))[1] != "power_in":
            return False
    if flag_pins.get("1", (None, None))[1] != "power_out":
        return False
    return True


def run(command: list[str], environment: dict[str, str], timeout: int = 90):
    return subprocess.run(command, text=True, capture_output=True, env=environment, timeout=timeout)


def endpoint(node: ET.Element) -> tuple[str, str, str]:
    ref = node.attrib.get("ref", "")
    pin = node.attrib.get("pin", "")
    function = re.sub(r"_\d+$", "", node.attrib.get("pinfunction", ""))
    return ref, pin, function


def netlist_checks(root: ET.Element) -> bool:
    if root.tag != "export":
        return False
    components = root.find("components")
    if components is None:
        return False
    component_refs = {comp.attrib.get("ref", "") for comp in components.findall("comp")}
    if component_refs != {"U1", "U2", "C1", "C2", "C3", "C4", "R1", "R2", "R3"}:
        return False

    net_root = root.find("nets")
    if net_root is None:
        return False
    net_map = {}
    for net in net_root.findall("net"):
        name = net.attrib.get("name", "").lstrip("/")
        if name in net_map:
            return False
        net_map[name] = {endpoint(item) for item in net.findall("node")}

    named_nets = {name for name in net_map if not name.startswith("unconnected-")}
    expected_named_nets = {"+3V3", "GND", "CE_N", "OE_N", "WE_N"} | {f"DATA{index}" for index in range(8)}
    if named_nets != expected_named_nets:
        return False

    sram_pins = ("7", "8", "9", "10", "13", "14", "15", "16")
    for index, sram_pin in enumerate(sram_pins):
        expected = {
            ("U1", str(10 + index), f"PA{index}"),
            ("U2", sram_pin, f"IO{index}"),
        }
        if net_map.get(f"DATA{index}") != expected:
            return False

    controls = {
        "CE_N": {("R1", "2", ""), ("U2", "6", "~{CS1}")},
        "OE_N": {("R2", "2", ""), ("U2", "41", "~{OE}")},
        "WE_N": {("R3", "2", ""), ("U2", "17", "~{WE}")},
    }
    for name, expected in controls.items():
        if net_map.get(name) != expected:
            return False

    expected_3v3 = {
        *((f"C{index}", "1", "") for index in range(1, 5)),
        *((f"R{index}", "1", "") for index in range(1, 4)),
        *(("U1", pin, function) for pin, function in (("1", "VBAT"), ("9", "VDDA"), ("24", "VDD"), ("36", "VDD"), ("48", "VDD"))),
        ("U2", "11", "VDD"),
        ("U2", "33", "VDD"),
    }
    expected_gnd = {
        *((f"C{index}", "2", "") for index in range(1, 5)),
        *(("U1", pin, function) for pin, function in (("8", "VSSA"), ("23", "VSS"), ("35", "VSS"), ("47", "VSS"))),
        ("U2", "12", "GND"),
        ("U2", "34", "GND"),
    }
    if net_map.get("+3V3") != expected_3v3:
        return False
    if net_map.get("GND") != expected_gnd:
        return False
    return True


def erc_violations(report_path: Path):
    report = json.loads(report_path.read_text(encoding="utf-8"))
    result = []
    for sheet in report.get("sheets", []):
        result.extend(sheet.get("violations", []))
    return result


def evaluate(root: Path = DESKTOP) -> bool:
    if not no_gui_bypass(root):
        return False
    candidate = root / OUTPUT
    if not candidate.is_file() or candidate.stat().st_size < 10000:
        return False
    raw = candidate.read_text(encoding="utf-8")
    schematic = parse_sexp(raw)
    if not static_schematic_checks(schematic, raw):
        return False

    version = subprocess.run(
        ["kicad-cli", "version", "--format", "plain"],
        text=True,
        capture_output=True,
        timeout=20,
    )
    if version.returncode != 0 or not version.stdout.strip().startswith("10.0.2"):
        return False

    with tempfile.TemporaryDirectory(prefix="engiworld_kicad_v03_") as temp_text:
        temp = Path(temp_text)
        work = temp / OUTPUT
        shutil.copy2(candidate, work)
        environment = os.environ.copy()
        environment["XDG_CONFIG_HOME"] = str(temp / "config")
        environment["XDG_CACHE_HOME"] = str(temp / "cache")
        config_dir = temp / "config" / "kicad" / "10.0"
        config_dir.mkdir(parents=True, exist_ok=True)
        source_config = Path.home() / ".config" / "kicad" / "10.0"
        for table_name in ("sym-lib-table", "fp-lib-table"):
            source_table = source_config / table_name
            if source_table.is_file():
                shutil.copy2(source_table, config_dir / table_name)
        upgrade = run(["kicad-cli", "sch", "upgrade", "--force", str(work)], environment)
        if upgrade.returncode != 0:
            return False
        netlist_path = temp / "answer.net"
        netlist = run(
            [
                "kicad-cli", "sch", "export", "netlist", "--format", "kicadxml",
                "--output", str(netlist_path), str(work),
            ],
            environment,
        )
        if netlist.returncode != 0 or not netlist_path.is_file():
            return False
        if not netlist_checks(ET.parse(netlist_path).getroot()):
            return False

        error_report = temp / "erc-errors.json"
        errors = run(
            [
                "kicad-cli", "sch", "erc", "--format", "json", "--severity-error",
                "--exit-code-violations", "--output", str(error_report), str(work),
            ],
            environment,
        )
        if errors.returncode != 0 or not error_report.is_file() or erc_violations(error_report):
            return False

        all_report = temp / "erc-all.json"
        all_results = run(
            [
                "kicad-cli", "sch", "erc", "--format", "json", "--severity-all",
                "--exit-code-violations", "--output", str(all_report), str(work),
            ],
            environment,
        )
        if all_results.returncode not in {0, 5} or not all_report.is_file():
            return False
        violations = erc_violations(all_report)
        if any(item.get("severity") == "error" for item in violations):
            return False
        if any(item.get("type") not in ALLOWED_WARNING_TYPES for item in violations):
            return False
    return True


if __name__ == "__main__":
    try:
        print("True" if evaluate() else "False")
    except Exception:
        print("False")
