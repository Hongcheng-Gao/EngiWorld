from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


def _board_contactrefs(path: Path) -> list[tuple[str, str]]:
    root = ET.parse(path).getroot()
    refs: list[tuple[str, str]] = []
    for sig in root.findall(".//signal"):
        name = sig.get("name") or ""
        for cr in sig.findall("contactref"):
            refs.append((name, cr.get("element") or ""))
    return refs


def _ipc_records(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for line in text.splitlines():
        if not line.startswith("317"):
            continue
        m = re.match(r"^317\s*([^\s]+)\s+([^\s]+)", line)
        if not m:
            continue
        out.append((m.group(1), m.group(2)))
    return out


def evaluate(submission_dir: str) -> bool:
    sub = Path(submission_dir).resolve()
    target = None
    for name in ("board.ipc", "answer.ipc"):
        cand = sub / name
        if cand.exists():
            target = cand
            break
    if target is None:
        return False

    try:
        text = target.read_text(encoding="utf-8")
    except Exception:
        return False

    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    if not lines or not lines[0].startswith("C"):
        return False
    if not any(re.match(r"^P\s+JOB\b", ln) for ln in lines):
        return False
    if not any(re.match(r"^P\s+UNITS\b", ln) for ln in lines):
        return False
    if lines[-1] != "999":
        return False

    test_records = [ln for ln in lines if re.match(r"^317", ln)]
    if not test_records:
        return False
    for ln in test_records:
        if not re.search(r"D\s*\d+\s*A\d+", ln):
            return False

    brd = Path(__file__).resolve().parent / "init_file" / "board.brd"
    expected_refs = _board_contactrefs(brd)
    if len(test_records) != len(expected_refs):
        return False

    if Counter(_ipc_records(text)) != Counter(expected_refs):
        return False
    return True


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python eval.py SUBMISSION_DIR", file=sys.stderr)
        return 2
    ok = evaluate(argv[1])
    print("True" if ok else "False")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
