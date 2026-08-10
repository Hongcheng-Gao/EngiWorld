from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


SHARED_PARTS = {
    "C1", "C2", "C3", "C4", "C5", "C6", "D1", "IC1", "J1", "Q1", "R1", "U1"
}
SCH_ONLY = {
    "F1", "GND1", "GND2", "GND3", "GND4", "GND5", "GND6", "GND7",
    "GND8", "GND9", "GND10", "P+1", "P+2", "P+3", "P+4", "P+5", "P+6",
}
BRD_ONLY = {"X1"}


def _find_deliverable(root: Path) -> Path | None:
    for name in ("consistency_report.md", "answer.md"):
        cand = root / name
        if cand.exists():
            return cand
    return None


def _section(text: str, heading: str) -> str:
    pat = re.compile(rf"(?im)^#{{1,6}}\s*{re.escape(heading)}(?:\s*\([^)]*\))?\s*$")
    m = pat.search(text)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"(?m)^#{1,6}\s", rest)
    return text[m.start():m.end() + nxt.start()] if nxt else text[m.start():]


def _section_items(section: str) -> list[str]:
    items = []
    for line in section.splitlines():
        m = re.match(r"^\-\s*(\S+)", line.strip())
        if m:
            items.append(m.group(1))
    return items


def evaluate(submission_dir: str) -> bool:
    sub = Path(submission_dir).resolve()
    target = _find_deliverable(sub)
    if target is None:
        return False
    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = target.read_text(encoding="latin-1")
    if not text.strip():
        return False

    sections = {
        "parts_shared": _section(text, "parts_shared"),
        "parts_only_in_sch": _section(text, "parts_only_in_sch"),
        "parts_only_in_brd": _section(text, "parts_only_in_brd"),
        "value_mismatch": _section(text, "value_mismatch"),
        "package_mismatch": _section(text, "package_mismatch"),
    }
    if not all(sections.values()):
        return False

    if set(_section_items(sections["parts_shared"])) != SHARED_PARTS:
        return False
    if set(_section_items(sections["parts_only_in_sch"])) != SCH_ONLY:
        return False
    if set(_section_items(sections["parts_only_in_brd"])) != BRD_ONLY:
        return False
    if _section_items(sections["value_mismatch"]):
        return False
    if _section_items(sections["package_mismatch"]):
        return False
    if "X1" not in text:
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
