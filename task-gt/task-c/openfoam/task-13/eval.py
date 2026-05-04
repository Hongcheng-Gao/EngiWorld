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
    required = [
        "cylinder_fo/0/U",
        "cylinder_fo/constant/transportProperties",
        "cylinder_fo/system/controlDict",
        "summary.txt",
    ]
    if not check_required_files(root, required):
        return False

    avg_cl, avg_cd = parse_single_line_csv_numbers(root / "summary.txt", 2)
    if abs(avg_cl) > 0.5:
        return False
    if avg_cd <= 0.0:
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
