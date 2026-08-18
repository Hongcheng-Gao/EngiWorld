from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
from pathlib import Path, PureWindowsPath
from xml.etree import ElementTree as ET

import olefile


EXPECTED = {
    "rows": 4,
    "columns": 3,
    "row_spacing_mil": 1133.8583,
    "column_spacing_mil": 1338.5827,
    "mirror": True,
    "origin_mode": 1,
    "board_count": 12,
    "source": "wifi_board.PcbDoc",
}
EXPECTED_SOURCE_STEP_SHA256 = "d5b986879c1d5c39cb85711bb4704cc5b298ee0f85fb407d8342eff03776b41c"
IPC_NAMESPACE = "http://webstds.ipc.org/2581"


def _desktop() -> Path:
    return Path(__file__).resolve().parent


def _close(actual: object, expected: float, tolerance: float = 1e-3) -> bool:
    try:
        return abs(float(actual) - expected) <= tolerance
    except (TypeError, ValueError):
        return False


def _bool(actual: object, expected: bool) -> bool:
    if isinstance(actual, bool):
        return actual is expected
    if isinstance(actual, str):
        value = actual.strip().casefold()
        if value in {"true", "1", "yes"}:
            return expected is True
        if value in {"false", "0", "no"}:
            return expected is False
    return False


def _basename(value: object) -> str:
    text = str(value).strip().replace("/", "\\")
    return PureWindowsPath(text).name.casefold()


def _json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _panel_mapping_valid(value: object) -> bool:
    return (
        isinstance(value, dict)
        and value.get("rows") == EXPECTED["rows"]
        and value.get("columns") == EXPECTED["columns"]
        and _close(value.get("row_spacing_mil"), EXPECTED["row_spacing_mil"])
        and _close(value.get("column_spacing_mil"), EXPECTED["column_spacing_mil"])
        and _bool(value.get("mirror"), EXPECTED["mirror"])
        and value.get("origin_mode") == EXPECTED["origin_mode"]
    )


def _panel_summary_valid(path: Path) -> bool:
    try:
        value = _json(path)
        return (
            _panel_mapping_valid(value)
            and value.get("board_count") == EXPECTED["board_count"]
            and _basename(value.get("source")) == EXPECTED["source"].casefold()
            and value.get("software") == "Altium Designer 17.0.6"
        )
    except Exception:
        return False


def _panel_json_valid(path: Path) -> bool:
    try:
        value = _json(path)
        arrays = value.get("embedded_board_arrays") if isinstance(value, dict) else None
        ipc = value.get("ipc2581") if isinstance(value, dict) else None
        if not isinstance(arrays, list) or len(arrays) != 1 or not isinstance(ipc, dict):
            return False
        array = arrays[0]
        return (
            value.get("format") == "altium-designer-17-native-panel-evidence-v1"
            and _basename(value.get("native_file")) == "wifi_panel.pcbdoc"
            and _basename(value.get("source")) == EXPECTED["source"].casefold()
            and _panel_mapping_valid(array)
            and _basename(array.get("document_path")) == EXPECTED["source"].casefold()
            and _bool(array.get("child_board_loaded"), True)
            and ipc.get("revision") == "B"
            and ipc.get("native_extension") == ".cvg"
            and _basename(ipc.get("step_ref")) == "wifi_board"
            and ipc.get("nx") == 2
            and ipc.get("ny") == 3
            and _close(abs(float(ipc.get("dx_mm"))), 34.000001, 1e-5)
            and _close(abs(float(ipc.get("dy_mm"))), 28.800001, 1e-5)
            and _bool(ipc.get("mirror"), True)
        )
    except Exception:
        return False


def _ole_records(data: bytes) -> list[bytes] | None:
    records: list[bytes] = []
    offset = 0
    while offset < len(data):
        if len(data) - offset < 4:
            return records if not any(data[offset:]) else None
        size = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        if size == 0:
            return records if not any(data[offset:]) else None
        end = offset + size
        if end > len(data):
            return None
        records.append(data[offset:end])
        offset = end
    return records


def _parameter_record(data: bytes) -> dict[str, str]:
    text = data.decode("latin-1", errors="strict").strip("\x00")
    values: dict[str, str] = {}
    for item in text.split("|"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip().upper()
        if key:
            values[key] = value.strip()
    return values


def _mil(value: object) -> float:
    match = re.fullmatch(r"\s*([-+]?\d+(?:\.\d+)?)\s*mil\s*", str(value), re.IGNORECASE)
    if not match:
        raise ValueError("not a mil value")
    return float(match.group(1))


def _native_panel_valid(path: Path) -> bool:
    try:
        if not olefile.isOleFile(str(path)):
            return False
        with olefile.OleFileIO(str(path)) as document:
            stream = ["EmbeddedBoards6", "Data"]
            if not document.exists(stream):
                return False
            records = _ole_records(document.openstream(stream).read())
        if records is None or len(records) != 1:
            return False
        values = _parameter_record(records[0])
        return (
            _basename(values.get("DOCUMENTPATH")) == EXPECTED["source"].casefold()
            and values.get("ROWCOUNT") == "4"
            and values.get("COLCOUNT") == "3"
            and _close(_mil(values.get("ROWSPACING")), EXPECTED["row_spacing_mil"])
            and _close(_mil(values.get("COLSPACING")), EXPECTED["column_spacing_mil"])
            and _bool(values.get("MIRROR"), True)
            and values.get("ORIGINMODE") == "1"
        )
    except Exception:
        return False


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _canonical_xml(element: ET.Element) -> list[object]:
    children = [_canonical_xml(child) for child in element]
    children.sort(key=lambda child: json.dumps(child, separators=(",", ":"), ensure_ascii=True))
    return [
        _local_name(element.tag),
        sorted((str(key), str(value)) for key, value in element.attrib.items()),
        " ".join((element.text or "").split()),
        children,
    ]


def _source_step_digest(step: ET.Element) -> str:
    payload = json.dumps(
        _canonical_xml(step), separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _ipc_panel_valid(path: Path) -> bool:
    try:
        root = ET.parse(path).getroot()
        if (
            _local_name(root.tag) != "IPC-2581"
            or not root.tag.startswith("{" + IPC_NAMESPACE + "}")
            or root.get("revision") != "B"
        ):
            return False
        steps = {
            element.get("name"): element
            for element in root.iter()
            if _local_name(element.tag) == "Step" and element.get("name")
        }
        panel_step = steps.get("wifi_panel")
        source_step = steps.get("wifi_board")
        if panel_step is None or source_step is None:
            return False
        repeats = [
            element
            for element in panel_step.iter()
            if _local_name(element.tag) == "StepRepeat"
        ]
        if len(repeats) != 1:
            return False
        repeat = repeats[0]
        nx = int(repeat.get("nx", "-1"))
        ny = int(repeat.get("ny", "-1"))
        return (
            repeat.get("stepRef") == "wifi_board"
            and nx == 2
            and ny == 3
            and (nx + 1) * (ny + 1) == EXPECTED["board_count"]
            and _close(abs(float(repeat.get("dx", "nan"))), 34.000001, 1e-5)
            and _close(abs(float(repeat.get("dy", "nan"))), 28.800001, 1e-5)
            and _bool(repeat.get("mirror"), True)
            and _source_step_digest(source_step) == EXPECTED_SOURCE_STEP_SHA256
        )
    except Exception:
        return False


def evaluate() -> bool:
    desktop = _desktop()
    required = {
        "wifi_panel.PcbDoc",
        "wifi_panel.ipc2581",
        "wifi_panel.pcb.json",
        "panel_summary.json",
    }
    if not all((desktop / name).is_file() and (desktop / name).stat().st_size > 0 for name in required):
        return False
    return (
        _native_panel_valid(desktop / "wifi_panel.PcbDoc")
        and _ipc_panel_valid(desktop / "wifi_panel.ipc2581")
        and _panel_json_valid(desktop / "wifi_panel.pcb.json")
        and _panel_summary_valid(desktop / "panel_summary.json")
    )


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
