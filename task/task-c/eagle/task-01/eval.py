from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


INIT_BRD_NAME = "mystery.brd"


def _locate_init_board(start: Path) -> Path | None:
    for cand in (
        start / INIT_BRD_NAME,
        start / "init_file" / INIT_BRD_NAME,
        start.parent / "init_file" / INIT_BRD_NAME,
        start.parent.parent / "init_file" / INIT_BRD_NAME,
    ):
        if cand.exists():
            return cand
    return None


def _expected_signals(brd_path: Path) -> list[tuple[str, list[tuple[str, str]]]]:
    root = ET.parse(brd_path).getroot()
    out: list[tuple[str, list[tuple[str, str]]]] = []
    for sig in root.findall(".//signal"):
        name = sig.get("name") or ""
        refs = [(cr.get("element") or "", cr.get("pad") or "") for cr in sig.findall("contactref")]
        out.append((name, refs))
    return out


def _parse_netlist(text: str, signal_names: list[str]) -> list[tuple[str, list[tuple[str, str]]]]:
    sections: list[tuple[str, list[tuple[str, str]]]] = []
    current_name: str | None = None
    current_refs: list[tuple[str, str]] = []
    ordered_names = sorted(signal_names, key=len, reverse=True)
    ref_pat = re.compile(
        r"([A-Za-z0-9_+$./-]+)(?:\s+|\s*\.\s*)([A-Za-z0-9_+$./-]+|[+-])(?=$|\s|[,\);])"
    )

    def flush() -> None:
        nonlocal current_name, current_refs
        if current_name is not None:
            sections.append((current_name, current_refs))
        current_name = None
        current_refs = []

    def collect_refs(fragment: str) -> None:
        nonlocal current_refs
        for match in ref_pat.finditer(fragment):
            current_refs.append((match.group(1), match.group(2)))

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("Netlist") or line.startswith("Exported from") or line.startswith("EAGLE Version"):
            continue
        if line.startswith("Net") and "Part" in line and "Pad" in line:
            continue

        matched = None
        for name in ordered_names:
            if re.match(rf"^{re.escape(name)}(?:\s|$)", line):
                matched = name
                break

        if matched is not None:
            flush()
            current_name = matched
            collect_refs(line[len(matched):])
            continue

        if current_name is not None:
            collect_refs(line)

    flush()
    return sections


def evaluate(submission_dir: str) -> bool:
    sub = Path(submission_dir).resolve()
    target = None
    for name in ("mystery_netlist.txt",):
        cand = sub / name
        if cand.is_file():
            target = cand
            break
    if target is None:
        return False

    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = target.read_text(encoding="latin-1")
    if not text.strip():
        return False

    brd = _locate_init_board(Path(__file__).resolve().parent)
    if brd is None:
        return False

    expected = _expected_signals(brd)
    actual = _parse_netlist(text, [name for name, _ in expected])

    if {name for name, _ in actual} != {name for name, _ in expected}:
        return False

    expected_map = {name: Counter(refs) for name, refs in expected}
    actual_map = {name: Counter(refs) for name, refs in actual}
    if set(actual_map) != set(expected_map):
        return False
    for name, exp_refs in expected_map.items():
        if actual_map.get(name) != exp_refs:
            return False
    return True


def main(argv: list[str]) -> int:
    if len(argv) > 2:
        print("usage: python eval.py SUBMISSION_DIR", file=sys.stderr)
        return 2
    submission_dir = argv[1] if len(argv) == 2 else Path(__file__).resolve().parent
    ok = evaluate(submission_dir)
    print("True" if ok else "False")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
