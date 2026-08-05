from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_DESKTOP = Path(r"C:\Users\user\Desktop")
FORBIDDEN_SCRIPT_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr",
}
NATIVE_DOCUMENT_MARKER = (
    b'<Document xmlns="http://schemas.datacontract.org/2004/07/'
    b'Altium.Designer.PcbDrawing.DataSerialization.V1"'
)
REQUIRED_NATIVE_MARKERS = {
    b"<Page": 1,
    b"BoardSourceName": 1,
    b"Fabrication": 1,
    b"DrillTable": 1,
    b"Legend": 1,
    b"AssemblyDrawing": 2,
    b"BOM": 1,
    b"Notes": 1,
    b"Revision": 1,
    b"Title": 1,
}


def _has_unexpected_script(root: Path) -> bool:
    try:
        for path in root.rglob("*"):
            if not path.is_file() or path.name.lower() == "eval.py":
                continue
            if path.suffix.lower() in FORBIDDEN_SCRIPT_EXTENSIONS:
                return True
    except OSError:
        return True
    return False


def eval_outputs(output_dir: Path) -> bool:
    output_dir = Path(output_dir).resolve()
    if _has_unexpected_script(output_dir):
        return False

    output = output_dir / "release.PCBDwf"
    if not output.is_file():
        return False
    try:
        data = output.read_bytes()
    except OSError:
        return False

    if len(data) < 4096 or NATIVE_DOCUMENT_MARKER not in data:
        return False
    if data.count(b"</Document>") != 1:
        return False
    return all(data.count(marker) >= count for marker, count in REQUIRED_NATIVE_MARKERS.items())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?", default=str(DEFAULT_DESKTOP))
    args = parser.parse_args()
    print("True" if eval_outputs(Path(args.output_dir)) else "False")
