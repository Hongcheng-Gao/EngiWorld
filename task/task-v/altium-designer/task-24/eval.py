from __future__ import annotations

import argparse
import json
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
REQUIRED_NATIVE_MARKERS = (
    b"<Page",
    b"Fabrication",
    b"AssemblyDrawing",
    b"DrillTable",
    b"BOM",
)


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

    mods_path = output_dir / "mods.json"
    output = output_dir / "custom.PCBDwf"
    if not mods_path.is_file() or not output.is_file():
        return False
    try:
        mods = json.loads(mods_path.read_text(encoding="utf-8"))
        data = output.read_bytes()
    except (OSError, ValueError):
        return False

    if len(data) < 4096 or NATIVE_DOCUMENT_MARKER not in data:
        return False
    if data.count(b"</Document>") != 1:
        return False
    if any(marker not in data for marker in REQUIRED_NATIVE_MARKERS):
        return False

    expected_sheet_token = ("M" + mods["sheet_size"]).encode("ascii")
    expected_company = mods["company_name"].encode("utf-8")
    if expected_sheet_token not in data or expected_company.lower() not in data.lower():
        return False

    drill = mods.get("drill_table", {})
    linked_board = Path(drill.get("linked_board", "")).name.encode("utf-8")
    return bool(linked_board) and linked_board in data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?", default=str(DEFAULT_DESKTOP))
    args = parser.parse_args()
    print("True" if eval_outputs(Path(args.output_dir)) else "False")
