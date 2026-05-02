#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


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


def parse_csv_values(path: Path) -> list[str]:
    content = read_text(path).strip()
    if not content:
        return []
    return [p.strip() for p in content.split(",")]


def write_result(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"result": int(1 if value else 0)}, ensure_ascii=False) + "\n", encoding="utf-8")


def check_task(root: Path) -> bool:
    required = ["print.inp", "print.dat", "summary.txt"]
    for rel in required:
        if not is_nonempty_file(root / rel):
            return False

    parts = parse_csv_values(root / "summary.txt")
    if len(parts) < 4:
        return False

    try:
        u2 = float(parts[0])
        mises = float(parts[1])
        other_node_records = float(parts[2])
        other_element_records = float(parts[3])
    except (TypeError, ValueError):
        return False

    if abs(abs(u2) - 0.1905) / 0.1905 > 0.05:
        return False
    if abs(mises - 60.0) / 60.0 > 0.05:
        return False
    if other_node_records < 0 or other_element_records < 0:
        return False
    if abs(other_node_records - round(other_node_records)) > 1e-9:
        return False
    if abs(other_element_records - round(other_element_records)) > 1e-9:
        return False
    if int(round(other_node_records)) != 0:
        return False
    if int(round(other_element_records)) != 0:
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
    print("true" if result == 1 else "false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
