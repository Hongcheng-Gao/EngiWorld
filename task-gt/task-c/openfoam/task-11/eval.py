#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?$")


def is_result_artifact(path: Path) -> bool:
    name = path.name.lower()
    return (
        any(k in name for k in ("summary", "result", "report", "diagnosis"))
        or path.suffix.lower() in {".txt", ".csv", ".xy", ".result"}
    )


def is_nonempty_file(path: Path) -> bool:
    if not is_result_artifact(path):
        return True
    return path.exists() and path.is_file() and path.stat().st_size > 0


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_number(token: str) -> float:
    s = token.strip()
    if not NUMBER_RE.fullmatch(s):
        raise ValueError(f"not a plain float token: {token!r}")
    return float(s)


def parse_single_line_csv_numbers(path: Path, expected_len: int) -> list[float]:
    lines = [
        ln.strip()
        for ln in read_text(path).splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    if len(lines) != 1:
        raise ValueError("summary must contain exactly one non-comment data line")
    parts = [p.strip() for p in lines[0].split(",")]
    if len(parts) != expected_len:
        raise ValueError(f"expected {expected_len} columns, got {len(parts)}")
    return [parse_number(p) for p in parts]


def check_required_files(root: Path, required: list[str]) -> bool:
    for rel in required:
        if not is_nonempty_file(root / rel):
            return False
    return True


def is_numeric_dirname(name: str) -> bool:
    try:
        float(name)
    except (TypeError, ValueError):
        return False
    return True


def write_result(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"result": int(1 if value else 0)}, ensure_ascii=False) + "\n", encoding="utf-8")

def check_task(root: Path) -> bool:
    summary = root / "summary.txt"
    if not is_nonempty_file(summary):
        return False

    records: dict[float, float] = {}
    for raw in read_text(summary).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 2:
            return False
        re_val = parse_number(parts[0])
        center_ux = parse_number(parts[1])
        records[re_val] = center_ux

    if len(records) < 3:
        return False

    re_vals = sorted(records.keys())
    ux_vals = [records[r] for r in re_vals]
    if max(ux_vals) - min(ux_vals) < 0.01:
        return False
    return True

def evaluate() -> int:
    root = Path("/home/user/Desktop")
    try:
        ok = check_task(root)
    except Exception:
        ok = False
    return 1 if ok else 0


def main() -> int:
    result = evaluate()
    print("True" if result == 1 else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
