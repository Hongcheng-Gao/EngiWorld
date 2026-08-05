from __future__ import annotations

import base64
import csv
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

EXPECTED = {
  "fixes.json": "ewogICJEUkMwMDEiOiAicmV2aWV3ZWRfY2xlYXJhbmNlIiwKICAiRFJDMDAyIjogImFjY2VwdGVkX3NpbGtzY3JlZW5fd2FybmluZyIKfQo=",
  "gerbers.zip": "UEsDBBQAAAAIAPVs5VwMMhCWMAAAAC4AAAAKAAAAQk9UVE9NLmdicnM3MFFw8g8J8fdVcHcNcnINUnDzD1JISc3N51J1C/ZxjDAyiTQy0VLl8jUw0uICAFBLAwQUAAAACAD1bOVcbbxG/i0AAAArAAAABwAAAEdORC5nYnJzNzBRcPdzUXB3DXJyDVJw8w9SSEnNzedSdQv2cYwwMok0MtFS5fI1MNLiAgBQSwMEFAAAAAgA9WzlXEOMNpAtAAAALQAAAAkAAABQT1dFUi5nYnJzNzBRCPAPdw1ScHcNcgJSbv5BCimpuflcqm7BPo4RRiaRRiZaqly+BkZaXABQSwMEFAAAAAgA9WzlXGD4jJ8tAAAAKwAAAAcAAABUT1AuZ2JyczcwUQjxD1Bwdw1ycg1ScPMPUkhJzc3nUnUL9nGMMDKJNDLRUuXyNTDS4gIAUEsBAhQAFAAAAAgA9WzlXAwyEJYwAAAALgAAAAoAAAAAAAAAAAAAAIABAAAAAEJPVFRPTS5nYnJQSwECFAAUAAAACAD1bOVcbbxG/i0AAAArAAAABwAAAAAAAAAAAAAAgAFYAAAAR05ELmdiclBLAQIUABQAAAAIAPVs5VxDjDaQLQAAAC0AAAAJAAAAAAAAAAAAAACAAaoAAABQT1dFUi5nYnJQSwECFAAUAAAACAD1bOVcYPiMny0AAAArAAAABwAAAAAAAAAAAAAAgAH+AAAAVE9QLmdiclBLBQYAAAAABAAEANkAAABQAQAAAAA=",
  "photoplot.log": "R2VuZXJhdGVkIDQgR2VyYmVyIGZpbG1zOiBUT1AsIEJPVFRPTSwgR05ELCBQT1dFUgpObyBmYXRhbCBDQU0gZXJyb3JzLgo="
}


def _desktop() -> Path:
    return Path(__file__).resolve().parent


def _decode(name: str) -> bytes:
    return base64.b64decode(EXPECTED[name].encode("ascii"))


def _text(data: bytes) -> str:
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"


def _json_equal(path: Path, expected: bytes) -> bool:
    try:
        return json.loads(path.read_text(encoding="utf-8")) == json.loads(expected.decode("utf-8"))
    except Exception:
        return False


def _csv_equal(path: Path, expected: bytes) -> bool:
    try:
        actual_text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        expected_text = expected.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        actual_rows = [[cell.strip() for cell in row] for row in csv.reader(io.StringIO(actual_text)) if any(cell.strip() for cell in row)]
        expected_rows = [[cell.strip() for cell in row] for row in csv.reader(io.StringIO(expected_text)) if any(cell.strip() for cell in row)]
        if not actual_rows or not expected_rows:
            return actual_rows == expected_rows
        if actual_rows[0] != expected_rows[0]:
            return False
        return sorted(actual_rows[1:]) == sorted(expected_rows[1:])
    except Exception:
        return False


def _xml_equal(path: Path, expected: bytes) -> bool:
    try:
        actual_root = ET.parse(path).getroot()
        expected_root = ET.fromstring(expected)
    except Exception:
        return False

    def canon(elem):
        return (
            elem.tag,
            tuple(sorted((k, str(v)) for k, v in elem.attrib.items())),
            (elem.text or "").strip(),
            tuple(canon(child) for child in list(elem)),
        )

    return canon(actual_root) == canon(expected_root)



def _edif_equal(path: Path, expected: bytes) -> bool:
    try:
        def tokens(text: str):
            return re.findall(r'"[^"]*"|[()]|[^\s()]+', text)
        actual_text = path.read_text(encoding="utf-8-sig", errors="ignore")
        expected_text = expected.decode("utf-8", errors="ignore")
        return tokens(actual_text) == tokens(expected_text)
    except Exception:
        return False

def _zip_equal(path: Path, expected: bytes) -> bool:
    try:
        with zipfile.ZipFile(path) as actual, zipfile.ZipFile(io.BytesIO(expected)) as exp:
            if sorted(actual.namelist()) != sorted(exp.namelist()):
                return False
            for name in exp.namelist():
                actual_data = actual.read(name)
                expected_data = exp.read(name)
                suffix = Path(name).suffix.lower()
                if suffix in {".txt", ".log", ".gbr", ".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".drl", ".gm1", ".gml"}:
                    if _text(actual_data) != _text(expected_data):
                        return False
                elif actual_data != expected_data:
                    return False
        return True
    except Exception:
        return False


def _bytes_equal(path: Path, expected: bytes) -> bool:
    try:
        if path.suffix.lower() in {".json"}:
            return _json_equal(path, expected)
        if path.suffix.lower() in {".csv"}:
            return _csv_equal(path, expected)
        if path.suffix.lower() in {".ipc2581", ".xml"}:
            return _xml_equal(path, expected)
        if path.suffix.lower() in {".zip"}:
            return _zip_equal(path, expected)
        if path.suffix.lower() in {".edif"}:
            return _edif_equal(path, expected)
        return _text(path.read_bytes()) == _text(expected)
    except Exception:
        return False


def evaluate() -> bool:
    desktop = _desktop()
    for rel in EXPECTED:
        path = desktop / rel
        if not path.is_file():
            return False
        if not _bytes_equal(path, _decode(rel)):
            return False
    return True


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
